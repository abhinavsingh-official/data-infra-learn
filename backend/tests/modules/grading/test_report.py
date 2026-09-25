import secrets

import psycopg

from app.core.config import get_settings
from app.core.db import get_admin_connection
from app.modules.grading.report import grade_submission
from app.modules.postgres_phase.session_provisioning import deprovision_session, provision_session, role_name


def _new_session():
    session_id = secrets.token_hex(16)
    with get_admin_connection() as conn:
        password = provision_session(conn, session_id)
    return session_id, password


def _session_dsn(role: str, password: str) -> str:
    settings = get_settings()
    return f"postgresql://{role}:{password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"


def test_submission_with_no_dedup_fails_with_real_duplicate_remediation():
    """Reproduces the exact bug found by manual testing: a uniqueness
    violation used to map to an unhelpful 'UNKNOWN' error code instead of
    the real duplicate-delivery remediation."""
    session_id, password = _new_session()
    role = role_name(session_id)
    try:
        with psycopg.connect(_session_dsn(role, password)) as conn:
            conn.execute(
                "CREATE TABLE clean_transactions "
                "(event_id text, amount numeric, merchant text, currency text, event_timestamp timestamptz)"
            )
            conn.execute(
                "INSERT INTO clean_transactions "
                "SELECT payload->>'event_id', 1, payload->>'merchant', 'USD', received_at "
                "FROM public.raw_transaction_events LIMIT 500"
            )
            conn.commit()

        report = grade_submission(role, password)
        assert report.passed is False
        assert len(report.structural_findings) > 0
        finding = report.structural_findings[0]
        assert finding.error_code == "ERR_DUPLICATE_DELIVERY"
        assert "Deduplicate" in finding.fix
    finally:
        with get_admin_connection() as conn:
            deprovision_session(conn, session_id)


def test_complete_submission_passes_with_zero_findings():
    session_id, password = _new_session()
    role = role_name(session_id)
    try:
        with psycopg.connect(_session_dsn(role, password)) as conn:
            conn.execute(
                "CREATE TABLE clean_transactions "
                "(event_id text unique, amount numeric, merchant text, currency text, event_timestamp timestamptz)"
            )
            conn.execute(
                """
                INSERT INTO clean_transactions (event_id, amount, merchant, currency, event_timestamp)
                SELECT DISTINCT ON (payload->>'event_id')
                  payload->>'event_id',
                  CASE WHEN jsonb_typeof(payload->'amount') = 'number' THEN (payload->>'amount')::numeric / 100
                       WHEN payload ? 'amount' THEN (payload->>'amount')::numeric
                       ELSE 1 END,
                  COALESCE(payload->>'merchant', payload->>'merchant_name', 'UNKNOWN'),
                  COALESCE(payload->>'currency', 'USD'),
                  COALESCE(NULLIF(payload->>'timestamp', '')::timestamptz, received_at)
                FROM public.raw_transaction_events
                WHERE payload ? 'event_id'
                ORDER BY payload->>'event_id', received_at ASC
                """
            )
            conn.commit()

        report = grade_submission(role, password)
        assert report.passed is True
        assert report.structural_findings == []
        assert report.fault_findings == []
        assert report.total_clean_rows > 0
    finally:
        with get_admin_connection() as conn:
            deprovision_session(conn, session_id)
