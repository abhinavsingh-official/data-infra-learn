import secrets
import threading

from app.core.db import get_admin_connection
from app.modules.lakehouse_phase.commit_batch import commit_batch
from app.modules.lakehouse_phase.session_provisioning import deprovision_session, provision_session


def _new_session():
    session_id = secrets.token_hex(16)
    with get_admin_connection() as conn:
        session_spark, _password = provision_session(conn, session_id)
    return session_id, session_spark


def _teardown(session_id):
    with get_admin_connection() as conn:
        deprovision_session(conn, session_id)


def test_commit_batch_requires_a_select():
    session_id, session_spark = _new_session()
    try:
        result = commit_batch(session_spark, session_id, "CREATE TABLE x USING DELTA AS SELECT 1 AS x")
        assert result.success is False
        assert result.error_code == "NOT_A_SELECT"
    finally:
        _teardown(session_id)


def test_commit_batch_requires_required_columns():
    session_id, session_spark = _new_session()
    try:
        result = commit_batch(session_spark, session_id, "SELECT 1 AS event_id, 2 AS amount")
        assert result.success is False
        assert result.error_code == "MISSING_REQUIRED_COLUMNS"
    finally:
        _teardown(session_id)


def test_commit_batch_rejects_multiple_statements():
    session_id, session_spark = _new_session()
    try:
        result = commit_batch(session_spark, session_id, "SELECT 1 AS event_id; SELECT 2 AS event_id")
        assert result.success is False
        assert result.error_code == "MULTIPLE_STATEMENTS"
    finally:
        _teardown(session_id)


def test_real_commit_creates_a_delta_table_at_version_zero():
    session_id, session_spark = _new_session()
    try:
        result = commit_batch(
            session_spark,
            session_id,
            "SELECT '1' AS event_id, 5.0 AS amount, 'Acme' AS merchant, 'USD' AS currency, "
            "TIMESTAMP'2024-01-01 00:00:00' AS event_timestamp",
        )
        assert result.success is True
        assert result.version == 0
        assert result.row_count == 1
        assert session_spark.catalog.tableExists("clean_transactions")
    finally:
        _teardown(session_id)


def test_schema_mismatch_is_rejected_atomically_not_a_crash():
    """Real ACID guarantee, confirmed directly: a batch whose amount
    column can't be coerced to the required numeric type is rejected by
    Delta's own schema enforcement, and the table's version does NOT
    advance - a failed write never partially commits."""
    session_id, session_spark = _new_session()
    try:
        first = commit_batch(
            session_spark,
            session_id,
            "SELECT '1' AS event_id, 5.0 AS amount, 'Acme' AS merchant, 'USD' AS currency, "
            "TIMESTAMP'2024-01-01 00:00:00' AS event_timestamp",
        )
        assert first.success is True
        assert first.version == 0

        # amount as a non-numeric string - should fail to cast against the
        # existing double column, not silently coerce or crash
        bad = commit_batch(
            session_spark,
            session_id,
            "SELECT '2' AS event_id, 'not-a-number' AS amount, 'Beta' AS merchant, "
            "'USD' AS currency, TIMESTAMP'2024-01-02 00:00:00' AS event_timestamp",
        )
        assert bad.success is False
        assert bad.error_code is not None

        history = session_spark.sql("DESCRIBE HISTORY clean_transactions").collect()
        assert max(row["version"] for row in history) == 0  # unaffected by the failed write
    finally:
        _teardown(session_id)


def test_concurrent_commits_get_unique_sequential_versions_not_a_race():
    """Regression for the DuckDB-era version of this bug: with only the
    read under the per-session lock (not the actual Delta write),
    concurrent commit_batch() calls against one session could race on
    the real write. Extending the lock over the whole commit (read +
    write) fixes both wasted conflicts and incorrect version reporting."""
    session_id, session_spark = _new_session()
    try:
        results = []

        def run(n):
            results.append(
                commit_batch(
                    session_spark,
                    session_id,
                    f"SELECT '{n}' AS event_id, 1.0 AS amount, 'x' AS merchant, 'USD' AS currency, "
                    "TIMESTAMP'2024-01-01 00:00:00' AS event_timestamp",
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
