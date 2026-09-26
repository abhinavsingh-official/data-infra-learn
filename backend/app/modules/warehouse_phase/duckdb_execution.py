"""Module 8's submission mechanism. DuckDB is embedded, not a network
service, so there's no persistent per-session connection to hold open the
way Postgres/Mongo phases do - every submission opens the session's own
file, re-attaches the Postgres source (see session_provisioning.py on why
that doesn't persist across connections), runs exactly one statement, and
closes. Same resilience contract as the other phases: any failure comes
back as a structured result, never an unhandled 500.

The actual mechanics live in app.core.duckdb_sessions - shared with
lake_phase (Module 9), the second phase needing the identical shape."""

from app.core.duckdb_sessions import DuckDbExecutionResult, execute_duckdb_submission
from app.modules.warehouse_phase.session_provisioning import open_session_db, session_lock

__all__ = ["DuckDbExecutionResult", "execute_submission"]


def execute_submission(session_id: str, pg_role: str, pg_password: str, sql_text: str) -> DuckDbExecutionResult:
    return execute_duckdb_submission(session_id, open_session_db, session_lock(session_id), pg_role, pg_password, sql_text)
