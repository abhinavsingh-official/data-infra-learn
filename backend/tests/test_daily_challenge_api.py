import secrets
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.db import get_admin_connection
from app.main import app

client = TestClient(app)


@pytest.fixture
def signed_in_session():
    """Same fixture shape as test_progress_api.py's own - a real
    auth.users + auth.sessions row, standing in for a real Google sign-in
    that isn't scriptable from here."""
    token = secrets.token_hex(32)
    expires = datetime.now(timezone.utc) + timedelta(days=1)
    with get_admin_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO auth.users (name, email) VALUES ('Daily Challenge Test User', "
                "'daily-challenge-api-test@example.com') RETURNING id"
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


def test_today_requires_sign_in():
    assert client.get("/progress/daily/today").status_code == 401


def test_today_returns_both_tracks_without_leaking_the_answer(signed_in_session):
    response = client.get("/progress/daily/today", headers={"X-Session-Token": signed_in_session})
    assert response.status_code == 200
    body = response.json()
    assert "expected_output_rows" not in body["sql"]
    assert "test_cases" not in body["python"]
    assert body["sql"]["completed_today"] is False
    assert body["python"]["completed_today"] is False


def test_today_is_stable_across_repeated_calls_same_day(signed_in_session):
    first = client.get("/progress/daily/today", headers={"X-Session-Token": signed_in_session}).json()
    second = client.get("/progress/daily/today", headers={"X-Session-Token": signed_in_session}).json()
    assert first["sql"]["id"] == second["sql"]["id"]
    assert first["python"]["id"] == second["python"]["id"]


def test_sql_check_requires_sign_in():
    assert client.post("/progress/daily/sql/check", json={"sql": "SELECT 1"}).status_code == 401


def test_wrong_sql_fails_without_awarding_progress(signed_in_session):
    response = client.post(
        "/progress/daily/sql/check",
        json={"sql": "SELECT 1 WHERE false"},
        headers={"X-Session-Token": signed_in_session},
    )
    assert response.status_code == 200
    assert response.json()["passed"] is False
    assert "progress" not in response.json()


def test_correct_sql_passes_and_awards_xp_and_marks_completed_today(signed_in_session):
    today = client.get("/progress/daily/today", headers={"X-Session-Token": signed_in_session}).json()
    sql_problem = today["sql"]

    # Tier-1 problems in the pool only ever need WHERE/GROUP BY - a
    # correct-for-every-tier-1-problem submission doesn't exist, so this
    # test asserts against whichever problem id today's rotation actually
    # picked rather than hardcoding one query.
    reference_by_id = {
        "sql_tier1_filter_sort": "SELECT id, channel, transaction_amount FROM transactions "
        "WHERE channel = 'online' ORDER BY id",
        "sql_tier1_count_group": "SELECT account_id, COUNT(*) AS transaction_count FROM transactions "
        "GROUP BY account_id ORDER BY account_id",
        "sql_tier2_join_refunds": "SELECT t.id AS transaction_id, t.transaction_amount, r.refund_amount "
        "FROM transactions t JOIN refunds r ON r.transaction_id = t.id ORDER BY t.id",
        "sql_tier2_having": "SELECT account_id, SUM(transaction_amount) AS total FROM transactions "
        "GROUP BY account_id HAVING SUM(transaction_amount) > 500 ORDER BY account_id",
        "sql_tier3_running_total": "SELECT id, account_id, transaction_amount, "
        "SUM(transaction_amount) OVER (PARTITION BY account_id ORDER BY id) AS running_total FROM transactions",
        "sql_tier3_dedupe_redelivered": "SELECT event_id, amount FROM ("
        "  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY received_at) AS rn FROM raw_events"
        ") t WHERE rn = 1 ORDER BY event_id",
    }
    sql = reference_by_id[sql_problem["id"]]

    response = client.post(
        "/progress/daily/sql/check", json={"sql": sql}, headers={"X-Session-Token": signed_in_session}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["passed"] is True
    assert body["progress"]["xp_total"] == 10

    again = client.get("/progress/daily/today", headers={"X-Session-Token": signed_in_session}).json()
    assert again["sql"]["completed_today"] is True


def test_correct_python_passes_and_awards_xp(signed_in_session):
    today = client.get("/progress/daily/today", headers={"X-Session-Token": signed_in_session}).json()
    python_problem = today["python"]

    reference_by_function = {
        "dedupe_preserve_order": "def dedupe_preserve_order(items):\n"
        "    seen = set()\n    out = []\n"
        "    for x in items:\n"
        "        if x not in seen:\n"
        "            seen.add(x)\n            out.append(x)\n"
        "    return out\n",
        "total_amount": "def total_amount(transactions):\n    return sum(t['amount'] for t in transactions)\n",
        "group_by_key": "def group_by_key(records, key):\n"
        "    groups = {}\n"
        "    for r in records:\n"
        "        groups.setdefault(r[key], []).append(r)\n"
        "    return groups\n",
        "running_total": "def running_total(amounts):\n"
        "    out = []\n    total = 0\n"
        "    for a in amounts:\n        total += a\n        out.append(total)\n"
        "    return out\n",
        "dedupe_by_key_keep_latest": "def dedupe_by_key_keep_latest(records, key, timestamp_key):\n"
        "    winners = {}\n"
        "    for r in records:\n"
        "        existing = winners.get(r[key])\n"
        "        if existing is None or r[timestamp_key] > existing[timestamp_key]:\n"
        "            winners[r[key]] = r\n"
        "    return winners\n",
        "parse_fixed_width": "def parse_fixed_width(line, widths):\n"
        "    out = []\n    pos = 0\n"
        "    for w in widths:\n        out.append(line[pos:pos + w].strip())\n        pos += w\n"
        "    return out\n",
    }
    code = reference_by_function[python_problem["function_name"]]

    response = client.post(
        "/progress/daily/python/check", json={"code": code}, headers={"X-Session-Token": signed_in_session}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["passed"] is True
    assert body["progress"]["xp_total"] == 10
