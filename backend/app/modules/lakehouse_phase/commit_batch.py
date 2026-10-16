"""The Delta-write mechanism for the lakehouse phase, built on real
PySpark/Delta. The user only ever submits a SELECT (their own
edge-case-handling logic, same intellectual work as every other phase's
task) - the platform, not user code, commits that query's result as a
real Delta transaction via Spark's own DataFrameWriter.

This isn't forced by a hard technical limit - Spark/Delta SQL can write
Delta tables directly via `INSERT INTO ... USING DELTA`, so a student
could in principle write the commit themselves in plain SQL. It's kept
platform-mediated because it's the one real ACID-commit-history check
this phase's grading depends on (COMMIT 1 is always a fresh CREATE,
COMMIT 2 is always an append - see report.py's time-travel check), and
that's cleaner to guarantee server-side than to trust every possible
student query shape to preserve it."""

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
    """Runs the submitted SELECT via Spark and commits its *entire*
    result as one atomic Delta `append` write. This is deliberately not
    routed through execute_spark_submission, which caps results at 1000
    rows for interactive previews - a real batch here is ~25,000 rows,
    and capping it the same way would silently commit a truncated batch
    instead of the real one. execute() and commit_batch() look like they
    should share the same plumbing but can't: one is for looking at
    data, the other is for writing all of it."""
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
        except Exception as e:  # noqa: BLE001 - same resilience contract as execute(): a bad
            # submission comes back structured, never crashes the request.
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
            # saveAsTable every time (not just on the first commit) races
            # under concurrent calls even when fully serialized by
            # session_lock above: sequential saveAsTable calls against the
            # same not-yet-existing table name can intermittently see a
            # half-registered catalog entry (schema struct<>) left by a
            # prior call. insertInto for every commit after the first
            # avoids the table-creation path entirely, since there's
            # nothing left to race on.
            if session_spark.catalog.tableExists("clean_transactions"):
                df.write.format("delta").mode("append").insertInto("clean_transactions")
            else:
                df.write.format("delta").mode("append").saveAsTable("clean_transactions")
        except Exception as e:  # noqa: BLE001
            # Delta's own schema enforcement is what rejects an incompatible batch here
            # (e.g. amount not castable against the existing table's type) - same resilience
            # contract as execute(): never a crash, always a structured result.
            return CommitResult(success=False, error_code=type(e).__name__, error_message=str(e).strip())

        history = session_spark.sql("DESCRIBE HISTORY clean_transactions").collect()
        version = max(row["version"] for row in history)
        return CommitResult(success=True, version=version, row_count=row_count)
