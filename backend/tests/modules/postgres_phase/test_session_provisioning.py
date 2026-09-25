import secrets

import psycopg
import pytest

from app.core.config import get_settings
from app.core.db import get_admin_connection
from app.modules.postgres_phase.session_provisioning import (
    UnsafeSessionId,
    deprovision_session,
    provision_session,
)


def _dsn(role: str, password: str) -> str:
    settings = get_settings()
    return f"postgresql://{role}:{password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"


@pytest.mark.parametrize("bad_id", ["", "not-hex!", "short", "'; DROP TABLE users; --", "a" * 65])
def test_rejects_unsafe_session_ids_before_touching_sql(bad_id):
    with get_admin_connection() as conn:
        with pytest.raises(UnsafeSessionId):
            provision_session(conn, bad_id)


def test_provision_creates_isolated_role_and_schema_then_deprovision_removes_them():
    session_id = secrets.token_hex(16)
    role = f"session_{session_id}"

    with get_admin_connection() as conn:
        password = provision_session(conn, session_id)

    with psycopg.connect(_dsn(role, password)) as conn:
        conn.execute("CREATE TABLE t (id int)")
        conn.commit()

    with get_admin_connection() as conn:
        deprovision_session(conn, session_id)
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
            assert cur.fetchone() is None
            cur.execute("SELECT 1 FROM information_schema.schemata WHERE schema_name = %s", (role,))
            assert cur.fetchone() is None


def test_two_sessions_cannot_see_each_others_schema():
    session_a, session_b = secrets.token_hex(16), secrets.token_hex(16)
    role_a, role_b = f"session_{session_a}", f"session_{session_b}"

    with get_admin_connection() as conn:
        pw_a = provision_session(conn, session_a)
        pw_b = provision_session(conn, session_b)

    try:
        with psycopg.connect(_dsn(role_a, pw_a)) as conn_a:
            conn_a.execute("CREATE TABLE secret (id int)")
            conn_a.commit()

        with psycopg.connect(_dsn(role_b, pw_b)) as conn_b:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn_b.execute(f"SELECT * FROM {role_a}.secret")
    finally:
        with get_admin_connection() as conn:
            deprovision_session(conn, session_a)
            deprovision_session(conn, session_b)


def test_session_can_read_raw_feed_but_not_the_answer_key():
    """The exercise is 'ETL this raw feed into your own schema' - a
    session role needs read access to raw_transaction_events, but must
    never see injected_fault_log (the literal answer key Module 5 grades
    against). Found by running this: granting the read access broke
    deprovision_session (DROP ROLE fails while grants on shared objects
    still exist) - fixed with DROP OWNED BY, tested here too."""
    session_id = secrets.token_hex(16)
    role = f"session_{session_id}"

    with get_admin_connection() as conn:
        password = provision_session(conn, session_id)

    with psycopg.connect(_dsn(role, password)) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM public.raw_transaction_events")
            assert cur.fetchone()[0] >= 0  # doesn't raise - that's the actual assertion
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT COUNT(*) FROM public.injected_fault_log")

    with get_admin_connection() as conn:
        deprovision_session(conn, session_id)  # must not raise despite the grants above
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
            assert cur.fetchone() is None
