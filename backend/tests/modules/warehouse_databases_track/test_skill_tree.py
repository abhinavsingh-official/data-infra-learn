from app.modules.warehouse_databases_track.skill_tree import WAREHOUSE_DATABASES_SKILL_TREE


def test_tree_has_expected_node_ids_in_order():
    ids = [node["id"] for node in WAREHOUSE_DATABASES_SKILL_TREE["nodes"]]
    assert ids == [
        "intro",
        "node_1_grain",
        "node_2_star_join",
        "node_3_scd2_current",
        "node_4_fact_aggregate",
        "review",
    ]


def test_every_skill_node_has_teach_and_practice():
    for node in WAREHOUSE_DATABASES_SKILL_TREE["nodes"]:
        if node["type"] == "skill":
            assert "teach" in node
            assert "practice" in node
            assert "expected_output_rows" in node["practice"]


def test_star_join_node_declares_three_tables_not_the_single_table_fallback():
    join_node = next(n for n in WAREHOUSE_DATABASES_SKILL_TREE["nodes"] if n["id"] == "node_2_star_join")
    assert "tables" in join_node["practice"]
    assert {t["name"] for t in join_node["practice"]["tables"]} == {
        "fact_transactions",
        "dim_accounts",
        "dim_merchants",
    }


def test_scd2_node_has_historized_columns():
    scd2_node = next(n for n in WAREHOUSE_DATABASES_SKILL_TREE["nodes"] if n["id"] == "node_3_scd2_current")
    columns = {c["column"] for c in scd2_node["practice"]["schema"]}
    assert {"valid_from", "valid_to", "is_current"} <= columns
