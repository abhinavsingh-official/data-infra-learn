from datetime import date, timedelta

from app.modules.progress.xp_rules import newly_earned_badges, update_streak, xp_for_node


def test_xp_for_node_known_and_unknown_types():
    assert xp_for_node("skill") == 10
    assert xp_for_node("review") == 5
    assert xp_for_node("capstone") == 50
    assert xp_for_node("something_new") == 10  # falls back to DEFAULT_NODE_XP


def test_streak_same_day_does_not_double_count():
    today = date(2026, 10, 15)
    current, longest = update_streak(today, today, current_streak=3, longest_streak=5)
    assert current == 3
    assert longest == 5


def test_streak_consecutive_day_increments():
    today = date(2026, 10, 15)
    yesterday = today - timedelta(days=1)
    current, longest = update_streak(yesterday, today, current_streak=3, longest_streak=3)
    assert current == 4
    assert longest == 4


def test_streak_gap_resets_to_one():
    today = date(2026, 10, 15)
    three_days_ago = today - timedelta(days=3)
    current, longest = update_streak(three_days_ago, today, current_streak=10, longest_streak=10)
    assert current == 1
    assert longest == 10  # longest never decreases


def test_streak_no_prior_activity_starts_at_one():
    today = date(2026, 10, 15)
    current, longest = update_streak(None, today, current_streak=0, longest_streak=0)
    assert current == 1
    assert longest == 1


def test_newly_earned_badges_only_returns_crossed_not_already_held_thresholds():
    badges = newly_earned_badges(
        total_nodes_completed=5, current_streak=3, xp_total=100, already_earned=set()
    )
    badge_ids = {b.badge_id for b in badges}
    assert badge_ids == {"first_steps", "node_novice", "streak_3", "xp_100"}


def test_newly_earned_badges_excludes_already_held():
    badges = newly_earned_badges(
        total_nodes_completed=5,
        current_streak=3,
        xp_total=100,
        already_earned={"first_steps", "node_novice", "streak_3", "xp_100"},
    )
    assert badges == []
