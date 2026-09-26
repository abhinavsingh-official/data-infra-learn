"""Module 9's submission mechanism - identical shape to warehouse_phase's,
via the shared core in app.core.duckdb_sessions."""

from app.core.duckdb_sessions import DuckDbExecutionResult, execute_duckdb_submission
from app.modules.lake_phase.session_provisioning import open_session_db, session_lock

__all__ = ["DuckDbExecutionResult", "execute_submission"]


def execute_submission(session_id: str, pg_role: str, pg_password: str, sql_text: str) -> DuckDbExecutionResult:
    return execute_duckdb_submission(session_id, open_session_db, session_lock(session_id), pg_role, pg_password, sql_text)
