"""Module 5.3: the grading report generator. Runs pandera's structural
checks plus per-fault-type checks (see MODULE_5_PLAN.md for exactly what
each checks and why some are presence/plausibility rather than
exact-match), and attaches the hand-authored remediation text to every
failure - never just a pass/fail."""

from dataclasses import dataclass, field
from typing import Any

import pandera.polars as pa
import polars as pl
import psycopg
from psycopg.rows import dict_row

from app.core.config import get_settings
from app.core.db import get_admin_connection
from app.modules.grading.remediation import REMEDIATION
from app.modules.grading.schema import CLEAN_TRANSACTIONS_SCHEMA


@dataclass
class Finding:
    error_code: str
    event_id: str
    detail: str
    why: str
    fix: str
    tradeoffs: str


@dataclass
class GradingReport:
    total_clean_rows: int
    structural_findings: list[Finding] = field(default_factory=list)
    fault_findings: list[Finding] = field(default_factory=list)
    fault_type_summary: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return not self.structural_findings and not self.fault_findings


def _make_finding(error_code: str, event_id: str, detail: str) -> Finding:
    text = REMEDIATION.get(
        error_code, {"why": "Unrecognized error code.", "fix": "N/A", "tradeoffs": "N/A"}
    )
    return Finding(error_code=error_code, event_id=event_id, detail=detail, **text)


def _fetch_clean_transactions(role: str, password: str) -> pl.DataFrame:
    settings = get_settings()
    dsn = f"postgresql://{role}:{password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    with psycopg.connect(dsn) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # amount::float8 explicitly - Postgres NUMERIC comes back as
            # Python Decimal via psycopg, and polars keeps that dtype
            # rather than auto-casting to Float64, which made pandera's
            # float check fail on entirely legitimate data. Found by
            # running this against a real submission, not assumed.
            cur.execute(
                "SELECT event_id, amount::float8 AS amount, merchant, currency, event_timestamp FROM clean_transactions"
            )
            rows = cur.fetchall()
    if not rows:
        return pl.DataFrame(
            schema={"event_id": pl.Utf8, "amount": pl.Float64, "merchant": pl.Utf8, "currency": pl.Utf8, "event_timestamp": pl.Datetime}
        )
    return pl.DataFrame(rows)


def _fetch_ground_truth() -> list[dict[str, Any]]:
    """Admin connection deliberately - the grader is a trusted process
    and needs the answer key the user's own session role can't see."""
    with get_admin_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT f.fault_type, f.error_code, r.payload->>'event_id' AS event_id
                FROM injected_fault_log f
                JOIN raw_transaction_events r ON f.raw_event_id = r.id
                WHERE r.payload ? 'event_id'
                """
            )
            return cur.fetchall()


def _check_fault(fault_type: str, event_id: str, clean_by_event_id: dict[str, dict]) -> Finding | None:
    row = clean_by_event_id.get(event_id)

    if fault_type == "null_required_field":
        if row is not None and any(row.get(f) is None for f in ("amount", "merchant", "currency", "event_timestamp")):
            return _make_finding("ERR_NULL_REQUIRED_FIELD", event_id, "Clean row exists but still has a null field.")
    elif fault_type == "duplicate_delivery":
        pass  # uniqueness is enforced structurally by the pandera schema check
    elif fault_type == "late_arrival":
        if row is None:
            return _make_finding("ERR_LATE_ARRIVAL", event_id, "Event is missing from clean_transactions entirely.")
    elif fault_type == "schema_drift_added_field":
        if row is None or row.get("amount") is None:
            return _make_finding("ERR_SCHEMA_DRIFT_ADDED_FIELD", event_id, "Event missing or amount not parsed.")
    elif fault_type == "schema_drift_renamed_field":
        if row is None or row.get("merchant") is None:
            return _make_finding("ERR_SCHEMA_DRIFT_RENAMED_FIELD", event_id, "merchant is null - the rename wasn't re-mapped.")
    elif fault_type == "schema_drift_type_change":
        if row is None or row.get("amount") is None or row["amount"] <= 0:
            return _make_finding("ERR_SCHEMA_DRIFT_TYPE_CHANGE", event_id, "amount missing or non-positive after conversion.")
    elif fault_type == "malformed_excel_corruption":
        if row is None:
            return _make_finding("ERR_MALFORMED_EXCEL_CORRUPTION", event_id, "Event is missing from clean_transactions entirely.")
    elif fault_type == "malformed_ambiguous_date":
        if row is None or row.get("event_timestamp") is None:
            return _make_finding("ERR_MALFORMED_AMBIGUOUS_DATE", event_id, "event_timestamp is null or event missing.")
    return None


# Maps pandera's actual check names (confirmed by testing directly, not
# guessed - "not_nullable" and "field_uniqueness" are pandera's real
# names) to the remediation entry that's actually relevant. A uniqueness
# violation IS the duplicate-delivery problem, so mapping it to
# "UNKNOWN" (found while testing a real bad submission) gave useless
# generic text instead of the real fix.
_PANDERA_CHECK_TO_ERROR_CODE = {
    "not_nullable": "ERR_NULL_REQUIRED_FIELD",
    "field_uniqueness": "ERR_DUPLICATE_DELIVERY",
}


def _error_code_for_pandera_check(check_name: str) -> str:
    for prefix, error_code in _PANDERA_CHECK_TO_ERROR_CODE.items():
        if check_name.startswith(prefix):
            return error_code
    return "ERR_SCHEMA_DRIFT_TYPE_CHANGE"  # e.g. greater_than(0) failing - most often a bad type conversion


def grade_clean_transactions(clean_df: pl.DataFrame) -> GradingReport:
    """The reusable core: structural (pandera) + per-fault-type checks
    against the real ground truth, given an already-fetched
    clean_transactions dataframe. Deliberately has no opinion on WHERE
    clean_df came from - Module 5 (postgres_phase) fetches it via a
    session's Postgres role; Module 9 (lake_phase) fetches the identical
    contract from a DuckDB file instead. The required-output shape and
    the ground truth (injected_fault_log) are the same either way, so
    this logic is shared rather than reimplemented a second time."""
    report = GradingReport(total_clean_rows=clean_df.height)

    if clean_df.height > 0:
        try:
            CLEAN_TRANSACTIONS_SCHEMA.validate(clean_df, lazy=True)
        except pa.errors.SchemaErrors as e:
            for row in e.failure_cases.iter_rows(named=True):
                report.structural_findings.append(
                    _make_finding(
                        _error_code_for_pandera_check(str(row.get("check", ""))),
                        str(row.get("failure_case")),
                        f"pandera check '{row.get('check')}' failed on column '{row.get('column')}'",
                    )
                )

    clean_by_event_id = {r["event_id"]: r for r in clean_df.to_dicts()} if clean_df.height > 0 else {}
    ground_truth = _fetch_ground_truth()

    for entry in ground_truth:
        fault_type = entry["fault_type"]
        summary = report.fault_type_summary.setdefault(fault_type, {"total": 0, "issues": 0})
        summary["total"] += 1
        finding = _check_fault(fault_type, entry["event_id"], clean_by_event_id)
        if finding:
            summary["issues"] += 1
            report.fault_findings.append(finding)

    return report


def grade_submission(role: str, password: str) -> GradingReport:
    clean_df = _fetch_clean_transactions(role, password)
    return grade_clean_transactions(clean_df)
