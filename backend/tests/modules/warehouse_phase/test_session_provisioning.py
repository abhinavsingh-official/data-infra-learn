import secrets

import duckdb
import pytest

from app.core.db import get_admin_connection
from app.core.session_ids import UnsafeSessionId
from app.modules.warehouse_phase.session_provisioning import (
    db_path,
    deprovision_session,
    pg_role_name,
    provision_session,
)


@pytest.mark.parametrize("bad_id", ["", "not-hex!", "short", "'; DROP TABLE users; --", "a" * 65])
def test_rejects_unsafe_session_ids(bad_id):
    with pytest.raises(UnsafeSessionId):
        db_path(bad_id)


def test_provision_creates_file_with_pg_attached_and_snapshot_then_deprovision_removes_it():
    session_id = secrets.token_hex(16)
    with get_admin_connection() as conn:
        provision_session(conn, session_id)

        path = db_path(session_id)
        assert path.exists()

        con = duckdb.connect(str(path))
        try:
            count = con.execute("SELECT COUNT(*) FROM source_accounts_snapshot").fetchone()[0]
            assert count > 0
        finally:
            con.close()

        deprovision_session(conn, session_id)
        assert not path.exists()

        role = pg_role_name(session_id)
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
            assert cur.fetchone() is None
