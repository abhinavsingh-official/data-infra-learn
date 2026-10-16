from app.modules.progress.node_practice import check_node_submission, find_skill_node


def test_find_skill_node_known_and_unknown():
    assert find_skill_node("postgres", "node_1_base_load") is not None
    assert find_skill_node("postgres", "does-not-exist") is None
    assert find_skill_node("unknown-paradigm", "node_1_base_load") is None


def test_correct_submission_passes_node_1():
    sql = (
        "SELECT payload->>'event_id' AS event_id, "
        "(payload->>'amount')::numeric AS amount, "
        "payload->>'merchant' AS merchant, "
        "payload->>'currency' AS currency, "
        "(payload->>'timestamp')::timestamptz AS event_timestamp "
        "FROM raw_transaction_events"
    )
    result = check_node_submission("postgres", "node_1_base_load", sql)
    assert result["passed"] is True
    assert result["mismatch"] is None
    assert len(result["actual_rows"]) == 1


def test_wrong_row_count_fails_with_mismatch_reason():
    result = check_node_submission("postgres", "node_1_base_load", "SELECT 1 WHERE false")
    assert result["passed"] is False
    assert "0 row" in result["mismatch"] or "row(s)" in result["mismatch"]


def test_wrong_values_fail():
    sql = (
        "SELECT payload->>'event_id' AS event_id, "
        "(payload->>'amount')::numeric + 1 AS amount, "  # deliberately wrong
        "payload->>'merchant' AS merchant, "
        "payload->>'currency' AS currency, "
        "(payload->>'timestamp')::timestamptz AS event_timestamp "
        "FROM raw_transaction_events"
    )
    result = check_node_submission("postgres", "node_1_base_load", sql)
    assert result["passed"] is False


def test_bad_sql_returns_structured_error_not_a_crash():
    result = check_node_submission("postgres", "node_1_base_load", "SELECT * FROM nonexistent_table")
    assert result["passed"] is False
    assert result["error_code"] is not None


def test_sql_databases_where_node_passes():
    sql = (
        "SELECT id, merchant_name, transaction_amount FROM transactions "
        "WHERE transaction_amount > 1000"
    )
    result = check_node_submission("sql-databases", "node_1_where", sql)
    assert result["passed"] is True
    assert len(result["actual_rows"]) == 2


def test_sql_databases_join_node_uses_two_private_tables():
    sql = (
        "SELECT t.id AS transaction_id, a.card_network, t.transaction_amount "
        "FROM transactions t JOIN accounts a ON a.id = t.account_id"
    )
    result = check_node_submission("sql-databases", "node_2_join", sql)
    assert result["passed"] is True
    assert len(result["actual_rows"]) == 3


def test_sql_databases_group_order_node_passes():
    sql = (
        "SELECT account_id, SUM(transaction_amount) AS total_spent FROM transactions "
        "GROUP BY account_id ORDER BY total_spent DESC"
    )
    result = check_node_submission("sql-databases", "node_3_group_order", sql)
    assert result["passed"] is True


def test_sql_databases_nulls_node_passes():
    sql = (
        "SELECT id, COALESCE(merchant_name, 'Unknown merchant') AS merchant_name, transaction_amount "
        "FROM transactions"
    )
    result = check_node_submission("sql-databases", "node_4_nulls", sql)
    assert result["passed"] is True


def test_sql_databases_distinct_node_passes():
    sql = "SELECT DISTINCT channel FROM transactions"
    result = check_node_submission("sql-databases", "node_5_distinct", sql)
    assert result["passed"] is True
    assert len(result["actual_rows"]) == 3


def test_sql_databases_having_node_passes():
    sql = (
        "SELECT account_id, COUNT(*) AS txn_count FROM transactions "
        "GROUP BY account_id HAVING COUNT(*) > 1"
    )
    result = check_node_submission("sql-databases", "node_6_having", sql)
    assert result["passed"] is True
    assert len(result["actual_rows"]) == 2


def test_sql_databases_having_node_fails_without_having_filter():
    sql = "SELECT account_id, COUNT(*) AS txn_count FROM transactions GROUP BY account_id"
    result = check_node_submission("sql-databases", "node_6_having", sql)
    assert result["passed"] is False


def test_sql_databases_subquery_node_passes():
    sql = (
        "SELECT id, card_network FROM accounts "
        "WHERE id IN (SELECT account_id FROM transactions WHERE transaction_amount > 1000)"
    )
    result = check_node_submission("sql-databases", "node_7_subquery", sql)
    assert result["passed"] is True
    assert len(result["actual_rows"]) == 1


def test_sql_databases_case_node_passes():
    sql = (
        "SELECT id, transaction_amount, "
        "CASE WHEN transaction_amount < 100 THEN 'small' "
        "WHEN transaction_amount < 1000 THEN 'medium' "
        "ELSE 'large' END AS amount_tier FROM transactions"
    )
    result = check_node_submission("sql-databases", "node_8_case", sql)
    assert result["passed"] is True
    assert len(result["actual_rows"]) == 3


