"""The "SQL Databases" track - generic, DB-agnostic SQL fundamentals
(WHERE, JOIN, GROUP BY/ORDER BY, NULL handling). Not the real
51,495-row fintech feed or the real `public.transactions`/`public.accounts`
tables - those are Postgres-track/capstone-scale content. These are
small, hand-sized teaching copies of the same fintech domain, with only
the few columns each lesson actually needs, not the real ~20-column
ISO-8583-inspired schema from data_generation/schema.py. Every example
row and expected output below was captured by creating these exact
tables and running these exact queries against real Postgres, then
copying the real result rather than hand-typing it."""

SQL_DATABASES_SKILL_TREE = {
    "paradigm": "sql-databases",
    "nodes": [
        {
            "id": "intro",
            "type": "intro",
            "title": "SQL: one language, every relational database",
            "body": (
                "WHERE, JOIN, GROUP BY, and NULL handling work almost identically whether you're "
                "writing Postgres, MySQL, or SQL Server - these are the universal fundamentals, "
                "not Postgres-specific ones. This short track covers them on small, hand-sized "
                "data; the Postgres track right after goes deep on what's specific to Postgres "
                "itself (and does it at real, million-row scale)."
            ),
        },
        {
            "id": "node_1_where",
            "type": "skill",
            "title": "Filtering rows with WHERE",
            "teach": {
                "sql": (
                    "SELECT id, merchant_name, transaction_amount\n"
                    "FROM transactions\n"
                    "WHERE transaction_amount > 1000;"
                ),
                "note": (
                    "WHERE filters rows before they're returned - only rows where the condition "
                    "is true make it into the result. Comparison operators (>, <, =, !=) work on "
                    "numbers, text, and dates alike. Mechanically, Postgres evaluates the WHERE "
                    "condition once per candidate row, independently, before any SELECT-list "
                    "expression or ordering is computed - which is exactly why you can't reference "
                    "a column alias you defined in SELECT inside a WHERE clause (the alias doesn't "
                    "exist yet when WHERE runs)."
                ),
                "steps": [
                    {
                        "body": "Sometimes you don't want every row back - just the ones that "
                        "match something. That's what WHERE does."
                    },
                    {
                        "body": "The pattern is always the same:",
                        "sql": "SELECT column1, column2\nFROM table\nWHERE condition;",
                    },
                    {
                        "body": "On the transactions table below, this returns only the big purchases:",
                        "sql": (
                            "SELECT id, merchant_name, transaction_amount\n"
                            "FROM transactions\n"
                            "WHERE transaction_amount > 1000;"
                        ),
                    },
                    {
                        "body": "WHERE runs before grouping or sorting ever happens, and "
                        "comparison operators (>, <, =, !=) work the same way on numbers, text, "
                        "and dates."
                    },
                    {
                        "body": "You can stack more than one condition with AND / OR - AND "
                        "narrows the result (both sides must be true), OR widens it (either side "
                        "is enough). Mixing them without parentheses is a classic mistake: "
                        "`WHERE channel = 'online' OR channel = 'POS' AND transaction_amount > 1000` "
                        "doesn't mean what it looks like, because AND binds tighter than OR - it "
                        "actually reads as `channel = 'online' OR (channel = 'POS' AND "
                        "transaction_amount > 1000)`, silently including every online transaction "
                        "no matter the amount. Parenthesize explicitly whenever you mix them.",
                        "sql": "WHERE (channel = 'online' OR channel = 'POS')\n  AND transaction_amount > 1000",
                    },
                    {
                        "body": "A second common mistake: text comparisons are case- and "
                        "whitespace-sensitive by default. `WHERE merchant_name = 'best electronics'` "
                        "will NOT match a row stored as 'Best Electronics' - there's no implicit "
                        "case-folding in a plain `=`. If you need case-insensitive matching you'd "
                        "reach for `ILIKE` or `LOWER(merchant_name) = LOWER('...')` instead, each "
                        "with its own cost (ILIKE can't use a plain b-tree index as efficiently as "
                        "an exact `=` can)."
                    },
                    {
                        "body": "WHERE filters rows one at a time against a condition, before "
                        "anything else runs. Try it yourself in the Practice tab - same table, "
                        "same data."
                    },
                ],
            },
            "practice": {
                "prompt": "Find every transaction over $1000. Return id, merchant_name, and transaction_amount.",
                "table_name": "transactions",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "account_id", "type": "bigint"},
                    {"column": "transaction_amount", "type": "numeric"},
                    {"column": "merchant_name", "type": "text"},
                    {"column": "channel", "type": "text"},
                ],
                "example_rows": [
                    {"id": 1, "account_id": 101, "transaction_amount": 45.00, "merchant_name": "Corner Cafe", "channel": "POS"},
                    {"id": 2, "account_id": 101, "transaction_amount": 1250.00, "merchant_name": "Best Electronics", "channel": "online"},
                    {"id": 3, "account_id": 102, "transaction_amount": 2500.50, "merchant_name": "Travel Agency", "channel": "online"},
                ],
                "expected_output_rows": [
                    {"id": 2, "merchant_name": "Best Electronics", "transaction_amount": 1250.00},
                    {"id": 3, "merchant_name": "Travel Agency", "transaction_amount": 2500.50},
                ],
            },
        },
        {
            "id": "node_2_join",
            "type": "skill",
            "title": "Combining tables with JOIN",
            "teach": {
                "sql": (
                    "SELECT t.id AS transaction_id, a.card_network, t.transaction_amount\n"
                    "FROM transactions t\n"
                    "JOIN accounts a ON a.id = t.account_id;"
                ),
                "note": (
                    "A JOIN matches rows across two tables using a shared key (here, "
                    "accounts.id = transactions.account_id) - this is exactly how you'd pull "
                    "card_network onto a transactions row without duplicating it into every "
                    "single transaction. Under the hood this plain JOIN is an INNER JOIN - "
                    "Postgres's planner is free to execute it as a nested loop, a hash join, or "
                    "a merge join depending on table size and available indexes, but the logical "
                    "result (and the SQL you write) is the same regardless of which physical "
                    "strategy it picks."
                ),
                "steps": [
                    {
                        "body": "card_network lives on the accounts table, not on transactions - "
                        "so how do you put both on the same row without copying data everywhere?"
                    },
                    {
                        "body": "The pattern joins two tables on a shared key:",
                        "sql": "SELECT ...\nFROM table_a a\nJOIN table_b b ON b.key = a.key;",
                    },
                    {
                        "body": "Match each transaction to its own account's card network:",
                        "sql": (
                            "SELECT t.id AS transaction_id, a.card_network, t.transaction_amount\n"
                            "FROM transactions t\n"
                            "JOIN accounts a ON a.id = t.account_id;"
                        ),
                    },
                    {
                        "body": "A JOIN only keeps rows that find a match on both sides - if an "
                        "account_id didn't exist in accounts, that transaction would silently "
                        "disappear from the result. This is the single most common cause of "
                        "'my row count went down after I joined' bugs: the fix isn't to debug the "
                        "WHERE clause, it's to check whether you actually wanted an INNER JOIN at "
                        "all, or a LEFT JOIN that keeps every transactions row and fills "
                        "card_network with NULL when there's no matching account."
                    },
                    {
                        "body": "LEFT JOIN flips that behavior: every row from the left table "
                        "(transactions) survives, matched or not. This is the right tool whenever "
                        "the question is framed around the left table's own completeness - 'every "
                        "transaction, with its account info if we have it' rather than 'only "
                        "transactions that have a valid account'.",
                        "sql": (
                            "SELECT t.id AS transaction_id, a.card_network, t.transaction_amount\n"
                            "FROM transactions t\n"
                            "LEFT JOIN accounts a ON a.id = t.account_id;"
                        ),
                    },
                    {
                        "body": "A second gotcha: putting a filter on the right-hand table inside "
                        "the ON clause behaves differently from putting it in WHERE, once you're "
                        "using LEFT JOIN. `ON a.id = t.account_id AND a.card_network = 'Visa'` "
                        "still keeps every transactions row (non-Visa accounts just get NULL for "
                        "card_network); moving that same condition into a WHERE clause silently "
                        "turns the LEFT JOIN back into an INNER JOIN, because WHERE runs after the "
                        "join and throws away any row where card_network ended up NULL."
                    },
                    {
                        "body": "JOIN combines two tables by matching a shared key, row by row. "
                        "Try it yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": (
                    "Join accounts to transactions on account id. Return transaction_id, "
                    "card_network, and transaction_amount for every transaction."
                ),
                "tables": [
                    {
                        "name": "transactions",
                        "schema": [
                            {"column": "id", "type": "bigint"},
                            {"column": "account_id", "type": "bigint"},
                            {"column": "transaction_amount", "type": "numeric"},
                        ],
                        "rows": [
                            {"id": 1, "account_id": 101, "transaction_amount": 45.00},
                            {"id": 2, "account_id": 101, "transaction_amount": 1250.00},
                            {"id": 3, "account_id": 102, "transaction_amount": 2500.50},
                        ],
                    },
                    {
                        "name": "accounts",
                        "schema": [
                            {"column": "id", "type": "bigint"},
                            {"column": "card_network", "type": "text"},
                        ],
                        "rows": [
                            {"id": 101, "card_network": "Visa"},
                            {"id": 102, "card_network": "Mastercard"},
                        ],
                    },
                ],
                "expected_output_rows": [
                    {"transaction_id": 1, "card_network": "Visa", "transaction_amount": 45.00},
                    {"transaction_id": 2, "card_network": "Visa", "transaction_amount": 1250.00},
                    {"transaction_id": 3, "card_network": "Mastercard", "transaction_amount": 2500.50},
                ],
            },
        },
        {
            "id": "node_3_group_order",
            "type": "skill",
            "title": "Aggregating with GROUP BY and ORDER BY",
            "teach": {
                "sql": (
                    "SELECT account_id, SUM(transaction_amount) AS total_spent\n"
                    "FROM transactions\n"
                    "GROUP BY account_id\n"
                    "ORDER BY total_spent DESC;"
                ),
                "note": (
                    "GROUP BY collapses rows sharing the same account_id into one row per group, "
                    "letting an aggregate (SUM, COUNT, AVG) summarize each group. ORDER BY then "
                    "sorts the *groups themselves* by that summary - here, biggest spender first. "
                    "Conceptually, Postgres evaluates GROUP BY before SELECT: it forms the groups "
                    "first, then evaluates each SELECT expression once per group - which is why "
                    "every non-aggregated column in SELECT must also appear in GROUP BY, otherwise "
                    "the engine has no rule for which of that group's many values to show."
                ),
                "steps": [
                    {
                        "body": "What's the total spend per account? One row per transaction "
                        "won't answer that - you need to collapse rows together first."
                    },
                    {
                        "body": "The pattern groups rows, then summarizes each group:",
                        "sql": "SELECT column, AGG(column)\nFROM table\nGROUP BY column\nORDER BY ...;",
                    },
                    {
                        "body": "Total spend per account, highest spender first:",
                        "sql": (
                            "SELECT account_id, SUM(transaction_amount) AS total_spent\n"
                            "FROM transactions\n"
                            "GROUP BY account_id\n"
                            "ORDER BY total_spent DESC;"
                        ),
                    },
                    {
                        "body": "ORDER BY here sorts the *groups themselves* by their summary "
                        "value, not the original rows - and anything in SELECT that isn't "
                        "aggregated has to appear in GROUP BY too."
                    },
                    {
                        "body": "To filter on an aggregate itself - say, only accounts that spent "
                        "over $1000 in total - WHERE is the wrong tool, because WHERE runs before "
                        "grouping happens and has no concept of SUM yet. HAVING is the equivalent "
                        "clause that runs after grouping, filtering whole groups by their own "
                        "aggregate value.",
                        "sql": (
                            "SELECT account_id, SUM(transaction_amount) AS total_spent\n"
                            "FROM transactions\n"
                            "GROUP BY account_id\n"
                            "HAVING SUM(transaction_amount) > 1000\n"
                            "ORDER BY total_spent DESC;"
                        ),
                    },
                    {
                        "body": "A common mistake: forgetting that COUNT(*) counts rows, while "
                        "COUNT(some_column) only counts rows where that column is NOT NULL. If "
                        "merchant_name has gaps, COUNT(merchant_name) per account will quietly "
                        "under-count compared to COUNT(*) - two different, easily confused "
                        "numbers that answer two different questions."
                    },
                    {
                        "body": "GROUP BY collapses rows into one per group so an aggregate can "
                        "summarize each one. Try it yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Total spend per account, highest spender first.",
                "table_name": "transactions",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "account_id", "type": "bigint"},
                    {"column": "transaction_amount", "type": "numeric"},
                ],
                "example_rows": [
                    {"id": 1, "account_id": 101, "transaction_amount": 45.00},
                    {"id": 2, "account_id": 101, "transaction_amount": 1250.00},
                    {"id": 3, "account_id": 102, "transaction_amount": 2500.50},
                ],
                "expected_output_rows": [
                    {"account_id": 102, "total_spent": 2500.50},
                    {"account_id": 101, "total_spent": 1295.00},
                ],
            },
        },
        {
            "id": "node_4_nulls",
            "type": "skill",
            "title": "Handling NULLs with COALESCE",
            "teach": {
                "sql": (
                    "SELECT id, COALESCE(merchant_name, 'Unknown merchant') AS merchant_name, transaction_amount\n"
                    "FROM transactions;"
                ),
                "note": (
                    "A missing merchant_name isn't an empty string - it's NULL, SQL's \"no value "
                    "recorded\" marker. COALESCE(a, b) returns a unless it's NULL, in which case it "
                    "returns the fallback b - the standard way to substitute a readable default "
                    "instead of surfacing a raw NULL. NULL is also contagious in comparisons: "
                    "`merchant_name = NULL` is never true, not even when merchant_name actually is "
                    "NULL - equality with NULL always evaluates to NULL itself (SQL's third truth "
                    "value, alongside true/false), which WHERE treats as 'exclude this row'. The "
                    "only correct way to test for it is `IS NULL` / `IS NOT NULL`."
                ),
                "steps": [
                    {
                        "body": "A missing merchant_name isn't an empty string - it's NULL, "
                        "SQL's own \"no value recorded\" marker."
                    },
                    {
                        "body": "The pattern substitutes a fallback only when the real value is NULL:",
                        "sql": "COALESCE(column, 'fallback')",
                    },
                    {
                        "body": "Replace a missing merchant_name with a readable default:",
                        "sql": (
                            "SELECT id, COALESCE(merchant_name, 'Unknown merchant') AS merchant_name, "
                            "transaction_amount\nFROM transactions;"
                        ),
                    },
                    {
                        "body": "COALESCE checks its arguments left to right and returns the "
                        "first one that isn't NULL - chain more than two if you want several "
                        "fallbacks in a row, e.g. COALESCE(nickname, merchant_name, 'Unknown')."
                    },
                    {
                        "body": "The classic gotcha this sets up: `WHERE merchant_name = NULL` "
                        "silently matches nothing, ever - it looks like valid SQL and Postgres "
                        "won't warn you, it just quietly returns zero rows. `WHERE merchant_name "
                        "IS NULL` is the only correct way to ask that question, and `IS NOT NULL` "
                        "is the correct way to exclude NULLs - neither uses `=` at all."
                    },
                    {
                        "body": "Aggregates have their own NULL rule worth knowing: SUM, AVG, "
                        "MAX, and MIN all simply skip NULL values rather than treating them as "
                        "zero - SUM over a column that's entirely NULL returns NULL, not 0, which "
                        "can be a surprising default to feed into further arithmetic downstream."
                    },
                    {
                        "body": "COALESCE substitutes a default value only when the real one is "
                        "NULL. Try it yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Replace a missing merchant_name with 'Unknown merchant' instead of leaving it NULL.",
                "table_name": "transactions",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "account_id", "type": "bigint"},
                    {"column": "transaction_amount", "type": "numeric"},
                    {"column": "merchant_name", "type": "text"},
                    {"column": "channel", "type": "text"},
                ],
                "example_rows": [
                    {"id": 1, "account_id": 101, "transaction_amount": 45.00, "merchant_name": "Corner Cafe", "channel": "POS"},
                    {"id": 2, "account_id": 101, "transaction_amount": 1250.00, "merchant_name": None, "channel": "online"},
                ],
                "expected_output_rows": [
                    {"id": 1, "merchant_name": "Corner Cafe", "transaction_amount": 45.00},
                    {"id": 2, "merchant_name": "Unknown merchant", "transaction_amount": 1250.00},
                ],
            },
        },
        {
            "id": "node_5_distinct",
            "type": "skill",
            "title": "Removing duplicates with DISTINCT",
            "teach": {
                "sql": "SELECT DISTINCT channel FROM transactions;",
                "note": (
                    "DISTINCT collapses duplicate rows in the result down to one copy each - "
                    "here, every repeated 'POS' or 'online' value becomes a single row. It runs "
                    "on the whole SELECT list as a combination, not column by column: "
                    "`SELECT DISTINCT channel, merchant_name` keeps a row for every unique "
                    "(channel, merchant_name) PAIR, not a separately-deduplicated channel list "
                    "and merchant_name list. Mechanically, Postgres has to compare every row "
                    "against every other row (typically via a sort or a hash) to find the "
                    "duplicates, which makes DISTINCT meaningfully more expensive than a plain "
                    "SELECT - it's a real operation, not free punctuation."
                ),
                "steps": [
                    {
                        "body": "A channel column with thousands of transactions might really "
                        "only have a handful of distinct values ('POS', 'online', 'atm') - how do "
                        "you list just the unique ones?"
                    },
                    {
                        "body": "The pattern collapses duplicate rows down to one each:",
                        "sql": "SELECT DISTINCT column\nFROM table;",
                    },
                    {
                        "body": "List every distinct channel that appears:",
                        "sql": "SELECT DISTINCT channel FROM transactions;",
                    },
                    {
                        "body": "DISTINCT runs on the whole SELECT list as a combination, not "
                        "column by column - `SELECT DISTINCT channel, merchant_name` keeps a row "
                        "for every unique (channel, merchant_name) pair, not a separately-"
                        "deduplicated list of each."
                    },
                    {
                        "body": "A common mistake: reaching for DISTINCT to 'fix' a JOIN that's "
                        "fanning out duplicate rows (e.g. a one-to-many join producing several "
                        "copies of the same left-side row). DISTINCT will often make the "
                        "symptom disappear without fixing the actual cause, and can silently "
                        "discard rows that were legitimately different in a column you forgot to "
                        "include - GROUP BY or fixing the join's cardinality is almost always the "
                        "more honest tool for that job."
                    },
                    {
                        "body": "DISTINCT is also meaningfully more expensive than it looks - "
                        "Postgres has to compare every row against every other row (via a sort or "
                        "a hash) to find the duplicates, so it's a real operation, not free "
                        "punctuation added onto a SELECT."
                    },
                    {
                        "body": "DISTINCT collapses duplicate rows in the result down to one "
                        "copy each. Try it yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "List every distinct channel that appears in the transactions table.",
                "table_name": "transactions",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "account_id", "type": "bigint"},
                    {"column": "transaction_amount", "type": "numeric"},
                    {"column": "merchant_name", "type": "text"},
                    {"column": "channel", "type": "text"},
                ],
                "example_rows": [
                    {"id": 1, "account_id": 101, "transaction_amount": 45.00, "merchant_name": "Corner Cafe", "channel": "POS"},
                    {"id": 2, "account_id": 101, "transaction_amount": 1250.00, "merchant_name": "Best Electronics", "channel": "online"},
                    {"id": 3, "account_id": 102, "transaction_amount": 2500.50, "merchant_name": "Travel Agency", "channel": "online"},
                    {"id": 4, "account_id": 102, "transaction_amount": 60.00, "merchant_name": "Corner Cafe", "channel": "POS"},
                    {"id": 5, "account_id": 103, "transaction_amount": 20.00, "merchant_name": "ATM", "channel": "atm"},
                ],
                "expected_output_rows": [
                    {"channel": "POS"},
                    {"channel": "online"},
                    {"channel": "atm"},
                ],
            },
        },
        {
            "id": "node_6_having",
            "type": "skill",
            "title": "Filtering groups with HAVING",
            "teach": {
                "sql": (
                    "SELECT account_id, COUNT(*) AS txn_count\n"
                    "FROM transactions\n"
                    "GROUP BY account_id\n"
                    "HAVING COUNT(*) > 1;"
                ),
                "note": (
                    "HAVING filters whole GROUPS after GROUP BY has already collapsed rows - "
                    "the group-level counterpart to WHERE, which only ever sees individual rows "
                    "before any grouping happens. That ordering is the whole reason HAVING exists "
                    "as a separate clause at all: by the time GROUP BY has run, the individual "
                    "rows inside each group are gone, so there'd be nothing left for WHERE to "
                    "filter on if you tried to write `WHERE COUNT(*) > 1` instead - COUNT(*) isn't "
                    "even a legal thing for WHERE to reference, because WHERE runs before any "
                    "aggregate has been computed."
                ),
                "steps": [
                    {
                        "body": "Which accounts have made MORE than one transaction? That's a "
                        "question about the group's own size, not about any individual row."
                    },
                    {
                        "body": "HAVING filters groups by their own aggregate, after grouping:",
                        "sql": "SELECT column, AGG(column)\nFROM table\nGROUP BY column\nHAVING AGG(column) > value;",
                    },
                    {
                        "body": "Keep only accounts with more than one transaction:",
                        "sql": (
                            "SELECT account_id, COUNT(*) AS txn_count\n"
                            "FROM transactions\n"
                            "GROUP BY account_id\n"
                            "HAVING COUNT(*) > 1;"
                        ),
                    },
                    {
                        "body": "HAVING is the group-level counterpart to WHERE, which only "
                        "ever sees individual rows before any grouping happens - by the time "
                        "GROUP BY has run, there's nothing left for WHERE to filter on, which is "
                        "why `WHERE COUNT(*) > 1` isn't even legal SQL here."
                    },
                    {
                        "body": "WHERE and HAVING aren't interchangeable, and combining them is "
                        "common and useful: WHERE narrows which ROWS get grouped in the first "
                        "place (e.g. only this year's transactions), HAVING then narrows which "
                        "resulting GROUPS survive (e.g. only accounts spending over $1000) - each "
                        "one is doing a genuinely different job, at a different stage of "
                        "execution.",
                        "sql": (
                            "SELECT account_id, SUM(transaction_amount) AS total\n"
                            "FROM transactions\n"
                            "WHERE channel = 'online'\n"
                            "GROUP BY account_id\n"
                            "HAVING SUM(transaction_amount) > 1000;"
                        ),
                    },
                    {
                        "body": "A common mistake: using HAVING to filter on something that "
                        "doesn't actually need grouping at all (e.g. `HAVING account_id = 101`). "
                        "That condition could be checked per-row before any grouping happens, so "
                        "it belongs in WHERE - pushing a non-aggregate condition into HAVING just "
                        "means Postgres groups rows it was always going to throw away anyway."
                    },
                    {
                        "body": "HAVING filters whole groups by their own aggregate value, after "
                        "GROUP BY has already collapsed the rows. Try it yourself in the Practice "
                        "tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Find every account with more than one transaction. Return account_id and the transaction count.",
                "table_name": "transactions",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "account_id", "type": "bigint"},
                    {"column": "transaction_amount", "type": "numeric"},
                    {"column": "merchant_name", "type": "text"},
                    {"column": "channel", "type": "text"},
                ],
                "example_rows": [
                    {"id": 1, "account_id": 101, "transaction_amount": 45.00, "merchant_name": "Corner Cafe", "channel": "POS"},
                    {"id": 2, "account_id": 101, "transaction_amount": 1250.00, "merchant_name": "Best Electronics", "channel": "online"},
                    {"id": 3, "account_id": 102, "transaction_amount": 2500.50, "merchant_name": "Travel Agency", "channel": "online"},
                    {"id": 4, "account_id": 103, "transaction_amount": 60.00, "merchant_name": "Corner Cafe", "channel": "POS"},
                    {"id": 5, "account_id": 103, "transaction_amount": 20.00, "merchant_name": "ATM", "channel": "atm"},
                ],
                "expected_output_rows": [
                    {"account_id": 101, "txn_count": 2},
                    {"account_id": 103, "txn_count": 2},
                ],
            },
        },
        {
            "id": "node_7_subquery",
            "type": "skill",
            "title": "Subqueries: a query inside a query",
            "teach": {
                "sql": (
                    "SELECT id, card_network\n"
                    "FROM accounts\n"
                    "WHERE id IN (SELECT account_id FROM transactions WHERE transaction_amount > 1000);"
                ),
                "note": (
                    "A subquery is a complete SELECT nested inside another query's WHERE clause - "
                    "here, 'which accounts had a transaction over $1000' is answered first, and "
                    "the outer query only keeps accounts whose id shows up in that inner result. "
                    "Mechanically, Postgres is free to evaluate this either by running the inner "
                    "query once and reusing its result, or by rewriting it into an equivalent "
                    "JOIN internally - the IN-subquery form is simply the more readable way to "
                    "express 'does this id appear anywhere in that other set', without you having "
                    "to hand-write the join yourself."
                ),
                "steps": [
                    {
                        "body": "Which accounts have made at least one transaction over $1000? "
                        "You need an answer from one table (transactions) to filter another "
                        "(accounts)."
                    },
                    {
                        "body": "A subquery nests a complete SELECT inside WHERE:",
                        "sql": "SELECT ...\nFROM table_a\nWHERE key IN (SELECT key FROM table_b WHERE condition);",
                    },
                    {
                        "body": "Find accounts that have at least one transaction over $1000:",
                        "sql": (
                            "SELECT id, card_network\n"
                            "FROM accounts\n"
                            "WHERE id IN (SELECT account_id FROM transactions WHERE transaction_amount > 1000);"
                        ),
                    },
                    {
                        "body": "'Which accounts had a transaction over $1000' is answered "
                        "first, by the inner query - the outer query only keeps accounts whose id "
                        "shows up in that inner result."
                    },
                    {
                        "body": "This particular shape (filtering one table by presence in "
                        "another) could also be written as a JOIN with DISTINCT, but the subquery "
                        "version is usually clearer here, because you're not actually trying to "
                        "PULL any columns from transactions into the result - you only care "
                        "whether a matching row exists, not what it contains. Reach for a JOIN "
                        "instead whenever you need columns from both tables in the same output row."
                    },
                    {
                        "body": "A sharp gotcha: IN behaves very differently from NOT IN the "
                        "moment NULL enters the picture. If the subquery can return even one NULL "
                        "value, `WHERE id NOT IN (subquery)` silently returns ZERO rows for the "
                        "entire outer query - not an error, just an empty result - because SQL "
                        "can't prove id is unequal to an unknown value. `NOT EXISTS (SELECT 1 FROM "
                        "... WHERE ...)` sidesteps this trap entirely and is the safer default "
                        "whenever NULLs are possible in the inner query's result."
                    },
                    {
                        "body": "A subquery nests a complete SELECT inside another query's WHERE "
                        "clause. Try it yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": (
                    "Find every account that has at least one transaction over $1000. "
                    "Return id and card_network."
                ),
                "tables": [
                    {
                        "name": "transactions",
                        "schema": [
                            {"column": "id", "type": "bigint"},
                            {"column": "account_id", "type": "bigint"},
                            {"column": "transaction_amount", "type": "numeric"},
                            {"column": "merchant_name", "type": "text"},
                            {"column": "channel", "type": "text"},
                        ],
                        "rows": [
                            {"id": 1, "account_id": 101, "transaction_amount": 45.00, "merchant_name": "Corner Cafe", "channel": "POS"},
                            {"id": 2, "account_id": 101, "transaction_amount": 1250.00, "merchant_name": "Best Electronics", "channel": "online"},
                            {"id": 3, "account_id": 102, "transaction_amount": 60.00, "merchant_name": "Corner Cafe", "channel": "POS"},
                        ],
                    },
                    {
                        "name": "accounts",
                        "schema": [
                            {"column": "id", "type": "bigint"},
                            {"column": "card_network", "type": "text"},
                        ],
                        "rows": [
                            {"id": 101, "card_network": "Visa"},
                            {"id": 102, "card_network": "Mastercard"},
                            {"id": 103, "card_network": "Amex"},
                        ],
                    },
                ],
                "expected_output_rows": [
                    {"id": 101, "card_network": "Visa"},
                ],
            },
        },
        {
            "id": "node_8_case",
            "type": "skill",
            "title": "Branching logic with CASE",
            "teach": {
                "sql": (
                    "SELECT id, transaction_amount,\n"
                    "  CASE WHEN transaction_amount < 100 THEN 'small'\n"
                    "       WHEN transaction_amount < 1000 THEN 'medium'\n"
                    "       ELSE 'large' END AS amount_tier\n"
                    "FROM transactions;"
                ),
                "note": (
                    "CASE is SQL's if/elif/else, usable anywhere an expression is allowed - here, "
                    "inside a SELECT list to compute a brand new column. Postgres evaluates the "
                    "WHEN conditions top to bottom and stops at the first one that's true, which "
                    "is why order matters: a later, narrower condition that was placed above a "
                    "broader one would never be reached. If no WHEN matches and there's no ELSE, "
                    "the expression simply evaluates to NULL rather than raising an error - a "
                    "silent fallthrough worth knowing about."
                ),
                "steps": [
                    {
                        "body": "You want to label each transaction as 'small', 'medium', or "
                        "'large' based on its amount - that's branching logic, inside a SELECT."
                    },
                    {
                        "body": "CASE checks conditions top to bottom and returns the first match:",
                        "sql": "CASE WHEN condition1 THEN result1\n     WHEN condition2 THEN result2\n     ELSE default END",
                    },
                    {
                        "body": "Label each transaction by its amount tier:",
                        "sql": (
                            "SELECT id, transaction_amount,\n"
                            "  CASE WHEN transaction_amount < 100 THEN 'small'\n"
                            "       WHEN transaction_amount < 1000 THEN 'medium'\n"
                            "       ELSE 'large' END AS amount_tier\n"
                            "FROM transactions;"
                        ),
                    },
                    {
                        "body": "Postgres evaluates the WHEN conditions top to bottom and stops "
                        "at the first one that's true - order matters, since a narrower condition "
                        "placed below a broader one would never be reached."
                    },
                    {
                        "body": "If no WHEN matches and there's no ELSE, the whole expression "
                        "quietly evaluates to NULL rather than raising an error - always include "
                        "an ELSE unless you deliberately want 'no match' to mean NULL."
                    },
                    {
                        "body": "CASE can also be used inside an aggregate to count or sum "
                        "conditionally - a common pattern called 'conditional aggregation', e.g. "
                        "counting online transactions and POS transactions in the same row "
                        "instead of running two separate queries.",
                        "sql": (
                            "SELECT\n"
                            "  COUNT(CASE WHEN channel = 'online' THEN 1 END) AS online_count,\n"
                            "  COUNT(CASE WHEN channel = 'POS' THEN 1 END) AS pos_count\n"
                            "FROM transactions;"
                        ),
                    },
                    {
                        "body": "CASE is SQL's if/elif/else, usable anywhere an expression is "
                        "allowed. Try it yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": (
                    "Label each transaction's amount_tier: 'small' under $100, 'medium' under "
                    "$1000, otherwise 'large'. Return id, transaction_amount, and amount_tier."
                ),
                "table_name": "transactions",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "account_id", "type": "bigint"},
                    {"column": "transaction_amount", "type": "numeric"},
                    {"column": "merchant_name", "type": "text"},
                    {"column": "channel", "type": "text"},
                ],
                "example_rows": [
                    {"id": 1, "account_id": 101, "transaction_amount": 45.00, "merchant_name": "Corner Cafe", "channel": "POS"},
                    {"id": 2, "account_id": 101, "transaction_amount": 250.00, "merchant_name": "Best Electronics", "channel": "online"},
                    {"id": 3, "account_id": 102, "transaction_amount": 2500.50, "merchant_name": "Travel Agency", "channel": "online"},
                ],
                "expected_output_rows": [
                    {"id": 1, "transaction_amount": 45.00, "amount_tier": "small"},
                    {"id": 2, "transaction_amount": 250.00, "amount_tier": "medium"},
                    {"id": 3, "transaction_amount": 2500.50, "amount_tier": "large"},
                ],
            },
        },
        {
            "id": "node_9_string_functions",
            "type": "skill",
            "title": "Cleaning up text with string functions",
            "teach": {
                "sql": (
                    "SELECT id, UPPER(merchant_name) AS merchant_name_upper,\n"
                    "  merchant_name || ' (' || channel || ')' AS merchant_and_channel\n"
                    "FROM transactions;"
                ),
                "note": (
                    "UPPER/LOWER normalize case, and `||` concatenates strings together - "
                    "Postgres-standard SQL spells concatenation as `||`, not `+` the way some "
                    "other languages do (CONCAT(a, b, c) works too, and has one advantage over "
                    "`||`: CONCAT treats a NULL argument as an empty string, where `||` makes the "
                    "entire concatenated result NULL the instant any single piece is NULL - a "
                    "classic silent-data-loss trap if you concatenate a possibly-NULL column "
                    "without COALESCing it first)."
                ),
                "steps": [
                    {
                        "body": "Merchant names come in inconsistent casing, and you often want "
                        "to combine two text columns into one readable label - both are jobs for "
                        "string functions."
                    },
                    {
                        "body": "UPPER/LOWER normalize case; || concatenates:",
                        "sql": "SELECT UPPER(column), column_a || ' ' || column_b\nFROM table;",
                    },
                    {
                        "body": "Normalize merchant_name's case, and combine it with channel:",
                        "sql": (
                            "SELECT id, UPPER(merchant_name) AS merchant_name_upper,\n"
                            "  merchant_name || ' (' || channel || ')' AS merchant_and_channel\n"
                            "FROM transactions;"
                        ),
                    },
                    {
                        "body": "Postgres-standard SQL spells concatenation as `||`, not `+` the "
                        "way some other languages do - CONCAT(a, b, c) is the function-call "
                        "equivalent, for when you'd rather not chain several `||` operators "
                        "together."
                    },
                    {
                        "body": "The sharp difference between the two: `||` makes its ENTIRE "
                        "result NULL the instant any single piece being concatenated is NULL, "
                        "while CONCAT() quietly treats a NULL argument as an empty string instead. "
                        "A merchant_name || ' (' || channel || ')' expression silently returns "
                        "NULL for the whole row if channel happens to be NULL - COALESCE the "
                        "nullable column first if that's not what you want.",
                        "sql": "merchant_name || ' (' || COALESCE(channel, 'unknown') || ')'",
                    },
                    {
                        "body": "Other common string functions worth knowing: LENGTH (character "
                        "count), TRIM (strips leading/trailing whitespace), and SUBSTRING(column "
                        "FROM start FOR length) (extracts part of a string) - all of them, like "
                        "UPPER/LOWER, leave the original column untouched and just compute a new "
                        "value."
                    },
                    {
                        "body": "String functions transform text values inside a query without "
                        "changing the underlying data. Try it yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": (
                    "Return id, an upper-cased merchant_name_upper, and a merchant_and_channel "
                    "column combining merchant_name and channel like 'name (channel)'."
                ),
                "table_name": "transactions",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "account_id", "type": "bigint"},
                    {"column": "transaction_amount", "type": "numeric"},
                    {"column": "merchant_name", "type": "text"},
                    {"column": "channel", "type": "text"},
                ],
                "example_rows": [
                    {"id": 1, "account_id": 101, "transaction_amount": 45.00, "merchant_name": "corner cafe", "channel": "pos"},
                    {"id": 2, "account_id": 101, "transaction_amount": 250.00, "merchant_name": "Best Electronics", "channel": "online"},
                ],
                "expected_output_rows": [
                    {"id": 1, "merchant_name_upper": "CORNER CAFE", "merchant_and_channel": "corner cafe (pos)"},
                    {"id": 2, "merchant_name_upper": "BEST ELECTRONICS", "merchant_and_channel": "Best Electronics (online)"},
                ],
            },
        },
        {
            "id": "node_10_date_functions",
            "type": "skill",
            "title": "Pulling parts out of a date with EXTRACT",
            "teach": {
                "sql": "SELECT id, EXTRACT(month FROM transaction_time) AS txn_month FROM transactions;",
                "note": (
                    "EXTRACT(field FROM timestamp) pulls one component (year, month, day, hour, "
                    "dow for day-of-week, ...) out of a date/time value as a plain number - here, "
                    "the calendar month a transaction happened in, independent of its year. "
                    "DATE_TRUNC('month', timestamp) is the related, often more useful, sibling "
                    "function: instead of returning a bare number, it rounds the full timestamp "
                    "DOWN to the start of that unit (e.g. every March transaction becomes exactly "
                    "'2026-03-01 00:00:00'), which is what you actually want when grouping by "
                    "month - GROUP BY EXTRACT(month ...) alone would wrongly merge March 2025 and "
                    "March 2026 into a single bucket, since EXTRACT throws the year away entirely."
                ),
                "steps": [
                    {
                        "body": "Reporting often needs just the month or year a transaction "
                        "happened in, not the full timestamp - how do you pull one piece out of a "
                        "date?"
                    },
                    {
                        "body": "EXTRACT pulls one named component out as a number:",
                        "sql": "SELECT EXTRACT(field FROM timestamp_column)\nFROM table;",
                    },
                    {
                        "body": "Pull out the calendar month each transaction happened in:",
                        "sql": "SELECT id, EXTRACT(month FROM transaction_time) AS txn_month FROM transactions;",
                    },
                    {
                        "body": "EXTRACT supports several fields beyond month - year, day, hour, "
                        "and dow (day of week, 0=Sunday) are the ones you'll reach for most often, "
                        "each pulling out that one numeric component and discarding the rest."
                    },
                    {
                        "body": "The gotcha: EXTRACT(month ...) throws the year away entirely, "
                        "so `GROUP BY EXTRACT(month FROM transaction_time)` wrongly merges March "
                        "2025 and March 2026 transactions into one bucket. DATE_TRUNC('month', "
                        "transaction_time) is the fix - it rounds the full timestamp down to the "
                        "start of that month instead of reducing it to a bare number, so different "
                        "years stay in different buckets.",
                        "sql": (
                            "SELECT DATE_TRUNC('month', transaction_time) AS txn_month, "
                            "SUM(transaction_amount)\nFROM transactions\nGROUP BY 1;"
                        ),
                    },
                    {
                        "body": "Comparing dates directly also works the way you'd hope - "
                        "`transaction_time >= '2026-01-01' AND transaction_time < '2026-02-01'` is "
                        "a perfectly normal WHERE clause, and is usually cheaper than wrapping the "
                        "column in EXTRACT or DATE_TRUNC when all you need is a range filter, since "
                        "a direct comparison can still use an index on that column."
                    },
                    {
                        "body": "EXTRACT pulls one named component out of a date/time value as a "
                        "plain number. Try it yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Return id and the calendar month (txn_month) each transaction happened in.",
                "table_name": "transactions",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "account_id", "type": "bigint"},
                    {"column": "transaction_amount", "type": "numeric"},
                    {"column": "transaction_time", "type": "timestamptz"},
                ],
                "example_rows": [
                    {"id": 1, "account_id": 101, "transaction_amount": 45.00, "transaction_time": "2026-03-15T10:30:00+00"},
                    {"id": 2, "account_id": 101, "transaction_amount": 250.00, "transaction_time": "2026-07-04T22:00:00+00"},
                ],
                "expected_output_rows": [
                    {"id": 1, "txn_month": 3},
                    {"id": 2, "txn_month": 7},
                ],
            },
        },
        {
            "id": "review",
            "type": "review",
            "title": "Review: WHERE, JOIN, GROUP BY/ORDER BY/HAVING, NULLs, subqueries, CASE, text & dates",
            "prompt": (
                "A quick recap of this track's ten fundamentals before moving into the Postgres "
                "track, which goes deep on Postgres specifically - constraints, indexing, "
                "transactions, partitioning - starting from the real million-row feed."
            ),
        },
    ],
}
