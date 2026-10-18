"""Lake-phase grading - reuses grading.report.grade_clean_transactions
for the ground truth, plus two lake-specific checks: is the output
actually partitioned, and is payload deferred to read time rather than
flattened at write time."""

import polars as pl

from app.modules.grading.report import Finding, GradingReport, grade_clean_transactions
from app.modules.lake_phase.remediation import REMEDIATION as LAKE_REMEDIATION
from app.modules.lake_phase.session_provisioning import output_dir

_CLEAN_TRANSACTIONS_SCHEMA = {
    "event_id": pl.Utf8,
    "amount": pl.Float64,
    "merchant": pl.Utf8,
    "currency": pl.Utf8,
    "event_timestamp": pl.Datetime,
}


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


def _check_not_preflattened(session_spark, session_id: str) -> Finding | None:
    sample_file = next(output_dir(session_id).rglob("*.parquet"), None)
    if sample_file is None:
        return None  # no files at all - _check_partitioning already covers this case
    columns = set(session_spark.read.parquet(str(sample_file)).columns)
    if "payload" not in columns:
        return _make_lake_finding(
            "ERR_LAKE_PAYLOAD_PREFLATTENED", f"Written Parquet columns: {sorted(columns)} - no payload column."
        )
    return None


def _fetch_clean_transactions(session_spark) -> pl.DataFrame:
    if not session_spark.catalog.tableExists("clean_transactions"):
        return pl.DataFrame(schema=_CLEAN_TRANSACTIONS_SCHEMA)
    rows = session_spark.sql(
        "SELECT event_id, amount, merchant, currency, event_timestamp FROM clean_transactions"
    ).collect()
    if not rows:
        return pl.DataFrame(schema=_CLEAN_TRANSACTIONS_SCHEMA)
    return pl.DataFrame([row.asDict() for row in rows], schema=_CLEAN_TRANSACTIONS_SCHEMA, orient="row")


def grade_submission(session_spark, session_id: str) -> GradingReport:
    lake_findings: list[Finding] = []
    partition_finding = _check_partitioning(session_id)
    if partition_finding:
        lake_findings.append(partition_finding)
    preflattened_finding = _check_not_preflattened(session_spark, session_id)
    if preflattened_finding:
        lake_findings.append(preflattened_finding)

    clean_df = _fetch_clean_transactions(session_spark)
    report = grade_clean_transactions(clean_df)
    report.structural_findings = lake_findings + report.structural_findings
    return report
