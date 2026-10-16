"""Deterministic daily rotation plus a simple adaptive-difficulty rule.

Rather than track per-attempt accuracy (which would need a new table -
the progress schema only records completions, not every attempt),
difficulty tier is tied directly to completion count, already available
via progress.node_completions with zero new schema: every 5 completed
daily challenges on a track raises its tier by one, up to tier 3. This
is a simple first pass, similar to xp_rules.py's XP amounts, not a
claim that it's the most sophisticated possible version."""

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
