from app.modules.sql_databases_track.skill_tree import SQL_DATABASES_SKILL_TREE


def test_tree_has_expected_node_ids_in_order():
    ids = [node["id"] for node in SQL_DATABASES_SKILL_TREE["nodes"]]
    assert ids == [
        "intro",
        "node_1_where",
        "node_2_join",
        "node_3_group_order",
        "node_4_nulls",
        "node_5_distinct",
        "node_6_having",
        "node_7_subquery",
        "node_8_case",
        "node_9_string_functions",
        "node_10_date_functions",
        "review",
    ]


def test_every_skill_node_has_teach_and_practice():
    for node in SQL_DATABASES_SKILL_TREE["nodes"]:
        if node["type"] == "skill":
            assert "teach" in node
            assert "practice" in node
            assert "expected_output_rows" in node["practice"]


def test_join_node_declares_two_tables_not_the_single_table_fallback():
    join_node = next(n for n in SQL_DATABASES_SKILL_TREE["nodes"] if n["id"] == "node_2_join")
    assert "tables" in join_node["practice"]
    assert {t["name"] for t in join_node["practice"]["tables"]} == {"transactions", "accounts"}
