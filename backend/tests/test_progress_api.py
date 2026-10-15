import secrets
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.db import get_admin_connection
from app.main import app

client = TestClient(app)

_CORRECT_NODE_1_SQL = (
    "SELECT payload->>'event_id' AS event_id, "
    "(payload->>'amount')::numeric AS amount, "
    "payload->>'merchant' AS merchant, "
    "payload->>'currency' AS currency, "
    "(payload->>'timestamp')::timestamptz AS event_timestamp "
    "FROM raw_transaction_events"
)


@pytest.fixture
def signed_in_session():
    """Inserts a real auth.users + auth.sessions row directly - exactly
    what Auth.js's own adapter would have written after a real Google
    sign-in - so this test doesn't need a real OAuth flow (and can't:
    Google's own login page isn't scriptable from here)."""
    token = secrets.token_hex(32)
    expires = datetime.now(timezone.utc) + timedelta(days=1)
    with get_admin_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO auth.users (name, email) VALUES ('API Test User', 'progress-api-test@example.com') "
                "RETURNING id"
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


def test_progress_me_requires_sign_in():
    response = client.get("/progress/me")
    assert response.status_code == 401


def test_progress_me_for_signed_in_user_starts_empty(signed_in_session):
    response = client.get("/progress/me", headers={"X-Session-Token": signed_in_session})
    assert response.status_code == 200
    assert response.json()["xp_total"] == 0


def test_check_node_requires_sign_in():
    response = client.post(
        "/progress/nodes/postgres/node_1_base_load/check", json={"sql": "SELECT 1"}
    )
    assert response.status_code == 401


def test_check_node_unknown_node_returns_404(signed_in_session):
    response = client.post(
        "/progress/nodes/postgres/does-not-exist/check",
        json={"sql": "SELECT 1"},
        headers={"X-Session-Token": signed_in_session},
    )
    assert response.status_code == 404


def test_correct_submission_passes_and_updates_progress(signed_in_session):
    check = client.post(
        "/progress/nodes/postgres/node_1_base_load/check",
        json={"sql": _CORRECT_NODE_1_SQL},
        headers={"X-Session-Token": signed_in_session},
    )
    assert check.status_code == 200
    body = check.json()
    assert body["passed"] is True
    assert body["progress"]["xp_total"] == 10
    assert body["progress"]["completed_nodes"] == {"postgres": ["node_1_base_load"]}

    me = client.get("/progress/me", headers={"X-Session-Token": signed_in_session})
    assert me.json()["xp_total"] == 10
