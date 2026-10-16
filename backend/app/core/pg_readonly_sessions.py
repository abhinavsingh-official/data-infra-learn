"""Read-only Postgres session provisioning, shared across every phase
module that needs to let a session query the same five relational source
tables without write access."""

import secrets
import string

from psycopg import Connection, sql

from app.core.session_ids import validate_session_id

READABLE_SOURCE_TABLES = [
    "users",
    "accounts",
    "transactions",
    "reward_events",
    "repayments",
    # Raw JSONB feed - not sensitive (the actual answer key,
    # injected_fault_log, is a separate table that stays default-deny).
    "raw_transaction_events",
]
STATEMENT_TIMEOUT = "30s"


def _generate_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(32))


def provision_pg_readonly_session(conn: Connection, role: str) -> str:
    """Creates a Postgres role with SELECT-only access to the five
    relational-phase source tables - no schema of its own, since this
    role never creates anything, only reads. Returns the generated
    password. `role` is the caller's own fully-formed role name (already
    prefixed per-phase) - this function doesn't validate the session_id
    itself, since by this point it's already baked into `role`."""
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


def deprovision_pg_readonly_session(conn: Connection, role: str) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
        role_exists = cur.fetchone() is not None
    if role_exists:
        conn.execute(sql.SQL("DROP OWNED BY {role} CASCADE").format(role=sql.Identifier(role)))
    conn.execute(sql.SQL("DROP ROLE IF EXISTS {role}").format(role=sql.Identifier(role)))
    conn.commit()


def make_role_name(prefix: str, session_id: str) -> str:
    validate_session_id(session_id)
    return f"{prefix}{session_id}"
