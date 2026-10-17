from app.modules.lake_databases_track.skill_tree import LAKE_DATABASES_SKILL_TREE


def test_tree_has_expected_node_ids_in_order():
    ids = [node["id"] for node in LAKE_DATABASES_SKILL_TREE["nodes"]]
    assert ids == [
        "intro",
        "node_1_schema_on_read",
        "node_2_columnar_storage",
        "node_3_partitioning",
        "node_4_partition_pruning",
        "node_5_schema_drift",
        "node_6_dedupe_redelivery",
        "node_7_medallion_bronze_silver",
        "node_8_small_file_compaction",
        "node_9_late_arriving_data",
        "node_10_data_skipping",
        "review",
    ]


def test_every_skill_node_has_teach_and_practice():
    for node in LAKE_DATABASES_SKILL_TREE["nodes"]:
        if node["type"] == "skill":
            assert "teach" in node
            assert "sql" in node["teach"]
            assert "note" in node["teach"]
            assert "steps" in node["teach"]
            assert "practice" in node
            assert "expected_output_rows" in node["practice"]


def test_schema_on_read_node_uses_jsonb_payload():
    node = next(n for n in LAKE_DATABASES_SKILL_TREE["nodes"] if n["id"] == "node_1_schema_on_read")
    columns = {c["column"]: c["type"] for c in node["practice"]["schema"]}
    assert columns["payload"] == "jsonb"


def test_partition_pruning_node_filters_on_a_date_range():
    node = next(n for n in LAKE_DATABASES_SKILL_TREE["nodes"] if n["id"] == "node_4_partition_pruning")
    assert "sale_date" in node["teach"]["sql"]
    assert len(node["practice"]["expected_output_rows"]) == 2


def test_dedupe_node_has_an_idempotency_key_column():
    node = next(n for n in LAKE_DATABASES_SKILL_TREE["nodes"] if n["id"] == "node_6_dedupe_redelivery")
    columns = {c["column"] for c in node["practice"]["schema"]}
    assert "event_id" in columns
    assert "received_at" in columns


def test_review_node_exists_and_mentions_capstone():
    review = next(n for n in LAKE_DATABASES_SKILL_TREE["nodes"] if n["id"] == "review")
    assert review["type"] == "review"
    assert "capstone" in review["prompt"].lower()
