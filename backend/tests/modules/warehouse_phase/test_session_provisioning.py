import secrets

import pytest

from app.core.db import get_admin_connection
from app.core.session_ids import UnsafeSessionId
from app.modules.warehouse_phase.session_provisioning import (
    deprovision_session,
    pg_role_name,
    provision_session,
)


@pytest.mark.parametrize("bad_id", ["", "not-hex!", "short", "'; DROP TABLE users; --", "a" * 65])
def test_rejects_unsafe_session_ids(bad_id):
    with get_admin_connection() as conn:
        with pytest.raises(UnsafeSessionId):
            provision_session(conn, bad_id)


def test_provision_creates_database_with_snapshot_then_deprovision_removes_it():
    session_id = secrets.token_hex(16)
    with get_admin_connection() as conn:
        session_spark, _password = provision_session(conn, session_id)

        count = session_spark.sql("SELECT COUNT(*) AS n FROM source_accounts_snapshot").collect()[0]["n"]
        assert count > 0

        deprovision_session(conn, session_id)

        role = pg_role_name(session_id)
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
            assert cur.fetchone() is None

        databases = {row.namespace for row in session_spark.sql("SHOW DATABASES").collect()}
        assert f"warehouse_{session_id}" not in databases
