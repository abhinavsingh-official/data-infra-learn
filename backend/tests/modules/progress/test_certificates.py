from app.modules.progress.certificates import CERTIFICATE_GROUPS, certificate_status


def test_every_group_is_locked_with_no_completions():
    status = certificate_status({})
    for group_id in CERTIFICATE_GROUPS:
        assert status[group_id]["unlocked"] is False
        assert status[group_id]["completed"] == 0
        assert status[group_id]["total"] > 0


def test_lake_requires_both_lake_databases_and_lake_tracks():
    lake_databases_nodes = [
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
    ]
    partial = certificate_status({"lake-databases": lake_databases_nodes})
    assert partial["lake"]["unlocked"] is False
    assert partial["lake"]["completed"] == len(lake_databases_nodes)

    full = certificate_status({"lake-databases": lake_databases_nodes, "lake": ["capstone"]})
    assert full["lake"]["unlocked"] is True


def test_lakehouse_requires_both_lakehouse_databases_and_lakehouse_tracks():
    lakehouse_databases_nodes = [
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
    ]
    partial = certificate_status({"lakehouse-databases": lakehouse_databases_nodes})
    assert partial["lakehouse"]["unlocked"] is False
    assert partial["lakehouse"]["completed"] == len(lakehouse_databases_nodes)

    full = certificate_status(
        {"lakehouse-databases": lakehouse_databases_nodes, "lakehouse": ["capstone"]}
    )
    assert full["lakehouse"]["unlocked"] is True


def test_sql_requires_both_sql_databases_and_postgres_tracks():
    sql_databases_nodes = [
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
    ]
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
