"""Module 8's exercise description. Content, not logic - same pattern as
the other phases' task_content modules."""

WAREHOUSE_PHASE_TASK = {
    "title": "Build a star schema, then survive a changing dimension",
    "summary": (
        "The same fintech data, remodeled a third way: a Kimball-style star schema instead of "
        "rows or documents. Your DuckDB session already has the Postgres source attached as "
        "'pg' and a local copy of accounts as source_accounts_snapshot - build your star schema "
        "from those, then prove it survives a real dimension change, not just a first load."
    ),
    "source": {
        "pg.users, pg.transactions, pg.reward_events, pg.repayments": (
            "live, read-only, attached automatically - query them directly, e.g. "
            "SELECT * FROM pg.users LIMIT 10"
        ),
        "source_accounts_snapshot": (
            "a local, session-owned copy of accounts (the bronze layer) - build dim_accounts "
            "from THIS, not pg.accounts directly, since this is the table that changes on day 2"
        ),
    },
    "required_output": {
        "dim_accounts": {
            "note": "SCD Type 2 - every historical version of an account's tracked attributes, not just the latest.",
            "columns": {
                "account_key": "surrogate key, unique per row (not per account)",
                "account_id": "natural key - source_accounts_snapshot.id",
                "card_network": "from source_accounts_snapshot",
                "account_status": "from source_accounts_snapshot - the tracked attribute",
                "credit_limit": "from source_accounts_snapshot - the other tracked attribute",
                "valid_from": "timestamp this version became current",
                "valid_to": "timestamp this version stopped being current, or null if it's still current",
                "is_current": "boolean - exactly one true row per account_id, always",
            },
        },
        "dim_users": {
            "note": "SCD Type 1 (deliberate contrast to dim_accounts) - always overwritten in place, no history kept.",
            "columns": {
                "user_key": "surrogate key",
                "external_user_id": "natural key - pg.users.external_user_id",
                "full_name": "from pg.users",
                "email": "from pg.users",
                "kyc_status": "from pg.users",
                "country": "from pg.users",
                "is_active": "from pg.users",
            },
        },
        "fact_transactions": {
            "note": (
                "grain: one row per transaction. account_key/user_key resolve to whichever "
                "dimension row is CURRENT at query time - not a point-in-time-accurate "
                "historical join. Stated as a deliberate scope simplification, not hidden."
            ),
            "columns": {
                "transaction_key": "pg.transactions.retrieval_reference_number (natural key, unique)",
                "account_key": "FK into dim_accounts' current row for this transaction's account",
                "user_key": "FK into dim_users for this account's owner",
                "amount": "pg.transactions.transaction_amount",
                "merchant": "pg.transactions.merchant_name",
                "transaction_timestamp": "pg.transactions.transaction_timestamp",
            },
        },
    },
    "workflow": [
        "1. Build dim_users and dim_accounts (v1, every row is_current) and fact_transactions from the day-1 snapshot.",
        "2. POST /warehouse-phase/sessions/{id}/simulate-changes - the platform mutates ~10% of "
        "source_accounts_snapshot's account_status/credit_limit (day 2 begins). This step is "
        "idempotent - calling it again after it's already run does nothing further.",
        "3. Re-run your dim_accounts ETL. Correct SCD2 logic closes out the old row for every "
        "changed account (valid_to set, is_current = false) and inserts one new current row - "
        "unchanged accounts must be left with exactly one row, untouched.",
        "4. Grade with POST /warehouse-phase/sessions/{id}/grade.",
    ],
    "hint": (
        "A naive re-run that just overwrites dim_accounts in place, or that always inserts a new "
        "row whether or not anything changed, both look fine on a single load and both fail this "
        "task's actual point - test your ETL by running it twice before you grade."
    ),
    "dataset_stats": [
        {"label": "Users", "value": "10,000", "hint": "pg.users - dim_users, SCD Type 1"},
        {"label": "Accounts", "value": "15,000", "hint": "source_accounts_snapshot - dim_accounts, SCD Type 2"},
        {"label": "Transactions", "value": "1,000,000", "hint": "pg.transactions - fact_transactions"},
        {"label": "Accounts mutated on day 2", "value": "~1,188", "hint": "id % 10 = 0 and still active"},
    ],
    "starter_sql": (
        "-- Start by looking at the day-1 snapshot you build from:\n"
        "SELECT * FROM source_accounts_snapshot LIMIT 20;\n\n"
        "-- Then build your dimensions and fact table, e.g.:\n"
        "-- CREATE TABLE dim_users AS\n"
        "-- SELECT ROW_NUMBER() OVER () AS user_key, external_user_id, full_name, email, kyc_status, country, is_active\n"
        "-- FROM pg.users;\n"
    ),
    "reference_solution": {
        "sql": (
            "CREATE TABLE dim_users AS\n"
            "SELECT ROW_NUMBER() OVER () AS user_key, external_user_id, full_name, email, kyc_status, country, is_active\n"
            "FROM pg.users;\n\n"
            "CREATE TABLE dim_accounts AS\n"
            "SELECT\n"
            "  ROW_NUMBER() OVER () AS account_key,\n"
            "  id AS account_id, card_network, account_status, credit_limit,\n"
            "  now() AS valid_from, CAST(NULL AS TIMESTAMP) AS valid_to, true AS is_current\n"
            "FROM source_accounts_snapshot;\n\n"
            "-- Re-run after simulate-changes: close out changed rows, then insert new current ones.\n"
            "UPDATE dim_accounts da\n"
            "SET valid_to = now(), is_current = false\n"
            "FROM source_accounts_snapshot s\n"
            "WHERE da.account_id = s.id AND da.is_current\n"
            "  AND (da.account_status != s.account_status OR da.credit_limit != s.credit_limit);\n\n"
            "INSERT INTO dim_accounts (account_key, account_id, card_network, account_status, credit_limit, valid_from, valid_to, is_current)\n"
            "SELECT\n"
            "  (SELECT COALESCE(MAX(account_key), 0) FROM dim_accounts) + ROW_NUMBER() OVER (),\n"
            "  s.id, s.card_network, s.account_status, s.credit_limit, now(), NULL, true\n"
            "FROM source_accounts_snapshot s\n"
            "JOIN dim_accounts da ON da.account_id = s.id AND NOT da.is_current\n"
            "WHERE NOT EXISTS (SELECT 1 FROM dim_accounts cur WHERE cur.account_id = s.id AND cur.is_current);\n"
        ),
        "note": (
            "The UPDATE closes out exactly the rows whose tracked attributes changed since the last "
            "load - unchanged accounts never get touched, so re-running this twice in a row inserts "
            "nothing further. dim_users stays SCD Type 1 on purpose (deliberate contrast): it's always "
            "overwritten wholesale, no history kept, no valid_from/valid_to at all."
        ),
        "steps": [
            {
                "title": "1. Naive - dim_accounts as a plain overwrite, no history at all",
                "sql": (
                    "CREATE OR REPLACE TABLE dim_accounts AS\n"
                    "SELECT\n"
                    "  ROW_NUMBER() OVER () AS account_key,\n"
                    "  id AS account_id, card_network, account_status, credit_limit\n"
                    "FROM source_accounts_snapshot;\n"
                ),
                "note": (
                    "This is what you'd write if you only ever cared about 'right now'. It works on day 1 "
                    "and looks identical on day 2 after simulate-changes - CREATE OR REPLACE just throws "
                    "the old rows away, so there's no way to tell which accounts changed or recover the "
                    "prior version. dim_accounts is supposed to be SCD Type 2 - this has zero history."
                ),
            },
            {
                "title": "2. + add the SCD2 tracking columns on initial load",
                "sql": (
                    "CREATE TABLE dim_accounts AS\n"
                    "SELECT\n"
                    "  ROW_NUMBER() OVER () AS account_key,\n"
                    "  id AS account_id, card_network, account_status, credit_limit,\n"
                    "  now() AS valid_from, CAST(NULL AS TIMESTAMP) AS valid_to, true AS is_current\n"
                    "FROM source_accounts_snapshot;\n"
                ),
                "note": (
                    "Every row starts current with an open-ended valid_to. This alone still isn't SCD2 - "
                    "there's no logic yet for what happens to a row when its account actually changes on "
                    "day 2. Without step 3, a naive re-run would still have to overwrite or duplicate."
                ),
            },
            {
                "title": "3. + on re-run, close out only the rows that actually changed",
                "sql": (
                    "UPDATE dim_accounts da\n"
                    "SET valid_to = now(), is_current = false\n"
                    "FROM source_accounts_snapshot s\n"
                    "WHERE da.account_id = s.id AND da.is_current\n"
                    "  AND (da.account_status != s.account_status OR da.credit_limit != s.credit_limit);\n"
                ),
                "note": (
                    "This is the piece a naive re-run skips entirely. Comparing the current row's tracked "
                    "attributes against the source is what tells changed accounts apart from unchanged "
                    "ones - only the changed rows get closed out, so running this against an untouched "
                    "day-1 snapshot updates nothing."
                ),
            },
            {
                "title": "4. Final: + insert one new current row per changed account",
                "sql": (
                    "CREATE TABLE dim_users AS\n"
                    "SELECT ROW_NUMBER() OVER () AS user_key, external_user_id, full_name, email, kyc_status, country, is_active\n"
                    "FROM pg.users;\n\n"
                    "CREATE TABLE dim_accounts AS\n"
                    "SELECT\n"
                    "  ROW_NUMBER() OVER () AS account_key,\n"
                    "  id AS account_id, card_network, account_status, credit_limit,\n"
                    "  now() AS valid_from, CAST(NULL AS TIMESTAMP) AS valid_to, true AS is_current\n"
                    "FROM source_accounts_snapshot;\n\n"
                    "-- Re-run after simulate-changes: close out changed rows, then insert new current ones.\n"
                    "UPDATE dim_accounts da\n"
                    "SET valid_to = now(), is_current = false\n"
                    "FROM source_accounts_snapshot s\n"
                    "WHERE da.account_id = s.id AND da.is_current\n"
                    "  AND (da.account_status != s.account_status OR da.credit_limit != s.credit_limit);\n\n"
                    "INSERT INTO dim_accounts (account_key, account_id, card_network, account_status, credit_limit, valid_from, valid_to, is_current)\n"
                    "SELECT\n"
                    "  (SELECT COALESCE(MAX(account_key), 0) FROM dim_accounts) + ROW_NUMBER() OVER (),\n"
                    "  s.id, s.card_network, s.account_status, s.credit_limit, now(), NULL, true\n"
                    "FROM source_accounts_snapshot s\n"
                    "JOIN dim_accounts da ON da.account_id = s.id AND NOT da.is_current\n"
                    "WHERE NOT EXISTS (SELECT 1 FROM dim_accounts cur WHERE cur.account_id = s.id AND cur.is_current);\n"
                ),
                "note": (
                    "Closing the old row (step 3) isn't enough on its own - every account whose old row "
                    "just got closed still needs a fresh current row inserted, or it silently drops out "
                    "of 'is_current = true'. This INSERT is scoped to exactly the accounts step 3 just "
                    "closed out, so re-running the whole thing twice in a row inserts nothing further -"
                    " that idempotency is the actual thing this task grades."
                ),
            },
        ],
    },
}
