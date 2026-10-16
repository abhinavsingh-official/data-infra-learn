"""Hand-authored remediation writeups, one per grading check in
report.py - why it broke, a concrete fix, and the tradeoffs between
valid approaches, never just detection."""

REMEDIATION = {
    "ERR_MISSING_ACCOUNT_PROFILE": {
        "why": (
            "This account exists in Postgres but has no document in account_profiles at all. "
            "A join-based ETL naturally covers every source row; a per-account denormalization "
            "pass is easy to leave incomplete if the query driving it filters accounts out "
            "(e.g. only accounts with at least one transaction) without meaning to."
        ),
        "fix": (
            "Drive the build from accounts itself (SELECT id FROM accounts), left-joining in "
            "everything else - not from transactions or reward_events, which would silently "
            "exclude any account with no activity yet."
        ),
        "tradeoffs": (
            "A brand-new account with zero transactions/rewards/repayments should still get a "
            "profile with empty/zero-valued embedded fields, not be skipped - the same 'is a "
            "zero real, or missing' question as the relational phase's null-handling task."
        ),
    },
    "ERR_OWNER_NOT_EMBEDDED": {
        "why": (
            "owner.name/owner.email don't match the account's real user row, or the field is "
            "missing/null entirely - this is the actual denormalization decision this exercise "
            "is testing, not a formatting detail."
        ),
        "fix": "Join accounts to users via user_id and embed full_name/email directly on the document.",
        "tradeoffs": (
            "Embedding means a user's name change requires updating every account_profiles "
            "document that embeds it (real MongoDB write-amplification cost) - acceptable here "
            "because a 1:1, rarely-changing relationship is exactly what embedding suits; the "
            "same tradeoff would be wrong for a 1:many relationship that changes often."
        ),
    },
    "ERR_BALANCE_MISMATCH": {
        "why": (
            "balance_cents or credit_limit_cents doesn't match accounts.current_balance/"
            "credit_limit converted to cents - most often a units bug (dollars left as decimal, "
            "or cents computed by truncating instead of rounding)."
        ),
        "fix": "round(current_balance * 100) and round(credit_limit * 100), stored as integers, not floats.",
        "tradeoffs": (
            "Storing money as integer cents (not a decimal/float) avoids floating-point rounding "
            "error entirely - the same reasoning real payment systems (Stripe, etc.) use, and the "
            "same 'don't let a naive type conversion corrupt an amount' lesson as the relational "
            "phase's schema-drift type-change fault."
        ),
    },
    "ERR_UNBOUNDED_ARRAY": {
        "why": (
            "recent_transactions has more than 20 items - a real, well-known MongoDB anti-pattern "
            "(unbounded array growth). Documents keep growing without limit, eventually threatening "
            "the real 16MB per-document size limit, and every read of the profile pays the cost of "
            "transferring the entire history even when only the recent activity is actually needed."
        ),
        "fix": (
            "Cap the array at build time (ORDER BY transaction_timestamp DESC LIMIT 20 per account) "
            "rather than embedding the full history and trimming it after the fact."
        ),
        "tradeoffs": (
            "A capped embedded array is fast to read but can't answer 'show me all of this "
            "account's transactions' - that query has to go back to a separate, non-embedded "
            "transactions collection/table. Embedding is a bet on which query pattern is more "
            "common, not a universal win."
        ),
    },
    "ERR_RECENT_TRANSACTIONS_MISMATCH": {
        "why": (
            "recent_transactions doesn't reflect the account's actual most recent transactions, or "
            "isn't ordered most-recent-first - most often caused by ordering on the wrong timestamp "
            "column (posted_timestamp instead of transaction_timestamp) or forgetting DESC."
        ),
        "fix": "ORDER BY transaction_timestamp DESC LIMIT 20, and map amount_cents the same way as balance_cents.",
        "tradeoffs": "N/A - this is a correctness bug, not a design choice with a valid alternative.",
    },
    "ERR_REWARD_SUMMARY_MISMATCH": {
        "why": (
            "reward_summary.total_points or event_count doesn't match a real aggregation over the "
            "account's reward_events - most often summing the wrong column (cash_value instead of "
            "points_earned) or forgetting that redeemed events still count toward the total earned."
        ),
        "fix": "SUM(points_earned) and COUNT(*) grouped by account_id over the full reward_events history.",
        "tradeoffs": (
            "Aggregating instead of embedding every event is the same unbounded-growth tradeoff as "
            "recent_transactions, just resolved with a summary instead of a cap - the right choice "
            "when the individual events themselves are rarely needed alongside the profile."
        ),
    },
    "ERR_REPAYMENT_STATUS_MISMATCH": {
        "why": (
            "outstanding_cents or next_due_date doesn't match a real computation over the account's "
            "repayments - most often summing amount_due alone (ignoring amount_paid) or picking the "
            "next due_date without filtering out already-fully-paid repayments."
        ),
        "fix": (
            "outstanding_cents = SUM(amount_due - amount_paid) across all repayments; next_due_date = "
            "MIN(due_date) WHERE amount_paid < amount_due, or null if every repayment is fully paid."
        ),
        "tradeoffs": (
            "Whether a partially-paid repayment should still count toward 'next due' is a real "
            "product decision (it does here) - a stricter definition might only flag repayments "
            "with zero payment at all, which would under-report real outstanding risk."
        ),
    },
}
