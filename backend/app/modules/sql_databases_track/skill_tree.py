"""Module 18: the new "SQL Databases" track - generic, DB-agnostic SQL
fundamentals (WHERE, JOIN, GROUP BY/ORDER BY, NULL handling), per
CURRICULUM_STRUCTURE.md's SQL-umbrella split. Deliberately NOT the real
51,495-row fintech feed or the real `public.transactions`/`public.accounts`
tables - those are Postgres-track/capstone-scale content. These are
small, hand-sized teaching copies of the same fintech domain (consistent
with the project's one-company throughline) with only the few columns
each lesson actually needs, not the real ~20-column ISO-8583-inspired
schema from data_generation/schema.py. Every example row and expected
output below was captured by actually creating these exact tables and
running these exact queries against real Postgres, then copying the real
result - not hand-typed (same verify-by-running standard as Module 14)."""

SQL_DATABASES_SKILL_TREE = {
    "paradigm": "sql-databases",
    "nodes": [
        {
            "id": "intro",
            "type": "intro",
            "title": "SQL: one language, every relational database",
            "body": (
                "WHERE, JOIN, GROUP BY, and NULL handling work almost identically whether you're "
                "writing Postgres, MySQL, or SQL Server - these are the universal fundamentals, "
                "not Postgres-specific ones. This short track covers them on small, hand-sized "
                "data; the Postgres track right after goes deep on what's specific to Postgres "
                "itself (and does it at real, million-row scale)."
            ),
        },
        {
            "id": "node_1_where",
            "type": "skill",
            "title": "Filtering rows with WHERE",
            "teach": {
                "sql": (
                    "SELECT id, merchant_name, transaction_amount\n"
                    "FROM transactions\n"
                    "WHERE transaction_amount > 1000;"
                ),
                "note": (
                    "WHERE filters rows before they're returned - only rows where the condition "
                    "is true make it into the result. Comparison operators (>, <, =, !=) work on "
                    "numbers, text, and dates alike."
                ),
            },
            "practice": {
                "prompt": "Find every transaction over $1000. Return id, merchant_name, and transaction_amount.",
                "table_name": "transactions",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "account_id", "type": "bigint"},
                    {"column": "transaction_amount", "type": "numeric"},
                    {"column": "merchant_name", "type": "text"},
                    {"column": "channel", "type": "text"},
                ],
                "example_rows": [
                    {"id": 1, "account_id": 101, "transaction_amount": 45.00, "merchant_name": "Corner Cafe", "channel": "POS"},
                    {"id": 2, "account_id": 101, "transaction_amount": 1250.00, "merchant_name": "Best Electronics", "channel": "online"},
                    {"id": 3, "account_id": 102, "transaction_amount": 2500.50, "merchant_name": "Travel Agency", "channel": "online"},
                ],
                "expected_output_rows": [
                    {"id": 2, "merchant_name": "Best Electronics", "transaction_amount": 1250.00},
                    {"id": 3, "merchant_name": "Travel Agency", "transaction_amount": 2500.50},
                ],
            },
        },
        {
            "id": "node_2_join",
            "type": "skill",
            "title": "Combining tables with JOIN",
            "teach": {
                "sql": (
                    "SELECT t.id AS transaction_id, a.card_network, t.transaction_amount\n"
                    "FROM transactions t\n"
                    "JOIN accounts a ON a.id = t.account_id;"
                ),
                "note": (
                    "A JOIN matches rows across two tables using a shared key (here, "
                    "accounts.id = transactions.account_id) - this is exactly how you'd pull "
                    "card_network onto a transactions row without duplicating it into every "
                    "single transaction."
                ),
            },
            "practice": {
                "prompt": (
                    "Join accounts to transactions on account id. Return transaction_id, "
                    "card_network, and transaction_amount for every transaction."
                ),
                "tables": [
                    {
                        "name": "transactions",
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
                        "name": "accounts",
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
                    {"transaction_id": 1, "card_network": "Visa", "transaction_amount": 45.00},
                    {"transaction_id": 2, "card_network": "Visa", "transaction_amount": 1250.00},
                    {"transaction_id": 3, "card_network": "Mastercard", "transaction_amount": 2500.50},
                ],
            },
        },
        {
            "id": "node_3_group_order",
            "type": "skill",
            "title": "Aggregating with GROUP BY and ORDER BY",
            "teach": {
                "sql": (
                    "SELECT account_id, SUM(transaction_amount) AS total_spent\n"
                    "FROM transactions\n"
                    "GROUP BY account_id\n"
                    "ORDER BY total_spent DESC;"
                ),
                "note": (
                    "GROUP BY collapses rows sharing the same account_id into one row per group, "
                    "letting an aggregate (SUM, COUNT, AVG) summarize each group. ORDER BY then "
                    "sorts the *groups themselves* by that summary - here, biggest spender first."
                ),
            },
            "practice": {
                "prompt": "Total spend per account, highest spender first.",
                "table_name": "transactions",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "account_id", "type": "bigint"},
                    {"column": "transaction_amount", "type": "numeric"},
                ],
                "example_rows": [
                    {"id": 1, "account_id": 101, "transaction_amount": 45.00},
                    {"id": 2, "account_id": 101, "transaction_amount": 1250.00},
                    {"id": 3, "account_id": 102, "transaction_amount": 2500.50},
                ],
                "expected_output_rows": [
                    {"account_id": 102, "total_spent": 2500.50},
                    {"account_id": 101, "total_spent": 1295.00},
                ],
            },
        },
        {
            "id": "node_4_nulls",
            "type": "skill",
            "title": "Handling NULLs with COALESCE",
            "teach": {
                "sql": (
                    "SELECT id, COALESCE(merchant_name, 'Unknown merchant') AS merchant_name, transaction_amount\n"
                    "FROM transactions;"
                ),
                "note": (
                    "A missing merchant_name isn't an empty string - it's NULL, SQL's \"no value "
                    "recorded\" marker. COALESCE(a, b) returns a unless it's NULL, in which case it "
                    "returns the fallback b - the standard way to substitute a readable default "
                    "instead of surfacing a raw NULL."
                ),
            },
            "practice": {
                "prompt": "Replace a missing merchant_name with 'Unknown merchant' instead of leaving it NULL.",
                "table_name": "transactions",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "account_id", "type": "bigint"},
                    {"column": "transaction_amount", "type": "numeric"},
                    {"column": "merchant_name", "type": "text"},
                    {"column": "channel", "type": "text"},
                ],
                "example_rows": [
                    {"id": 1, "account_id": 101, "transaction_amount": 45.00, "merchant_name": "Corner Cafe", "channel": "POS"},
                    {"id": 2, "account_id": 101, "transaction_amount": 1250.00, "merchant_name": None, "channel": "online"},
                ],
                "expected_output_rows": [
                    {"id": 1, "merchant_name": "Corner Cafe", "transaction_amount": 45.00},
                    {"id": 2, "merchant_name": "Unknown merchant", "transaction_amount": 1250.00},
                ],
            },
        },
        {
            "id": "review",
            "type": "review",
            "title": "Review: WHERE, JOIN, GROUP BY/ORDER BY, NULLs",
            "prompt": (
                "A quick recap of this track's four fundamentals before moving into the Postgres "
                "track, which goes deep on Postgres specifically - constraints, indexing, "
                "transactions, partitioning - starting from the real million-row feed."
            ),
        },
    ],
}
