"""Module 10's inspection/preview submission mechanism - identical shape
to warehouse_phase's and lake_phase's, via the shared core in
app.core.duckdb_sessions. Used for exploring batch_1_events/
batch_2_events and reading the Delta table back (delta_scan) - NOT for
committing a batch, which goes through commit_batch.py instead, since
DuckDB itself cannot write Delta (see MODULE_10_PLAN.md)."""

from app.core.duckdb_sessions import DuckDbExecutionResult, execute_duckdb_submission
from app.modules.lakehouse_phase.session_provisioning import open_session_db, session_lock

__all__ = ["DuckDbExecutionResult", "execute_submission"]


def execute_submission(session_id: str, pg_role: str, pg_password: str, sql_text: str) -> DuckDbExecutionResult:
    return execute_duckdb_submission(session_id, open_session_db, session_lock(session_id), pg_role, pg_password, sql_text)
