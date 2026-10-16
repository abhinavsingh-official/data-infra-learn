"""The "Warehouse Databases" track - generic dimensional-modeling
fundamentals (declaring the grain, star-schema JOINs, querying a
historized SCD2 dimension, fact aggregation), grounded in the Kimball
method's four-step design process. Same division of labor as
sql_databases_track vs. postgres_phase, and mongo_databases_track vs.
nosql_phase: these are small, hand-sized teaching tables run through
node_practice.py's plain-Postgres engine, not the real warehouse_phase
capstone's Spark/Delta star schema at real scale (see node_practice.py's
own docstring - the fundamentals-track engine isn't tied to whatever the
real capstone happens to run on). Every example row and expected output
below was captured by creating these exact tables and running these
exact queries against real Postgres, then copying the real result
rather than hand-typing it."""

WAREHOUSE_DATABASES_SKILL_TREE = {
    "paradigm": "warehouse-databases",
    "nodes": [
        {
            "id": "intro",
            "type": "intro",
            "title": "Kimball's four steps: process, grain, dimensions, facts",
            "body": (
                "Kimball's own design process has four steps: pick a business process, declare "
                "the grain (what one row in the fact table actually represents), identify the "
                "dimensions that describe it, identify the facts (numbers) to measure. This track "
                "walks through the SQL consequence of each step, on small, hand-sized data - the "
                "Warehouse capstone right after does the same four steps for real, against real "
                "Spark + Delta at full scale."
            ),
        },
        {
            "id": "node_1_grain",
            "type": "skill",
            "title": "Declaring the grain: one row per account, not per event",
            "teach": {
                "sql": (
                    "SELECT account_id, card_network\n"
                    "FROM raw_account_events\n"
                    "GROUP BY account_id, card_network;"
                ),
                "note": (
                    "Declaring the grain means deciding up front what one output row represents. "
                    "The raw feed has one row per *event* (opened, reissued); a dim_accounts table "
                    "needs one row per *account*. GROUP BY on the dimension's own key collapses "
                    "repeated events down to that grain - the first real decision in Kimball's "
                    "four-step process, before a single fact table exists."
                ),
                "steps": [
                    {
                        "body": "Before you build anything, Kimball's process asks one question "
                        "first: what does one row in your output actually represent?"
                    },
                    {
                        "body": "GROUP BY on the key you want collapses repeats down to it:",
                        "sql": "SELECT key_column\nFROM raw_events\nGROUP BY key_column;",
                    },
                    {
                        "body": "Collapse this raw event feed into one row per account:",
                        "sql": "SELECT account_id, card_network\nFROM raw_account_events\nGROUP BY account_id, card_network;",
                    },
                    {
                        "body": "The raw feed has one row per *event* (opened, reissued); "
                        "a dim_accounts table needs one row per *account* - that's the grain "
                        "decision, made before a single fact table exists."
                    },
                    {
                        "body": "Declaring the grain means deciding up front what one output row "
                        "represents. Try it yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Collapse this raw event feed into one row per account, with its card_network.",
                "table_name": "raw_account_events",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "account_id", "type": "bigint"},
                    {"column": "card_network", "type": "text"},
                    {"column": "event_type", "type": "text"},
                ],
                "example_rows": [
                    {"id": 1, "account_id": 101, "card_network": "Visa", "event_type": "opened"},
                    {"id": 2, "account_id": 101, "card_network": "Visa", "event_type": "card_reissued"},
                    {"id": 3, "account_id": 102, "card_network": "Mastercard", "event_type": "opened"},
                ],
                "expected_output_rows": [
                    {"account_id": 101, "card_network": "Visa"},
                    {"account_id": 102, "card_network": "Mastercard"},
                ],
            },
        },
        {
            "id": "node_2_star_join",
            "type": "skill",
            "title": "The star schema: one fact table, dimensions radiating out",
            "teach": {
                "sql": (
                    "SELECT f.id AS transaction_id, a.card_network, m.merchant_name, f.transaction_amount\n"
                    "FROM fact_transactions f\n"
                    "JOIN dim_accounts a ON a.id = f.account_id\n"
                    "JOIN dim_merchants m ON m.id = f.merchant_id;"
                ),
                "note": (
                    "A star schema's fact table holds foreign keys and numbers; every descriptive "
                    "attribute lives in a dimension table one JOIN away. This is the whole point of "
                    "the shape - fact_transactions never repeats 'Visa' or 'Corner Cafe' on every "
                    "row, it just points at the one dimension row that says so."
                ),
                "steps": [
                    {
                        "body": "A star schema puts one fact table at the center, with "
                        "descriptive dimension tables radiating out - a shape, not just a name."
                    },
                    {
                        "body": "The fact table holds keys and numbers; dimensions hold the rest:",
                        "sql": "SELECT f.id, d1.name, d2.name, f.amount\nFROM fact f\nJOIN dim_a d1 ON d1.id = f.a_id\nJOIN dim_b d2 ON d2.id = f.b_id;",
                    },
                    {
                        "body": "Join the fact table to both dimension tables:",
                        "sql": (
                            "SELECT f.id AS transaction_id, a.card_network, m.merchant_name, f.transaction_amount\n"
                            "FROM fact_transactions f\n"
                            "JOIN dim_accounts a ON a.id = f.account_id\n"
                            "JOIN dim_merchants m ON m.id = f.merchant_id;"
                        ),
                    },
                    {
                        "body": "fact_transactions never repeats 'Visa' or 'Corner Cafe' on "
                        "every row - it just points at the one dimension row that says so. This "
                        "is the whole point of the shape."
                    },
                    {
                        "body": "A fact table holds foreign keys and numbers; dimensions hold "
                        "every descriptive attribute, one JOIN away. Try it yourself in the "
                        "Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": (
                    "Join the fact table to both dimension tables. Return transaction_id, "
                    "card_network, merchant_name, and transaction_amount."
                ),
                "tables": [
                    {
                        "name": "fact_transactions",
                        "schema": [
                            {"column": "id", "type": "bigint"},
                            {"column": "account_id", "type": "bigint"},
                            {"column": "merchant_id", "type": "bigint"},
                            {"column": "transaction_amount", "type": "numeric"},
                        ],
                        "rows": [
                            {"id": 1, "account_id": 101, "merchant_id": 201, "transaction_amount": 45.00},
                            {"id": 2, "account_id": 101, "merchant_id": 202, "transaction_amount": 1250.00},
                            {"id": 3, "account_id": 102, "merchant_id": 201, "transaction_amount": 2500.50},
                        ],
                    },
                    {
                        "name": "dim_accounts",
                        "schema": [
                            {"column": "id", "type": "bigint"},
                            {"column": "card_network", "type": "text"},
                        ],
                        "rows": [
                            {"id": 101, "card_network": "Visa"},
                            {"id": 102, "card_network": "Mastercard"},
                        ],
                    },
                    {
                        "name": "dim_merchants",
                        "schema": [
                            {"column": "id", "type": "bigint"},
                            {"column": "merchant_name", "type": "text"},
                        ],
                        "rows": [
                            {"id": 201, "merchant_name": "Corner Cafe"},
                            {"id": 202, "merchant_name": "Best Electronics"},
                        ],
                    },
                ],
                "expected_output_rows": [
                    {"transaction_id": 1, "card_network": "Visa", "merchant_name": "Corner Cafe", "transaction_amount": 45.00},
                    {"transaction_id": 2, "card_network": "Visa", "merchant_name": "Best Electronics", "transaction_amount": 1250.00},
                    {"transaction_id": 3, "card_network": "Mastercard", "merchant_name": "Corner Cafe", "transaction_amount": 2500.50},
                ],
            },
        },
        {
            "id": "node_3_scd2_current",
            "type": "skill",
            "title": "Querying a Slowly Changing Dimension: only the current row",
            "teach": {
                "sql": (
                    "SELECT account_id, card_network\n"
                    "FROM dim_accounts_scd2\n"
                    "WHERE is_current = true;"
                ),
                "note": (
                    "SCD Type 2 keeps every historical version of a dimension row instead of "
                    "overwriting it - each version gets its own valid_from/valid_to and an "
                    "is_current flag. A query that forgets the is_current filter double-counts an "
                    "account that's changed: here, account 101 has two rows (old network, new "
                    "network), and only one of them is current."
                ),
                "steps": [
                    {
                        "body": "When a customer's own attributes change, do you overwrite the "
                        "old value and lose history, or keep both versions? SCD Type 2 keeps both."
                    },
                    {
                        "body": "Every version gets a flag - filter to the current one:",
                        "sql": "SELECT key, value\nFROM dim_table\nWHERE is_current = true;",
                    },
                    {
                        "body": "Return each account's current card_network only:",
                        "sql": "SELECT account_id, card_network\nFROM dim_accounts_scd2\nWHERE is_current = true;",
                    },
                    {
                        "body": "A query that forgets the is_current filter double-counts an "
                        "account that's changed - here, account 101 has two rows (old network, "
                        "new network), and only one of them is current."
                    },
                    {
                        "body": "SCD Type 2 keeps every historical version of a row instead of "
                        "overwriting it. Try it yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Return each account's current card_network only - not its historical versions.",
                "table_name": "dim_accounts_scd2",
                "schema": [
                    {"column": "surrogate_key", "type": "bigint"},
                    {"column": "account_id", "type": "bigint"},
                    {"column": "card_network", "type": "text"},
                    {"column": "valid_from", "type": "date"},
                    {"column": "valid_to", "type": "date"},
                    {"column": "is_current", "type": "boolean"},
                ],
                "example_rows": [
                    {"surrogate_key": 1, "account_id": 101, "card_network": "Visa Classic", "valid_from": "2025-01-01", "valid_to": "2026-03-01", "is_current": False},
                    {"surrogate_key": 2, "account_id": 101, "card_network": "Visa Signature", "valid_from": "2026-03-01", "valid_to": None, "is_current": True},
                    {"surrogate_key": 3, "account_id": 102, "card_network": "Mastercard", "valid_from": "2025-01-01", "valid_to": None, "is_current": True},
                ],
                "expected_output_rows": [
                    {"account_id": 101, "card_network": "Visa Signature"},
                    {"account_id": 102, "card_network": "Mastercard"},
                ],
            },
        },
        {
            "id": "node_4_fact_aggregate",
            "type": "skill",
            "title": "Analytics queries: the whole reason the star schema exists",
            "teach": {
                "sql": (
                    "SELECT a.card_network, SUM(f.transaction_amount) AS total_spent\n"
                    "FROM fact_transactions f\n"
                    "JOIN dim_accounts a ON a.id = f.account_id\n"
                    "GROUP BY a.card_network\n"
                    "ORDER BY total_spent DESC;"
                ),
                "note": (
                    "Total spend by card network is one JOIN and one GROUP BY against a star "
                    "schema - the same question against raw OLTP tables would need to untangle "
                    "accounts, cards, and transactions across several more joins. This is the "
                    "payoff for the grain decision back in node 1."
                ),
                "steps": [
                    {
                        "body": "This is the actual payoff for everything so far: a star schema "
                        "turns a real business question into one JOIN and one GROUP BY."
                    },
                    {
                        "body": "Join to a dimension, then aggregate by its attribute:",
                        "sql": "SELECT d.attribute, SUM(f.amount)\nFROM fact f\nJOIN dim d ON d.id = f.dim_id\nGROUP BY d.attribute;",
                    },
                    {
                        "body": "Total transaction amount by card_network, highest spender first:",
                        "sql": (
                            "SELECT a.card_network, SUM(f.transaction_amount) AS total_spent\n"
                            "FROM fact_transactions f\n"
                            "JOIN dim_accounts a ON a.id = f.account_id\n"
                            "GROUP BY a.card_network\n"
                            "ORDER BY total_spent DESC;"
                        ),
                    },
                    {
                        "body": "The same question against raw OLTP tables would need to "
                        "untangle accounts, cards, and transactions across several more joins - "
                        "this is the payoff for the grain decision back in node 1."
                    },
                    {
                        "body": "Analytics-shaped questions are one JOIN and one GROUP BY away "
                        "on a star schema. Try it yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Total transaction amount by card_network, highest spender first.",
                "tables": [
                    {
                        "name": "fact_transactions",
                        "schema": [
                            {"column": "id", "type": "bigint"},
                            {"column": "account_id", "type": "bigint"},
                            {"column": "transaction_amount", "type": "numeric"},
                        ],
                        "rows": [
                            {"id": 1, "account_id": 101, "transaction_amount": 45.00},
                            {"id": 2, "account_id": 101, "transaction_amount": 1250.00},
                            {"id": 3, "account_id": 102, "transaction_amount": 2500.50},
                        ],
                    },
                    {
                        "name": "dim_accounts",
                        "schema": [
                            {"column": "id", "type": "bigint"},
                            {"column": "card_network", "type": "text"},
                        ],
                        "rows": [
                            {"id": 101, "card_network": "Visa"},
                            {"id": 102, "card_network": "Mastercard"},
                        ],
                    },
                ],
                "expected_output_rows": [
                    {"card_network": "Mastercard", "total_spent": 2500.50},
                    {"card_network": "Visa", "total_spent": 1295.00},
                ],
            },
        },
        {
            "id": "review",
            "type": "review",
            "title": "Review: grain, star JOINs, SCD2, fact aggregation",
            "prompt": (
                "A quick recap of Kimball's four-step process in SQL form before moving into the "
                "Warehouse capstone, which builds this same star schema for real - against the "
                "actual fintech feed, on real Spark + Delta, with a real SCD2 re-run."
            ),
        },
    ],
}