def test_sql_databases_string_functions_node_passes():
    sql = (
        "SELECT id, UPPER(merchant_name) AS merchant_name_upper, "
        "merchant_name || ' (' || channel || ')' AS merchant_and_channel FROM transactions"
    )
    result = check_node_submission("sql-databases", "node_9_string_functions", sql)
    assert result["passed"] is True


def test_sql_databases_date_functions_node_passes():
    sql = "SELECT id, EXTRACT(month FROM transaction_time) AS txn_month FROM transactions"
    result = check_node_submission("sql-databases", "node_10_date_functions", sql)
    assert result["passed"] is True
    assert len(result["actual_rows"]) == 2


def test_warehouse_databases_grain_node_passes():
    sql = "SELECT account_id, card_network FROM raw_account_events GROUP BY account_id, card_network"
    result = check_node_submission("warehouse-databases", "node_1_grain", sql)
    assert result["passed"] is True
    assert len(result["actual_rows"]) == 2


def test_warehouse_databases_star_join_node_uses_three_private_tables():
    sql = (
        "SELECT f.id AS transaction_id, a.card_network, m.merchant_name, f.transaction_amount "
        "FROM fact_transactions f "
        "JOIN dim_accounts a ON a.id = f.account_id "
        "JOIN dim_merchants m ON m.id = f.merchant_id"
    )
    result = check_node_submission("warehouse-databases", "node_2_star_join", sql)
    assert result["passed"] is True
    assert len(result["actual_rows"]) == 3


def test_warehouse_databases_scd2_node_filters_to_current_only():
    sql = "SELECT account_id, card_network FROM dim_accounts_scd2 WHERE is_current = true"
    result = check_node_submission("warehouse-databases", "node_3_scd2_current", sql)
    assert result["passed"] is True
    assert len(result["actual_rows"]) == 2


def test_warehouse_databases_scd2_node_fails_without_current_filter():
    sql = "SELECT account_id, card_network FROM dim_accounts_scd2"
    result = check_node_submission("warehouse-databases", "node_3_scd2_current", sql)
    assert result["passed"] is False


def test_pipeline_architecture_idempotent_pipelines_node_passes():
    sql = (
        "SELECT idempotency_key, amount FROM ("
        "  SELECT *, ROW_NUMBER() OVER (PARTITION BY idempotency_key ORDER BY attempt) AS rn "
        "  FROM webhook_deliveries"
        ") t WHERE rn = 1"
    )
    result = check_node_submission("pipeline-architecture", "node_1_idempotent_pipelines", sql)
    assert result["passed"] is True
    assert len(result["actual_rows"]) == 2


def test_pipeline_architecture_schema_evolution_node_passes():
    sql = "SELECT id, COALESCE(full_name_v2, customer_name_v1) AS customer_name FROM customer_events"
    result = check_node_submission("pipeline-architecture", "node_2_schema_evolution", sql)
    assert result["passed"] is True


def test_pipeline_architecture_batch_vs_streaming_node_passes():
    sql = "SELECT id, amount FROM stream_events"
    result = check_node_submission("pipeline-architecture", "node_3_batch_vs_streaming", sql)
    assert result["passed"] is True
    assert len(result["actual_rows"]) == 2


def test_pipeline_architecture_batch_vs_streaming_node_fails_if_late_event_dropped():
    sql = "SELECT id, amount FROM stream_events WHERE processed_at - event_time < interval '1 day'"
    result = check_node_submission("pipeline-architecture", "node_3_batch_vs_streaming", sql)
    assert result["passed"] is False


def test_pipeline_architecture_monitoring_alerting_node_passes():
    sql = "SELECT error_code, COUNT(*) AS error_count FROM pipeline_errors GROUP BY error_code ORDER BY error_count DESC"
    result = check_node_submission("pipeline-architecture", "node_4_monitoring_alerting", sql)
    assert result["passed"] is True
    assert result["actual_rows"][0]["error_code"] == "ERR_NULL_FIELD"


def test_warehouse_databases_degenerate_dimension_node_passes():
    sql = "SELECT id, account_id, invoice_number FROM fact_transactions"
    result = check_node_submission("warehouse-databases", "node_5_degenerate_dimension", sql)
    assert result["passed"] is True
    assert len(result["actual_rows"]) == 3


def test_warehouse_databases_role_playing_dimension_node_uses_two_private_tables():
    sql = (
        "SELECT f.id AS order_id, od.calendar_date::text AS order_date, "
        "sd.calendar_date::text AS ship_date, f.order_amount "
        "FROM fact_orders f "
        "JOIN dim_dates od ON od.id = f.order_date_id "
        "JOIN dim_dates sd ON sd.id = f.ship_date_id"
    )
    result = check_node_submission("warehouse-databases", "node_6_role_playing_dimension", sql)
    assert result["passed"] is True
    assert len(result["actual_rows"]) == 2


