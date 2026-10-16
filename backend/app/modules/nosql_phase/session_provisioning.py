"""Per-session provisioning across TWO databases at once - a Mongo user
scoped to readWrite on its own database (where the user builds
account_profiles), and a Postgres role scoped to read-only access on
the same five source tables from the relational phase (where the
source data actually lives - there's no reason to duplicate it into
Mongo just so this phase has "its own" copy). Mirrors the Postgres
phase's role/schema isolation, but the isolation mechanism on the Mongo
side is its own native per-database authentication.

The Postgres read-only side is a thin, name-stable wrapper around
app.core.pg_readonly_sessions, shared with warehouse_phase, which needs
the identical shape."""

import secrets
import string

from psycopg import Connection
from pymongo import MongoClient
from pymongo.errors import OperationFailure

from app.core.pg_readonly_sessions import (
    deprovision_pg_readonly_session as _deprovision_pg_readonly_session,
)
from app.core.pg_readonly_sessions import (
    make_role_name,
    provision_pg_readonly_session as _provision_pg_readonly_session,
)
from app.core.session_ids import validate_session_id

# Distinct prefix from postgres_phase.session_provisioning.role_name's
# "session_" - a nosql-phase session_id and a postgres-phase session_id
# are independently generated and could theoretically coincide, and a
# distinct prefix keeps that impossible rather than merely unlikely.
PG_ROLE_PREFIX = "nosql_session_"

# Mongo's error code for "no such user" (from dropUser against a
# nonexistent user).
_USER_NOT_FOUND = 11


def mongo_db_name(session_id: str) -> str:
    return f"session_{session_id}"


def pg_role_name(session_id: str) -> str:
    return make_role_name(PG_ROLE_PREFIX, session_id)


def _generate_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(32))


def provision_mongo_session(admin_client: MongoClient, session_id: str) -> str:
    """Creates a Mongo user scoped to readWrite on `session_<id>` only.
    Returns the generated password."""
    validate_session_id(session_id)
    name = mongo_db_name(session_id)
    password = _generate_password()
    admin_client[name].command(
        "createUser",
        name,
        pwd=password,
        roles=[{"role": "readWrite", "db": name}],
    )
    return password


def deprovision_mongo_session(admin_client: MongoClient, session_id: str) -> None:
    validate_session_id(session_id)
    name = mongo_db_name(session_id)
    try:
        admin_client[name].command("dropUser", name)
    except OperationFailure as e:
        if e.code != _USER_NOT_FOUND:
            raise
    admin_client.drop_database(name)


def provision_pg_readonly_session(conn: Connection, session_id: str) -> str:
    return _provision_pg_readonly_session(conn, pg_role_name(session_id))


def deprovision_pg_readonly_session(conn: Connection, session_id: str) -> None:
    _deprovision_pg_readonly_session(conn, pg_role_name(session_id))
