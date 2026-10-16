"""The warehouse-phase exercise description, for PySpark/Spark SQL. A few
Spark-specific quirks worth knowing when writing or grading this
exercise's SQL:
- Spark temp views are always single-part names (no `pg.`-style
  qualification), so users/accounts/transactions/etc. are plain
  unqualified names.
- Every CREATE TABLE needs an explicit `USING DELTA` - a bare CTAS tries
  Hive's SerDe path and fails outright without Hive support configured,
  and UPDATE (needed for the SCD2 exercise) only works on Delta tables.
- `ROW_NUMBER() OVER ()` with empty parens (valid in DuckDB) isn't valid
  Spark SQL - every window function needs an explicit ORDER BY."""

WAREHOUSE_PHASE_TASK = {
    "title": "Build a star schema, then survive a changing dimension",
    "summary": (
        "The same fintech data, remodeled a third way: a Kimball-style star schema instead of "
        "rows or documents. Your Spark session already has the five relational source tables "
        "registered as live, read-only views and a local Delta copy of accounts as "
        "source_accounts_snapshot - build your star schema from those, then prove it survives a "
        "real dimension change, not just a first load."
    ),
    "source": {
        "users, transactions, reward_events, repayments": (
            "live, read-only temp views backed by the real Postgres tables - query them "
            "directly, e.g. SELECT * FROM users LIMIT 10"
        ),
        "source_accounts_snapshot": (
            "a local, session-owned Delta copy of accounts (the bronze layer) - build "
            "dim_accounts from THIS, not accounts directly, since this is the table that "
            "changes on day 2"
        ),
    },
    "required_output": {
        "dim_accounts": {
            "note": "SCD Type 2 - every historical version of an account's tracked attributes, not just the latest. Must be USING DELTA (this exercise re-runs UPDATE against it).",
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
                "external_user_id": "natural key - users.external_user_id",
                "full_name": "from users",
                "email": "from users",
                "kyc_status": "from users",
                "country": "from users",
                "is_active": "from users",
            },
        },
        "fact_transactions": {
            "note": (
                "grain: one row per transaction. account_key/user_key resolve to whichever "
                "dimension row is CURRENT at query time - not a point-in-time-accurate "
                "historical join. Stated as a deliberate scope simplification, not hidden."
            ),
            "columns": {
                "transaction_key": "transactions.retrieval_reference_number (natural key, unique)",
                "account_key": "FK into dim_accounts' current row for this transaction's account",
                "user_key": "FK into dim_users for this account's owner",
                "amount": "transactions.transaction_amount",
                "merchant": "transactions.merchant_name",
                "transaction_timestamp": "transactions.transaction_timestamp",
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
        {"label": "Users", "value": "10,000", "hint": "users - dim_users, SCD Type 1"},
        {"label": "Accounts", "value": "15,000", "hint": "source_accounts_snapshot - dim_accounts, SCD Type 2"},
        {"label": "Transactions", "value": "1,000,000", "hint": "transactions - fact_transactions"},
        {"label": "Accounts mutated on day 2", "value": "~1,188", "hint": "id % 10 = 0 and still active"},
    ],
    "starter_sql": (
        "-- Start by looking at the shape of the day-1 snapshot you build from:\n"
        "SELECT * FROM source_accounts_snapshot LIMIT 20;\n\n"
        "-- Then build your dimensions and fact table, e.g.:\n"
        "-- CREATE TABLE dim_users USING DELTA AS\n"
        "-- SELECT ROW_NUMBER() OVER (ORDER BY external_user_id) AS user_key,\n"
        "--   external_user_id, full_name, email, kyc_status, country, is_active\n"
        "-- FROM users;\n"
    ),
    "reference_solution": {
        "sql": (
            "CREATE TABLE dim_users USING DELTA AS\n"
            "SELECT ROW_NUMBER() OVER (ORDER BY external_user_id) AS user_key,\n"
            "  external_user_id, full_name, email, kyc_status, country, is_active\n"
            "FROM users;\n\n"
            "CREATE TABLE dim_accounts USING DELTA AS\n"
            "SELECT\n"
            "  ROW_NUMBER() OVER (ORDER BY id) AS account_key,\n"
            "  id AS account_id, card_network, account_status, credit_limit,\n"
            "  current_timestamp() AS valid_from, CAST(NULL AS TIMESTAMP) AS valid_to, true AS is_current\n"
            "FROM source_accounts_snapshot;\n\n"
            "-- Re-run after simulate-changes: close out changed rows, then insert new current ones.\n"
            "MERGE INTO dim_accounts tgt\n"
            "USING (\n"
            "  SELECT s.id FROM source_accounts_snapshot s\n"
            "  JOIN dim_accounts da ON da.account_id = s.id AND da.is_current\n"
            "  WHERE da.account_status != s.account_status OR da.credit_limit != s.credit_limit\n"
            ") changed\n"
            "ON tgt.account_id = changed.id AND tgt.is_current\n"
            "WHEN MATCHED THEN UPDATE SET valid_to = current_timestamp(), is_current = false;\n\n"
            "INSERT INTO dim_accounts\n"
            "SELECT\n"
            "  (SELECT COALESCE(MAX(account_key), 0) FROM dim_accounts) + ROW_NUMBER() OVER (ORDER BY s.id),\n"
            "  s.id, s.card_network, s.account_status, s.credit_limit, current_timestamp(), NULL, true\n"
            "FROM source_accounts_snapshot s\n"
            "JOIN dim_accounts da ON da.account_id = s.id AND NOT da.is_current\n"
            "WHERE NOT EXISTS (SELECT 1 FROM dim_accounts cur WHERE cur.account_id = s.id AND cur.is_current);\n"
        ),
        "note": (
            "MERGE INTO, not UPDATE, closes out exactly the rows whose tracked attributes changed since "
            "the last load - unchanged accounts never get touched, so re-running this twice in a row "
            "inserts nothing further. This has to be MERGE, not a plain UPDATE with a join/subquery in its "
            "condition - Delta's UPDATE doesn't support subqueries in the WHERE clause at all; MERGE INTO "
            "is Delta's real mechanism for 'update rows based on matching another table', the same "
            "technique real Databricks SCD2 pipelines use. dim_accounts "
            "must be USING DELTA for MERGE/UPDATE to work at all - Spark SQL's plain managed tables don't "
            "support them, only Delta (and a few other formats) do. dim_users stays SCD Type 1 on purpose "
            "(deliberate contrast): it's always overwritten wholesale, no history kept, no "
            "valid_from/valid_to at all."
        ),
        "steps": [
            {
                "title": "1. Naive - dim_accounts as a plain overwrite, no history at all",
                "sql": (
                    "CREATE OR REPLACE TABLE dim_accounts USING DELTA AS\n"
                    "SELECT\n"
                    "  ROW_NUMBER() OVER (ORDER BY id) AS account_key,\n"
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
                    "CREATE TABLE dim_accounts USING DELTA AS\n"
                    "SELECT\n"
                    "  ROW_NUMBER() OVER (ORDER BY id) AS account_key,\n"
                    "  id AS account_id, card_network, account_status, credit_limit,\n"
                    "  current_timestamp() AS valid_from, CAST(NULL AS TIMESTAMP) AS valid_to, true AS is_current\n"
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
                    "MERGE INTO dim_accounts tgt\n"
                    "USING (\n"
                    "  SELECT s.id FROM source_accounts_snapshot s\n"
                    "  JOIN dim_accounts da ON da.account_id = s.id AND da.is_current\n"
                    "  WHERE da.account_status != s.account_status OR da.credit_limit != s.credit_limit\n"
                    ") changed\n"
                    "ON tgt.account_id = changed.id AND tgt.is_current\n"
                    "WHEN MATCHED THEN UPDATE SET valid_to = current_timestamp(), is_current = false;\n"
                ),
                "note": (
                    "This is the piece a naive re-run skips entirely. Comparing the current row's tracked "
                    "attributes against the source is what tells changed accounts apart from unchanged "
                    "ones - only the changed rows get closed out, so running this against an untouched "
                    "day-1 snapshot updates nothing. Written as MERGE INTO, not a plain UPDATE - Delta's "
                    "UPDATE doesn't support a subquery/join in its condition at all, so 'update rows based "
                    "on matching another table' always goes through MERGE on this engine, not Postgres's "
                    "UPDATE ... FROM syntax."
                ),
            },
            {
                "title": "4. Final: + insert one new current row per changed account",
                "sql": (
                    "CREATE TABLE dim_users USING DELTA AS\n"
                    "SELECT ROW_NUMBER() OVER (ORDER BY external_user_id) AS user_key,\n"
                    "  external_user_id, full_name, email, kyc_status, country, is_active\n"
                    "FROM users;\n\n"
                    "CREATE TABLE dim_accounts USING DELTA AS\n"
                    "SELECT\n"
                    "  ROW_NUMBER() OVER (ORDER BY id) AS account_key,\n"
                    "  id AS account_id, card_network, account_status, credit_limit,\n"
                    "  current_timestamp() AS valid_from, CAST(NULL AS TIMESTAMP) AS valid_to, true AS is_current\n"
                    "FROM source_accounts_snapshot;\n\n"
                    "-- Re-run after simulate-changes: close out changed rows, then insert new current ones.\n"
                    "MERGE INTO dim_accounts tgt\n"
                    "USING (\n"
                    "  SELECT s.id FROM source_accounts_snapshot s\n"
                    "  JOIN dim_accounts da ON da.account_id = s.id AND da.is_current\n"
                    "  WHERE da.account_status != s.account_status OR da.credit_limit != s.credit_limit\n"
                    ") changed\n"
                    "ON tgt.account_id = changed.id AND tgt.is_current\n"
                    "WHEN MATCHED THEN UPDATE SET valid_to = current_timestamp(), is_current = false;\n\n"
                    "INSERT INTO dim_accounts\n"
                    "SELECT\n"
                    "  (SELECT COALESCE(MAX(account_key), 0) FROM dim_accounts) + ROW_NUMBER() OVER (ORDER BY s.id),\n"
                    "  s.id, s.card_network, s.account_status, s.credit_limit, current_timestamp(), NULL, true\n"
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
