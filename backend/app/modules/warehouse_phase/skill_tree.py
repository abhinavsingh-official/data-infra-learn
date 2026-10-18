"""Warehouse-phase skill tree - a thin intro+capstone wrapper around
WAREHOUSE_PHASE_TASK. No step-by-step nodes: the reference solution runs
on real Spark/Delta (SCD2 via MERGE INTO), which node_practice's
plain-Postgres engine can't grade. The fundamentals live in
warehouse_databases_track instead."""

from app.modules.warehouse_phase.task_content import WAREHOUSE_PHASE_TASK

WAREHOUSE_SKILL_TREE = {
    "paradigm": "warehouse",
    "nodes": [
        {
            "id": "intro",
            "type": "intro",
            "title": "Dimensional modeling: optimized for analytics, not transactions",
            "body": (
                "A warehouse reshapes the same source data around how it gets queried, not how "
                "it gets written - a star schema (one fact table, several dimension tables) makes "
                "'total spend by card network, by month' a simple JOIN + GROUP BY instead of a "
                "query across a dozen OLTP tables. The Warehouse Databases track right before this "
                "covers that shape on small data; this capstone builds the real star schema, then "
                "survives a dimension that changes underneath it."
            ),
        },
        {
            "id": "capstone",
            "type": "capstone",
            "title": WAREHOUSE_PHASE_TASK["title"],
            "task_ref": "warehouse",
            "note": (
                "The real task, against real Spark + Delta - build dim_users/dim_accounts/"
                "fact_transactions, then handle a Slowly Changing Dimension (SCD Type 2) when "
                "an account's own attributes change on a later load."
            ),
        },
    ],
}
