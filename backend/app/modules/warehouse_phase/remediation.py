"""Hand-authored remediation writeups, one per grading check in
report.py - why it broke, a concrete fix, and the tradeoffs where more
than one valid approach exists."""

REMEDIATION = {
    "ERR_MISSING_DIM_USER_ROW": {
        "why": (
            "A user from the source has no row in dim_users at all - the grain violation the "
            "fundamentals track warns about in the abstract. dim_users promises one row per user, "
            "and the moment the build query drives off anything other than the users table itself, "
            "that promise is only as complete as whatever filter the substitute table applies."
        ),
        "fix": "Drive dim_users from users itself, not from a table that filters some users out.",
        "fix_sql": (
            "CREATE TABLE dim_users USING DELTA AS\n"
            "SELECT ROW_NUMBER() OVER (ORDER BY external_user_id) AS user_key,\n"
            "  external_user_id, full_name, email, kyc_status, country, is_active\n"
            "FROM users;"
        ),
        "tradeoffs": "N/A - every user should always have a dimension row; there's no valid reason to exclude one.",
    },
    "ERR_DIM_USER_MISMATCH": {
        "why": (
            "A dim_users row exists for this user but one or more fields don't match users. "
            "dim_users is deliberately SCD Type 1 (overwrite in place, no history) rather than "
            "Type 2 like dim_accounts, which makes a mismatch here purely a copy/mapping bug, "
            "never a 'which version is current' question."
        ),
        "fix": "Copy full_name/email/kyc_status/country/is_active directly from users - not a stale or partially-mapped copy.",
        "fix_sql": (
            "CREATE OR REPLACE TABLE dim_users USING DELTA AS\n"
            "SELECT ROW_NUMBER() OVER (ORDER BY external_user_id) AS user_key,\n"
            "  external_user_id, full_name, email, kyc_status, country, is_active\n"
            "FROM users;"
        ),
        "tradeoffs": "N/A - a correctness bug, not a design choice.",
    },
    "ERR_MISSING_DIM_ACCOUNT_ROW": {
        "why": (
            "An account from source_accounts_snapshot has no row in dim_accounts at all, in "
            "either day-1 or day-2 state. Same grain-completeness failure as "
            "ERR_MISSING_DIM_USER_ROW on the SCD2 dimension instead of the SCD1 one - an account "
            "with zero transactions still needs a current dimension row before fact_transactions "
            "can resolve anything against it."
        ),
        "fix": "Drive dim_accounts from source_accounts_snapshot itself, not from a join that could drop accounts with no activity.",
        "fix_sql": (
            "CREATE TABLE dim_accounts USING DELTA AS\n"
            "SELECT ROW_NUMBER() OVER (ORDER BY id) AS account_key,\n"
            "  id AS account_id, card_network, account_status, credit_limit,\n"
            "  current_timestamp() AS valid_from, CAST(NULL AS TIMESTAMP) AS valid_to, true AS is_current\n"
            "FROM source_accounts_snapshot;"
        ),
        "tradeoffs": "N/A - every account should always have at least one dimension row.",
    },
    "ERR_DIM_ACCOUNT_CURRENT_ROW_COUNT": {
        "why": (
            "An account has a number of is_current = true rows other than exactly one - either "
            "zero (every version got closed out and nothing replaced it) or more than one (a new "
            "version was inserted without closing out the old one first). Both directions trace "
            "back to the same root cause: close-the-old-row and insert-the-new-row are two separate "
            "statements, not one atomic operation, so a bug or a race between concurrent ETL runs "
            "can leave the table in either broken state."
        ),
        "fix": "Close the existing current row before inserting the new one, in that order, driven by a comparison against the source - not both at once.",
        "fix_sql": (
            "MERGE INTO dim_accounts tgt\n"
            "USING (\n"
            "  SELECT s.id FROM source_accounts_snapshot s\n"
            "  JOIN dim_accounts da ON da.account_id = s.id AND da.is_current\n"
            "  WHERE da.account_status != s.account_status OR da.credit_limit != s.credit_limit\n"
            ") changed\n"
            "ON tgt.account_id = changed.id AND tgt.is_current\n"
            "WHEN MATCHED THEN UPDATE SET valid_to = current_timestamp(), is_current = false;"
        ),
        "tradeoffs": (
            "This is a strict invariant, not a design choice - a dimension row set with anything "
            "other than exactly one current version per business key isn't a working SCD2 "
            "implementation. Standard SQL can't enforce 'exactly one is_current row per account_id' "
            "with a table-level CHECK (it's a cross-row invariant), so this has to be enforced by "
            "disciplined ETL logic, or a partial unique index on (account_id) WHERE is_current to "
            "at least block the 'more than one' direction."
        ),
    },
    "ERR_SCD_HISTORY_NOT_PRESERVED": {
        "why": (
            "This account was mutated (account_status/credit_limit changed after simulate-changes) "
            "but dim_accounts still has only ONE row for it - the ETL overwrote the row in place "
            "instead of versioning it. The current values may even be correct, but the history - "
            "the entire point of SCD2 - is gone, and that loss is invisible in any check that only "
            "looks at current data."
        ),
        "fix": "Never UPDATE a tracked attribute on an existing dim_accounts row in place - detect the change, close the current row, and INSERT a new one.",
        "fix_sql": (
            "-- after the MERGE above closes the changed rows:\n"
            "INSERT INTO dim_accounts\n"
            "SELECT (SELECT COALESCE(MAX(account_key), 0) FROM dim_accounts) + ROW_NUMBER() OVER (ORDER BY s.id),\n"
            "  s.id, s.card_network, s.account_status, s.credit_limit, current_timestamp(), NULL, true\n"
            "FROM source_accounts_snapshot s\n"
            "JOIN dim_accounts da ON da.account_id = s.id AND NOT da.is_current\n"
            "WHERE NOT EXISTS (SELECT 1 FROM dim_accounts cur WHERE cur.account_id = s.id AND cur.is_current);"
        ),
        "tradeoffs": (
            "SCD Type 1 (overwrite in place, what dim_users does deliberately) is simpler and "
            "cheaper, and right when history genuinely isn't needed - wrong for dim_accounts "
            "specifically because credit-limit/status history is exactly what a risk/compliance "
            "team would need to reconstruct later."
        ),
    },
    "ERR_SCD_STALE_CURRENT_VALUES": {
        "why": (
            "This account was mutated, but its dim_accounts current row still shows the "
            "pre-mutation account_status/credit_limit - the day-2 ETL either wasn't re-run, or its "
            "change-detection didn't actually compare against the new source values. This is the "
            "mirror image of ERR_SCD_HISTORY_NOT_PRESERVED: that one versions too eagerly, this one "
            "doesn't version at all."
        ),
        "fix": "Re-run the ETL after simulate-changes, comparing source_accounts_snapshot's current value against dim_accounts' current row, not a cached copy.",
        "fix_sql": (
            "SELECT s.id FROM source_accounts_snapshot s\n"
            "JOIN dim_accounts da ON da.account_id = s.id AND da.is_current\n"
            "WHERE da.account_status != s.account_status OR da.credit_limit != s.credit_limit;"
        ),
        "tradeoffs": "N/A - a correctness bug, not a design choice.",
    },
    "ERR_SCD_UNNECESSARY_NEW_ROW": {
        "why": (
            "This account was NOT mutated, but dim_accounts has more than one row for it - the ETL "
            "inserted a new version unconditionally on every run instead of only when a tracked "
            "attribute actually changed. That bug passes any test that only checks 'is the current "
            "value right'; it takes a specific churn check to catch it."
        ),
        "fix": "Compare the incoming source row against the current dim_accounts row before deciding to version - only close-and-insert when account_status or credit_limit actually differ.",
        "fix_sql": (
            "-- the same comparison used by ERR_SCD_STALE_CURRENT_VALUES's fix_sql is the guard:\n"
            "-- an unmutated account never satisfies the WHERE clause, so neither the MERGE nor the\n"
            "-- INSERT touches it, and re-running the pipeline against it is a no-op."
        ),
        "tradeoffs": (
            "Re-running an SCD2 ETL should be idempotent when nothing changed - the same 'don't "
            "silently corrupt on a re-run' principle as the relational phase's duplicate-webhook "
            "handling. Unnecessary versioning isn't just wasted storage - every no-op version is a "
            "fake 'change' in the history, corrupting any later query asking how many times an "
            "account's status actually changed."
        ),
    },
    "ERR_MISSING_FACT_ROW": {
        "why": (
            "A transaction from transactions has no row in fact_transactions - the same "
            "grain-completeness failure as the missing-dim-row checks, now on the fact table. "
            "Building it with an INNER JOIN against dim_accounts/dim_users instead of driving the "
            "loop from transactions itself silently drops any transaction whose key doesn't "
            "resolve cleanly."
        ),
        "fix": "Drive fact_transactions from transactions itself, resolving dimension keys without dropping rows that fail to match.",
        "fix_sql": (
            "CREATE TABLE fact_transactions USING DELTA AS\n"
            "SELECT t.retrieval_reference_number AS transaction_key, da.account_key, du.user_key,\n"
            "  t.transaction_amount AS amount, t.merchant_name AS merchant, t.transaction_timestamp\n"
            "FROM transactions t\n"
            "JOIN dim_accounts da ON da.account_id = t.account_id AND da.is_current\n"
            "JOIN accounts a ON a.id = t.account_id\n"
            "JOIN users u ON u.id = a.user_id\n"
            "JOIN dim_users du ON du.external_user_id = u.external_user_id;"
        ),
        "tradeoffs": "N/A - every transaction should always have a fact row.",
    },
    "ERR_FACT_ROW_MISMATCH": {
        "why": (
            "fact_transactions' account_key/user_key/amount/merchant doesn't resolve correctly - "
            "most often a wrong join or amount left in source units. If this fires only for "
            "mutated accounts, fact_transactions was likely never rebuilt after simulate-changes - "
            "its account_key values still point at the OLD, now closed-out dim_accounts row."
        ),
        "fix": "Join fact_transactions to dim_accounts on account_id AND is_current = true, and rebuild it after any dim_accounts change.",
        "fix_sql": (
            "CREATE OR REPLACE TABLE fact_transactions USING DELTA AS\n"
            "SELECT t.retrieval_reference_number AS transaction_key, da.account_key, du.user_key,\n"
            "  t.transaction_amount AS amount, t.merchant_name AS merchant, t.transaction_timestamp\n"
            "FROM transactions t\n"
            "JOIN dim_accounts da ON da.account_id = t.account_id AND da.is_current\n"
            "JOIN accounts a ON a.id = t.account_id\n"
            "JOIN users u ON u.id = a.user_id\n"
            "JOIN dim_users du ON du.external_user_id = u.external_user_id;"
        ),
        "tradeoffs": (
            "Resolving to the CURRENT dimension row (this task's required approach) is simpler but "
            "not point-in-time accurate - a transaction from before an account's status changed "
            "still shows the account's current status. A production warehouse would resolve to the "
            "dimension row that was current AT THE TRANSACTION'S OWN TIMESTAMP instead; that's out "
            "of scope here and stated as such."
        ),
    },
}
