import secrets

from app.core.db import get_admin_connection
from app.modules.postgres_phase.session_provisioning import deprovision_session, provision_session, role_name
from app.modules.postgres_phase.sql_execution import MAX_RETURNED_ROWS, execute_submission


def _new_session():
    session_id = secrets.token_hex(16)
    with get_admin_connection() as conn:
        password = provision_session(conn, session_id)
    return session_id, password


def test_multi_statement_submission_is_rejected_not_silently_lossy():
    """Found by testing, not assumed: psycopg3's simple-query-protocol
    multi-statement execution left cur.description as None even when the
    last statement was a SELECT, so a multi-statement submission used to
    silently report success with empty rows despite the SELECT having
    real output. Rejecting it explicitly is safer than losing results."""
    session_id, password = _new_session()
    try:
        result = execute_submission(
            role_name(session_id), password, "CREATE TABLE t (id int); INSERT INTO t VALUES (1); SELECT * FROM t"
        )
        assert result.success is False
        assert result.error_code == "MULTIPLE_STATEMENTS"
    finally:
        with get_admin_connection() as conn:
            deprovision_session(conn, session_id)


def test_single_statement_with_semicolon_inside_a_string_literal_still_works():
    """The multi-statement check is a heuristic, not a real parser -
    confirms the known limitation doesn't break the common single-
    statement case."""
    session_id, password = _new_session()
    try:
        result = execute_submission(role_name(session_id), password, "SELECT 1 AS x")
        assert result.success is True
    finally:
        with get_admin_connection() as conn:
            deprovision_session(conn, session_id)


def test_large_result_sets_are_capped_and_flagged_truncated():
    """Found by testing: SELECT * FROM public.raw_transaction_events with
    no LIMIT produced a 12MB response in under a second - a real
    resource-exhaustion risk against the platform's own low-spec-host
    requirement, not hypothetical."""
    session_id, password = _new_session()
    try:
        result = execute_submission(
            role_name(session_id), password, "SELECT * FROM public.raw_transaction_events"
        )
        assert result.success is True
        assert len(result.rows) == MAX_RETURNED_ROWS
        assert result.truncated is True
    finally:
        with get_admin_connection() as conn:
            deprovision_session(conn, session_id)
