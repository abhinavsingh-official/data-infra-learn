import secrets

import pytest

from app.core.db import get_admin_connection
from app.core.session_ids import UnsafeSessionId
from app.modules.lake_phase.session_provisioning import (
    deprovision_session,
    output_dir,
    pg_role_name,
    provision_session,
)


@pytest.mark.parametrize("bad_id", ["", "not-hex!", "short", "'; DROP TABLE users; --", "a" * 65])
def test_rejects_unsafe_session_ids(bad_id):
    with get_admin_connection() as conn:
        with pytest.raises(UnsafeSessionId):
            provision_session(conn, bad_id)


def test_provision_creates_output_dir_and_role_then_deprovision_removes_all_of_it():
    session_id = secrets.token_hex(16)
    with get_admin_connection() as conn:
        session_spark, _password = provision_session(conn, session_id)

        assert output_dir(session_id).is_dir()

        count = session_spark.sql("SELECT COUNT(*) AS n FROM raw_transaction_events").collect()[0]["n"]
        assert count > 0

        deprovision_session(conn, session_id)
        assert not output_dir(session_id).parent.exists()

        role = pg_role_name(session_id)
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
            assert cur.fetchone() is None
