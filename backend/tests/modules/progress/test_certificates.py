from app.modules.progress.certificates import CERTIFICATE_GROUPS, certificate_status


def test_every_group_is_locked_with_no_completions():
    status = certificate_status({})
    for group_id in CERTIFICATE_GROUPS:
        assert status[group_id]["unlocked"] is False
        assert status[group_id]["completed"] == 0
        assert status[group_id]["total"] > 0


def test_lake_unlocks_once_its_only_node_is_done():
    # Lake's tree is intro+capstone only - "capstone" is its sole
    # gradable requirement.
    status = certificate_status({"lake": ["capstone"]})
    assert status["lake"]["unlocked"] is True
    assert status["lake"]["completed"] == status["lake"]["total"]


def test_sql_requires_both_sql_databases_and_postgres_tracks():
    sql_databases_nodes = ["node_1_where", "node_2_join", "node_3_group_order", "node_4_nulls"]
    partial = certificate_status({"sql-databases": sql_databases_nodes})
    assert partial["sql"]["unlocked"] is False
    assert partial["sql"]["completed"] == len(sql_databases_nodes)

    postgres_nodes = [
        "node_1_base_load",
        "node_2_renamed_missing",
        "node_3_dedupe",
        "node_4_watermark",
        "node_5_minor_unit",
        "capstone",
    ]
    full = certificate_status({"sql-databases": sql_databases_nodes, "postgres": postgres_nodes})
    assert full["sql"]["unlocked"] is True
