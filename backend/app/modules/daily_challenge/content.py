"""The Daily Challenge's content pool - small, hand-sized problems tagged
by difficulty tier (1-3), one fresh SQL problem and one fresh Python
problem picked per day (see selection.py).

Practice blocks reuse the exact same dict keys as sql_databases_track's
content (table_name/schema/example_rows/tables/expected_output_rows) so
the SQL half of a daily challenge is gradable via node_practice.py's
existing check_practice_submission with zero new grading code."""

SQL_CHALLENGE_POOL: list[dict] = [
    {
        "id": "sql_tier1_filter_sort",
        "difficulty": 1,
        "prompt": "Find every 'online' channel transaction. Return id, channel, and transaction_amount, ordered by id.",
        "table_name": "transactions",
        "schema": [
            {"column": "id", "type": "bigint"},
            {"column": "account_id", "type": "bigint"},
            {"column": "transaction_amount", "type": "numeric"},
            {"column": "channel", "type": "text"},
        ],
        "example_rows": [
            {"id": 1, "account_id": 201, "transaction_amount": 25.00, "channel": "POS"},
            {"id": 2, "account_id": 201, "transaction_amount": 890.00, "channel": "online"},
            {"id": 3, "account_id": 202, "transaction_amount": 1500.00, "channel": "ATM"},
            {"id": 4, "account_id": 202, "transaction_amount": 42.50, "channel": "POS"},
        ],
        "expected_output_rows": [
            {"id": 2, "channel": "online", "transaction_amount": 890.00},
        ],
    },
    {
        "id": "sql_tier1_count_group",
        "difficulty": 1,
        "prompt": "Count how many transactions each account has.",
        "table_name": "transactions",
        "schema": [
            {"column": "id", "type": "bigint"},
            {"column": "account_id", "type": "bigint"},
            {"column": "transaction_amount", "type": "numeric"},
            {"column": "channel", "type": "text"},
        ],
        "example_rows": [
            {"id": 1, "account_id": 201, "transaction_amount": 25.00, "channel": "POS"},
            {"id": 2, "account_id": 201, "transaction_amount": 890.00, "channel": "online"},
            {"id": 3, "account_id": 202, "transaction_amount": 1500.00, "channel": "ATM"},
            {"id": 4, "account_id": 202, "transaction_amount": 42.50, "channel": "POS"},
        ],
        "expected_output_rows": [
            {"account_id": 201, "transaction_count": 2},
            {"account_id": 202, "transaction_count": 2},
        ],
    },
    {
        "id": "sql_tier2_join_refunds",
        "difficulty": 2,
        "prompt": "Join refunds onto their transaction. Return transaction_id, transaction_amount, and refund_amount.",
        "tables": [
            {
                "name": "transactions",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "transaction_amount", "type": "numeric"},
                ],
                "rows": [
                    {"id": 2, "transaction_amount": 890.00},
                    {"id": 4, "transaction_amount": 42.50},
                ],
            },
            {
                "name": "refunds",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "transaction_id", "type": "bigint"},
                    {"column": "refund_amount", "type": "numeric"},
                ],
                "rows": [
                    {"id": 1, "transaction_id": 2, "refund_amount": 890.00},
                    {"id": 2, "transaction_id": 4, "refund_amount": 10.00},
                ],
            },
        ],
        "expected_output_rows": [
            {"transaction_id": 2, "transaction_amount": 890.00, "refund_amount": 890.00},
            {"transaction_id": 4, "transaction_amount": 42.50, "refund_amount": 10.00},
        ],
    },
    {
        "id": "sql_tier2_having",
        "difficulty": 2,
        "prompt": "Total spend per account, only accounts whose total spend is over 500.",
        "table_name": "transactions",
        "schema": [
            {"column": "id", "type": "bigint"},
            {"column": "account_id", "type": "bigint"},
            {"column": "transaction_amount", "type": "numeric"},
        ],
        "example_rows": [
            {"id": 1, "account_id": 201, "transaction_amount": 25.00},
            {"id": 2, "account_id": 201, "transaction_amount": 890.00},
            {"id": 3, "account_id": 202, "transaction_amount": 1500.00},
            {"id": 4, "account_id": 202, "transaction_amount": 42.50},
        ],
        "expected_output_rows": [
            {"account_id": 201, "total": 915.00},
            {"account_id": 202, "total": 1542.50},
        ],
    },
    {
        "id": "sql_tier3_running_total",
        "difficulty": 3,
        "prompt": "Add a running total of transaction_amount per account, ordered by id within each account.",
        "table_name": "transactions",
        "schema": [
            {"column": "id", "type": "bigint"},
            {"column": "account_id", "type": "bigint"},
            {"column": "transaction_amount", "type": "numeric"},
        ],
        "example_rows": [
            {"id": 1, "account_id": 201, "transaction_amount": 25.00},
            {"id": 2, "account_id": 201, "transaction_amount": 890.00},
            {"id": 3, "account_id": 202, "transaction_amount": 1500.00},
            {"id": 4, "account_id": 202, "transaction_amount": 42.50},
        ],
        "expected_output_rows": [
            {"id": 1, "account_id": 201, "transaction_amount": 25.00, "running_total": 25.00},
            {"id": 2, "account_id": 201, "transaction_amount": 890.00, "running_total": 915.00},
            {"id": 3, "account_id": 202, "transaction_amount": 1500.00, "running_total": 1500.00},
            {"id": 4, "account_id": 202, "transaction_amount": 42.50, "running_total": 1542.50},
        ],
        "starter_sql": (
            "SELECT id, account_id, transaction_amount,\n"
            "       SUM(transaction_amount) OVER (PARTITION BY account_id ORDER BY id) AS running_total\n"
            "FROM transactions;"
        ),
    },
    {
        "id": "sql_tier3_dedupe_redelivered",
        "difficulty": 3,
        "prompt": "These events were redelivered (same event_id, different received_at). Keep only the first delivery of each.",
        "table_name": "raw_events",
        "schema": [
            {"column": "id", "type": "bigint"},
            {"column": "event_id", "type": "text"},
            {"column": "received_at", "type": "timestamptz"},
            {"column": "amount", "type": "numeric"},
        ],
        "example_rows": [
            {"id": 1, "event_id": "evt_1", "received_at": "2026-01-01T10:00:00+00", "amount": 50.00},
            {"id": 2, "event_id": "evt_1", "received_at": "2026-01-01T10:05:00+00", "amount": 50.00},
            {"id": 3, "event_id": "evt_2", "received_at": "2026-01-01T11:00:00+00", "amount": 75.00},
        ],
        "expected_output_rows": [
            {"event_id": "evt_1", "amount": 50.00},
            {"event_id": "evt_2", "amount": 75.00},
        ],
    },
]

