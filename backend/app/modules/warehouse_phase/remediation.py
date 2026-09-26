"""Module 8.4: hand-authored remediation writeups, one per grading check
in report.py. Same remediation-first requirement as every other phase -
why it broke, a concrete fix, and the tradeoffs where more than one valid
approach exists."""

REMEDIATION = {
    "ERR_MISSING_DIM_USER_ROW": {
        "why": "A user from the source has no row in dim_users at all.",
        "fix": "Drive dim_users from pg.users itself (SELECT * FROM pg.users), not from a table that filters some users out.",
        "tradeoffs": "N/A - every user should always have a dimension row; there's no valid reason to exclude one.",
    },
    "ERR_DIM_USER_MISMATCH": {
        "why": "A dim_users row exists for this user but one or more fields don't match pg.users.",
        "fix": "Copy full_name/email/kyc_status/country/is_active directly from pg.users - not a stale or partially-mapped copy.",
        "tradeoffs": "N/A - a correctness bug, not a design choice.",
    },
    "ERR_MISSING_DIM_ACCOUNT_ROW": {
        "why": (
            "An account from source_accounts_snapshot has no row in dim_accounts at all, in "
            "either day-1 or day-2 state."
        ),
        "fix": "Drive dim_accounts from source_accounts_snapshot itself, not from a join that could drop accounts with no activity.",
        "tradeoffs": "N/A - every account should always have at least one dimension row.",
    },
    "ERR_DIM_ACCOUNT_CURRENT_ROW_COUNT": {
        "why": (
            "An account has a number of is_current = true rows other than exactly one - either "
            "zero (every version got closed out and nothing replaced it) or more than one (a new "
            "version was inserted without closing out the old one first)."
        ),
        "fix": (
            "Before inserting a new version, close the existing current row first: "
            "UPDATE dim_accounts SET valid_to = now(), is_current = false WHERE account_id = ? "
            "AND is_current, THEN insert the new row - not the other way around, and not both at once."
        ),
        "tradeoffs": (
            "This is a strict invariant, not a design choice - a dimension row set with anything "
            "other than exactly one current version per business key isn't a working SCD2 "
            "implementation, whichever direction it's wrong in."
        ),
    },
    "ERR_SCD_HISTORY_NOT_PRESERVED": {
        "why": (
            "This account was mutated (its account_status/credit_limit changed after "
            "simulate-changes) but dim_accounts still has only ONE row for it - the ETL "
            "overwrote the existing row in place (UPDATE ... SET account_status = ...) instead "
            "of versioning it. The current values may even be correct, but the history - the "
            "entire point of SCD2 - is gone."
        ),
        "fix": (
            "Never UPDATE a tracked attribute on an existing dim_accounts row in place. Detect "
            "the change (compare the new source value to the current row's value), close the "
            "current row, and INSERT a new one with the new values."
        ),
        "tradeoffs": (
            "SCD Type 1 (overwrite in place, what dim_users does deliberately here) is simpler "
            "and cheaper, and is the right choice when history genuinely isn't needed - it's the "
            "wrong choice for dim_accounts specifically because account status/credit-limit "
            "history is exactly the kind of thing a real risk/compliance team would need to "
            "reconstruct later."
        ),
    },
    "ERR_SCD_STALE_CURRENT_VALUES": {
        "why": (
            "This account was mutated, but its dim_accounts current row still shows the "
            "pre-mutation account_status/credit_limit - the day-2 ETL either wasn't re-run, or "
            "its change-detection logic didn't actually compare against the new source values."
        ),
        "fix": "Re-run the ETL after simulate-changes, and compare source_accounts_snapshot's current value against dim_accounts' current row, not against a cached/stale copy.",
        "tradeoffs": "N/A - a correctness bug, not a design choice.",
    },
    "ERR_SCD_UNNECESSARY_NEW_ROW": {
        "why": (
            "This account was NOT mutated, but dim_accounts has more than one row for it - the "
            "ETL inserted a new version unconditionally on every run instead of only when a "
            "tracked attribute actually changed."
        ),
        "fix": (
            "Compare the incoming source row against the existing current dim_accounts row "
            "before deciding to version - only close-and-insert when account_status or "
            "credit_limit actually differ, otherwise leave the current row alone."
        ),
        "tradeoffs": (
            "Re-running an SCD2 ETL should be idempotent when nothing changed - the same "
            "'don't silently corrupt on a re-run' principle as Module 4's duplicate-webhook "
            "handling, just applied to dimension history instead of transaction rows."
        ),
    },
    "ERR_MISSING_FACT_ROW": {
        "why": "A transaction from pg.transactions has no row in fact_transactions.",
        "fix": "Drive fact_transactions from pg.transactions itself, not from a join that could drop rows (e.g. an inner join against a dimension missing a key).",
        "tradeoffs": "N/A - every transaction should always have a fact row.",
    },
    "ERR_FACT_ROW_MISMATCH": {
        "why": (
            "fact_transactions' account_key/user_key/amount/merchant doesn't resolve correctly - "
            "most often a wrong join (joining transactions to the wrong dim_accounts row, or "
            "amount left as source units instead of mapped consistently). If this fires only for "
            "mutated accounts specifically, the real cause is usually that fact_transactions was "
            "never rebuilt after simulate-changes - its account_key values still point at the "
            "OLD (now closed-out) dim_accounts row, since this task requires current-row "
            "resolution, not the row that was current when the transaction happened."
        ),
        "fix": "Join fact_transactions to dim_accounts on account_id + is_current = true, and to dim_users via the account's owner - not on a stale or ambiguous key. Rebuild fact_transactions after any dim_accounts change, for the same reason.",
        "tradeoffs": (
            "Resolving to the CURRENT dimension row (this task's required approach) is simpler "
            "but not point-in-time accurate - a transaction from before an account's status "
            "changed still shows the account's current status in a join, not its status at the "
            "time. A production warehouse would resolve to the dimension row that was current "
            "AT THE TRANSACTION'S OWN TIMESTAMP instead; that's out of scope here and stated as such."
        ),
    },
}
