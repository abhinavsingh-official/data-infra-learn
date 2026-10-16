"""NoSQL-phase exercise description. Content, not logic - same pattern
as postgres_phase.task_content: a plain dict, checked by
nosql_phase.report, not by this module itself."""

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
    "dataset_stats": [
        {"label": "Accounts to profile", "value": "15,000", "hint": "one account_profiles document each"},
        {"label": "Users", "value": "10,000", "hint": "embed as owner, don't reference"},
        {"label": "Transactions", "value": "1,000,000", "hint": "only the most recent 20 per account get embedded"},
        {"label": "Reward events / repayments", "value": "200,000 / 150,000", "hint": "aggregate into summaries, don't embed raw"},
    ],
    "starter_command": (
        "// Start by looking at what you're working with:\n"
        "db.getSiblingDB('admin')\n\n"
        "// Then build account_profiles with a raw Mongo command, e.g.:\n"
        "{\n"
        '  "insert": "account_profiles",\n'
        '  "documents": [\n'
        "    // one document per account, shaped per required_output.document_shape\n"
        "  ]\n"
        "}\n"
    ),
    "reference_solution": {
        "sql": (
            "// 1. Query the Postgres source (via query-source) to build each piece:\n"
            "SELECT a.id, u.full_name, u.email, a.current_balance, a.credit_limit\n"
            "FROM accounts a JOIN users u ON a.user_id = u.id;\n\n"
            "// 2. Then insert the assembled documents into Mongo (via execute):\n"
            "{\n"
            '  "insert": "account_profiles",\n'
            '  "documents": [\n'
            "    {\n"
            '      "_id": "1042",\n'
            '      "owner": { "name": "Jordan Diaz", "email": "jordan@example.com" },\n'
            '      "balance_cents": 128350,\n'
            '      "credit_limit_cents": 500000,\n'
            '      "recent_transactions": [\n'
            '        { "event_id": "RRN123", "amount_cents": 4599, "merchant": "Coffee Co", "occurred_at": "2024-03-01T12:00:00Z" }\n'
            "      ],\n"
            '      "reward_summary": { "total_points": 1240.5, "event_count": 37 },\n'
            '      "repayment_status": { "outstanding_cents": 32000, "next_due_date": "2024-04-01" }\n'
            "    }\n"
            "  ]\n"
            "}\n"
        ),
        "note": (
            "recent_transactions is capped at 20 and ordered most-recent-first, not a full copy of the "
            "account's transaction history - an unbounded embedded array is the anti-pattern this phase "
            "is testing for. reward_summary and repayment_status are aggregates computed over ALL of the "
            "account's events, not embedded raw event lists - build those with a GROUP BY against the "
            "Postgres source before you insert, not by embedding every row and summing client-side."
        ),
        "steps": [
            {
                "title": "1. Naive - one flat document, nothing embedded or aggregated",
                "sql": (
                    "// Query the source and insert a document with just the account's own scalars:\n"
                    "{\n"
                    '  "insert": "account_profiles",\n'
                    '  "documents": [\n'
                    "    {\n"
                    '      "_id": "1042",\n'
                    '      "balance_cents": 128350,\n'
                    '      "credit_limit_cents": 500000\n'
                    "    }\n"
                    "  ]\n"
                    "}\n"
                ),
                "note": (
                    "This document answers nothing on its own - 'what does this account look like' still "
                    "needs a join back to users for the owner, and another two joins for transactions and "
                    "rewards. That defeats the entire point of choosing a document store."
                ),
            },
            {
                "title": "2. + embed owner (1:1, doesn't change independently)",
                "sql": (
                    "{\n"
                    '  "insert": "account_profiles",\n'
                    '  "documents": [\n'
                    "    {\n"
                    '      "_id": "1042",\n'
                    '      "owner": { "name": "Jordan Diaz", "email": "jordan@example.com" },\n'
                    '      "balance_cents": 128350,\n'
                    '      "credit_limit_cents": 500000\n'
                    "    }\n"
                    "  ]\n"
                    "}\n"
                ),
                "note": (
                    "accounts:users is 1:1 and the owner relationship doesn't change independently of the "
                    "account, so embedding it is safe - no risk of the copy going stale behind the source's "
                    "back. That's the actual test in 'what do you embed vs. reference?'."
                ),
            },
            {
                "title": "3. + embed recent_transactions, capped at 20",
                "sql": (
                    "{\n"
                    '  "insert": "account_profiles",\n'
                    '  "documents": [\n'
                    "    {\n"
                    '      "_id": "1042",\n'
                    '      "owner": { "name": "Jordan Diaz", "email": "jordan@example.com" },\n'
                    '      "balance_cents": 128350,\n'
                    '      "credit_limit_cents": 500000,\n'
                    '      "recent_transactions": [\n'
                    '        { "event_id": "RRN123", "amount_cents": 4599, "merchant": "Coffee Co", "occurred_at": "2024-03-01T12:00:00Z" }\n'
                    "        // ... most-recent-first, stop at 20\n"
                    "      ]\n"
                    "    }\n"
                    "  ]\n"
                    "}\n"
                ),
                "note": (
                    "transactions is large and keeps growing - embedding the full history is the unbounded "
                    "array anti-pattern MongoDB itself warns about. Capping at 20, most-recent-first, is "
                    "what keeps the embed bounded instead of reaching for a full reference table."
                ),
            },
            {
                "title": "4. Final: + aggregate reward_summary and repayment_status instead of embedding raw",
                "sql": (
                    "// 1. Query the Postgres source (via query-source) to build each piece:\n"
                    "SELECT a.id, u.full_name, u.email, a.current_balance, a.credit_limit\n"
                    "FROM accounts a JOIN users u ON a.user_id = u.id;\n\n"
                    "// 2. Then insert the assembled documents into Mongo (via execute):\n"
                    "{\n"
                    '  "insert": "account_profiles",\n'
                    '  "documents": [\n'
                    "    {\n"
                    '      "_id": "1042",\n'
                    '      "owner": { "name": "Jordan Diaz", "email": "jordan@example.com" },\n'
                    '      "balance_cents": 128350,\n'
                    '      "credit_limit_cents": 500000,\n'
                    '      "recent_transactions": [\n'
                    '        { "event_id": "RRN123", "amount_cents": 4599, "merchant": "Coffee Co", "occurred_at": "2024-03-01T12:00:00Z" }\n'
                    "      ],\n"
                    '      "reward_summary": { "total_points": 1240.5, "event_count": 37 },\n'
                    '      "repayment_status": { "outstanding_cents": 32000, "next_due_date": "2024-04-01" }\n'
                    "    }\n"
                    "  ]\n"
                    "}\n"
                ),
                "note": (
                    "reward_events and repayments are independently-queried histories, same shape problem "
                    "as transactions - but here the fix isn't capping a copy, it's not copying at all: "
                    "reward_summary and repayment_status are GROUP BY aggregates computed over ALL of the "
                    "account's events before insert, not a raw list summed client-side."
                ),
            },
        ],
    },
}
