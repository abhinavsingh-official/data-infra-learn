"""A thin skill-tree wrapper around nosql_phase's existing capstone
task - mirrors postgres_phase.skill_tree's intro+capstone shape, but has
no step-by-step skill nodes of its own. Postgres's skill tree can source
teach/practice content from its own reference_solution.steps (a staged,
one-edge-case-at-a-time breakdown); the NoSQL capstone's
reference_solution isn't staged that way, and its real exercise is an
open-ended design question ("what do you embed/cap/aggregate"), not a
sequence of individually-gradable edge cases - so there's nothing to
turn into skill nodes here. The node-by-node fundamentals (find,
$lookup, $group, $ifNull) live in the separate mongo_databases_track
instead, the same division of labor the SQL umbrella uses between
sql_databases_track and postgres_phase."""

from app.modules.nosql_phase.task_content import NOSQL_PHASE_TASK

NOSQL_SKILL_TREE = {
    "paradigm": "nosql",
    "nodes": [
        {
            "id": "intro",
            "type": "intro",
            "title": "From five relational tables to one document",
            "body": (
                "The MongoDB Databases track just covered find, $lookup, $group, and $ifNull on "
                "small, hand-sized collections someone else modeled for you. This capstone is the "
                "other half: the same real fintech data from the relational phase - users, "
                "accounts, transactions, reward_events, repayments - and it's on you to decide "
                "what belongs embedded in one account_profiles document, what gets capped, and "
                "what gets aggregated instead of copied raw, at real 15,000-account scale."
            ),
        },
        {
            "id": "capstone",
            "type": "capstone",
            "title": NOSQL_PHASE_TASK["title"],
            "task_ref": "nosql",
            "note": (
                "Design and populate account_profiles from the real relational source - no "
                "hand-sized seed data this time, the actual edge cases (an unbounded embedded "
                "array, a stale copy of a 1:1 relationship, a raw list instead of an aggregate) "
                "are yours to find and avoid."
            ),
        },
    ],
}
