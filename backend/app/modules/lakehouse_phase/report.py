"""Module 10.4: the lakehouse-phase grading report generator. Reuses
grading.report.grade_clean_transactions directly for the required-output
contract and ground truth (the third phase to do so - Module 9 was the
second) and adds three lakehouse-specific structural checks: is this a
real Delta table, does its history show genuine incremental commits, and
does time travel actually work (an earlier version doesn't leak later
batches' rows)."""

import duckdb
import polars as pl
from deltalake import DeltaTable

from app.core.db import get_admin_connection
from app.modules.grading.report import Finding, GradingReport, grade_clean_transactions
from app.modules.lakehouse_phase.remediation import REMEDIATION as LAKEHOUSE_REMEDIATION
from app.modules.lakehouse_phase.session_provisioning import delta_table_dir


def _make_finding(error_code: str, detail: str) -> Finding:
    text = LAKEHOUSE_REMEDIATION[error_code]
    return Finding(error_code=error_code, event_id="*", detail=detail, **text)


def _is_real_delta_table(session_id: str) -> bool:
    return (delta_table_dir(session_id) / "_delta_log").is_dir()


def _fetch_clean_transactions(session_id: str) -> pl.DataFrame:
    con = duckdb.connect(":memory:")
    try:
        result = con.execute(
            f"SELECT event_id, amount, merchant, currency, event_timestamp "
            f"FROM delta_scan('{delta_table_dir(session_id)}')"
        )
        columns = [d[0] for d in result.description]
        rows = result.fetchall()
    finally:
        con.close()
    if not rows:
        return pl.DataFrame(
            schema={"event_id": pl.Utf8, "amount": pl.Float64, "merchant": pl.Utf8, "currency": pl.Utf8, "event_timestamp": pl.Datetime}
        )
    return pl.DataFrame(rows, schema=columns, orient="row")


def _check_time_travel(session_id: str, findings: list[Finding]) -> None:
    """Reads the Delta table at the version recorded right after its
    FIRST commit (always version 0 - confirmed directly: the platform's
    own commit_batch() always writes with mode='append', and the first
    append to a not-yet-existing table is version 0) and checks it
    contains only event ids that genuinely had a row in batch_1_events,
    per the ground truth this phase itself controls (id % 2 = 0), not
    inferred from the user's own submission.

    Deliberately NOT "any event id that also has an id % 2 = 1 row is
    leaked" - some real event ids have duplicate-delivery rows spanning
    BOTH batches (confirmed directly: several event_ids have rows with
    both id % 2 = 0 and id % 2 = 1). Those legitimately belong in version
    0, since they genuinely had a batch-1 row too - flagging them as
    "leaked" was a real bug in this check itself, found by grading a
    real two-batch submission and seeing an unexpected finding."""
    con = duckdb.connect(":memory:")
    try:
        version_0_ids = {
            row[0]
            for row in con.execute(
                f"SELECT event_id FROM delta_scan('{delta_table_dir(session_id)}', version=0)"
            ).fetchall()
        }
    except duckdb.Error:
        return  # no version 0 at all - already covered by the "not a real Delta table" check
    finally:
        con.close()

    if not version_0_ids:
        return  # empty first commit - nothing to check leakage against

    with get_admin_connection() as pg_conn:
        with pg_conn.cursor() as cur:
            cur.execute("SELECT DISTINCT payload->>'event_id' FROM raw_transaction_events WHERE id % 2 = 0")
            batch_1_eligible_ids = {row[0] for row in cur.fetchall() if row[0] is not None}

    leaked = version_0_ids - batch_1_eligible_ids
    if leaked:
        findings.append(
            _make_finding(
                "ERR_LAKEHOUSE_TIME_TRAVEL_INCORRECT",
                f"{len(leaked)} event(s) visible at version 0 with no batch-1 row at all, e.g. {sorted(leaked)[:3]}.",
            )
        )


def grade_submission(session_id: str) -> GradingReport:
    lakehouse_findings: list[Finding] = []

    if not _is_real_delta_table(session_id):
        lakehouse_findings.append(_make_finding("ERR_LAKEHOUSE_NOT_DELTA", "No _delta_log directory found."))
    else:
        dt = DeltaTable(str(delta_table_dir(session_id)))
        write_ops = [h for h in dt.history() if h.get("operation") == "WRITE"]
        if len(write_ops) < 2:
            lakehouse_findings.append(
                _make_finding("ERR_LAKEHOUSE_NOT_INCREMENTAL", f"{len(write_ops)} WRITE operation(s) in history, expected at least 2.")
            )
        _check_time_travel(session_id, lakehouse_findings)

    clean_df = _fetch_clean_transactions(session_id)
    report = grade_clean_transactions(clean_df)
    report.structural_findings = lakehouse_findings + report.structural_findings
    return report
