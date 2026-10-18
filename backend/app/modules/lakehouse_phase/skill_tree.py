"""Lakehouse-phase skill tree - a thin intro+capstone wrapper around
LAKEHOUSE_PHASE_TASK. No sibling fundamentals track: the transaction
log, atomic commits, and time travel are real Delta semantics with no
Postgres equivalent to grade against."""

from app.modules.lakehouse_phase.task_content import LAKEHOUSE_PHASE_TASK

LAKEHOUSE_SKILL_TREE = {
    "paradigm": "lakehouse",
    "nodes": [
        {
            "id": "intro",
            "type": "intro",
            "title": "ACID on object storage: the transaction log",
            "body": (
                "A lake alone has no atomicity - two concurrent writers can corrupt the same "
                "directory, and there's no way to ask 'what did this table look like an hour "
                "ago.' A lakehouse closes that gap by keeping a transaction log next to the data "
                "files: every write is a numbered commit, so the table has real ACID guarantees "
                "and you can query any prior commit directly - the actual feature this capstone "
                "exercises."
            ),
        },
        {
            "id": "capstone",
            "type": "capstone",
            "title": LAKEHOUSE_PHASE_TASK["title"],
            "task_ref": "lakehouse",
            "note": (
                "The real task, against real Delta Lake - commit two incremental batches, dedupe "
                "both within and across batches, then confirm it with real time travel "
                "(DESCRIBE HISTORY, VERSION AS OF)."
            ),
        },
    ],
}
