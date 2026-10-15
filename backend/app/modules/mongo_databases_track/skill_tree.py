"""Module 20: the "MongoDB Databases" track - the NoSQL-umbrella sibling
of sql_databases_track (Module 18), same deliberate scope: generic
document-model fundamentals (filtering, referencing via $lookup,
aggregation with $group, and Mongo's own "no NULL, just a missing field"
semantics) on small, hand-sized data, not the real 15,000-account
account_profiles capstone - that's nosql_phase's job.

Practice blocks here deliberately reuse the exact same dict keys as
postgres_phase/sql_databases_track's practice blocks (table_name,
example_rows, tables/rows, expected_output_rows, starter_sql) even
though these are documents, not rows - that's what lets node_practice's
"tables" plumbing and the entire existing frontend (types, modal, result
table) work completely unchanged. Only the backend check function
(mongo_node_practice.py) and the submitted text's meaning (a JSON Mongo
command, not SQL) differ; see that module's docstring. A `schema` key is
simply never present here - Mongo has no fixed-column DDL to declare,
and the frontend never reads that field for rendering anyway.

Every example document and expected output below was captured by
actually creating these exact collections and running these exact
commands against real Mongo, then copying the real reply - same
verify-by-running standard as every other phase/track."""

MONGO_DATABASES_SKILL_TREE = {
    "paradigm": "mongo-databases",
    "nodes": [
        {
            "id": "intro",
            "type": "intro",
            "title": "MongoDB: the document model",
            "body": (
                "A relational table forces every row into the same fixed columns. A Mongo "
                "collection just holds documents - JSON-like objects that can nest, and don't "
                "all have to share the same fields. This track covers the fundamentals every "
                "MongoDB course starts with: querying documents, modeling relationships "
                "(embedding vs. referencing), aggregating, and what 'no value' looks like when "
                "there's no NULL type to begin with - on the same small fintech dataset this "
                "whole platform uses."
            ),
        },
        {
            "id": "node_1_find",
            "type": "skill",
            "title": "Querying documents with find",
            "teach": {
                "sql": (
                    '{ "find": "transactions", "filter": { "amount_cents": { "$gt": 100000 } } }'
                ),
                "note": (
                    "A find command's filter is itself a document, not an infix expression - "
                    "comparisons use operators like $gt/$lt/$eq as keys inside the filter, where "
                    "SQL would write `amount_cents > 100000`. Every matching document comes back "
                    "whole unless you also pass a projection to pick specific fields."
                ),
            },
            "practice": {
                "prompt": (
                    "Find every account with status \"active\". Return _id, owner_name, and "
                    "balance_cents - use a projection to leave out status."
                ),
                "table_name": "accounts",
                "example_rows": [
                    {"_id": "1", "owner_name": "Jordan Diaz", "balance_cents": 128350, "status": "active"},
                    {"_id": "2", "owner_name": "Sam Lee", "balance_cents": 50000, "status": "closed"},
                    {"_id": "3", "owner_name": "Alex Kim", "balance_cents": 999999, "status": "active"},
                ],
                "expected_output_rows": [
                    {"_id": "1", "owner_name": "Jordan Diaz", "balance_cents": 128350},
                    {"_id": "3", "owner_name": "Alex Kim", "balance_cents": 999999},
                ],
                "starter_sql": (
                    '{\n  "find": "accounts",\n  "filter": {},\n  "projection": {}\n}'
                ),
            },
        },
        {
            "id": "node_2_lookup",
            "type": "skill",
            "title": "Referencing across collections with $lookup",
            "teach": {
                "sql": (
                    "{ \"aggregate\": \"transactions\", \"pipeline\": [\n"
                    '  { "$lookup": { "from": "accounts", "localField": "account_id", '
                    '"foreignField": "_id", "as": "account" } },\n'
                    '  { "$unwind": "$account" },\n'
                    '  { "$project": { "_id": 1, "amount_cents": 1, "status": "$account.status" } }\n'
                    '], "cursor": {} }'
                ),
                "note": (
                    "Not everything belongs embedded in one document - two independently-growing "
                    "collections (here, transactions referencing accounts by account_id) are "
                    "combined at query time with $lookup, Mongo's aggregation-pipeline equivalent "
                    "of a SQL JOIN. $unwind flattens the single-element array $lookup always "
                    "produces into a plain embedded object, which makes projecting its fields "
                    "afterward straightforward."
                ),
            },
            "practice": {
                "prompt": (
                    "Join accounts to transactions on account id. Return transaction_id, "
                    "card_network, and amount_cents for every transaction."
                ),
                "tables": [
                    {
                        "name": "transactions",
                        "rows": [
                            {"_id": "t1", "account_id": "101", "amount_cents": 4500},
                            {"_id": "t2", "account_id": "101", "amount_cents": 125000},
                            {"_id": "t3", "account_id": "102", "amount_cents": 250050},
                        ],
                    },
                    {
                        "name": "accounts",
                        "rows": [
                            {"_id": "101", "card_network": "Visa"},
                            {"_id": "102", "card_network": "Mastercard"},
                        ],
                    },
                ],
                "expected_output_rows": [
                    {"transaction_id": "t1", "card_network": "Visa", "amount_cents": 4500},
                    {"transaction_id": "t2", "card_network": "Visa", "amount_cents": 125000},
                    {"transaction_id": "t3", "card_network": "Mastercard", "amount_cents": 250050},
                ],
                "starter_sql": (
                    '{\n  "aggregate": "transactions",\n  "pipeline": [\n'
                    '    { "$lookup": { "from": "accounts", "localField": "account_id", '
                    '"foreignField": "_id", "as": "account" } }\n'
                    '  ],\n  "cursor": {}\n}'
                ),
            },
        },
        {
            "id": "node_3_group",
            "type": "skill",
            "title": "Aggregating with $group and $sort",
            "teach": {
                "sql": (
                    "{ \"aggregate\": \"transactions\", \"pipeline\": [\n"
                    '  { "$group": { "_id": "$account_id", "total_spent_cents": { "$sum": "$amount_cents" } } },\n'
                    '  { "$sort": { "total_spent_cents": -1 } }\n'
                    '], "cursor": {} }'
                ),
                "note": (
                    "$group collapses documents sharing the same _id expression into one output "
                    "document per group, same idea as SQL's GROUP BY - $sum here is the "
                    "aggregation operator, same role as SQL's SUM(). A later $sort stage then "
                    "orders those *grouped* documents, not the original ones - this is also the "
                    "shape of MongoDB's Computed Pattern: store the aggregate instead of re-summing "
                    "the raw collection on every read."
                ),
            },
            "practice": {
                "prompt": "Total spend per account, highest spender first.",
                "table_name": "transactions",
                "example_rows": [
                    {"_id": "t1", "account_id": "101", "amount_cents": 4500},
                    {"_id": "t2", "account_id": "101", "amount_cents": 125000},
                    {"_id": "t3", "account_id": "102", "amount_cents": 250050},
                ],
                "expected_output_rows": [
                    {"_id": "102", "total_spent_cents": 250050},
                    {"_id": "101", "total_spent_cents": 129500},
                ],
                "starter_sql": (
                    '{\n  "aggregate": "transactions",\n  "pipeline": [\n'
                    '    { "$group": { "_id": "$account_id" } }\n'
                    '  ],\n  "cursor": {}\n}'
                ),
            },
        },
        {
            "id": "node_4_missing_fields",
            "type": "skill",
            "title": "Handling missing fields with $ifNull",
            "teach": {
                "sql": (
                    "{ \"aggregate\": \"accounts\", \"pipeline\": [\n"
                    '  { "$project": { "_id": 1, "nickname": { "$ifNull": ["$nickname", "Unnamed account"] } } }\n'
                    '], "cursor": {} }'
                ),
                "note": (
                    "Mongo's document model has no fixed schema, so a field doesn't have to be "
                    "NULL to be missing - it can simply not exist on that document at all. "
                    "$ifNull substitutes a fallback whenever a field is missing OR explicitly "
                    "null, the same role COALESCE plays for a relational NULL."
                ),
            },
            "practice": {
                "prompt": (
                    "Project _id and nickname for every account, substituting 'Unnamed account' "
                    "wherever nickname is missing."
                ),
                "table_name": "accounts",
                "example_rows": [
                    {"_id": "1", "nickname": "Primary checking"},
                    {"_id": "2"},
                ],
                "expected_output_rows": [
                    {"_id": "1", "nickname": "Primary checking"},
                    {"_id": "2", "nickname": "Unnamed account"},
                ],
                "starter_sql": (
                    '{\n  "aggregate": "accounts",\n  "pipeline": [\n'
                    '    { "$project": { "_id": 1 } }\n'
                    '  ],\n  "cursor": {}\n}'
                ),
            },
        },
        {
            "id": "review",
            "type": "review",
            "title": "Review: find, $lookup, $group/$sort, $ifNull",
            "prompt": (
                "A quick recap of this track's four fundamentals before the real NoSQL capstone, "
                "which asks you to design and populate a whole denormalized account_profiles "
                "collection from scratch at real 15,000-account scale - deciding what to embed, "
                "cap, and aggregate instead of just querying documents someone else modeled."
            ),
        },
    ],
}
