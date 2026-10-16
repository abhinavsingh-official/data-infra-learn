from app.modules.pipeline_architecture_track.skill_tree import PIPELINE_ARCHITECTURE_SKILL_TREE


def test_tree_has_expected_node_ids_in_order():
    ids = [node["id"] for node in PIPELINE_ARCHITECTURE_SKILL_TREE["nodes"]]
    assert ids == [
        "intro",
        "node_1_idempotent_pipelines",
        "node_2_schema_evolution",
        "node_3_batch_vs_streaming",
        "node_4_monitoring_alerting",
        "node_5_data_quality_gates",
        "node_6_incremental_watermark",
        "node_7_change_data_capture",
        "node_8_dead_letter_queue",
        "node_9_backfill_reprocessing",
        "node_10_data_lineage",
        "review",
    ]


def test_every_skill_node_has_teach_and_practice():
    for node in PIPELINE_ARCHITECTURE_SKILL_TREE["nodes"]:
        if node["type"] == "skill":
            assert "teach" in node
            assert "practice" in node
            assert "expected_output_rows" in node["practice"]


def test_tree_has_no_capstone_node():
    # Deliberately cross-cutting, no sibling phase/dataset of its own.
    assert all(node["type"] != "capstone" for node in PIPELINE_ARCHITECTURE_SKILL_TREE["nodes"])
