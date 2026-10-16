"""Hand-authored remediation writeups, one per grading check in
report.py - why it broke, a concrete fix, and the tradeoffs between
valid approaches, never just detection."""

REMEDIATION = {
    "ERR_MISSING_ACCOUNT_PROFILE": {
        "why": (
            "This account exists in Postgres but has no document in account_profiles at all. "
            "A join-based ETL naturally covers every source row; a per-account denormalization "
            "pass is easy to leave incomplete if the query driving it filters accounts out "
            "(e.g. only accounts with at least one transaction) without meaning to. This is a "
            "structural risk specific to the document model: in a relational JOIN, an account "
            "with no transactions still exists as its own row regardless of what you join to it; "
            "in a build-one-document-per-account pipeline, the account's very existence depends "
            "entirely on which query seeds the loop that creates documents."
        ),
        "fix": (
            "Drive the build from accounts itself (SELECT id FROM accounts), left-joining in "
            "everything else - not from transactions or reward_events, which would silently "
            "exclude any account with no activity yet. The general rule: whichever entity the "
            "document is 'about' (here, one document per account) is the table that must drive "
            "the loop; everything else is an embedded/aggregated detail joined onto it, never "
            "the other way around."
        ),
        "tradeoffs": (
            "A brand-new account with zero transactions/rewards/repayments should still get a "
            "profile with empty/zero-valued embedded fields, not be skipped - the same 'is a "
            "zero real, or missing' question as the relational phase's null-handling task. An "
            "empty recent_transactions array and a reward_summary of {total_points: 0, "
            "event_count: 0} are both legitimate, meaningful states - they say 'we checked, "
            "there's genuinely nothing here yet', which is different information from the "
            "document not existing at all."
        ),
    },
    "ERR_OWNER_NOT_EMBEDDED": {
        "why": (
            "owner.name/owner.email don't match the account's real user row, or the field is "
            "missing/null entirely - this is the actual denormalization decision this exercise "
            "is testing, not a formatting detail. Getting this wrong usually means the build "
            "query joined on the wrong key (e.g. account.id instead of account.user_id), or "
            "pulled from a stale intermediate result computed before a user's profile was updated."
        ),
        "fix": "Join accounts to users via user_id and embed full_name/email directly on the document.",
        "tradeoffs": (
            "Embedding means a user's name change requires updating every account_profiles "
            "document that embeds it (real MongoDB write-amplification cost) - acceptable here "
            "because a 1:1, rarely-changing relationship is exactly what embedding suits; the "
            "same tradeoff would be wrong for a 1:many relationship that changes often. The "
            "underlying principle (from MongoDB's own documented schema-design guidance) is "
            "to embed when data is read together far more often than either side changes "
            "independently, and reference (via $lookup, like node 2 of the fundamentals track) "
            "when the referenced entity is large, grows unboundedly, or changes on its own "
            "schedule independent of the document embedding it."
        ),
    },
    "ERR_BALANCE_MISMATCH": {
        "why": (
            "balance_cents or credit_limit_cents doesn't match accounts.current_balance/"
            "credit_limit converted to cents - most often a units bug (dollars left as decimal, "
            "or cents computed by truncating instead of rounding). A truncating bug specifically "
            "shows up as being off by at most 1 cent, in a biased direction (always down, never "
            "up) - a telltale signature that distinguishes it from a more fundamental mapping bug, "
            "which tends to be off by a much larger, less predictable amount."
        ),
        "fix": "round(current_balance * 100) and round(credit_limit * 100), stored as integers, not floats.",
        "tradeoffs": (
            "Storing money as integer cents (not a decimal/float) avoids floating-point rounding "
            "error entirely - the same reasoning real payment systems (Stripe, etc.) use, and the "
            "same 'don't let a naive type conversion corrupt an amount' lesson as the relational "
            "phase's schema-drift type-change fault. The deeper reason floats are unsafe for money "
            "at all is that most decimal fractions (0.1, 0.2, ...) have no exact binary floating-"
            "point representation - an operation as simple as adding $0.10 ten times in IEEE 754 "
            "double precision does not reliably equal exactly $1.00, which is an unacceptable "
            "property for a balance field, however rare the discrepancy might seem."
        ),
    },
    "ERR_UNBOUNDED_ARRAY": {
        "why": (
            "recent_transactions has more than 20 items - a real, well-known MongoDB anti-pattern "
            "(unbounded array growth). Documents keep growing without limit, eventually threatening "
            "the real 16MB per-document size limit, and every read of the profile pays the cost of "
            "transferring the entire history even when only the recent activity is actually needed. "
            "There's a second, subtler cost beyond document size: on MongoDB's default storage "
            "engine, a document that keeps growing in place can force the storage layer to "
            "relocate it on disk once it outgrows its originally allocated space - an expensive "
            "operation that a bounded-size document never triggers."
        ),
        "fix": (
            "Cap the array at build time (ORDER BY transaction_timestamp DESC LIMIT 20 per account) "
            "rather than embedding the full history and trimming it after the fact."
        ),
        "tradeoffs": (
            "A capped embedded array is fast to read but can't answer 'show me all of this "
            "account's transactions' - that query has to go back to a separate, non-embedded "
            "transactions collection/table. Embedding is a bet on which query pattern is more "
            "common, not a universal win. This is the same embed-vs-reference tradeoff as "
            "ERR_OWNER_NOT_EMBEDDED, just landing on the opposite answer: owner info is small and "
            "bounded (embed it), transaction history is unbounded and grows forever (cap what you "
            "embed, or don't embed it at all and reference the source collection instead) - the "
            "'Outlier Pattern', MongoDB's own documented name for exactly this cap-and-reference "
            "approach to an otherwise-unbounded relationship."
        ),
    },
    "ERR_RECENT_TRANSACTIONS_MISMATCH": {
        "why": (
            "recent_transactions doesn't reflect the account's actual most recent transactions, or "
            "isn't ordered most-recent-first - most often caused by ordering on the wrong timestamp "
            "column (posted_timestamp instead of transaction_timestamp) or forgetting DESC. The two "
            "timestamp columns exist for a real reason (a transaction can be authorized at one "
            "moment and posted/settled at another), which is exactly what makes picking the wrong "
            "one an easy, plausible-looking mistake rather than an obvious typo."
        ),
        "fix": "ORDER BY transaction_timestamp DESC LIMIT 20, and map amount_cents the same way as balance_cents.",
        "tradeoffs": "N/A - this is a correctness bug, not a design choice with a valid alternative.",
    },
    "ERR_REWARD_SUMMARY_MISMATCH": {
        "why": (
            "reward_summary.total_points or event_count doesn't match a real aggregation over the "
            "account's reward_events - most often summing the wrong column (cash_value instead of "
            "points_earned) or forgetting that redeemed events still count toward the total earned. "
            "The 'total earned' framing matters here: a redemption doesn't erase the fact that the "
            "points were earned in the first place, it's a separate downstream event - conflating "
            "'earned' and 'currently available to redeem' produces a plausible-looking but wrong "
            "number."
        ),
        "fix": "SUM(points_earned) and COUNT(*) grouped by account_id over the full reward_events history.",
        "tradeoffs": (
            "Aggregating instead of embedding every event is the same unbounded-growth tradeoff as "
            "recent_transactions, just resolved with a summary instead of a cap - the right choice "
            "when the individual events themselves are rarely needed alongside the profile. This is "
            "the Computed Pattern in practice: store the pre-aggregated total rather than recomputing "
            "SUM/COUNT over potentially thousands of reward_events on every single profile read, at "
            "the cost of needing a defined process (a rebuild, or an incremental update on each new "
            "reward event) to keep that stored total correct as new events arrive."
        ),
    },
    "ERR_REPAYMENT_STATUS_MISMATCH": {
        "why": (
            "outstanding_cents or next_due_date doesn't match a real computation over the account's "
            "repayments - most often summing amount_due alone (ignoring amount_paid) or picking the "
            "next due_date without filtering out already-fully-paid repayments. The second failure "
            "mode is the sneakier one: a repayment schedule with its earliest due_date already fully "
            "paid off still has that early date in the raw data, so an unfiltered MIN(due_date) "
            "returns a real date - just the wrong one, pointing at an obligation that's already "
            "settled instead of the next one actually owed."
        ),
        "fix": (
            "outstanding_cents = SUM(amount_due - amount_paid) across all repayments; next_due_date = "
            "MIN(due_date) WHERE amount_paid < amount_due, or null if every repayment is fully paid."
        ),
        "tradeoffs": (
            "Whether a partially-paid repayment should still count toward 'next due' is a real "
            "product decision (it does here) - a stricter definition might only flag repayments "
            "with zero payment at all, which would under-report real outstanding risk. A looser "
            "definition in the other direction - treating any repayment within some rounding "
            "tolerance of amount_due as 'effectively paid' - would be defensible too if the business "
            "has a documented policy of writing off small residual balances, but that's a deliberate "
            "policy decision to make explicit, not something to default into silently."
        ),
    },
}
