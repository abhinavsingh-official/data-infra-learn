"""The "MongoDB Databases" track - document-model fundamentals
(filtering, $lookup, $group, "no NULL, just a missing field") on small
data, paired with the real account_profiles capstone in nosql_phase.

Practice blocks reuse sql_databases_track's exact dict keys
(table_name, example_rows, expected_output_rows, ...) even for
documents, so node_practice's plumbing and the frontend work unchanged
- only mongo_node_practice.py's check function and the submitted
text's meaning (a JSON command, not SQL) differ. No `schema` key here;
Mongo has no fixed-column DDL.

Every example document/expected output was captured against real
Mongo."""

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
                    "whole unless you also pass a projection to pick specific fields. Mechanically, "
                    "a bare equality filter like `{ status: \"active\" }` is actually shorthand for "
                    "`{ status: { $eq: \"active\" } }` - Mongo only requires the explicit `$op` key "
                    "syntax once you need something other than equality."
                ),
                "steps": [
                    {
                        "body": "A relational table forces every row into the same fixed "
                        "columns. A Mongo collection just holds documents - and you can query "
                        "them without a JOIN or a fixed schema."
                    },
                    {
                        "body": "A find command's filter is itself a document:",
                        "sql": '{ "find": "collection", "filter": { "field": { "$gt": value } } }',
                    },
                    {
                        "body": "Find every transaction over $1000 (amount_cents > 100000):",
                        "sql": '{ "find": "transactions", "filter": { "amount_cents": { "$gt": 100000 } } }',
                    },
                    {
                        "body": "Comparisons use operators like $gt/$lt/$eq as keys inside the "
                        "filter, where SQL would write a bare `amount_cents > 100000` - and every "
                        "matching document comes back whole unless you also pass a projection to "
                        "pick specific fields."
                    },
                    {
                        "body": "A projection controls exactly which fields come back - pass 1 "
                        "to include a field, 0 to exclude one, but (with one exception) you can't "
                        "mix inclusion and exclusion in the same projection document. The one "
                        "exception is _id: Mongo includes it by default even in an otherwise "
                        "inclusion-only projection, so `{ owner_name: 1, _id: 0 }` is the standard "
                        "way to explicitly drop it when you don't want it.",
                        "sql": '{ "find": "accounts", "filter": {}, "projection": { "owner_name": 1, "balance_cents": 1, "_id": 0 } }',
                    },
                    {
                        "body": "A common mistake coming from SQL: there's no NULL vs. missing "
                        "distinction to lean on inside a filter the way COALESCE works in SQL - "
                        "`{ status: { $ne: \"closed\" } }` will also match documents where status "
                        "doesn't exist on the document at all, which may or may not be what you "
                        "meant. If you need 'has this field AND it isn't closed', combine $ne with "
                        "an explicit $exists check."
                    },
                    {
                        "body": "find() matches documents against a filter document, the same "
                        "job WHERE does in SQL. Try it yourself in the Practice tab."
                    },
                ],
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
                    "afterward straightforward. $lookup is also, by default, always a left outer "
                    "join - every document from the base collection survives in the `as` array "
                    "(empty if nothing matched), the same default direction as SQL's LEFT JOIN, "
                    "not INNER JOIN."
                ),
                "steps": [
                    {
                        "body": "card_network lives on the accounts collection, not on "
                        "transactions - so how do you combine two independently-growing "
                        "collections at query time?"
                    },
                    {
                        "body": "The pattern joins two collections, then flattens the result:",
                        "sql": (
                            '{ "aggregate": "collection", "pipeline": [\n'
                            '  { "$lookup": { "from": "other", "localField": "key", '
                            '"foreignField": "_id", "as": "joined" } },\n'
                            '  { "$unwind": "$joined" }\n'
                            '], "cursor": {} }'
                        ),
                    },
                    {
                        "body": "Join accounts onto transactions by account_id:",
                        "sql": (
                            '{ "aggregate": "transactions", "pipeline": [\n'
                            '  { "$lookup": { "from": "accounts", "localField": "account_id", '
                            '"foreignField": "_id", "as": "account" } },\n'
                            '  { "$unwind": "$account" }\n'
                            '], "cursor": {} }'
                        ),
                    },
                    {
                        "body": "$lookup always produces a single-element array even for a 1:1 "
                        "match - $unwind flattens that array into a plain embedded object, which "
                        "is what makes projecting its fields afterward straightforward."
                    },
                    {
                        "body": "The gotcha: $lookup defaults to a LEFT outer join behavior - a "
                        "transaction whose account_id matches no account still survives the "
                        "$lookup stage, just with an empty `account` array. $unwind then silently "
                        "DROPS that document entirely (by default, $unwind removes any document "
                        "whose array field is empty), which quietly turns your left join back "
                        "into an inner join - the exact same 'row count went down' trap SQL's "
                        "WHERE-after-LEFT-JOIN has, just reached through a different stage."
                    },
                    {
                        "body": "If you need to keep unmatched documents through the unwind "
                        "step, pass `preserveNullAndEmptyArrays: true` as an option to $unwind - "
                        "the deliberate way to keep this a true left join all the way through "
                        "the pipeline.",
                        "sql": '{ "$unwind": { "path": "$account", "preserveNullAndEmptyArrays": true } }',
                    },
                    {
                        "body": "$lookup is Mongo's aggregation-pipeline equivalent of a SQL "
                        "JOIN. Try it yourself in the Practice tab."
                    },
                ],
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
                    "the raw collection on every read. Unlike SQL, the group key in Mongo isn't a "
                    "column name, it's an expression assigned to `_id` - which is why you can group "
                    "by a computed value (e.g. `{ \"$dateToString\": { \"format\": \"%Y-%m\", "
                    "\"date\": \"$event_time\" } }` to bucket by month) with no separate "
                    "computed-column step required first."
                ),
                "steps": [
                    {
                        "body": "What's the total spend per account? One document per "
                        "transaction won't answer that - you need to collapse documents "
                        "together first."
                    },
                    {
                        "body": "$group collapses, then $sort orders the groups:",
                        "sql": (
                            '{ "aggregate": "collection", "pipeline": [\n'
                            '  { "$group": { "_id": "$key", "total": { "$sum": "$amount" } } },\n'
                            '  { "$sort": { "total": -1 } }\n'
                            '], "cursor": {} }'
                        ),
                    },
                    {
                        "body": "Total spend per account, highest spender first:",
                        "sql": (
                            '{ "aggregate": "transactions", "pipeline": [\n'
                            '  { "$group": { "_id": "$account_id", "total_spent_cents": '
                            '{ "$sum": "$amount_cents" } } },\n'
                            '  { "$sort": { "total_spent_cents": -1 } }\n'
                            '], "cursor": {} }'
                        ),
                    },
                    {
                        "body": "A later $sort stage orders the *grouped* documents, not the "
                        "original ones - this is also the shape of MongoDB's own Computed "
                        "Pattern: store the aggregate instead of re-summing the raw collection "
                        "on every read."
                    },
                    {
                        "body": "A common mistake: putting $sort BEFORE $group when you actually "
                        "want to sort the aggregated totals, not the raw documents. "
                        "`[{ $sort: { amount_cents: -1 } }, { $group: ... }]` sorts individual "
                        "transactions by amount first, then groups them - the group's own output "
                        "order is undefined, because $group doesn't promise to preserve the input "
                        "order of the documents it collapsed. The $sort has to come AFTER $group "
                        "to sort the groups themselves."
                    },
                    {
                        "body": "Stage order matters everywhere in an aggregation pipeline, not "
                        "just here - each stage's output becomes the next stage's entire input, "
                        "so reordering stages can change both the result and the performance "
                        "(e.g. a $match placed early can shrink what later stages have to touch, "
                        "while the same $match placed late does no such favor)."
                    },
                    {
                        "body": "$group collapses documents sharing the same _id expression "
                        "into one per group, the same role GROUP BY plays in SQL. Try it "
                        "yourself in the Practice tab."
                    },
                ],
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
                    "null, the same role COALESCE plays for a relational NULL. This distinction - "
                    "'missing' vs. 'present but null' - is sharper in Mongo than in SQL, where "
                    "every column always exists for every row whether populated or not; a Mongo "
                    "document from an early version of your app might simply never have had the "
                    "field defined at all, which is a different failure mode than a later app "
                    "version writing `null` on purpose."
                ),
                "steps": [
                    {
                        "body": "Mongo's document model has no fixed schema, so a field doesn't "
                        "have to be NULL to be missing - it can simply not exist on that "
                        "document at all."
                    },
                    {
                        "body": "The pattern substitutes a fallback for a missing or null field:",
                        "sql": '{ "$ifNull": ["$field", "fallback"] }',
                    },
                    {
                        "body": "Substitute a readable default wherever nickname is missing:",
                        "sql": (
                            '{ "aggregate": "accounts", "pipeline": [\n'
                            '  { "$project": { "_id": 1, "nickname": '
                            '{ "$ifNull": ["$nickname", "Unnamed account"] } } }\n'
                            '], "cursor": {} }'
                        ),
                    },
                    {
                        "body": "$ifNull substitutes its fallback whenever a field is missing "
                        "OR explicitly null - the same role COALESCE plays for a relational NULL."
                    },
                    {
                        "body": "If you need to tell 'missing' and 'explicitly null' apart "
                        "instead of treating them the same, $ifNull is the wrong tool - reach for "
                        "`$type` (returns the string \"missing\" for an absent field) inside a "
                        "`$switch` or `$cond`, or query-side use `$exists` in a $match stage, "
                        "which is true/false on presence alone, independent of whether the value "
                        "is null.",
                        "sql": '{ "$match": { "nickname": { "$exists": false } } }',
                    },
                    {
                        "body": "$ifNull fills in a default for a field that's absent or null. "
                        "Try it yourself in the Practice tab."
                    },
                ],
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
            "id": "node_5_match_logic",
            "type": "skill",
            "title": "Combining conditions with $and/$or in $match",
            "teach": {
                "sql": (
                    '{ "aggregate": "transactions", "pipeline": [\n'
                    '  { "$match": { "$or": [\n'
                    '    { "channel": "online" },\n'
                    '    { "$and": [ { "channel": "pos" }, { "amount_cents": { "$gt": 1000 } } ] }\n'
                    '  ] } },\n'
                    '  { "$project": { "_id": 1, "amount_cents": 1 } }\n'
                    '], "cursor": {} }'
                ),
                "note": (
                    "A bare filter document with several keys already means AND ('status': "
                    "'active', 'channel': 'pos' matches only documents satisfying both) - $and is "
                    "only needed when you want to combine conditions that can't both be top-level "
                    "keys at once, like two conditions on the SAME field. $or (and $and spelled "
                    "out explicitly) take an ARRAY of condition documents, where a SQL WHERE "
                    "clause uses infix operators - so 'online, OR pos over $10' becomes an array "
                    "of two sub-filters, the second of which is itself an $and of two more."
                ),
                "steps": [
                    {
                        "body": "Find every online transaction, plus any POS transaction over "
                        "$10 - two different conditions, joined by OR, one of them itself an AND "
                        "of two conditions."
                    },
                    {
                        "body": "$or and $and both take an array of condition documents:",
                        "sql": '{ "$match": { "$or": [ { cond1 }, { "$and": [ { cond2 }, { cond3 } ] } ] } }',
                    },
                    {
                        "body": "Match online transactions, or POS transactions over $10:",
                        "sql": (
                            '{ "$match": { "$or": [\n'
                            '  { "channel": "online" },\n'
                            '  { "$and": [ { "channel": "pos" }, { "amount_cents": { "$gt": 1000 } } ] }\n'
                            '] } }'
                        ),
                    },
                    {
                        "body": "A bare filter document with several keys already means AND - "
                        "`{ status: 'active', channel: 'pos' }` matches only documents satisfying "
                        "both - so explicit $and is only needed for combining conditions that "
                        "can't both be top-level keys at once, like two conditions on the SAME "
                        "field."
                    },
                    {
                        "body": "That's exactly the case here: you can't write "
                        "`{ amount_cents: { $gt: 1000 }, amount_cents: { $lt: 5000 } }` as one "
                        "object (the second key would just overwrite the first in JSON) - you "
                        "need `$and: [ { amount_cents: { $gt: 1000 } }, { amount_cents: { $lt: 5000 } } ]` "
                        "to express two conditions on the same field at once.",
                        "sql": '{ "$and": [ { "amount_cents": { "$gt": 1000 } }, { "amount_cents": { "$lt": 5000 } } ] }',
                    },
                    {
                        "body": "A common mistake: forgetting that $or's array elements are "
                        "each a COMPLETE filter document on their own, not a bare value list - "
                        "`{ $or: [ \"online\", \"pos\" ] }` isn't valid, you still need "
                        "`{ $or: [ { channel: \"online\" }, { channel: \"pos\" } ] }` (or, for "
                        "that specific same-field case, the simpler $in: "
                        "`{ channel: { $in: [\"online\", \"pos\"] } }`)."
                    },
                    {
                        "body": "$and/$or combine conditions as an array of filter documents, "
                        "the same role parentheses and AND/OR play in a SQL WHERE clause. Try it "
                        "yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": (
                    "Find every online transaction, plus any POS transaction over $10 "
                    "(1000 cents). Return _id and amount_cents."
                ),
                "table_name": "transactions",
                "example_rows": [
                    {"_id": "t1", "account_id": "101", "amount_cents": 4500, "channel": "pos"},
                    {"_id": "t2", "account_id": "101", "amount_cents": 125000, "channel": "online"},
                    {"_id": "t3", "account_id": "102", "amount_cents": 250050, "channel": "online"},
                    {"_id": "t4", "account_id": "102", "amount_cents": 500, "channel": "pos"},
                ],
                "expected_output_rows": [
                    {"_id": "t1", "amount_cents": 4500},
                    {"_id": "t2", "amount_cents": 125000},
                    {"_id": "t3", "amount_cents": 250050},
                ],
                "starter_sql": (
                    '{\n  "aggregate": "transactions",\n  "pipeline": [\n'
                    '    { "$match": {} }\n'
                    '  ],\n  "cursor": {}\n}'
                ),
            },
        },
        {
            "id": "node_6_project_concat",
            "type": "skill",
            "title": "Computing new fields with $project and $concat",
            "teach": {
                "sql": (
                    '{ "aggregate": "accounts", "pipeline": [\n'
                    '  { "$project": { "_id": 1, "display": { "$concat": ["$owner_name", " - ", "$card_network"] } } }\n'
                    '], "cursor": {} }'
                ),
                "note": (
                    "$project isn't limited to including or excluding existing fields - any key "
                    "can be assigned the result of an expression instead, computed fresh per "
                    "document. $concat joins strings together, the aggregation-pipeline "
                    "equivalent of SQL's `||`. Unlike SQL's `||`, though, $concat is strict about "
                    "its inputs: every argument has to already be a string (or missing/null - see "
                    "the gotcha below), so concatenating a numeric field requires an explicit "
                    "$toString first rather than Mongo silently coercing it for you."
                ),
                "steps": [
                    {
                        "body": "A document doesn't have to go out exactly as it came in - "
                        "$project can compute a brand new field from existing ones, the way a "
                        "SQL SELECT list can."
                    },
                    {
                        "body": "Assign an expression to a field name instead of just 1/0:",
                        "sql": '{ "$project": { "field": { "$concat": ["$a", " - ", "$b"] } } }',
                    },
                    {
                        "body": "Combine owner_name and card_network into one display field:",
                        "sql": (
                            '{ "$project": { "_id": 1, "display": '
                            '{ "$concat": ["$owner_name", " - ", "$card_network"] } } }'
                        ),
                    },
                    {
                        "body": "$concat is the aggregation-pipeline equivalent of SQL's `||` - "
                        "it joins its arguments into one string, in order, left to right."
                    },
                    {
                        "body": "The gotcha: $concat is strict about types - every argument has "
                        "to already be a string, or the whole stage errors out. A numeric field "
                        "needs an explicit $toString wrapped around it first, and a field that's "
                        "missing or null makes the ENTIRE $concat result null (the same "
                        "contagious-null behavior SQL's `||` has) rather than treating it as an "
                        "empty string.",
                        "sql": '{ "$concat": ["$owner_name", " (", { "$toString": "$account_number" }, ")"] }',
                    },
                    {
                        "body": "$cond or $ifNull around the nullable piece is the fix, the same "
                        "way COALESCE fixes SQL's `||` NULL-contagion - substitute a safe fallback "
                        "before concatenating, not after."
                    },
                    {
                        "body": "$project can assign any computed expression to a field, not "
                        "just pass existing fields through. Try it yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Project _id and a display field combining owner_name and card_network as 'name - network'.",
                "table_name": "accounts",
                "example_rows": [
                    {"_id": "1", "owner_name": "Jordan", "card_network": "Visa"},
                    {"_id": "2", "owner_name": "Sam", "card_network": "Mastercard"},
                ],
                "expected_output_rows": [
                    {"_id": "1", "display": "Jordan - Visa"},
                    {"_id": "2", "display": "Sam - Mastercard"},
                ],
                "starter_sql": (
                    '{\n  "aggregate": "accounts",\n  "pipeline": [\n'
                    '    { "$project": { "_id": 1 } }\n'
                    '  ],\n  "cursor": {}\n}'
                ),
            },
        },
        {
            "id": "node_7_sort_limit",
            "type": "skill",
            "title": "Paginating results with $sort and $limit",
            "teach": {
                "sql": (
                    '{ "aggregate": "transactions", "pipeline": [\n'
                    '  { "$sort": { "amount_cents": -1 } },\n'
                    '  { "$limit": 2 },\n'
                    '  { "$project": { "_id": 1, "amount_cents": 1 } }\n'
                    '], "cursor": {} }'
                ),
                "note": (
                    "$sort orders the documents flowing through the pipeline; $limit then keeps "
                    "only the first N of whatever just came out of the previous stage - the same "
                    "job ORDER BY and LIMIT do together in SQL. Stage order matters here exactly "
                    "the same way it did for $group/$sort: $limit has to come AFTER $sort to keep "
                    "the biggest/smallest values, since a $limit placed before an unrelated $sort "
                    "would just keep an arbitrary, unordered 2 documents and throw the rest away "
                    "before sorting ever saw them."
                ),
                "steps": [
                    {
                        "body": "You only want the top 2 transactions by amount, not the whole "
                        "collection - that's sorting plus a cap on how many come back."
                    },
                    {
                        "body": "$sort orders the pipeline's documents; $limit caps how many pass through:",
                        "sql": '{ "aggregate": "collection", "pipeline": [\n  { "$sort": { "field": -1 } },\n  { "$limit": n }\n], "cursor": {} }',
                    },
                    {
                        "body": "Keep only the top 2 transactions by amount_cents:",
                        "sql": (
                            '{ "aggregate": "transactions", "pipeline": [\n'
                            '  { "$sort": { "amount_cents": -1 } },\n'
                            '  { "$limit": 2 }\n'
                            '], "cursor": {} }'
                        ),
                    },
                    {
                        "body": "$sort orders the documents flowing through the pipeline; "
                        "$limit then keeps only the first N of whatever just came out of the "
                        "previous stage - the same job ORDER BY + LIMIT do together in SQL."
                    },
                    {
                        "body": "Stage order matters exactly the way it did for $group/$sort: "
                        "$limit has to come AFTER $sort, or it keeps an arbitrary, unordered slice "
                        "of documents and throws the rest away before sorting ever ran on them."
                    },
                    {
                        "body": "For genuine pagination (page 2, page 3, ...) rather than just "
                        "'top N', $skip combines with $limit - $skip drops the first N documents "
                        "before $limit caps what's left. It's a correct but increasingly "
                        "expensive way to paginate deep into a large collection, though, since "
                        "Mongo still has to walk past every skipped document each time; a "
                        "range filter on a sorted field (e.g. '$match: { _id: { $gt: "
                        "last_seen_id } }') scales far better for deep pagination.",
                        "sql": '{ "aggregate": "transactions", "pipeline": [\n  { "$sort": { "amount_cents": -1 } },\n  { "$skip": 2 },\n  { "$limit": 2 }\n], "cursor": {} }',
                    },
                    {
                        "body": "$sort plus $limit together answer 'top N by some field', the "
                        "same job ORDER BY + LIMIT do in SQL. Try it yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Return the top 2 transactions by amount_cents, highest first. Return _id and amount_cents.",
                "table_name": "transactions",
                "example_rows": [
                    {"_id": "t1", "account_id": "101", "amount_cents": 4500},
                    {"_id": "t2", "account_id": "101", "amount_cents": 125000},
                    {"_id": "t3", "account_id": "102", "amount_cents": 250050},
                    {"_id": "t4", "account_id": "102", "amount_cents": 500},
                ],
                "expected_output_rows": [
                    {"_id": "t3", "amount_cents": 250050},
                    {"_id": "t2", "amount_cents": 125000},
                ],
                "starter_sql": (
                    '{\n  "aggregate": "transactions",\n  "pipeline": [\n'
                    '    { "$sort": { "amount_cents": -1 } }\n'
                    '  ],\n  "cursor": {}\n}'
                ),
            },
        },
        {
            "id": "node_8_count",
            "type": "skill",
            "title": "Counting documents with $group",
            "teach": {
                "sql": (
                    '{ "aggregate": "transactions", "pipeline": [\n'
                    '  { "$group": { "_id": null, "transaction_count": { "$sum": 1 } } },\n'
                    '  { "$project": { "_id": 0, "transaction_count": 1 } }\n'
                    '], "cursor": {} }'
                ),
                "note": (
                    "Grouping by `_id: null` puts every document into a single group - the "
                    "aggregation-pipeline equivalent of a bare SQL `SELECT COUNT(*) FROM table` "
                    "with no GROUP BY at all. `$sum: 1` is the idiom that counts documents rather "
                    "than summing a real field - each document contributes exactly 1 to the "
                    "running total, regardless of its own contents, which is a different pattern "
                    "from $sum: '$some_field' (node 3), which sums that field's actual values."
                ),
                "steps": [
                    {
                        "body": "How many transactions are there in total - not grouped by "
                        "account, just one grand total? That's a group with no real grouping key "
                        "at all."
                    },
                    {
                        "body": "Group everything into one bucket with _id: null:",
                        "sql": '{ "$group": { "_id": null, "n": { "$sum": 1 } } }',
                    },
                    {
                        "body": "Count every transaction in the collection:",
                        "sql": (
                            '{ "$group": { "_id": null, "transaction_count": { "$sum": 1 } } }'
                        ),
                    },
                    {
                        "body": "Grouping by `_id: null` puts every document into a single "
                        "group - the aggregation-pipeline equivalent of a bare "
                        "`SELECT COUNT(*) FROM table` with no GROUP BY at all."
                    },
                    {
                        "body": "`$sum: 1` is the idiom that counts documents rather than "
                        "summing a real field - each document contributes exactly 1, regardless "
                        "of its own contents. This is a different pattern from `$sum: "
                        "'$amount_cents'` (summing a real field's values), even though both use "
                        "the same $sum operator."
                    },
                    {
                        "body": "Mongo also has a dedicated $count stage that's shorthand for "
                        "exactly this pattern when all you want is a total - `{ $count: "
                        "'transaction_count' }` - though $group with `_id: null` is the more "
                        "general tool once you also want OTHER aggregates (a sum, an average) "
                        "computed over that same single group at the same time.",
                        "sql": '{ "aggregate": "transactions", "pipeline": [ { "$count": "transaction_count" } ], "cursor": {} }',
                    },
                    {
                        "body": "Grouping by `_id: null` collapses every document into one "
                        "group, the way an ungrouped SQL aggregate collapses every row. Try it "
                        "yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Count the total number of transactions in the collection.",
                "table_name": "transactions",
                "example_rows": [
                    {"_id": "t1", "account_id": "101", "amount_cents": 4500},
                    {"_id": "t2", "account_id": "101", "amount_cents": 125000},
                    {"_id": "t3", "account_id": "102", "amount_cents": 250050},
                ],
                "expected_output_rows": [
                    {"transaction_count": 3},
                ],
                "starter_sql": (
                    '{\n  "aggregate": "transactions",\n  "pipeline": [\n'
                    '    { "$group": { "_id": null } }\n'
                    '  ],\n  "cursor": {}\n}'
                ),
            },
        },
        {
            "id": "node_9_cond",
            "type": "skill",
            "title": "Conditional fields with $cond",
            "teach": {
                "sql": (
                    '{ "aggregate": "transactions", "pipeline": [\n'
                    '  { "$project": { "_id": 1, "amount_cents": 1, "tier": { "$cond": '
                    '{ "if": { "$gt": ["$amount_cents", 100000] }, "then": "large", "else": "small" } } } }\n'
                    '], "cursor": {} }'
                ),
                "note": (
                    "$cond is an if/then/else expression usable anywhere inside an aggregation "
                    "stage - the same role SQL's CASE plays inside a SELECT list. Its `if` takes "
                    "a boolean expression (built from comparison operators like $gt/$lt/$eq), and "
                    "exactly one of `then`/`else` is evaluated, never both - for more than two "
                    "branches, $switch (Mongo's multi-branch sibling, closer to CASE WHEN ... WHEN "
                    "... ELSE) is the better fit than nesting several $conds inside each other."
                ),
                "steps": [
                    {
                        "body": "You want to label each transaction as 'large' or 'small' based "
                        "on its amount - that's branching logic, inside a $project stage."
                    },
                    {
                        "body": "$cond takes a boolean condition plus a then/else pair:",
                        "sql": '{ "$cond": { "if": { "$gt": ["$field", value] }, "then": "a", "else": "b" } }',
                    },
                    {
                        "body": "Label each transaction's tier by its amount_cents:",
                        "sql": (
                            '{ "$project": { "_id": 1, "amount_cents": 1, "tier": { "$cond": '
                            '{ "if": { "$gt": ["$amount_cents", 100000] }, "then": "large", "else": "small" } } } }'
                        ),
                    },
                    {
                        "body": "$cond is an if/then/else expression usable anywhere inside an "
                        "aggregation stage - the same role SQL's CASE plays inside a SELECT list. "
                        "Exactly one of `then`/`else` is evaluated, never both."
                    },
                    {
                        "body": "$cond also has a shorter three-argument array form - "
                        "`{ $cond: [ condition, thenValue, elseValue ] }` - which behaves "
                        "identically to the if/then/else object form above; the object form is "
                        "usually preferred for readability once the condition itself gets at all "
                        "complex."
                    },
                    {
                        "body": "For more than two branches, nesting $cond inside its own `else` "
                        "works but gets hard to read fast - $switch (Mongo's closer sibling to "
                        "SQL's multi-branch CASE WHEN ... WHEN ... ELSE) is the better tool once "
                        "you need three or more tiers.",
                        "sql": (
                            '{ "$switch": { "branches": [\n'
                            '  { "case": { "$lt": ["$amount_cents", 10000] }, "then": "small" },\n'
                            '  { "case": { "$lt": ["$amount_cents", 100000] }, "then": "medium" }\n'
                            '], "default": "large" } }'
                        ),
                    },
                    {
                        "body": "$cond is an if/then/else expression, the same role CASE plays "
                        "inside a SQL SELECT list. Try it yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": (
                    "Project _id, amount_cents, and a tier field: 'large' if amount_cents is "
                    "over 100000, otherwise 'small'."
                ),
                "table_name": "transactions",
                "example_rows": [
                    {"_id": "t1", "amount_cents": 4500},
                    {"_id": "t2", "amount_cents": 125000},
                ],
                "expected_output_rows": [
                    {"_id": "t1", "amount_cents": 4500, "tier": "small"},
                    {"_id": "t2", "amount_cents": 125000, "tier": "large"},
                ],
                "starter_sql": (
                    '{\n  "aggregate": "transactions",\n  "pipeline": [\n'
                    '    { "$project": { "_id": 1, "amount_cents": 1 } }\n'
                    '  ],\n  "cursor": {}\n}'
                ),
            },
        },
        {
            "id": "node_10_unwind_array",
            "type": "skill",
            "title": "Flattening an array field with $unwind",
            "teach": {
                "sql": (
                    '{ "aggregate": "accounts", "pipeline": [\n'
                    '  { "$unwind": "$tags" },\n'
                    '  { "$project": { "_id": 1, "tag": "$tags" } }\n'
                    '], "cursor": {} }'
                ),
                "note": (
                    "$unwind isn't only for the single-element array $lookup produces (node 2) - "
                    "it works on any array field, producing one output document per array "
                    "element, with every other field copied unchanged onto each copy. A "
                    "two-element tags array on one account document becomes two separate output "
                    "documents here, both still carrying that same account's _id - this is the "
                    "document-model equivalent of what a JOIN against a multi-row child table "
                    "does in a normalized relational schema, except the 'child rows' were already "
                    "embedded in the parent document rather than living in a separate table."
                ),
                "steps": [
                    {
                        "body": "An account document can hold a tags array - ['vip', "
                        "'early_adopter'] - but sometimes you want one output row PER tag, not "
                        "one row per account."
                    },
                    {
                        "body": "$unwind turns one array field into one document per element:",
                        "sql": '{ "$unwind": "$array_field" }',
                    },
                    {
                        "body": "Flatten each account's tags array into one document per tag:",
                        "sql": (
                            '{ "aggregate": "accounts", "pipeline": [\n'
                            '  { "$unwind": "$tags" },\n'
                            '  { "$project": { "_id": 1, "tag": "$tags" } }\n'
                            '], "cursor": {} }'
                        ),
                    },
                    {
                        "body": "$unwind works on any array field, not only the single-element "
                        "array $lookup produces - it emits one output document per array "
                        "element, with every other field copied unchanged onto each copy."
                    },
                    {
                        "body": "A two-element tags array on one account becomes two separate "
                        "output documents here, both still carrying that SAME account's _id - "
                        "this is the document-model equivalent of what a JOIN against a "
                        "multi-row child table does in a normalized relational schema, except "
                        "the 'child rows' were already embedded in the parent rather than living "
                        "in a separate collection."
                    },
                    {
                        "body": "The same gotcha from node 2 applies here too: $unwind on an "
                        "empty array, or a missing field entirely, DROPS that document from the "
                        "output by default - pass `preserveNullAndEmptyArrays: true` if accounts "
                        "with no tags at all should still appear once, with a null tag.",
                        "sql": '{ "$unwind": { "path": "$tags", "preserveNullAndEmptyArrays": true } }',
                    },
                    {
                        "body": "$unwind turns one array field into one output document per "
                        "element, copying every other field unchanged onto each. Try it yourself "
                        "in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Flatten each account's tags array into one document per tag. Return _id and tag.",
                "table_name": "accounts",
                "example_rows": [
                    {"_id": "1", "owner_name": "Jordan", "tags": ["vip", "early_adopter"]},
                    {"_id": "2", "owner_name": "Sam", "tags": ["vip"]},
                ],
                "expected_output_rows": [
                    {"_id": "1", "tag": "vip"},
                    {"_id": "1", "tag": "early_adopter"},
                    {"_id": "2", "tag": "vip"},
                ],
                "starter_sql": (
                    '{\n  "aggregate": "accounts",\n  "pipeline": [\n'
                    '    { "$project": { "_id": 1, "tags": 1 } }\n'
                    '  ],\n  "cursor": {}\n}'
                ),
            },
        },
        {
            "id": "review",
            "type": "review",
            "title": "Review: find, $lookup, $group/$sort, $ifNull, $and/$or, $concat, pagination, $cond, $unwind",
            "prompt": (
                "A quick recap of this track's four fundamentals before the real NoSQL capstone, "
                "which asks you to design and populate a whole denormalized account_profiles "
                "collection from scratch at real 15,000-account scale - deciding what to embed, "
                "cap, and aggregate instead of just querying documents someone else modeled."
            ),
        },
    ],
}
