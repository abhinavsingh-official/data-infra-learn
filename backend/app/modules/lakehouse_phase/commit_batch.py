"""Module 19 rewrite of Module 10.1/10.2's Delta-write mechanism, now on
real PySpark/Delta instead of DuckDB (read) + the `deltalake` Python
library (write). The user still only ever submits a SELECT (their own
edge-case-handling logic, same intellectual work as every other phase's
task) - the platform, not user code, commits that query's result as a
real Delta transaction via Spark's own DataFrameWriter.

Unlike the original DuckDB version, this split is no longer forced by a
hard technical limit - Spark/Delta SQL can write Delta tables directly
(`INSERT INTO ... USING DELTA`, confirmed working in the warehouse
phase), so a student could in principle write the commit themselves in
plain SQL. Kept as a platform-mediated commit anyway, deliberately, not
because Spark can't do otherwise: it's the one real ACID-commit-history
check this phase's grading depends on (COMMIT 1 is always a fresh
CREATE, COMMIT 2 is always an append - see report.py's time-travel
check), and that's cleaner to guarantee server-side than to trust every
possible student query shape to preserve it."""

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
    result as one atomic Delta `append` write - deliberately NOT routed
    through execute_spark_submission, which caps results at 1000 rows
    for interactive previews. A real batch here is ~25,000 rows; capping
    it the same way would silently commit a truncated batch instead of
    the real one, a correctness bug a code reviewer could easily miss
    since execute() and commit_batch() look like they should share the
    same plumbing but can't - one is for looking at data, the other is
    for writing all of it."""
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
            # saveAsTable every time (not just on the first commit) raced
            # under concurrent calls even fully serialized by session_lock
            # above - confirmed directly: 8 sequential (lock-serialized)
            # saveAsTable calls against the same not-yet-existing table
            # name intermittently saw a half-registered catalog entry
            # (schema struct<>) from a prior call in the same sequence.
            # insertInto for every commit after the first avoids the
            # table-creation path entirely, since there's nothing left to
            # race on - confirmed directly to fix it.
            if session_spark.catalog.tableExists("clean_transactions"):
                df.write.format("delta").mode("append").insertInto("clean_transactions")
            else:
                df.write.format("delta").mode("append").saveAsTable("clean_transactions")
        except Exception as e:  # noqa: BLE001
            # Delta's own schema enforcement is what actually rejects an incompatible batch here
            # (e.g. amount not castable against the existing table's type) - confirmed directly,
            # same resilience contract as execute(): never a crash, always a structured result.
            return CommitResult(success=False, error_code=type(e).__name__, error_message=str(e).strip())

        history = session_spark.sql("DESCRIBE HISTORY clean_transactions").collect()
        version = max(row["version"] for row in history)
        return CommitResult(success=True, version=version, row_count=row_count)
