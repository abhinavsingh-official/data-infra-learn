"""Module 16: XP, streak, and badge rules - the gamification layer over
real node completions. Values/thresholds are a first pass (tunable
later, not grounded in external research the way the curriculum content
itself is), since this is reward-shaping for a single-learner portfolio
demo, not a tuned production retention system."""

from dataclasses import dataclass
from datetime import date, timedelta

XP_BY_NODE_TYPE = {
    "skill": 10,
    "review": 5,
    "capstone": 50,
}
DEFAULT_NODE_XP = 10

NODE_COUNT_BADGES = [
    (1, "first_steps", "Completed your first node"),
    (5, "node_novice", "Completed 5 nodes"),
    (20, "node_adept", "Completed 20 nodes"),
]
STREAK_BADGES = [
    (3, "streak_3", "3-day streak"),
    (7, "streak_7", "7-day streak"),
    (30, "streak_30", "30-day streak"),
]
XP_BADGES = [
    (100, "xp_100", "Earned 100 XP"),
    (500, "xp_500", "Earned 500 XP"),
]


@dataclass
class Badge:
    badge_id: str
    label: str


def xp_for_node(node_type: str) -> int:
    return XP_BY_NODE_TYPE.get(node_type, DEFAULT_NODE_XP)


def update_streak(
    last_activity_date: date | None, today: date, current_streak: int, longest_streak: int
) -> tuple[int, int]:
    """Same calendar day as the last recorded activity -> streak
    unchanged (completing a second node today doesn't double-count the
    day). Exactly one day later -> increments. Any larger gap (or no
    prior activity) -> resets to 1, today being day one of a new streak."""
    if last_activity_date == today:
        new_current = current_streak
    elif last_activity_date == today - timedelta(days=1):
        new_current = current_streak + 1
    else:
        new_current = 1
    return new_current, max(longest_streak, new_current)


def newly_earned_badges(
    *, total_nodes_completed: int, current_streak: int, xp_total: int, already_earned: set[str]
) -> list[Badge]:
    earned: list[Badge] = []
    for threshold, badge_id, label in NODE_COUNT_BADGES:
        if total_nodes_completed >= threshold and badge_id not in already_earned:
            earned.append(Badge(badge_id, label))
    for threshold, badge_id, label in STREAK_BADGES:
        if current_streak >= threshold and badge_id not in already_earned:
            earned.append(Badge(badge_id, label))
    for threshold, badge_id, label in XP_BADGES:
        if xp_total >= threshold and badge_id not in already_earned:
            earned.append(Badge(badge_id, label))
    return earned
