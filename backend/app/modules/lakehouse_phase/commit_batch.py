"""The Delta-write mechanism for the lakehouse phase. The user submits a
SELECT; the platform, not user code, commits its result as a real Delta
transaction - kept platform-mediated so the grading's commit-history
check (COMMIT 1 is a fresh CREATE, COMMIT 2 is an append) is guaranteed
server-side rather than trusting every possible student query shape."""

from dataclasses import dataclass

from app.core.spark_sessions import contains_multiple_statements
from app.modules.lakehouse_phase.session_provisioning import session_lock

REQUIRED_COLUMNS = ["event_id", "amount", "merchant", "currency", "event_timestamp"]


@dataclass
class CommitResult:
    success: bool
    version: int | None = None
    row_count: int | None = None
    error_code: str | None = None
    error_message: str | None = None


def commit_batch(session_spark, session_id: str, sql_text: str) -> CommitResult:
    """Commits the submitted SELECT's entire result as one atomic Delta
    append - not routed through execute_spark_submission, which caps
    results at 1000 rows for interactive previews and would silently
    truncate a real ~25,000-row batch."""
    if contains_multiple_statements(sql_text):
        return CommitResult(success=False, error_code="MULTIPLE_STATEMENTS", error_message="Submit one SELECT per request.")

    stripped = sql_text.strip().upper()
    if not (stripped.startswith("SELECT") or stripped.startswith("WITH")):
        return CommitResult(
            success=False,
            error_code="NOT_A_SELECT",
            error_message="A batch commit must be a SELECT - the platform commits its result, not arbitrary DDL/DML.",
        )

    with session_lock(session_id):
        try:
            df = session_spark.sql(sql_text)
        except Exception as e:  # noqa: BLE001 - a bad submission comes back structured, never crashes
            return CommitResult(success=False, error_code=type(e).__name__, error_message=str(e).strip())

        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            return CommitResult(
                success=False,
                error_code="MISSING_REQUIRED_COLUMNS",
                error_message=f"Missing required column(s): {missing}. Expected: {REQUIRED_COLUMNS}.",
            )

        try:
            df = df.select("event_id", "amount", "merchant", "currency", "event_timestamp")
            row_count = df.count()
            # saveAsTable on every commit races even under session_lock -
            # sequential calls against a not-yet-existing table can see a
            # half-registered catalog entry left by the prior call.
            # insertInto after the first commit avoids that path entirely.
            if session_spark.catalog.tableExists("clean_transactions"):
                df.write.format("delta").mode("append").insertInto("clean_transactions")
            else:
                df.write.format("delta").mode("append").saveAsTable("clean_transactions")
        except Exception as e:  # noqa: BLE001 - Delta's schema enforcement rejects an incompatible batch
            return CommitResult(success=False, error_code=type(e).__name__, error_message=str(e).strip())

        history = session_spark.sql("DESCRIBE HISTORY clean_transactions").collect()
        version = max(row["version"] for row in history)
        return CommitResult(success=True, version=version, row_count=row_count)
