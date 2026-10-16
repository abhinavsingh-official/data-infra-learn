import json

from app.modules.progress.mongo_node_practice import check_mongo_node_submission
from app.modules.progress.node_practice import find_skill_node


def test_find_skill_node_knows_the_mongo_tree():
    assert find_skill_node("mongo-databases", "node_1_find") is not None
    assert find_skill_node("mongo-databases", "does-not-exist") is None


def test_find_node_passes():
    command = json.dumps(
        {"find": "accounts", "filter": {"status": "active"}, "projection": {"status": 0}}
    )
    result = check_mongo_node_submission("mongo-databases", "node_1_find", command)
    assert result["passed"] is True
    assert result["mismatch"] is None
    assert len(result["actual_rows"]) == 2


def test_find_node_wrong_filter_fails_with_mismatch():
    command = json.dumps({"find": "accounts", "filter": {"status": "closed"}})
    result = check_mongo_node_submission("mongo-databases", "node_1_find", command)
    assert result["passed"] is False
    assert result["mismatch"] is not None


def test_lookup_node_joins_two_private_collections():
    command = json.dumps(
        {
            "aggregate": "transactions",
            "pipeline": [
                {
                    "$lookup": {
                        "from": "accounts",
                        "localField": "account_id",
                        "foreignField": "_id",
                        "as": "account",
                    }
                },
                {"$unwind": "$account"},
                {
                    "$project": {
                        "_id": 0,
                        "transaction_id": "$_id",
                        "card_network": "$account.card_network",
                        "amount_cents": 1,
                    }
                },
            ],
            "cursor": {},
        }
    )
    result = check_mongo_node_submission("mongo-databases", "node_2_lookup", command)
    assert result["passed"] is True
    assert len(result["actual_rows"]) == 3


def test_group_node_passes():
    command = json.dumps(
        {
            "aggregate": "transactions",
            "pipeline": [
                {"$group": {"_id": "$account_id", "total_spent_cents": {"$sum": "$amount_cents"}}},
                {"$sort": {"total_spent_cents": -1}},
            ],
            "cursor": {},
        }
    )
    result = check_mongo_node_submission("mongo-databases", "node_3_group", command)
    assert result["passed"] is True


def test_missing_fields_node_passes():
    command = json.dumps(
        {
            "aggregate": "accounts",
            "pipeline": [
                {"$project": {"_id": 1, "nickname": {"$ifNull": ["$nickname", "Unnamed account"]}}}
            ],
            "cursor": {},
        }
    )
    result = check_mongo_node_submission("mongo-databases", "node_4_missing_fields", command)
    assert result["passed"] is True


def test_match_logic_node_passes():
    command = json.dumps(
        {
            "aggregate": "transactions",
            "pipeline": [
                {
                    "$match": {
                        "$or": [
                            {"channel": "online"},
                            {"$and": [{"channel": "pos"}, {"amount_cents": {"$gt": 1000}}]},
                        ]
                    }
                },
                {"$project": {"_id": 1, "amount_cents": 1}},
            ],
            "cursor": {},
        }
    )
    result = check_mongo_node_submission("mongo-databases", "node_5_match_logic", command)
    assert result["passed"] is True
    assert len(result["actual_rows"]) == 3


def test_project_concat_node_passes():
    command = json.dumps(
        {
            "aggregate": "accounts",
            "pipeline": [
                {"$project": {"_id": 1, "display": {"$concat": ["$owner_name", " - ", "$card_network"]}}}
            ],
            "cursor": {},
        }
    )
    result = check_mongo_node_submission("mongo-databases", "node_6_project_concat", command)
    assert result["passed"] is True


def test_sort_limit_node_passes():
    command = json.dumps(
        {
            "aggregate": "transactions",
            "pipeline": [
                {"$sort": {"amount_cents": -1}},
                {"$limit": 2},
                {"$project": {"_id": 1, "amount_cents": 1}},
            ],
            "cursor": {},
        }
    )
    result = check_mongo_node_submission("mongo-databases", "node_7_sort_limit", command)
    assert result["passed"] is True
    assert result["actual_rows"][0]["_id"] == "t3"


def test_count_node_passes():
    command = json.dumps(
        {
            "aggregate": "transactions",
            "pipeline": [
                {"$group": {"_id": None, "transaction_count": {"$sum": 1}}},
                {"$project": {"_id": 0, "transaction_count": 1}},
            ],
            "cursor": {},
        }
    )
    result = check_mongo_node_submission("mongo-databases", "node_8_count", command)
    assert result["passed"] is True
    assert result["actual_rows"] == [{"transaction_count": 3}]


def test_cond_node_passes():
    command = json.dumps(
        {
            "aggregate": "transactions",
            "pipeline": [
                {
                    "$project": {
                        "_id": 1,
                        "amount_cents": 1,
                        "tier": {
                            "$cond": {
                                "if": {"$gt": ["$amount_cents", 100000]},
                                "then": "large",
                                "else": "small",
                            }
                        },
                    }
                }
            ],
            "cursor": {},
        }
    )
    result = check_mongo_node_submission("mongo-databases", "node_9_cond", command)
    assert result["passed"] is True


def test_unwind_array_node_passes():
    command = json.dumps(
        {
            "aggregate": "accounts",
            "pipeline": [
                {"$unwind": "$tags"},
                {"$project": {"_id": 1, "tag": "$tags"}},
            ],
            "cursor": {},
        }
    )
    result = check_mongo_node_submission("mongo-databases", "node_10_unwind_array", command)
    assert result["passed"] is True
    assert len(result["actual_rows"]) == 3


def test_invalid_json_returns_structured_error_not_a_crash():
    result = check_mongo_node_submission("mongo-databases", "node_1_find", "not json")
    assert result["passed"] is False
    assert result["error_code"] == "ERR_INVALID_JSON"


def test_non_query_command_returns_structured_error():
    result = check_mongo_node_submission("mongo-databases", "node_1_find", json.dumps({"count": "accounts"}))
    assert result["passed"] is False
    assert result["error_code"] == "ERR_NOT_A_QUERY_COMMAND"


def test_practice_db_and_user_are_torn_down_after_check():
    from app.core.db import get_mongo_admin_client

    check_mongo_node_submission("mongo-databases", "node_1_find", json.dumps({"find": "accounts", "filter": {}}))
    with get_mongo_admin_client() as admin_client:
        leftover = [n for n in admin_client.list_database_names() if n.startswith("practice_")]
    assert leftover == []
