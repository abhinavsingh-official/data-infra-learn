"""Lakehouse-phase session provisioning on PySpark/Delta (see
app.core.spark_sessions for the shared engine layer this builds on).
Splits the raw feed into two batches revealed progressively
(`batch_1_events` immediately, `batch_2_events` only on request) to
simulate incremental batch arrival - both are real Delta tables
(USING DELTA; see spark_sessions.py for why managed tables need that)."""

from psycopg import Connection

from app.core.spark_sessions import (
    deprovision_phase_session,
    execute_spark_submission,
    pg_role_name as _pg_role_name,
    provision_phase_session,
    session_lock as _session_lock,
)

PHASE_PREFIX = "lakehouse"


def pg_role_name(session_id: str) -> str:
    return _pg_role_name(PHASE_PREFIX, session_id)


def session_lock(session_id: str):
    return _session_lock(PHASE_PREFIX, session_id)


def provision_session(pg_conn: Connection, session_id: str):
    """Returns (spark_session, pg_password) - same shape as the other
    phases' provisioning."""
    session_spark, password = provision_phase_session(pg_conn, PHASE_PREFIX, session_id)
    session_spark.sql(
        "CREATE TABLE batch_1_events USING DELTA AS "
        "SELECT id, received_at, source_delivery_id, payload FROM raw_transaction_events WHERE id % 2 = 0"
    )
    return session_spark, password


def release_batch_two(session_spark, session_id: str) -> int:
    """Copies the second half of the raw feed (`id % 2 = 1`) into
    `batch_2_events` - idempotent, checked via the catalog rather than
    re-running the CREATE TABLE (which would error on an existing
    table)."""
    with session_lock(session_id):
        if session_spark.catalog.tableExists("batch_2_events"):
            return 0
        session_spark.sql(
            "CREATE TABLE batch_2_events USING DELTA AS "
            "SELECT id, received_at, source_delivery_id, payload FROM raw_transaction_events WHERE id % 2 = 1"
        )
        return session_spark.sql("SELECT COUNT(*) AS n FROM batch_2_events").collect()[0]["n"]


def deprovision_session(pg_conn: Connection, session_id: str) -> None:
    deprovision_phase_session(pg_conn, PHASE_PREFIX, session_id)


def execute(session_spark, session_id: str, sql_text: str):
    return execute_spark_submission(session_spark, session_lock(session_id), sql_text)
