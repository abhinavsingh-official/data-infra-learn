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


def test_warehouse_databases_fact_aggregate_node_passes():
    sql = (
        "SELECT a.card_network, SUM(f.transaction_amount) AS total_spent "
        "FROM fact_transactions f JOIN dim_accounts a ON a.id = f.account_id "
        "GROUP BY a.card_network ORDER BY total_spent DESC"
    )
    result = check_node_submission("warehouse-databases", "node_4_fact_aggregate", sql)
    assert result["passed"] is True
    assert result["actual_rows"][0]["card_network"] == "Mastercard"
