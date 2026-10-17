"""Certificates - purely a vanity reward, unlocked after finishing EVERY
node in a paradigm's tree, not just its capstone. The SQL and NoSQL
umbrellas each span two tracks (SQL Databases + Postgres; MongoDB
Databases + NoSQL; Warehouse Databases + Warehouse), so "a paradigm"
here is really a small group of tracks - a certificate covers the whole
group, matching how `/sql`, `/nosql`, and `/warehouse` already present
themselves as one umbrella to the learner, not two separate things to
finish."""

from app.modules.lake_databases_track.skill_tree import LAKE_DATABASES_SKILL_TREE
from app.modules.lakehouse_databases_track.skill_tree import LAKEHOUSE_DATABASES_SKILL_TREE
from app.modules.mongo_databases_track.skill_tree import MONGO_DATABASES_SKILL_TREE
from app.modules.lake_phase.skill_tree import LAKE_SKILL_TREE
from app.modules.lakehouse_phase.skill_tree import LAKEHOUSE_SKILL_TREE
from app.modules.nosql_phase.skill_tree import NOSQL_SKILL_TREE
from app.modules.pipeline_architecture_track.skill_tree import PIPELINE_ARCHITECTURE_SKILL_TREE
from app.modules.postgres_phase.skill_tree import POSTGRES_SKILL_TREE
from app.modules.sql_databases_track.skill_tree import SQL_DATABASES_SKILL_TREE
from app.modules.warehouse_databases_track.skill_tree import WAREHOUSE_DATABASES_SKILL_TREE
from app.modules.warehouse_phase.skill_tree import WAREHOUSE_SKILL_TREE

# Every skill tree that exists, keyed by its own `paradigm` field -
# deliberately broader than node_practice._SKILL_TREES (which only lists
# the gradable ones): a certificate needs to count capstone nodes too,
# and nosql's capstone-only wrapper has no gradable nodes of its own at
# all (lake and lakehouse used to be capstone-only wrappers too, but now
# each has a paired *_databases_track with real gradable nodes).
_ALL_TREES: dict[str, dict] = {
    "postgres": POSTGRES_SKILL_TREE,
    "sql-databases": SQL_DATABASES_SKILL_TREE,
    "mongo-databases": MONGO_DATABASES_SKILL_TREE,
    "nosql": NOSQL_SKILL_TREE,
    "warehouse-databases": WAREHOUSE_DATABASES_SKILL_TREE,
    "warehouse": WAREHOUSE_SKILL_TREE,
    "lake-databases": LAKE_DATABASES_SKILL_TREE,
    "lake": LAKE_SKILL_TREE,
    "lakehouse-databases": LAKEHOUSE_DATABASES_SKILL_TREE,
    "lakehouse": LAKEHOUSE_SKILL_TREE,
    "pipeline-architecture": PIPELINE_ARCHITECTURE_SKILL_TREE,
}

CERTIFICATE_GROUPS: dict[str, dict] = {
    "sql": {"label": "SQL", "paradigms": ["sql-databases", "postgres"]},
    "nosql": {"label": "NoSQL", "paradigms": ["mongo-databases", "nosql"]},
    "warehouse": {"label": "Data Warehouse", "paradigms": ["warehouse-databases", "warehouse"]},
    "lake": {"label": "Data Lake", "paradigms": ["lake-databases", "lake"]},
    "lakehouse": {"label": "Lakehouse", "paradigms": ["lakehouse-databases", "lakehouse"]},
    "pipeline-architecture": {"label": "Pipeline Architecture", "paradigms": ["pipeline-architecture"]},
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
