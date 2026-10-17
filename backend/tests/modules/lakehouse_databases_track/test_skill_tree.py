from app.modules.lakehouse_databases_track.skill_tree import LAKEHOUSE_DATABASES_SKILL_TREE


def test_tree_has_expected_node_ids_in_order():
    ids = [node["id"] for node in LAKEHOUSE_DATABASES_SKILL_TREE["nodes"]]
    assert ids == [
        "intro",
        "node_1_atomic_commits",
        "node_2_schema_enforcement",
        "node_3_schema_evolution",
        "node_4_merge_upsert",
        "node_5_time_travel",
        "node_6_transaction_log",
        "node_7_optimistic_concurrency",
        "node_8_compaction_optimize",
        "node_9_zorder_data_skipping",
        "node_10_retention_vacuum",
        "review",
    ]


def test_every_skill_node_has_teach_and_practice():
    for node in LAKEHOUSE_DATABASES_SKILL_TREE["nodes"]:
        if node["type"] == "skill":
            assert "teach" in node
            assert "sql" in node["teach"]
            assert "note" in node["teach"]
            assert "steps" in node["teach"]
            assert "practice" in node
            assert "expected_output_rows" in node["practice"]


def test_merge_upsert_node_uses_on_conflict_and_a_primary_key():
    node = next(n for n in LAKEHOUSE_DATABASES_SKILL_TREE["nodes"] if n["id"] == "node_4_merge_upsert")
    columns = {c["column"]: c["type"] for c in node["practice"]["schema"]}
    assert "primary key" in columns["id"]
    assert "ON CONFLICT" in node["teach"]["sql"]


def test_optimistic_concurrency_node_expects_zero_rows_on_conflict():
    node = next(n for n in LAKEHOUSE_DATABASES_SKILL_TREE["nodes"] if n["id"] == "node_7_optimistic_concurrency")
    assert node["practice"]["expected_output_rows"] == []


def test_time_travel_node_filters_on_version():
    node = next(n for n in LAKEHOUSE_DATABASES_SKILL_TREE["nodes"] if n["id"] == "node_5_time_travel")
    columns = {c["column"] for c in node["practice"]["schema"]}
    assert "version" in columns


def test_review_node_exists_and_mentions_capstone():
    review = next(n for n in LAKEHOUSE_DATABASES_SKILL_TREE["nodes"] if n["id"] == "review")
    assert review["type"] == "review"
    assert "capstone" in review["prompt"].lower()
