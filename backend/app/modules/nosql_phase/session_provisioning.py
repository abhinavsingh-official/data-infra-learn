"""Module 7.2: per-session provisioning across TWO databases at once -
a Mongo user scoped to readWrite on its own database (where the user
builds account_profiles), and a Postgres role scoped to read-only access
on the same five source tables from the relational phase (where the
source data actually lives - there's no reason to duplicate it into
Mongo just so this phase has "its own" copy). Mirrors Module 4's
role/schema isolation, but the isolation mechanism on the Mongo side is
its own native per-database authentication - see MODULE_7_PLAN.md."""

import secrets
import string

from psycopg import Connection, sql
from pymongo import MongoClient
from pymongo.errors import OperationFailure

from app.core.session_ids import validate_session_id

# Distinct prefix from postgres_phase.session_provisioning.role_name's
# "session_" - a nosql-phase session_id and a postgres-phase session_id
# are independently generated and could theoretically coincide, and a
# distinct prefix keeps that impossible rather than merely unlikely.
PG_ROLE_PREFIX = "nosql_session_"
READABLE_SOURCE_TABLES = ["users", "accounts", "transactions", "reward_events", "repayments"]
STATEMENT_TIMEOUT = "30s"

# Confirmed by calling dropUser against a nonexistent user directly
# (see MODULE_7_PLAN.md) - Mongo's real error code for "no such user".
_USER_NOT_FOUND = 11


def mongo_db_name(session_id: str) -> str:
    return f"session_{session_id}"


def pg_role_name(session_id: str) -> str:
    return f"{PG_ROLE_PREFIX}{session_id}"


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
    """Creates a Postgres role with SELECT-only access to the five
    relational-phase source tables - no schema of its own, since this
    role never creates anything, only reads. Returns the generated
    password."""
    validate_session_id(session_id)
    role = pg_role_name(session_id)
    password = _generate_password()

    conn.execute(
        sql.SQL("CREATE ROLE {role} WITH LOGIN PASSWORD {password} NOSUPERUSER NOCREATEDB NOCREATEROLE").format(
            role=sql.Identifier(role), password=sql.Literal(password)
        )
    )
    conn.execute(
        sql.SQL("ALTER ROLE {role} SET statement_timeout = {timeout}").format(
            role=sql.Identifier(role), timeout=sql.Literal(STATEMENT_TIMEOUT)
        )
    )
    conn.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {role}").format(role=sql.Identifier(role)))
    for table in READABLE_SOURCE_TABLES:
        conn.execute(
            sql.SQL("GRANT SELECT ON public.{table} TO {role}").format(
                table=sql.Identifier(table), role=sql.Identifier(role)
            )
        )
    conn.commit()
    return password


def deprovision_pg_readonly_session(conn: Connection, session_id: str) -> None:
    validate_session_id(session_id)
    role = pg_role_name(session_id)
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
        role_exists = cur.fetchone() is not None
    if role_exists:
        conn.execute(sql.SQL("DROP OWNED BY {role} CASCADE").format(role=sql.Identifier(role)))
    conn.execute(sql.SQL("DROP ROLE IF EXISTS {role}").format(role=sql.Identifier(role)))
    conn.commit()
