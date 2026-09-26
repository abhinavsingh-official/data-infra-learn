"""Module 9.4: the lake-phase grading report generator. Reuses
grading.report.grade_clean_transactions directly for the required-output
contract and ground truth (identical to Module 5's, since the task
deliberately asks for the same clean_transactions shape) and adds two
lake-specific structural checks on top: was the output genuinely
partitioned, and was payload actually deferred to read time rather than
flattened at write time."""

import duckdb
import polars as pl

from app.core.duckdb_sessions import attach_postgres_source
from app.modules.grading.report import Finding, GradingReport, grade_clean_transactions
from app.modules.lake_phase.remediation import REMEDIATION as LAKE_REMEDIATION
from app.modules.lake_phase.session_provisioning import open_session_db, output_dir, pg_role_name


def _make_lake_finding(error_code: str, detail: str) -> Finding:
    text = LAKE_REMEDIATION[error_code]
    return Finding(error_code=error_code, event_id="*", detail=detail, **text)


def _check_partitioning(session_id: str) -> Finding | None:
    partition_dirs = [p for p in output_dir(session_id).iterdir() if p.is_dir() and p.name.startswith("event_date=")]
    if len(partition_dirs) <= 1:
        return _make_lake_finding(
            "ERR_LAKE_NOT_PARTITIONED", f"{len(partition_dirs)} event_date= partition folder(s) found, expected many."
        )
    return None


def _check_not_preflattened(session_id: str) -> Finding | None:
    sample_file = next(output_dir(session_id).rglob("*.parquet"), None)
    if sample_file is None:
        return None  # no files at all - _check_partitioning already covers this case
    con = duckdb.connect(":memory:")
    try:
        columns = {row[0] for row in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{sample_file}')").fetchall()}
    finally:
        con.close()
    if "payload" not in columns:
        return _make_lake_finding(
            "ERR_LAKE_PAYLOAD_PREFLATTENED", f"Written Parquet columns: {sorted(columns)} - no payload column."
        )
    return None


def _table_exists(con: duckdb.DuckDBPyConnection, table: str) -> bool:
    return bool(
        con.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = ? AND table_schema = 'main'", [table]
        ).fetchone()
    )


def _fetch_clean_transactions(session_id: str, pg_role: str, pg_password: str) -> pl.DataFrame:
    con = open_session_db(session_id)
    try:
        attach_postgres_source(con, pg_role, pg_password)
        if not _table_exists(con, "clean_transactions"):
            return pl.DataFrame(
                schema={"event_id": pl.Utf8, "amount": pl.Float64, "merchant": pl.Utf8, "currency": pl.Utf8, "event_timestamp": pl.Datetime}
            )
        result = con.execute("SELECT event_id, amount, merchant, currency, event_timestamp FROM clean_transactions")
        columns = [d[0] for d in result.description]
        rows = result.fetchall()
    finally:
        con.close()
    if not rows:
        return pl.DataFrame(
            schema={"event_id": pl.Utf8, "amount": pl.Float64, "merchant": pl.Utf8, "currency": pl.Utf8, "event_timestamp": pl.Datetime}
        )
    return pl.DataFrame(rows, schema=columns, orient="row")


def grade_submission(session_id: str, pg_password: str) -> GradingReport:
    lake_findings: list[Finding] = []
    partition_finding = _check_partitioning(session_id)
    if partition_finding:
        lake_findings.append(partition_finding)
    preflattened_finding = _check_not_preflattened(session_id)
    if preflattened_finding:
        lake_findings.append(preflattened_finding)

    clean_df = _fetch_clean_transactions(session_id, pg_role_name(session_id), pg_password)
    report = grade_clean_transactions(clean_df)
    report.structural_findings = lake_findings + report.structural_findings
    return report
