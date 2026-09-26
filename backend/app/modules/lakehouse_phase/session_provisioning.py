"""Module 10.2: per-session provisioning - a Postgres role scoped to
read-only access on the source tables (via app.core.pg_readonly_sessions,
the third phase to share it), a dedicated DuckDB file with that source
pre-attached and `batch_1_events` (half the raw feed) already copied in,
and a real local directory reserved for the user's Delta table. See
MODULE_10_PLAN.md for why the raw feed is split in two and revealed
progressively - the same "day 1 / day 2" mechanism Module 8 used for its
SCD2 mutation, applied here to simulate incremental batch arrival."""

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

PG_ROLE_PREFIX = "lakehouse_session_"
_LOCK_PREFIX = "lakehouse"

_EVENT_COLUMNS_SQL = "id, received_at, source_delivery_id, payload::VARCHAR AS payload"


def pg_role_name(session_id: str) -> str:
    return make_role_name(PG_ROLE_PREFIX, session_id)


def session_dir(session_id: str):
    validate_session_id(session_id)
    return get_settings().lakehouse_sessions_dir / session_id


def db_path(session_id: str):
    return session_dir(session_id) / "session.duckdb"


def delta_table_dir(session_id: str):
    return session_dir(session_id) / "clean_transactions_delta"


def session_lock(session_id: str):
    return session_locks[f"{_LOCK_PREFIX}:{session_id}"]


def open_session_db(session_id: str) -> duckdb.DuckDBPyConnection:
    return open_duckdb_file(db_path(session_id))


def provision_session(pg_conn: Connection, session_id: str) -> str:
    """Creates the read-only Postgres role, a fresh DuckDB file with `pg`
    attached and `batch_1_events` (the deterministic first half of the
    raw feed, `id % 2 = 0`) already copied in - `batch_2_events` is
    deliberately NOT created here, only by release_batch_two(). Returns
    the generated Postgres role password."""
    role = pg_role_name(session_id)
    password = _provision_pg_readonly_session(pg_conn, role)

    session_dir(session_id).mkdir(parents=True, exist_ok=True)
    con = open_session_db(session_id)
    try:
        attach_postgres_source(con, role, password)
        con.execute(
            f"CREATE TABLE batch_1_events AS SELECT {_EVENT_COLUMNS_SQL} "
            "FROM pg.raw_transaction_events WHERE id % 2 = 0"
        )
    finally:
        con.close()
    return password


def release_batch_two(session_id: str, pg_role: str, pg_password: str) -> int:
    """Copies the second half of the raw feed (`id % 2 = 1`) into
    `batch_2_events` - idempotent, since CREATE TABLE IF NOT EXISTS means
    calling this twice doesn't duplicate or re-copy. Returns the row
    count copied (0 if it already existed)."""
    with session_lock(session_id):
        con = open_session_db(session_id)
        try:
            already_exists = bool(
                con.execute(
                    "SELECT 1 FROM information_schema.tables WHERE table_name = 'batch_2_events'"
                ).fetchone()
            )
            if already_exists:
                return 0
            attach_postgres_source(con, pg_role, pg_password)
            con.execute(
                f"CREATE TABLE batch_2_events AS SELECT {_EVENT_COLUMNS_SQL} "
                "FROM pg.raw_transaction_events WHERE id % 2 = 1"
            )
            return con.execute("SELECT COUNT(*) FROM batch_2_events").fetchone()[0]
        finally:
            con.close()


def deprovision_session(pg_conn: Connection, session_id: str) -> None:
    _deprovision_pg_readonly_session(pg_conn, pg_role_name(session_id))
    shutil.rmtree(session_dir(session_id), ignore_errors=True)
