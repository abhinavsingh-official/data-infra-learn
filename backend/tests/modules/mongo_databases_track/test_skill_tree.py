from app.modules.mongo_databases_track.skill_tree import MONGO_DATABASES_SKILL_TREE


def test_tree_has_expected_node_ids_in_order():
    ids = [node["id"] for node in MONGO_DATABASES_SKILL_TREE["nodes"]]
    assert ids == [
        "intro",
        "node_1_find",
        "node_2_lookup",
        "node_3_group",
        "node_4_missing_fields",
        "node_5_match_logic",
        "node_6_project_concat",
        "node_7_sort_limit",
        "node_8_count",
        "node_9_cond",
        "node_10_unwind_array",
        "review",
    ]


def test_every_skill_node_has_teach_and_practice():
    for node in MONGO_DATABASES_SKILL_TREE["nodes"]:
        if node["type"] == "skill":
            assert "teach" in node
            assert "practice" in node
            assert "expected_output_rows" in node["practice"]


def test_lookup_node_declares_two_collections_not_the_single_collection_fallback():
    lookup_node = next(n for n in MONGO_DATABASES_SKILL_TREE["nodes"] if n["id"] == "node_2_lookup")
    assert "tables" in lookup_node["practice"]
    assert {t["name"] for t in lookup_node["practice"]["tables"]} == {"transactions", "accounts"}
