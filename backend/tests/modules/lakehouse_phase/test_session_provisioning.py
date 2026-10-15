import secrets

import pytest

from app.core.db import get_admin_connection
from app.core.session_ids import UnsafeSessionId
from app.modules.lakehouse_phase.session_provisioning import (
    deprovision_session,
    pg_role_name,
    provision_session,
    release_batch_two,
)


@pytest.mark.parametrize("bad_id", ["", "not-hex!", "short", "'; DROP TABLE users; --", "a" * 65])
def test_rejects_unsafe_session_ids(bad_id):
    with get_admin_connection() as conn:
        with pytest.raises(UnsafeSessionId):
            provision_session(conn, bad_id)


def test_provision_creates_batch_1_only_release_reveals_batch_2():
    session_id = secrets.token_hex(16)
    with get_admin_connection() as conn:
        session_spark, _password = provision_session(conn, session_id)

        batch_1_count = session_spark.sql("SELECT COUNT(*) AS n FROM batch_1_events").collect()[0]["n"]
        assert batch_1_count > 0
        assert not session_spark.catalog.tableExists("batch_2_events")

        released = release_batch_two(session_spark, session_id)
        assert released > 0

        # idempotent - calling again finds it already exists, copies nothing new
        assert release_batch_two(session_spark, session_id) == 0

        batch_2_count = session_spark.sql("SELECT COUNT(*) AS n FROM batch_2_events").collect()[0]["n"]
        assert batch_2_count == released

        deprovision_session(conn, session_id)

        role = pg_role_name(session_id)
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
            assert cur.fetchone() is None
