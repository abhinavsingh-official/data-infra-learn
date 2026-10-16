from datetime import date

from app.modules.daily_challenge.content import PYTHON_CHALLENGE_POOL, SQL_CHALLENGE_POOL
from app.modules.daily_challenge.selection import (
    daily_node_id,
    pick_python_problem,
    pick_sql_problem,
    tier_for_completions,
)


def test_tier_for_completions_steps_every_five_and_caps_at_three():
    assert tier_for_completions(0) == 1
    assert tier_for_completions(4) == 1
    assert tier_for_completions(5) == 2
    assert tier_for_completions(9) == 2
    assert tier_for_completions(10) == 3
    assert tier_for_completions(1000) == 3


def test_pick_sql_problem_matches_requested_tier_when_available():
    problem = pick_sql_problem(SQL_CHALLENGE_POOL, tier=2, today=date(2026, 10, 16))
    assert problem["difficulty"] == 2


def test_pick_is_deterministic_for_the_same_day():
    today = date(2026, 10, 16)
    first = pick_sql_problem(SQL_CHALLENGE_POOL, tier=1, today=today)
    second = pick_sql_problem(SQL_CHALLENGE_POOL, tier=1, today=today)
    assert first["id"] == second["id"]


def test_sql_and_python_picks_can_differ_in_relative_index():
    today = date(2026, 10, 16)
    sql = pick_sql_problem(SQL_CHALLENGE_POOL, tier=1, today=today)
    python = pick_python_problem(PYTHON_CHALLENGE_POOL, tier=1, today=today)
    assert sql["id"] != python["id"]  # different pools anyway, but confirms both resolve


def test_daily_node_id_is_namespaced_by_date():
    assert daily_node_id("sql_tier1_filter_sort", date(2026, 10, 16)) == "2026-10-16_sql_tier1_filter_sort"
    assert daily_node_id("sql_tier1_filter_sort", date(2026, 10, 17)) != daily_node_id(
        "sql_tier1_filter_sort", date(2026, 10, 16)
    )
