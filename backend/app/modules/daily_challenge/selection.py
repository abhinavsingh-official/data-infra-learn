"""Module 21: deterministic daily rotation + a deliberately simple
adaptive-difficulty rule.

"Adaptive difficulty" has no further spec anywhere in this project's
planning docs beyond the one line in PLAN.md - CURRICULUM_STRUCTURE.md's
own research paragraph names the feature bundle (streak/accuracy/adaptive
difficulty) but doesn't define the adaptation rule itself. Rather than
invent a sophisticated per-attempt accuracy tracker (which would need a
new table - this project's progress schema only records completions, not
every attempt), this ties difficulty tier directly to completion count,
already available via progress.node_completions with zero new schema:
every 5 completed daily challenges on a track raises its tier by one, up
to tier 3. This is an honest, simple first pass - like xp_rules.py's own
documented stance on its XP amounts ("tunable later, not grounded in
external research"), not a claim this is the sophisticated version."""

from datetime import date

COMPLETIONS_PER_TIER_STEP = 5
MAX_TIER = 3


def tier_for_completions(completed_count: int) -> int:
    return min(MAX_TIER, 1 + completed_count // COMPLETIONS_PER_TIER_STEP)


def _pick(pool: list[dict], tier: int, today: date, salt: int) -> dict:
    candidates = [p for p in pool if p["difficulty"] == tier] or pool
    index = (today.toordinal() + salt) % len(candidates)
    return candidates[index]


def pick_sql_problem(pool: list[dict], tier: int, today: date) -> dict:
    return _pick(pool, tier, today, salt=0)


def pick_python_problem(pool: list[dict], tier: int, today: date) -> dict:
    return _pick(pool, tier, today, salt=7)


def daily_node_id(problem_id: str, today: date) -> str:
    """Namespaces a challenge's node_id by date, so the same conceptual
    "today's SQL challenge" slot in progress.node_completions can be
    completed again on a later day (that table's own primary key is
    (user_id, paradigm, node_id) - without the date in the id, solving a
    given problem once would mark it permanently done)."""
    return f"{today.isoformat()}_{problem_id}"
