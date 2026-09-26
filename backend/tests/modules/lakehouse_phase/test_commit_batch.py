import secrets
import threading

from deltalake import DeltaTable

from app.core.db import get_admin_connection
from app.modules.lakehouse_phase.commit_batch import commit_batch
from app.modules.lakehouse_phase.session_provisioning import (
    delta_table_dir,
    deprovision_session,
    pg_role_name,
    provision_session,
)


def _new_session():
    session_id = secrets.token_hex(16)
    with get_admin_connection() as conn:
        password = provision_session(conn, session_id)
    return session_id, pg_role_name(session_id), password


def _teardown(session_id):
    with get_admin_connection() as conn:
        deprovision_session(conn, session_id)


def test_commit_batch_requires_a_select():
    session_id, role, password = _new_session()
    try:
        result = commit_batch(session_id, role, password, "CREATE TABLE x AS SELECT 1")
        assert result.success is False
        assert result.error_code == "NOT_A_SELECT"
    finally:
        _teardown(session_id)


def test_commit_batch_requires_required_columns():
    session_id, role, password = _new_session()
    try:
        result = commit_batch(session_id, role, password, "SELECT 1 AS event_id, 2 AS amount")
        assert result.success is False
        assert result.error_code == "MISSING_REQUIRED_COLUMNS"
    finally:
        _teardown(session_id)


def test_commit_batch_rejects_multiple_statements():
    session_id, role, password = _new_session()
    try:
        result = commit_batch(session_id, role, password, "SELECT 1 AS event_id; SELECT 2 AS event_id")
        assert result.success is False
        assert result.error_code == "MULTIPLE_STATEMENTS"
    finally:
        _teardown(session_id)


def test_real_commit_creates_a_delta_table_at_version_zero():
    session_id, role, password = _new_session()
    try:
        result = commit_batch(
            session_id,
            role,
            password,
            "SELECT '1' AS event_id, 5.0 AS amount, 'Acme' AS merchant, 'USD' AS currency, "
            "TIMESTAMPTZ '2024-01-01 00:00:00+00' AS event_timestamp",
        )
        assert result.success is True
        assert result.version == 0
        assert result.row_count == 1
        assert (delta_table_dir(session_id) / "_delta_log").is_dir()
    finally:
        _teardown(session_id)


def test_schema_mismatch_is_rejected_atomically_not_a_crash():
    """Real ACID guarantee, confirmed directly: a batch whose amount
    column can't be coerced to the required numeric type is rejected -
    caught by the canonical-schema cast before it ever reaches deltalake
    in this specific case (confirmed by testing directly which layer
    actually raises) - and the table's version does NOT advance either
    way. Whichever layer catches it, the failed write never partially
    commits."""
    session_id, role, password = _new_session()
    try:
        first = commit_batch(
            session_id,
            role,
            password,
            "SELECT '1' AS event_id, 5.0 AS amount, 'Acme' AS merchant, 'USD' AS currency, "
            "TIMESTAMPTZ '2024-01-01 00:00:00+00' AS event_timestamp",
        )
        assert first.success is True
        assert first.version == 0

        # amount as a non-numeric string - should fail to cast against the
        # existing Float64 column, not silently coerce or crash
        bad = commit_batch(
            session_id,
            role,
            password,
            "SELECT '2' AS event_id, 'not-a-number'::VARCHAR AS amount, 'Beta' AS merchant, "
            "'USD' AS currency, TIMESTAMPTZ '2024-01-02 00:00:00+00' AS event_timestamp",
        )
        assert bad.success is False
        assert bad.error_code is not None

        dt = DeltaTable(str(delta_table_dir(session_id)))
        assert dt.version() == 0  # unaffected by the failed write
    finally:
        _teardown(session_id)


def test_concurrent_commits_get_unique_sequential_versions_not_a_race():
    """Regression: with only the DuckDB read under the per-session lock
    (not the actual write_deltalake call), 8 concurrent commit_batch()
    calls against one session raced on the real Delta write - 4 of 8
    failed with a genuine CommitFailedError (Delta's own optimistic
    concurrency control caught it, nothing corrupted), but two of the
    "successful" ones both reported version=1, a wrong result for an API
    caller to receive. Extending the lock over the whole commit fixes
    both the wasted conflicts and the incorrect version reporting."""
    session_id, role, password = _new_session()
    try:
        results = []

        def run(n):
            results.append(
                commit_batch(
                    session_id,
                    role,
                    password,
                    f"SELECT '{n}' AS event_id, 1.0 AS amount, 'x' AS merchant, 'USD' AS currency, "
                    "TIMESTAMPTZ '2024-01-01' AS event_timestamp",
                )
            )

        threads = [threading.Thread(target=run, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 8
        assert all(r.success for r in results), [r.error_message for r in results if not r.success]
        versions = sorted(r.version for r in results)
        assert versions == list(range(8))
    finally:
        _teardown(session_id)
