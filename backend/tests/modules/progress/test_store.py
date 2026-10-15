import pytest

from app.core.db import get_admin_connection, get_connection
from app.modules.progress import store


@pytest.fixture
def test_user_id():
    with get_admin_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO auth.users (name, email) VALUES ('Progress Test User', 'progress-test@example.com') "
                "RETURNING id"
            )
            user_id = cur.fetchone()[0]
        conn.commit()
    yield user_id
    with get_admin_connection() as conn:
        conn.execute("DELETE FROM auth.users WHERE id = %s", (user_id,))
        conn.commit()


def test_get_progress_for_brand_new_user_is_all_zero(test_user_id):
    with get_connection() as conn:
        progress = store.get_progress(conn, test_user_id)
    assert progress == {
        "xp_total": 0,
        "current_streak": 0,
        "longest_streak": 0,
        "badges": [],
        "completed_nodes": {},
    }


def test_record_node_completion_awards_xp_and_streak(test_user_id):
    with get_connection() as conn:
        result = store.record_node_completion(conn, test_user_id, "postgres", "node_1_base_load", "skill")
    assert result["newly_awarded_xp"] == 10
    assert result["xp_total"] == 10
    assert result["current_streak"] == 1
    assert result["completed_nodes"] == {"postgres": ["node_1_base_load"]}
    assert "first_steps" in result["new_badges"]


def test_completing_the_same_node_twice_does_not_double_award(test_user_id):
    with get_connection() as conn:
        store.record_node_completion(conn, test_user_id, "postgres", "node_1_base_load", "skill")
        second = store.record_node_completion(conn, test_user_id, "postgres", "node_1_base_load", "skill")
    assert second["newly_awarded_xp"] == 0
    assert second["xp_total"] == 10  # not 20
    assert second["new_badges"] == []


def test_completing_multiple_distinct_nodes_accumulates_xp(test_user_id):
    with get_connection() as conn:
        store.record_node_completion(conn, test_user_id, "postgres", "node_1_base_load", "skill")
        store.record_node_completion(conn, test_user_id, "postgres", "node_2_renamed_missing", "skill")
        final = store.record_node_completion(conn, test_user_id, "postgres", "review", "review")
    assert final["xp_total"] == 10 + 10 + 5
    assert sorted(final["completed_nodes"]["postgres"]) == [
        "node_1_base_load",
        "node_2_renamed_missing",
        "review",
    ]
