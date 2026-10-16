"""Provisions a warehouse-phase session on PySpark (see
app.core.spark_sessions for the shared engine layer this builds on): a
read-only Postgres role plus a bronze-layer snapshot of `accounts` that
the session owns. `accounts` is the SCD2 exercise's mutation target, so
it needs a real local copy; users/transactions/etc. don't, since they're
never mutated and can stay live JDBC-backed temp views."""

from psycopg import Connection

from app.core.spark_sessions import (
    deprovision_phase_session,
    execute_spark_submission,
    pg_role_name as _pg_role_name,
    provision_phase_session,
    session_lock as _session_lock,
)

PHASE_PREFIX = "warehouse"


def pg_role_name(session_id: str) -> str:
    return _pg_role_name(PHASE_PREFIX, session_id)


def session_lock(session_id: str):
    return _session_lock(PHASE_PREFIX, session_id)


def provision_session(pg_conn: Connection, session_id: str):
    """Returns (spark_session, pg_password) - the caller (the API layer)
    stores both in session_registry so later requests reuse the exact
    same Spark session object (see session_registry.py's docstring)."""
    session_spark, password = provision_phase_session(pg_conn, PHASE_PREFIX, session_id)
    # USING DELTA, not a bare CTAS - see spark_sessions.py's module
    # docstring on why every managed table here needs this explicit.
    # No column rename needed here since the real schema already calls
    # the primary key `id`, matching what grading (report.py) and the
    # exercise's required_output expect.
    session_spark.sql("CREATE TABLE source_accounts_snapshot USING DELTA AS SELECT * FROM accounts")
    return session_spark, password


def deprovision_session(pg_conn: Connection, session_id: str) -> None:
    deprovision_phase_session(pg_conn, PHASE_PREFIX, session_id)


def execute(session_spark, session_id: str, sql_text: str):
    return execute_spark_submission(session_spark, session_lock(session_id), sql_text)
