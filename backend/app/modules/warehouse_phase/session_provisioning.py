"""Module 8.2: per-session provisioning - a Postgres role scoped to
read-only access on the five source tables (via app.core.pg_readonly_
sessions, shared with nosql_phase), and a dedicated DuckDB file with the
Postgres source pre-attached and a bronze-layer snapshot of `accounts`
already copied in. See MODULE_8_PLAN.md for why `accounts` gets a real
local snapshot (it's the mutation target for the SCD2 exercise) while
users/transactions/etc. don't need one - they're never mutated, so the
user's ETL can read them straight from the live `pg` attachment."""

import duckdb
from psycopg import Connection

from app.core.config import get_settings
from app.core.pg_readonly_sessions import (
    deprovision_pg_readonly_session as _deprovision_pg_readonly_session,
)
from app.core.pg_readonly_sessions import (
    make_role_name,
    provision_pg_readonly_session as _provision_pg_readonly_session,
)
from app.core.session_ids import validate_session_id

PG_ROLE_PREFIX = "warehouse_session_"


def pg_role_name(session_id: str) -> str:
    return make_role_name(PG_ROLE_PREFIX, session_id)


def db_path(session_id: str):
    validate_session_id(session_id)
    return get_settings().warehouse_sessions_dir / f"{session_id}.duckdb"


def attach_postgres_source(con: duckdb.DuckDBPyConnection, role: str, password: str) -> None:
    """ATTACH doesn't persist across a DuckDB file's connections (confirmed
    by testing directly - reopening a file with a `pg` schema previously
    attached raises CatalogException) - every caller that opens this
    session's file needs to redo this, not just provisioning."""
    settings = get_settings()
    con.execute("INSTALL postgres; LOAD postgres;")
    conninfo = settings.postgres_attach_conninfo(role, password)
    con.execute(f"ATTACH '{conninfo}' AS pg (TYPE postgres, READ_ONLY)")


def provision_session(pg_conn: Connection, session_id: str) -> str:
    """Creates the read-only Postgres role, then a fresh DuckDB file with
    `pg` attached and `source_accounts_snapshot` (the bronze layer)
    already copied in. Returns the generated Postgres role password -
    the caller stores it so later requests can re-attach `pg`."""
    role = pg_role_name(session_id)
    password = _provision_pg_readonly_session(pg_conn, role)

    path = db_path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    try:
        attach_postgres_source(con, role, password)
        con.execute("CREATE TABLE source_accounts_snapshot AS SELECT * FROM pg.accounts")
    finally:
        con.close()
    return password


def deprovision_session(pg_conn: Connection, session_id: str) -> None:
    _deprovision_pg_readonly_session(pg_conn, pg_role_name(session_id))
    path = db_path(session_id)
    path.unlink(missing_ok=True)
    path.with_suffix(".mutations.json").unlink(missing_ok=True)
