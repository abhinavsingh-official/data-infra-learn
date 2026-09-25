"""Module 4.2: per-session provisioning - a restricted role + an owned
schema, isolated from every other session. See MODULE_4_PLAN.md for the
two-connection-tier decision (this uses the admin connection, never the
regular app_role one) and the research behind the design."""

import re
import secrets
import string

from psycopg import Connection, sql

STATEMENT_TIMEOUT = "30s"

# The exercise is "ETL this raw feed into your own schema" - a session
# role needs read access to the raw feed to do that. It must NOT get
# access to injected_fault_log (the literal answer key) - default-deny
# already covers that as long as it's never explicitly granted, but this
# constant exists so the "readable" set is a deliberate, visible decision
# rather than an accident of what wasn't locked down.
READABLE_SHARED_TABLES = ["raw_transaction_events"]

_SAFE_SESSION_ID = re.compile(r"^[a-f0-9]{16,64}$")


class UnsafeSessionId(ValueError):
    pass


def _validate_session_id(session_id: str) -> None:
    """Defense in depth alongside sql.Identifier - reject anything that
    isn't a plain hex token *before* it ever reaches SQL construction,
    rather than relying solely on quoting to make arbitrary input safe."""
    if not _SAFE_SESSION_ID.match(session_id):
        raise UnsafeSessionId(f"session_id must be a 16-64 char lowercase hex token, got: {session_id!r}")


def role_name(session_id: str) -> str:
    return f"session_{session_id}"


def _generate_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(32))


def provision_session(conn: Connection, session_id: str) -> str:
    """Creates role+schema `session_<id>`, scopes its search_path to just
    that schema, and applies the statement_timeout from ARCHITECTURE_
    DECISIONS.md §7. Returns the generated password (the caller is
    responsible for handing it to whatever connects as this role)."""
    _validate_session_id(session_id)
    role = role_name(session_id)
    password = _generate_password()

    # Postgres doesn't accept a bind parameter in this DDL position (found
    # by running it, not assumed) - sql.Literal is the correct mechanism
    # for safely embedding a literal value here, not %s binding.
    conn.execute(
        sql.SQL("CREATE ROLE {role} WITH LOGIN PASSWORD {password} NOSUPERUSER NOCREATEDB NOCREATEROLE").format(
            role=sql.Identifier(role), password=sql.Literal(password)
        )
    )
    conn.execute(sql.SQL("CREATE SCHEMA {schema} AUTHORIZATION {role}").format(
        schema=sql.Identifier(role), role=sql.Identifier(role)
    ))
    conn.execute(
        sql.SQL("ALTER ROLE {role} SET search_path = {schema}").format(
            role=sql.Identifier(role), schema=sql.Identifier(role)
        )
    )
    conn.execute(
        sql.SQL("ALTER ROLE {role} SET statement_timeout = {timeout}").format(
            role=sql.Identifier(role), timeout=sql.Literal(STATEMENT_TIMEOUT)
        )
    )
    conn.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {role}").format(role=sql.Identifier(role)))
    for table in READABLE_SHARED_TABLES:
        conn.execute(
            sql.SQL("GRANT SELECT ON public.{table} TO {role}").format(
                table=sql.Identifier(table), role=sql.Identifier(role)
            )
        )
    conn.commit()
    return password


def deprovision_session(conn: Connection, session_id: str) -> None:
    """DROP ROLE fails if the role still holds privileges granted on
    shared objects (public.raw_transaction_events, public schema usage) -
    found by running this against a session that had actually used its
    read grants. DROP OWNED BY handles both the role's own schema AND any
    privileges granted to it on other objects in one step; DROP SCHEMA
    alone only ever covered the former."""
    _validate_session_id(session_id)
    role = role_name(session_id)
    # DROP OWNED BY errors if the role doesn't exist (unlike DROP ROLE IF
    # EXISTS) - guard so a double-deprovision or a partially-failed
    # provision doesn't crash this.
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
        role_exists = cur.fetchone() is not None
    if role_exists:
        conn.execute(sql.SQL("DROP OWNED BY {role} CASCADE").format(role=sql.Identifier(role)))
    conn.execute(sql.SQL("DROP ROLE IF EXISTS {role}").format(role=sql.Identifier(role)))
    conn.commit()
