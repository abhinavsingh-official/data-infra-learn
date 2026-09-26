"""Module 9.2: per-session provisioning - a Postgres role scoped to
read-only access on the source tables (via app.core.pg_readonly_sessions,
shared with nosql_phase/warehouse_phase - now including
raw_transaction_events, the actual source for this phase), a dedicated
DuckDB file with that source pre-attached, and a real local directory
for the user's own Parquet output. See MODULE_9_PLAN.md for why the
output directory is a real filesystem path (not a table inside the
DuckDB file) - COPY TO's target is a genuine file-write, and this phase
is specifically about files, not just SQL against another engine."""

import shutil

import duckdb
from psycopg import Connection

from app.core.config import get_settings
from app.core.duckdb_sessions import attach_postgres_source, open_duckdb_file, session_locks
from app.core.pg_readonly_sessions import (
    deprovision_pg_readonly_session as _deprovision_pg_readonly_session,
)
from app.core.pg_readonly_sessions import (
    make_role_name,
    provision_pg_readonly_session as _provision_pg_readonly_session,
)
from app.core.session_ids import validate_session_id

PG_ROLE_PREFIX = "lake_session_"
_LOCK_PREFIX = "lake"


def pg_role_name(session_id: str) -> str:
    return make_role_name(PG_ROLE_PREFIX, session_id)


def session_dir(session_id: str):
    validate_session_id(session_id)
    return get_settings().lake_sessions_dir / session_id


def db_path(session_id: str):
    return session_dir(session_id) / "session.duckdb"


def output_dir(session_id: str):
    return session_dir(session_id) / "output"


def session_lock(session_id: str):
    return session_locks[f"{_LOCK_PREFIX}:{session_id}"]


def open_session_db(session_id: str) -> duckdb.DuckDBPyConnection:
    return open_duckdb_file(db_path(session_id))


def provision_session(pg_conn: Connection, session_id: str) -> str:
    """Creates the read-only Postgres role, a fresh DuckDB file with `pg`
    attached, and an empty output directory for the user's Parquet
    files. Returns the generated Postgres role password."""
    role = pg_role_name(session_id)
    password = _provision_pg_readonly_session(pg_conn, role)

    session_dir(session_id).mkdir(parents=True, exist_ok=True)
    output_dir(session_id).mkdir(parents=True, exist_ok=True)
    con = open_session_db(session_id)
    try:
        attach_postgres_source(con, role, password)
    finally:
        con.close()
    return password


def deprovision_session(pg_conn: Connection, session_id: str) -> None:
    _deprovision_pg_readonly_session(pg_conn, pg_role_name(session_id))
    shutil.rmtree(session_dir(session_id), ignore_errors=True)
