"""Module 10.1/10.2: the actual Delta-write mechanism. The user submits
a SELECT (their own edge-case-handling logic, same intellectual work as
every other phase's task) - the PLATFORM, not user code, takes that
query's result and commits it as a real Delta transaction. See
MODULE_10_PLAN.md for why: DuckDB cannot write Delta at all, and letting
user-submitted code call a Python library directly would reopen the
code-execution-sandbox question ARCHITECTURE_DECISIONS.md §7 already
closed."""

from dataclasses import dataclass

import duckdb
import polars as pl
from deltalake import DeltaTable, write_deltalake

from app.core.duckdb_sessions import attach_postgres_source, contains_multiple_statements
from app.modules.lakehouse_phase.session_provisioning import (
    delta_table_dir,
    open_session_db,
    session_lock,
)

REQUIRED_COLUMNS = ["event_id", "amount", "merchant", "currency", "event_timestamp"]


@dataclass
class CommitResult:
    success: bool
    version: int | None = None
    row_count: int | None = None
    error_code: str | None = None
    error_message: str | None = None


def _canonical_frame(columns: list[str], rows: list[tuple]) -> pl.DataFrame:
    df = pl.DataFrame(rows, schema=columns, orient="row")
    return df.select(
        pl.col("event_id").cast(pl.Utf8),
        pl.col("amount").cast(pl.Float64),
        pl.col("merchant").cast(pl.Utf8),
        pl.col("currency").cast(pl.Utf8),
        pl.col("event_timestamp").cast(pl.Datetime("us")),
    )


def commit_batch(session_id: str, pg_role: str, pg_password: str, sql_text: str) -> CommitResult:
    """Runs the submitted SELECT via DuckDB (the untrusted part - same
    trust boundary as every other phase's execute()), then commits the
    result as one atomic Delta `append` transaction (the trusted part -
    platform code, not user code)."""
    if contains_multiple_statements(sql_text):
        return CommitResult(success=False, error_code="MULTIPLE_STATEMENTS", error_message="Submit one SELECT per request.")

    # DuckDB - unlike Postgres - returns a real result set (a "Count"
    # column) for CREATE TABLE/INSERT/DDL too, so `result.description is
    # None` never actually detects a non-SELECT here (confirmed directly
    # by testing: it let a CREATE TABLE through, which then failed with
    # a confusing MISSING_REQUIRED_COLUMNS instead of a clear one). Not a
    # real parser, but checking the statement text itself is what
    # Postgres's own result-shape check can't do on this engine.
    stripped = sql_text.strip().upper()
    if not (stripped.startswith("SELECT") or stripped.startswith("WITH")):
        return CommitResult(
            success=False,
            error_code="NOT_A_SELECT",
            error_message="A batch commit must be a SELECT - the platform commits its result, not arbitrary DDL/DML.",
        )

    # Everything below - the DuckDB read AND the actual Delta write - is
    # inside the one per-session lock. Found by testing directly: with
    # only the DuckDB read locked, 8 concurrent commit_batch() calls
    # against the same fresh session raced on the real write_deltalake
    # call - 4 of 8 failed with a real CommitFailedError (Delta's own
    # optimistic concurrency control caught it, so nothing corrupted),
    # but two of the "successful" ones both reported version=1, which is
    # a wrong, confusing result to hand back over the API for what a
    # normal single-user session should never even risk (e.g. a double
    # click on "Commit"). A DeltaTable is a single, session-owned
    # resource here, same reasoning as the DuckDB file lock already
    # covers for execute()/grade().
    with session_lock(session_id):
        con = open_session_db(session_id)
        try:
            attach_postgres_source(con, pg_role, pg_password)
            result = con.execute(sql_text)
            columns = [d[0] for d in result.description]
            missing = [c for c in REQUIRED_COLUMNS if c not in columns]
            if missing:
                return CommitResult(
                    success=False,
                    error_code="MISSING_REQUIRED_COLUMNS",
                    error_message=f"Missing required column(s): {missing}. Expected: {REQUIRED_COLUMNS}.",
                )
            rows = result.fetchall()
        except duckdb.Error as e:
            return CommitResult(success=False, error_code=type(e).__name__, error_message=str(e).strip())
        finally:
            con.close()

        try:
            df = _canonical_frame(columns, rows)
        except Exception as e:
            return CommitResult(success=False, error_code="SCHEMA_CAST_FAILED", error_message=str(e).strip())

        try:
            write_deltalake(str(delta_table_dir(session_id)), df, mode="append")
        except Exception as e:
            # Real Delta schema enforcement - e.g. a batch whose amount
            # column doesn't cast to the existing table's type is
            # rejected outright, and the table's version does not
            # advance (confirmed directly - see MODULE_10_PLAN.md).
            # Never a crash, always a structured result.
            return CommitResult(success=False, error_code=type(e).__name__, error_message=str(e).strip())

        version = DeltaTable(str(delta_table_dir(session_id))).version()
        return CommitResult(success=True, version=version, row_count=df.height)
