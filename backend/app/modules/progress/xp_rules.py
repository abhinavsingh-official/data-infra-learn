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

# Module 22: one badge per paradigm's real capstone, awarded on that
# capstone's grading report coming back `passed` (not via the node-check
# endpoint - the capstone node has no "practice" block of its own; it
# links out to the real full-scale session/grading flow instead). Keyed
# by the same paradigm string each phase's skill_tree.py and grade
# endpoint already use ("postgres", "nosql", "warehouse", "lake",
# "lakehouse").
CAPSTONE_BADGES: dict[str, tuple[str, str]] = {
    "postgres": ("relational_fundamentals", "Relational Fundamentals"),
    "nosql": ("document_modeler", "Document Modeler"),
    "warehouse": ("star_schema_builder", "Star Schema Builder"),
    "lake": ("schema_on_read_specialist", "Schema-on-Read Specialist"),
    "lakehouse": ("acid_on_object_storage", "ACID on Object Storage"),
}


@dataclass
class Badge:
    badge_id: str
    label: str


def capstone_badge_for(paradigm: str) -> Badge | None:
    entry = CAPSTONE_BADGES.get(paradigm)
    return Badge(entry[0], entry[1]) if entry else None


def all_badge_definitions() -> list[Badge]:
    """Every badge that can ever be earned, not just the ones a given
    user already has - the frontend's badge bar (Module 22) shows locked
    badges too, so it needs the full catalog, not just `progress.badges`
    rows."""
    definitions = [Badge(badge_id, label) for _, badge_id, label in NODE_COUNT_BADGES]
    definitions += [Badge(badge_id, label) for _, badge_id, label in STREAK_BADGES]
    definitions += [Badge(badge_id, label) for _, badge_id, label in XP_BADGES]
    definitions += [Badge(badge_id, label) for badge_id, label in CAPSTONE_BADGES.values()]
    return definitions


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
