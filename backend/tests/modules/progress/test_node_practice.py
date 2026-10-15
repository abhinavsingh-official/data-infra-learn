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
