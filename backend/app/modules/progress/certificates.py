"""Module 22: certificates, per MODULE_13_PLAN.md's own decision -
"purely vanity, format doesn't matter," unlocked after finishing EVERY
node in a paradigm's tree, not just its capstone. Module 18/20's SQL and
NoSQL splits mean "a paradigm" today is really a small group of tracks
(SQL Databases + Postgres; MongoDB Databases + NoSQL; Warehouse Databases
+ Warehouse) - a certificate covers the whole group, matching how `/sql`,
`/nosql`, and `/warehouse` already present themselves as one umbrella to
the learner, not two separate things to finish."""

from app.modules.mongo_databases_track.skill_tree import MONGO_DATABASES_SKILL_TREE
from app.modules.lake_phase.skill_tree import LAKE_SKILL_TREE
from app.modules.lakehouse_phase.skill_tree import LAKEHOUSE_SKILL_TREE
from app.modules.nosql_phase.skill_tree import NOSQL_SKILL_TREE
from app.modules.postgres_phase.skill_tree import POSTGRES_SKILL_TREE
from app.modules.sql_databases_track.skill_tree import SQL_DATABASES_SKILL_TREE
from app.modules.warehouse_databases_track.skill_tree import WAREHOUSE_DATABASES_SKILL_TREE
from app.modules.warehouse_phase.skill_tree import WAREHOUSE_SKILL_TREE

# Every skill tree that exists, keyed by its own `paradigm` field -
# deliberately broader than node_practice._SKILL_TREES (which only lists
# the gradable ones): a certificate needs to count capstone nodes too,
# and the capstone-only wrappers (nosql/warehouse/lake/lakehouse) have no
# gradable nodes of their own at all.
_ALL_TREES: dict[str, dict] = {
    "postgres": POSTGRES_SKILL_TREE,
    "sql-databases": SQL_DATABASES_SKILL_TREE,
    "mongo-databases": MONGO_DATABASES_SKILL_TREE,
    "nosql": NOSQL_SKILL_TREE,
    "warehouse-databases": WAREHOUSE_DATABASES_SKILL_TREE,
    "warehouse": WAREHOUSE_SKILL_TREE,
    "lake": LAKE_SKILL_TREE,
    "lakehouse": LAKEHOUSE_SKILL_TREE,
}

CERTIFICATE_GROUPS: dict[str, dict] = {
    "sql": {"label": "SQL", "paradigms": ["sql-databases", "postgres"]},
    "nosql": {"label": "NoSQL", "paradigms": ["mongo-databases", "nosql"]},
    "warehouse": {"label": "Data Warehouse", "paradigms": ["warehouse-databases", "warehouse"]},
    "lake": {"label": "Data Lake", "paradigms": ["lake"]},
    "lakehouse": {"label": "Lakehouse", "paradigms": ["lakehouse"]},
}


def _required_node_ids(paradigm: str) -> list[str]:
    tree = _ALL_TREES[paradigm]
    return [node["id"] for node in tree["nodes"] if node["type"] in ("skill", "capstone")]


def certificate_status(completed_nodes: dict[str, list[str]]) -> dict[str, dict]:
    status: dict[str, dict] = {}
    for group_id, group in CERTIFICATE_GROUPS.items():
        required = [
            (paradigm, node_id) for paradigm in group["paradigms"] for node_id in _required_node_ids(paradigm)
        ]
        done = sum(1 for paradigm, node_id in required if node_id in completed_nodes.get(paradigm, []))
        status[group_id] = {
            "label": group["label"],
            "completed": done,
            "total": len(required),
            "unlocked": len(required) > 0 and done == len(required),
        }
    return status
