import secrets

import pytest

from app.core.db import get_admin_connection
from app.core.duckdb_sessions import attach_postgres_source
from app.core.session_ids import UnsafeSessionId
from app.modules.lakehouse_phase.session_provisioning import (
    db_path,
    delta_table_dir,
    deprovision_session,
    open_session_db,
    pg_role_name,
    provision_session,
    release_batch_two,
    session_dir,
)


@pytest.mark.parametrize("bad_id", ["", "not-hex!", "short", "'; DROP TABLE users; --", "a" * 65])
def test_rejects_unsafe_session_ids(bad_id):
    with pytest.raises(UnsafeSessionId):
        session_dir(bad_id)


def test_provision_creates_batch_1_only_release_reveals_batch_2():
    session_id = secrets.token_hex(16)
    with get_admin_connection() as conn:
        password = provision_session(conn, session_id)

        assert db_path(session_id).exists()
        assert not delta_table_dir(session_id).exists()  # nothing committed yet

        con = open_session_db(session_id)
        try:
            attach_postgres_source(con, pg_role_name(session_id), password)
            batch_1_count = con.execute("SELECT COUNT(*) FROM batch_1_events").fetchone()[0]
            assert batch_1_count > 0
            with pytest.raises(Exception):
                con.execute("SELECT COUNT(*) FROM batch_2_events").fetchone()
        finally:
            con.close()

        released = release_batch_two(session_id, pg_role_name(session_id), password)
        assert released > 0

        # idempotent - calling again finds it already exists, copies nothing new
        assert release_batch_two(session_id, pg_role_name(session_id), password) == 0

        con = open_session_db(session_id)
        try:
            batch_2_count = con.execute("SELECT COUNT(*) FROM batch_2_events").fetchone()[0]
            assert batch_2_count == released
        finally:
            con.close()

        deprovision_session(conn, session_id)
        assert not session_dir(session_id).exists()

        role = pg_role_name(session_id)
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
            assert cur.fetchone() is None
