import secrets
import threading

from app.core.db import get_admin_connection
from app.modules.warehouse_phase.session_provisioning import (
    deprovision_session,
    execute,
    provision_session,
)


def _new_session():
    session_id = secrets.token_hex(16)
    with get_admin_connection() as conn:
        session_spark, _password = provision_session(conn, session_id)
    return session_id, session_spark


def _teardown(session_id):
    with get_admin_connection() as conn:
        deprovision_session(conn, session_id)


def test_execute_can_query_local_snapshot_and_live_source_views():
    session_id, session_spark = _new_session()
    try:
        result = execute(session_spark, session_id, "SELECT COUNT(*) FROM source_accounts_snapshot")
        assert result.success is True
        assert result.rows[0][0] > 0

        result = execute(session_spark, session_id, "SELECT COUNT(*) FROM users")
        assert result.success is True
        assert result.rows[0][0] > 0
    finally:
        _teardown(session_id)


def test_execute_returns_structured_error_for_bad_sql_not_a_crash():
    session_id, session_spark = _new_session()
    try:
        result = execute(session_spark, session_id, "SELECT * FROM this_table_does_not_exist")
        assert result.success is False
        assert result.error_code is not None
        assert result.error_message
    finally:
        _teardown(session_id)


def test_execute_rejects_multiple_statements():
    session_id, session_spark = _new_session()
    try:
        result = execute(session_spark, session_id, "SELECT 1; SELECT 2")
        assert result.success is False
        assert result.error_code == "MULTIPLE_STATEMENTS"
    finally:
        _teardown(session_id)


def test_execute_decimal_columns_are_jsonable_floats_not_strings():
    """Regression: Spark's driver returns Decimal for DECIMAL/NUMERIC
    columns, same as psycopg/DuckDB do - which FastAPI's bare `-> dict`
    response serialization renders as a quoted string instead of a
    number (see postgres_phase/sql_execution.py's identical fix)."""
    session_id, session_spark = _new_session()
    try:
        result = execute(session_spark, session_id, "SELECT credit_limit FROM source_accounts_snapshot LIMIT 1")
        assert result.success is True
        assert isinstance(result.rows[0][0], float)
    finally:
        _teardown(session_id)


def test_concurrent_execute_against_the_same_session_does_not_collide():
    session_id, session_spark = _new_session()
    try:
        results = []

        def run():
            results.append(execute(session_spark, session_id, "SELECT COUNT(*) FROM users"))

        threads = [threading.Thread(target=run) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 8
        assert all(r.success for r in results), [r.error_message for r in results if not r.success]
    finally:
        _teardown(session_id)
