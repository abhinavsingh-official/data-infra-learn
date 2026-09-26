import secrets

import pytest

from app.core.db import get_admin_connection
from app.core.duckdb_sessions import attach_postgres_source
from app.core.session_ids import UnsafeSessionId
from app.modules.lake_phase.session_provisioning import (
    db_path,
    deprovision_session,
    open_session_db,
    output_dir,
    pg_role_name,
    provision_session,
    session_dir,
)


@pytest.mark.parametrize("bad_id", ["", "not-hex!", "short", "'; DROP TABLE users; --", "a" * 65])
def test_rejects_unsafe_session_ids(bad_id):
    with pytest.raises(UnsafeSessionId):
        session_dir(bad_id)


def test_provision_creates_file_dir_and_role_then_deprovision_removes_all_of_it():
    session_id = secrets.token_hex(16)
    with get_admin_connection() as conn:
        password = provision_session(conn, session_id)

        assert db_path(session_id).exists()
        assert output_dir(session_id).is_dir()

        con = open_session_db(session_id)
        try:
            attach_postgres_source(con, pg_role_name(session_id), password)
            count = con.execute("SELECT COUNT(*) FROM pg.raw_transaction_events").fetchone()[0]
        finally:
            con.close()
        assert count > 0

        deprovision_session(conn, session_id)
        assert not session_dir(session_id).exists()

        role = pg_role_name(session_id)
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
            assert cur.fetchone() is None