PYTHON_CHALLENGE_POOL: list[dict] = [
    {
        "id": "py_tier1_dedupe_order",
        "difficulty": 1,
        "prompt": "Write dedupe_preserve_order(items) that removes duplicates from a list, keeping only each value's first occurrence, in order.",
        "function_name": "dedupe_preserve_order",
        "starter_code": "def dedupe_preserve_order(items):\n    pass\n",
        "test_cases": [
            {"args": [[3, 1, 3, 2, 1]], "expected": [3, 1, 2]},
            {"args": [["a", "b", "a"]], "expected": ["a", "b"]},
            {"args": [[]], "expected": []},
        ],
    },
    {
        "id": "py_tier1_total_amount",
        "difficulty": 1,
        "prompt": "Write total_amount(transactions) that sums the 'amount' field across a list of transaction dicts.",
        "function_name": "total_amount",
        "starter_code": "def total_amount(transactions):\n    pass\n",
        "test_cases": [
            {"args": [[{"amount": 10.5}, {"amount": 20}, {"amount": 5.5}]], "expected": 36.0},
            {"args": [[]], "expected": 0},
        ],
    },
    {
        "id": "py_tier2_group_by_key",
        "difficulty": 2,
        "prompt": "Write group_by_key(records, key) that groups a list of dicts into {value: [matching records]} by one of their own fields.",
        "function_name": "group_by_key",
        "starter_code": "def group_by_key(records, key):\n    pass\n",
        "test_cases": [
            {
                "args": [
                    [
                        {"category": "food", "amount": 10},
                        {"category": "transport", "amount": 20},
                        {"category": "food", "amount": 5},
                    ],
                    "category",
                ],
                "expected": {
                    "food": [{"category": "food", "amount": 10}, {"category": "food", "amount": 5}],
                    "transport": [{"category": "transport", "amount": 20}],
                },
            },
        ],
    },
    {
        "id": "py_tier2_running_total",
        "difficulty": 2,
        "prompt": "Write running_total(amounts) that returns the cumulative sum at each position.",
        "function_name": "running_total",
        "starter_code": "def running_total(amounts):\n    pass\n",
        "test_cases": [
            {"args": [[10, 20, -5, 15]], "expected": [10, 30, 25, 40]},
            {"args": [[]], "expected": []},
        ],
    },
    {
        "id": "py_tier3_dedupe_keep_latest",
        "difficulty": 3,
        "prompt": "Write dedupe_by_key_keep_latest(records, key, timestamp_key) that returns {key_value: winning_record}, keeping whichever record has the largest timestamp_key per key_value.",
        "function_name": "dedupe_by_key_keep_latest",
        "starter_code": "def dedupe_by_key_keep_latest(records, key, timestamp_key):\n    pass\n",
        "test_cases": [
            {
                "args": [
                    [
                        {"event_id": "e1", "ts": "2026-01-01T10:00:00", "amount": 50},
                        {"event_id": "e1", "ts": "2026-01-01T10:05:00", "amount": 50},
                        {"event_id": "e2", "ts": "2026-01-01T11:00:00", "amount": 75},
                    ],
                    "event_id",
                    "ts",
                ],
                "expected": {
                    "e1": {"event_id": "e1", "ts": "2026-01-01T10:05:00", "amount": 50},
                    "e2": {"event_id": "e2", "ts": "2026-01-01T11:00:00", "amount": 75},
                },
            },
        ],
    },
    {
        "id": "py_tier3_parse_fixed_width",
        "difficulty": 3,
        "prompt": "Write parse_fixed_width(line, widths) that slices a fixed-width record string into trimmed fields per the given column widths.",
        "function_name": "parse_fixed_width",
        "starter_code": "def parse_fixed_width(line, widths):\n    pass\n",
        "test_cases": [
            {"args": ["JOHN      DOE       030", [10, 10, 3]], "expected": ["JOHN", "DOE", "030"]},
        ],
    },
]