def test_warehouse_databases_unknown_member_node_keeps_orphaned_fact_row():
    sql = (
        "SELECT f.id AS transaction_id, COALESCE(a.card_network, 'Unknown') AS card_network, "
        "f.transaction_amount "
        "FROM fact_transactions f LEFT JOIN dim_accounts a ON a.id = f.account_id"
    )
    result = check_node_submission("warehouse-databases", "node_7_unknown_member", sql)
    assert result["passed"] is True
    assert len(result["actual_rows"]) == 2


def test_warehouse_databases_unknown_member_node_fails_with_inner_join():
    sql = (
        "SELECT f.id AS transaction_id, a.card_network, f.transaction_amount "
        "FROM fact_transactions f JOIN dim_accounts a ON a.id = f.account_id"
    )
    result = check_node_submission("warehouse-databases", "node_7_unknown_member", sql)
    assert result["passed"] is False


def test_warehouse_databases_conformed_dimension_node_passes():
    sql = (
        "SELECT a.card_network, SUM(x.amount) AS net_amount FROM ("
        "  SELECT account_id, amount FROM fact_transactions "
        "  UNION ALL "
        "  SELECT account_id, amount FROM fact_refunds"
        ") x JOIN dim_accounts a ON a.id = x.account_id "
        "GROUP BY a.card_network"
    )
    result = check_node_submission("warehouse-databases", "node_8_conformed_dimension", sql)
    assert result["passed"] is True
    assert result["actual_rows"][0]["net_amount"] == 35.00


def test_warehouse_databases_grain_violation_node_passes():
    sql = (
        "SELECT account_id, COUNT(*) AS row_count FROM dim_accounts_candidate "
        "GROUP BY account_id HAVING COUNT(*) > 1"
    )
    result = check_node_submission("warehouse-databases", "node_9_grain_violation", sql)
    assert result["passed"] is True
    assert result["actual_rows"] == [{"account_id": 101, "row_count": 2}]


def test_warehouse_databases_junk_dimension_node_passes():
    sql = (
        "SELECT f.id AS transaction_id, j.is_disputed, j.is_recurring, f.transaction_amount "
        "FROM fact_transactions f JOIN dim_transaction_flags j ON j.id = f.junk_dim_id"
    )
    result = check_node_submission("warehouse-databases", "node_10_junk_dimension", sql)
    assert result["passed"] is True
    assert len(result["actual_rows"]) == 2


def test_pipeline_architecture_data_quality_gates_node_passes():
    sql = "SELECT id, account_id, amount FROM raw_orders WHERE account_id IS NOT NULL AND amount > 0"
    result = check_node_submission("pipeline-architecture", "node_5_data_quality_gates", sql)
    assert result["passed"] is True
    assert len(result["actual_rows"]) == 2


def test_pipeline_architecture_incremental_watermark_node_passes():
    sql = "SELECT id, value FROM source_records WHERE updated_at > '2026-01-03T00:00:00+00'"
    result = check_node_submission("pipeline-architecture", "node_6_incremental_watermark", sql)
    assert result["passed"] is True
    assert len(result["actual_rows"]) == 2


def test_pipeline_architecture_change_data_capture_node_passes():
    sql = (
        "SELECT record_id, value FROM ("
        "  SELECT *, ROW_NUMBER() OVER (PARTITION BY record_id ORDER BY sequence_num DESC) AS rn"
        "  FROM cdc_log"
        ") t WHERE rn = 1"
    )
    result = check_node_submission("pipeline-architecture", "node_7_change_data_capture", sql)
    assert result["passed"] is True
    assert len(result["actual_rows"]) == 2


def test_pipeline_architecture_dead_letter_queue_node_passes():
    sql = "SELECT id, failure_reason FROM dead_letter_queue WHERE resolved = false"
    result = check_node_submission("pipeline-architecture", "node_8_dead_letter_queue", sql)
    assert result["passed"] is True
    assert len(result["actual_rows"]) == 2


def test_pipeline_architecture_backfill_reprocessing_node_passes():
    sql = (
        "SELECT id, batch_date::text AS batch_date, amount FROM fact_daily_loads "
        "WHERE batch_date BETWEEN '2026-01-01' AND '2026-01-02'"
    )
    result = check_node_submission("pipeline-architecture", "node_9_backfill_reprocessing", sql)
    assert result["passed"] is True
    assert len(result["actual_rows"]) == 2


def test_pipeline_architecture_data_lineage_node_passes():
    sql = "SELECT id, source_system, value FROM ingested_records WHERE source_system = 'new_kafka_feed'"
    result = check_node_submission("pipeline-architecture", "node_10_data_lineage", sql)
    assert result["passed"] is True
    assert len(result["actual_rows"]) == 1


def test_warehouse_databases_fact_aggregate_node_passes():
    sql = (
        "SELECT a.card_network, SUM(f.transaction_amount) AS total_spent "
        "FROM fact_transactions f JOIN dim_accounts a ON a.id = f.account_id "
        "GROUP BY a.card_network ORDER BY total_spent DESC"
    )
    result = check_node_submission("warehouse-databases", "node_4_fact_aggregate", sql)
    assert result["passed"] is True
    assert result["actual_rows"][0]["card_network"] == "Mastercard"
