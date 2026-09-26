"""Module 7's exercise description. Content, not logic - same pattern as
postgres_phase.task_content: a plain dict, checked by nosql_phase.report,
not by this module itself."""

NOSQL_PHASE_TASK = {
    "title": "Remodel account data as a denormalized document",
    "summary": (
        "The same fintech data from the relational phase - users, accounts, transactions, "
        "reward_events, repayments - lives in Postgres as five separate tables. Your job: "
        "design and populate ONE MongoDB collection, account_profiles, that answers 'what "
        "does this account look like right now' without a single join. What you choose to "
        "embed, aggregate, or leave out is the actual exercise."
    ),
    "source": (
        "Read-only access to the same five Postgres tables from the relational phase "
        "(users, accounts, transactions, reward_events, repayments) - query them with "
        "POST /nosql-phase/sessions/{id}/query-source (one SELECT per request, same "
        "single-statement/row-cap rules as the relational phase's SQL execution)."
    ),
    "design_questions_to_answer": [
        "What do you embed vs. reference? (the owner/account relationship is 1:1 and doesn't "
        "change independently - a strong embedding candidate. Compare that to reward_events, "
        "which is a large, growing, independently-queried history.)",
        "What do you cap? An embedded array that grows without bound is a well-known MongoDB "
        "anti-pattern (unbounded array growth) - recent_transactions must stay bounded.",
        "What do you aggregate instead of embedding raw? reward_summary and repayment_status "
        "are computed views over their source tables, not full copies of them.",
    ],
    "required_output": {
        "collection": "account_profiles",
        "note": (
            "One document per account, keyed by the account's own id. Any other collections "
            "you create along the way are entirely up to you - only this one collection's "
            "shape is fixed, since grading needs something concrete to check."
        ),
        "document_shape": {
            "_id": "string - accounts.id (the same id transactions/reward_events/repayments reference)",
            "owner": "embedded object {name, email} - from users (via accounts.user_id), NOT a reference",
            "balance_cents": "integer - accounts.current_balance in cents, not the source's decimal dollars",
            "credit_limit_cents": "integer - accounts.credit_limit in cents",
            "recent_transactions": (
                "embedded array, capped at 20, most-recent-first by transaction_timestamp - each "
                "item at minimum {event_id (retrieval_reference_number), amount_cents, merchant "
                "(merchant_name), occurred_at (transaction_timestamp)}"
            ),
            "reward_summary": (
                "embedded object {total_points, event_count} - aggregated over ALL of the account's "
                "reward_events, not a copy of the raw events themselves"
            ),
            "repayment_status": (
                "embedded object {outstanding_cents, next_due_date} - outstanding_cents is the sum of "
                "(amount_due - amount_paid) across the account's repayments; next_due_date is the "
                "earliest due_date among repayments not yet fully paid, or null if none are outstanding"
            ),
        },
    },
    "hint": (
        "Build account_profiles with POST /nosql-phase/sessions/{id}/execute - a raw Mongo "
        "command document (insert/update/aggregate/etc.), run as your session's own scoped "
        "user. Query the Postgres source and build your Mongo commands from the results; "
        "grade when you're done with POST /nosql-phase/sessions/{id}/grade."
    ),
}
