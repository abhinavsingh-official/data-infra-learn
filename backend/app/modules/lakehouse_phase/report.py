"""Module 19 rewrite of Module 10.4's lakehouse-phase grading report
generator, now against the session's own Spark session object instead
of DuckDB + the `deltalake` Python library. Reuses grading.report.
grade_clean_transactions directly for the required-output contract and
ground truth (unchanged - engine-agnostic), plus the same three
lakehouse-specific structural checks as before: is this a real Delta
table, does its history show genuine incremental commits, and does time
travel actually work (an earlier version doesn't leak later batches'
rows)."""

import polars as pl

from app.core.db import get_admin_connection
from app.modules.grading.report import Finding, GradingReport, grade_clean_transactions
from app.modules.lakehouse_phase.remediation import REMEDIATION as LAKEHOUSE_REMEDIATION

_CLEAN_TRANSACTIONS_SCHEMA = {
    "event_id": pl.Utf8,
    "amount": pl.Float64,
    "merchant": pl.Utf8,
    "currency": pl.Utf8,
    "event_timestamp": pl.Datetime,
}


def _make_finding(error_code: str, detail: str) -> Finding:
    text = LAKEHOUSE_REMEDIATION[error_code]
    return Finding(error_code=error_code, event_id="*", detail=detail, **text)


def _fetch_clean_transactions(session_spark) -> pl.DataFrame:
    rows = session_spark.sql(
        "SELECT event_id, amount, merchant, currency, event_timestamp FROM clean_transactions"
    ).collect()
    if not rows:
        return pl.DataFrame(schema=_CLEAN_TRANSACTIONS_SCHEMA)
    return pl.DataFrame([row.asDict() for row in rows], schema=_CLEAN_TRANSACTIONS_SCHEMA, orient="row")


def _check_time_travel(session_spark, findings: list[Finding]) -> None:
    """Reads the Delta table at the version recorded right after its
    FIRST commit (always version 0 - the platform's own commit_batch()
    always writes with mode='append', and the first append to a
    not-yet-existing table is version 0, confirmed directly) and checks
    it contains only event ids that genuinely had a row in batch_1_events,
    per the ground truth this phase itself controls (id % 2 = 0), not
    inferred from the user's own submission.

    Deliberately NOT "any event id that also has an id % 2 = 1 row is
    leaked" - some real event ids have duplicate-delivery rows spanning
    BOTH batches. Those legitimately belong in version 0, since they
    genuinely had a batch-1 row too (same reasoning as the original
    DuckDB version of this check - re-verified on this engine, not
    assumed to still hold)."""
    try:
        version_0_ids = {
            row["event_id"] for row in session_spark.sql("SELECT event_id FROM clean_transactions VERSION AS OF 0").collect()
        }
    except Exception:  # noqa: BLE001 - no version 0 at all, already covered by the "not a real Delta table" check
        return

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


def grade_submission(session_spark) -> GradingReport:
    lakehouse_findings: list[Finding] = []
    table_exists = session_spark.catalog.tableExists("clean_transactions")

    if not table_exists:
        lakehouse_findings.append(_make_finding("ERR_LAKEHOUSE_NOT_DELTA", "clean_transactions table doesn't exist."))
    else:
        history = session_spark.sql("DESCRIBE HISTORY clean_transactions").collect()
        # No operation-name filtering here (unlike the original DuckDB
        # version's "count WRITE ops") - confirmed directly that Spark's
        # own history labels the very first write "CREATE TABLE AS
        # SELECT", not "WRITE", when saveAsTable creates the table on its
        # first call. Every history row is a real commit either way, so
        # counting all of them is both simpler and correct.
        if len(history) < 2:
            lakehouse_findings.append(
                _make_finding(
                    "ERR_LAKEHOUSE_NOT_INCREMENTAL", f"{len(history)} commit(s) in history, expected at least 2."
                )
            )
        _check_time_travel(session_spark, lakehouse_findings)

    clean_df = _fetch_clean_transactions(session_spark) if table_exists else pl.DataFrame(schema=_CLEAN_TRANSACTIONS_SCHEMA)
    report = grade_clean_transactions(clean_df)
    report.structural_findings = lakehouse_findings + report.structural_findings
    return report
