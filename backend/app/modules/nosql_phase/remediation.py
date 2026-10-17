"""Hand-authored remediation writeups, one per grading check in
report.py - why it broke, a concrete fix, and the tradeoffs between
valid approaches, never just detection."""

REMEDIATION = {
    "ERR_MISSING_ACCOUNT_PROFILE": {
        "why": (
            "This account exists in Postgres but has no document in account_profiles at all. A "
            "per-account denormalization pass is easy to leave incomplete if the query driving it "
            "filters accounts out (e.g. only accounts with at least one transaction) without "
            "meaning to - unlike a relational JOIN, a build-one-document-per-account pipeline's "
            "coverage depends entirely on which query seeds the loop."
        ),
        "fix": "Drive the build from accounts itself, left-joining in everything else, so an account with zero activity still gets a profile with empty/zero-valued embedded fields.",
        "fix_sql": (
            "db.account_profiles.updateOne(\n"
            "  { _id: accountId },\n"
            "  { $setOnInsert: { _id: accountId, recent_transactions: [],\n"
            "      reward_summary: { total_points: 0, event_count: 0 } } },\n"
            "  { upsert: true }\n"
            ")"
        ),
        "tradeoffs": (
            "A brand-new account with zero transactions/rewards/repayments should still get a "
            "profile with empty/zero-valued embedded fields, not be skipped - the same 'is a zero "
            "real, or missing' question as the relational phase's null-handling task. An empty "
            "array and a zero-valued summary both say 'we checked, there's genuinely nothing here "
            "yet', which is different information from the document not existing at all."
        ),
    },
    "ERR_OWNER_NOT_EMBEDDED": {
        "why": (
            "owner.name/owner.email don't match the account's real user row, or the field is "
            "missing/null entirely - this is the actual denormalization decision this exercise is "
            "testing, not a formatting detail. Getting this wrong usually means the build query "
            "joined on the wrong key (account.id instead of account.user_id), or pulled from a "
            "stale intermediate result."
        ),
        "fix": "Join accounts to users via user_id and embed full_name/email directly on the document.",
        "fix_sql": (
            "db.account_profiles.updateOne(\n"
            "  { _id: accountId },\n"
            "  { $set: { owner: { name: user.full_name, email: user.email } } }\n"
            ")"
        ),
        "tradeoffs": (
            "Embedding means a user's name change requires updating every account_profiles "
            "document that embeds it - acceptable here because a 1:1, rarely-changing relationship "
            "is exactly what embedding suits. The underlying principle: embed when data is read "
            "together far more often than either side changes independently, and reference (via "
            "$lookup) when the referenced entity is large, unbounded, or changes on its own schedule."
        ),
    },
    "ERR_BALANCE_MISMATCH": {
        "why": (
            "balance_cents or credit_limit_cents doesn't match accounts.current_balance/"
            "credit_limit converted to cents - most often a units bug (dollars left as decimal, or "
            "cents computed by truncating instead of rounding). A truncating bug shows up as off by "
            "at most 1 cent in a biased (always down) direction, distinguishing it from a larger, "
            "less predictable mapping bug."
        ),
        "fix": "Round, don't truncate, and store cents as integers, not floats.",
        "fix_sql": (
            "db.account_profiles.updateOne(\n"
            "  { _id: accountId },\n"
            "  [{ $set: { balance_cents: { $round: [{ $multiply: ['$$current_balance', 100] }, 0] } } }]\n"
            ")"
        ),
        "tradeoffs": (
            "Storing money as integer cents avoids floating-point rounding error entirely - the "
            "same reasoning real payment systems use, and the same 'don't let a naive type "
            "conversion corrupt an amount' lesson as the relational phase's schema-drift fault. "
            "Floats are unsafe for money because most decimal fractions have no exact binary "
            "representation, so even a simple repeated addition can drift off the true value."
        ),
    },
    "ERR_UNBOUNDED_ARRAY": {
        "why": (
            "recent_transactions has more than 20 items - a well-known MongoDB anti-pattern "
            "(unbounded array growth). Documents keep growing without limit, eventually "
            "threatening the real 16MB per-document size limit, and every read pays the cost of "
            "transferring the entire history even when only recent activity is needed."
        ),
        "fix": "Cap the array at build time rather than embedding the full history and trimming it after the fact.",
        "fix_sql": (
            "db.account_profiles.updateOne(\n"
            "  { _id: accountId },\n"
            "  [{ $set: { recent_transactions: { $slice: [\n"
            "      { $sortArray: { input: '$recent_transactions', sortBy: { occurred_at: -1 } } }, 20\n"
            "  ] } } }]\n"
            ")"
        ),
        "tradeoffs": (
            "A capped embedded array is fast to read but can't answer 'show me all of this "
            "account's transactions' - that has to go back to a separate, non-embedded collection. "
            "This is the same embed-vs-reference tradeoff as ERR_OWNER_NOT_EMBEDDED landing on the "
            "opposite answer: owner info is small and bounded (embed it), transaction history is "
            "unbounded (cap what you embed) - MongoDB's documented 'Outlier Pattern'."
        ),
    },
    "ERR_RECENT_TRANSACTIONS_MISMATCH": {
        "why": (
            "recent_transactions doesn't reflect the account's actual most recent transactions, or "
            "isn't ordered most-recent-first - most often caused by ordering on the wrong timestamp "
            "column (posted_timestamp instead of transaction_timestamp) or forgetting DESC. The two "
            "timestamp columns exist for a real reason (authorized vs. posted/settled), which is "
            "what makes picking the wrong one an easy, plausible-looking mistake."
        ),
        "fix": "Order by transaction_timestamp DESC, limit 20, and map amount_cents the same way as balance_cents.",
        "fix_sql": (
            "db.transactions.find(\n"
            "  { account_id: accountId },\n"
            "  { _id: 0, event_id: 1, amount_cents: 1, merchant: 1, transaction_timestamp: 1 }\n"
            ").sort({ transaction_timestamp: -1 }).limit(20)"
        ),
        "tradeoffs": "N/A - this is a correctness bug, not a design choice with a valid alternative.",
    },
    "ERR_REWARD_SUMMARY_MISMATCH": {
        "why": (
            "reward_summary.total_points or event_count doesn't match a real aggregation over the "
            "account's reward_events - most often summing the wrong column (cash_value instead of "
            "points_earned) or forgetting that redeemed events still count toward the total earned. "
            "A redemption doesn't erase the fact the points were earned; conflating 'earned' with "
            "'currently available to redeem' produces a plausible-looking but wrong number."
        ),
        "fix": "Sum points_earned and count events grouped by account_id over the full reward_events history, then merge the result onto the profile.",
        "fix_sql": (
            "db.reward_events.aggregate([\n"
            "  { $group: { _id: '$account_id',\n"
            "      total_points: { $sum: '$points_earned' }, event_count: { $sum: 1 } } },\n"
            "  { $merge: { into: 'account_profiles', on: '_id', whenMatched: [\n"
            "      { $set: { reward_summary: { total_points: '$$new.total_points',\n"
            "                                  event_count: '$$new.event_count' } } }\n"
            "  ], whenNotMatched: 'discard' } }\n"
            "])"
        ),
        "tradeoffs": (
            "Aggregating instead of embedding every event is the same unbounded-growth tradeoff as "
            "recent_transactions, resolved with a summary instead of a cap - the right choice when "
            "individual events are rarely needed alongside the profile. This is the Computed "
            "Pattern: store the pre-aggregated total rather than recomputing it on every read, at "
            "the cost of needing a defined process to keep it correct as new events arrive."
        ),
    },
    "ERR_REPAYMENT_STATUS_MISMATCH": {
        "why": (
            "outstanding_cents or next_due_date doesn't match a real computation over the account's "
            "repayments - most often summing amount_due alone (ignoring amount_paid) or picking the "
            "next due_date without filtering out already-fully-paid repayments. The sneakier failure: "
            "a schedule whose earliest due_date is already fully paid off still has that date in the "
            "raw data, so an unfiltered MIN(due_date) returns a real but wrong date."
        ),
        "fix": "Sum (amount_due - amount_paid) across all repayments for outstanding_cents; take the earliest due_date among only the not-yet-fully-paid rows for next_due_date.",
        "fix_sql": (
            "db.repayments.aggregate([\n"
            "  { $match: { account_id: accountId } },\n"
            "  { $group: { _id: '$account_id',\n"
            "      outstanding_cents: { $sum: { $multiply: [\n"
            "          { $subtract: ['$amount_due', '$amount_paid'] }, 100 ] } },\n"
            "      next_due_date: { $min: { $cond: [\n"
            "          { $lt: ['$amount_paid', '$amount_due'] }, '$due_date', null ] } } } }\n"
            "])"
        ),
        "tradeoffs": (
            "Whether a partially-paid repayment should still count toward 'next due' is a real "
            "product decision (it does here) - a stricter definition might only flag repayments "
            "with zero payment at all, under-reporting real outstanding risk. A looser definition "
            "(treating a small residual as 'effectively paid') would be defensible too, but that's a "
            "deliberate policy to make explicit, not something to default into silently."
        ),
    },
}
