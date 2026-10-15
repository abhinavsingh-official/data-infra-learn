"""Module 19 rewrite of Module 9.2's provisioning, now on PySpark instead
of DuckDB (see app.core.spark_sessions for the shared engine layer this
builds on). Still a read-only Postgres role plus a real local output
directory - the directory stays a genuine filesystem path (not just a
Spark-catalog concept), since the whole point of this phase is writing
and reading real Parquet files, same reasoning as MODULE_9_PLAN.md's
original decision."""

import shutil

from psycopg import Connection

from app.core.config import get_settings
from app.core.session_ids import validate_session_id
from app.core.spark_sessions import (
    deprovision_phase_session,
    execute_spark_submission,
    pg_role_name as _pg_role_name,
    provision_phase_session,
    session_lock as _session_lock,
)

PHASE_PREFIX = "lake"


def pg_role_name(session_id: str) -> str:
    return _pg_role_name(PHASE_PREFIX, session_id)


def session_lock(session_id: str):
    return _session_lock(PHASE_PREFIX, session_id)


def output_dir(session_id: str):
    validate_session_id(session_id)
    return get_settings().lake_sessions_dir / session_id / "output"


def provision_session(pg_conn: Connection, session_id: str):
    """Returns (spark_session, pg_password) - same shape as warehouse_
    phase's provisioning, for the same reason (session_registry.py keeps
    the actual SparkSession object alive across requests)."""
    session_spark, password = provision_phase_session(pg_conn, PHASE_PREFIX, session_id)
    output_dir(session_id).mkdir(parents=True, exist_ok=True)
    return session_spark, password


def deprovision_session(pg_conn: Connection, session_id: str) -> None:
    deprovision_phase_session(pg_conn, PHASE_PREFIX, session_id)
    shutil.rmtree(output_dir(session_id).parent, ignore_errors=True)


def execute(session_spark, session_id: str, sql_text: str):
    return execute_spark_submission(session_spark, session_lock(session_id), sql_text)
