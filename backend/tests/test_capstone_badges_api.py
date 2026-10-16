"""Module 22: confirms the real end-to-end wiring from a phase's own
/grade endpoint to a capstone badge - representative of all five phases
since the edit is mechanically identical in each, so one real,
full-stack proof (Postgres, the simplest/fastest phase to provision) is
enough rather than repeating the same shape five times against
Mongo/Spark infrastructure that's already separately tested elsewhere."""

import secrets
from datetime import datetime, timedelta, timezone

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.db import get_admin_connection
from app.main import app

client = TestClient(app)


@pytest.fixture
def signed_in_session():
    token = secrets.token_hex(32)
    expires = datetime.now(timezone.utc) + timedelta(days=1)
    with get_admin_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO auth.users (name, email) VALUES ('Capstone Badge Test User', "
                "'capstone-badge-api-test@example.com') RETURNING id"
            )
            user_id = cur.fetchone()[0]
            cur.execute(
                'INSERT INTO auth.sessions ("userId", expires, "sessionToken") VALUES (%s, %s, %s)',
                (user_id, expires, token),
            )
        conn.commit()
    yield token
    with get_admin_connection() as conn:
        conn.execute("DELETE FROM auth.users WHERE id = %s", (user_id,))
        conn.commit()


def _session_dsn(role: str, password: str) -> str:
    settings = get_settings()
    return f"postgresql://{role}:{password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"


def test_passing_the_real_capstone_awards_the_capstone_badge(signed_in_session):
    create = client.post("/postgres-phase/sessions")
    session_id = create.json()["session_id"]

    # The exact known-good reference pipeline from
    # tests/modules/grading/test_report.py's own
    # test_complete_submission_passes_with_zero_findings - run directly
    # against the role (not through /execute, since this needs a
    # multi-statement DDL+DML the execute endpoint runs one at a time
    # anyway) to keep this test focused on the grade-endpoint wiring, not
    # re-proving the grading engine itself already covered elsewhere.
    from app.modules.postgres_phase.session_provisioning import role_name
    from app.modules.postgres_phase.session_registry import get as get_session

    record = get_session(session_id)
    with psycopg.connect(_session_dsn(role_name(session_id), record.password)) as conn:
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

    grade = client.post(
        f"/postgres-phase/sessions/{session_id}/grade", headers={"X-Session-Token": signed_in_session}
    )
    assert grade.status_code == 200
    body = grade.json()
    assert body["passed"] is True
    assert "relational_fundamentals" in body["progress"]["new_badges"]

    me = client.get("/progress/me", headers={"X-Session-Token": signed_in_session})
    assert "relational_fundamentals" in me.json()["badges"]
    assert me.json()["completed_nodes"]["postgres"] == ["capstone"]

    client.delete(f"/postgres-phase/sessions/{session_id}")


def test_grading_without_sign_in_still_works_but_awards_nothing():
    create = client.post("/postgres-phase/sessions")
    session_id = create.json()["session_id"]

    from app.modules.postgres_phase.session_provisioning import role_name
    from app.modules.postgres_phase.session_registry import get as get_session

    record = get_session(session_id)
    with psycopg.connect(_session_dsn(role_name(session_id), record.password)) as conn:
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

    grade = client.post(f"/postgres-phase/sessions/{session_id}/grade")
    assert grade.status_code == 200
    assert grade.json()["passed"] is True
    assert "progress" not in grade.json()
    client.delete(f"/postgres-phase/sessions/{session_id}")
