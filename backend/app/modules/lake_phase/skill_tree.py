"""Lake-phase skill tree - a thin intro+capstone wrapper around
LAKE_PHASE_TASK. No step-by-step nodes: Parquet/partitioning/schema-on-
read have no Postgres analog, so node_practice's plain-Postgres engine
couldn't grade them faithfully. The capstone is the whole lesson."""

from app.modules.lake_phase.task_content import LAKE_PHASE_TASK

LAKE_SKILL_TREE = {
    "paradigm": "lake",
    "nodes": [
        {
            "id": "intro",
            "type": "intro",
            "title": "Schema-on-read: the file is the table",
            "body": (
                "Every approach so far enforced a schema the moment data was written. A lake "
                "flips that: raw files (here, partitioned Parquet) are written once, and whatever "
                "reads them decides the schema at read time - cheaper writes, but no guarantee "
                "every file agrees on what its own columns mean. Partitioning by date/key (not "
                "just file format) is what makes reading back a narrow slice fast instead of a "
                "full scan."
            ),
        },
        {
            "id": "capstone",
            "type": "capstone",
            "title": LAKE_PHASE_TASK["title"],
            "task_ref": "lake",
            "note": (
                "The real task, against real Spark - write the feed as partitioned Parquet, then "
                "read it back schema-on-read, absorbing renamed fields and deduping redelivered "
                "events along the way."
            ),
        },
    ],
}
