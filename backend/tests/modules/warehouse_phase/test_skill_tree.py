from app.modules.warehouse_phase.skill_tree import WAREHOUSE_SKILL_TREE
from app.modules.warehouse_phase.task_content import WAREHOUSE_PHASE_TASK


def test_tree_has_intro_and_capstone_only():
    ids = [node["id"] for node in WAREHOUSE_SKILL_TREE["nodes"]]
    assert ids == ["intro", "capstone"]


def test_capstone_node_references_the_real_task():
    capstone = next(n for n in WAREHOUSE_SKILL_TREE["nodes"] if n["id"] == "capstone")
    assert capstone["title"] == WAREHOUSE_PHASE_TASK["title"]
    assert capstone["task_ref"] == "warehouse"
