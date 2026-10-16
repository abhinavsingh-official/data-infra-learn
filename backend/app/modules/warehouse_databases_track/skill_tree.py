"""The "Warehouse Databases" track - generic dimensional-modeling
fundamentals (declaring the grain, star-schema JOINs, querying a
historized SCD2 dimension, fact aggregation), grounded in the Kimball
method's four-step design process. Same division of labor as
sql_databases_track vs. postgres_phase, and mongo_databases_track vs.
nosql_phase: these are small, hand-sized teaching tables run through
node_practice.py's plain-Postgres engine, not the real warehouse_phase
capstone's Spark/Delta star schema at real scale (see node_practice.py's
own docstring - the fundamentals-track engine isn't tied to whatever the
real capstone happens to run on). Every example row and expected output
below was captured by creating these exact tables and running these
exact queries against real Postgres, then copying the real result
rather than hand-typing it."""

WAREHOUSE_DATABASES_SKILL_TREE = {
    "paradigm": "warehouse-databases",
    "nodes": [
        {
            "id": "intro",
            "type": "intro",
            "title": "Kimball's four steps: process, grain, dimensions, facts",
            "body": (
                "Kimball's own design process has four steps: pick a business process, declare "
                "the grain (what one row in the fact table actually represents), identify the "
                "dimensions that describe it, identify the facts (numbers) to measure. This track "
                "walks through the SQL consequence of each step, on small, hand-sized data - the "
                "Warehouse capstone right after does the same four steps for real, against real "
                "Spark + Delta at full scale."
            ),
        },
        {
            "id": "node_1_grain",
            "type": "skill",
            "title": "Declaring the grain: one row per account, not per event",
            "teach": {
                "sql": (
                    "SELECT account_id, card_network\n"
                    "FROM raw_account_events\n"
                    "GROUP BY account_id, card_network;"
                ),
                "note": (
                    "Declaring the grain means deciding up front what one output row represents. "
                    "The raw feed has one row per *event* (opened, reissued); a dim_accounts table "
                    "needs one row per *account*. GROUP BY on the dimension's own key collapses "
                    "repeated events down to that grain - the first real decision in Kimball's "
                    "four-step process, before a single fact table exists. Kimball's own advice "
                    "is to always declare the grain at the lowest practical level of detail, even "
                    "if nobody's asked for that detail yet - it's far cheaper to aggregate up from "
                    "a fine grain later than to rebuild an entire fact table from scratch because "
                    "the original grain was too coarse to answer a new question."
                ),
                "steps": [
                    {
                        "body": "Before you build anything, Kimball's process asks one question "
                        "first: what does one row in your output actually represent?"
                    },
                    {
                        "body": "GROUP BY on the key you want collapses repeats down to it:",
                        "sql": "SELECT key_column\nFROM raw_events\nGROUP BY key_column;",
                    },
                    {
                        "body": "Collapse this raw event feed into one row per account:",
                        "sql": "SELECT account_id, card_network\nFROM raw_account_events\nGROUP BY account_id, card_network;",
                    },
                    {
                        "body": "The raw feed has one row per *event* (opened, reissued); "
                        "a dim_accounts table needs one row per *account* - that's the grain "
                        "decision, made before a single fact table exists."
                    },
                    {
                        "body": "Getting the grain wrong doesn't announce itself with an error - "
                        "it shows up much later as numbers that are subtly too big. If two rows "
                        "share an account_id with genuinely different card_network values (say, a "
                        "mid-stream reissue to a different network), GROUP BY on both columns "
                        "together produces TWO rows for that one account, not one - silently "
                        "breaking the 'one row per account' contract this table promised. A real "
                        "SCD2 dimension table (see node 3) exists specifically to handle this case "
                        "correctly instead of GROUP BY papering over it."
                    },
                    {
                        "body": "This is also why the grain has to be decided before dimensions "
                        "and facts are identified, not after - every later design choice (what "
                        "counts as 'the same' dimension row, what a fact row is allowed to "
                        "aggregate) depends on already knowing what one row of this table means."
                    },
                    {
                        "body": "Declaring the grain means deciding up front what one output row "
                        "represents. Try it yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Collapse this raw event feed into one row per account, with its card_network.",
                "table_name": "raw_account_events",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "account_id", "type": "bigint"},
                    {"column": "card_network", "type": "text"},
                    {"column": "event_type", "type": "text"},
                ],
                "example_rows": [
                    {"id": 1, "account_id": 101, "card_network": "Visa", "event_type": "opened"},
                    {"id": 2, "account_id": 101, "card_network": "Visa", "event_type": "card_reissued"},
                    {"id": 3, "account_id": 102, "card_network": "Mastercard", "event_type": "opened"},
                ],
                "expected_output_rows": [
                    {"account_id": 101, "card_network": "Visa"},
                    {"account_id": 102, "card_network": "Mastercard"},
                ],
            },
        },
        {
            "id": "node_2_star_join",
            "type": "skill",
            "title": "The star schema: one fact table, dimensions radiating out",
            "teach": {
                "sql": (
                    "SELECT f.id AS transaction_id, a.card_network, m.merchant_name, f.transaction_amount\n"
                    "FROM fact_transactions f\n"
                    "JOIN dim_accounts a ON a.id = f.account_id\n"
                    "JOIN dim_merchants m ON m.id = f.merchant_id;"
                ),
                "note": (
                    "A star schema's fact table holds foreign keys and numbers; every descriptive "
                    "attribute lives in a dimension table one JOIN away. This is the whole point of "
                    "the shape - fact_transactions never repeats 'Visa' or 'Corner Cafe' on every "
                    "row, it just points at the one dimension row that says so. This is also why "
                    "star-schema JOINs are cheap at scale compared to a fully normalized (3NF) "
                    "schema: every fact row is exactly one hop from any dimension, never a chain of "
                    "several - the denormalization happens inside each dimension table instead, "
                    "trading some redundancy there for a flat, predictable join path everywhere else."
                ),
                "steps": [
                    {
                        "body": "A star schema puts one fact table at the center, with "
                        "descriptive dimension tables radiating out - a shape, not just a name."
                    },
                    {
                        "body": "The fact table holds keys and numbers; dimensions hold the rest:",
                        "sql": "SELECT f.id, d1.name, d2.name, f.amount\nFROM fact f\nJOIN dim_a d1 ON d1.id = f.a_id\nJOIN dim_b d2 ON d2.id = f.b_id;",
                    },
                    {
                        "body": "Join the fact table to both dimension tables:",
                        "sql": (
                            "SELECT f.id AS transaction_id, a.card_network, m.merchant_name, f.transaction_amount\n"
                            "FROM fact_transactions f\n"
                            "JOIN dim_accounts a ON a.id = f.account_id\n"
                            "JOIN dim_merchants m ON m.id = f.merchant_id;"
                        ),
                    },
                    {
                        "body": "fact_transactions never repeats 'Visa' or 'Corner Cafe' on "
                        "every row - it just points at the one dimension row that says so. This "
                        "is the whole point of the shape."
                    },
                    {
                        "body": "Contrast this with a fully normalized OLTP design, where "
                        "card_network might live on a separate card_networks lookup table, joined "
                        "through accounts, joined through a cards table, joined through "
                        "transactions - three or four hops to get one descriptive attribute. A "
                        "dimensional model deliberately flattens that chain into one wide "
                        "dim_accounts row, because analytics queries read far more than they "
                        "write, and OLTP-style normalization optimizes for the opposite tradeoff "
                        "(minimizing update anomalies on a write-heavy workload)."
                    },
                    {
                        "body": "The common mistake here is using an INNER JOIN by default and "
                        "never questioning it - if a fact row's foreign key doesn't resolve to any "
                        "dimension row (a transaction referencing a deleted or not-yet-loaded "
                        "account), an INNER JOIN silently drops that fact row from every report "
                        "built on top of it. Real warehouse ETL handles this with a dedicated "
                        "'Unknown Member' dimension row (surrogate key -1 or similar) that every "
                        "orphaned fact resolves to instead, keeping the fact table's row count "
                        "intact and the gap visible rather than invisible."
                    },
                    {
                        "body": "A fact table holds foreign keys and numbers; dimensions hold "
                        "every descriptive attribute, one JOIN away. Try it yourself in the "
                        "Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": (
                    "Join the fact table to both dimension tables. Return transaction_id, "
                    "card_network, merchant_name, and transaction_amount."
                ),
                "tables": [
                    {
                        "name": "fact_transactions",
                        "schema": [
                            {"column": "id", "type": "bigint"},
                            {"column": "account_id", "type": "bigint"},
                            {"column": "merchant_id", "type": "bigint"},
                            {"column": "transaction_amount", "type": "numeric"},
                        ],
                        "rows": [
                            {"id": 1, "account_id": 101, "merchant_id": 201, "transaction_amount": 45.00},
                            {"id": 2, "account_id": 101, "merchant_id": 202, "transaction_amount": 1250.00},
                            {"id": 3, "account_id": 102, "merchant_id": 201, "transaction_amount": 2500.50},
                        ],
                    },
                    {
                        "name": "dim_accounts",
                        "schema": [
                            {"column": "id", "type": "bigint"},
                            {"column": "card_network", "type": "text"},
                        ],
                        "rows": [
                            {"id": 101, "card_network": "Visa"},
                            {"id": 102, "card_network": "Mastercard"},
                        ],
                    },
                    {
                        "name": "dim_merchants",
                        "schema": [
                            {"column": "id", "type": "bigint"},
                            {"column": "merchant_name", "type": "text"},
                        ],
                        "rows": [
                            {"id": 201, "merchant_name": "Corner Cafe"},
                            {"id": 202, "merchant_name": "Best Electronics"},
                        ],
                    },
                ],
                "expected_output_rows": [
                    {"transaction_id": 1, "card_network": "Visa", "merchant_name": "Corner Cafe", "transaction_amount": 45.00},
                    {"transaction_id": 2, "card_network": "Visa", "merchant_name": "Best Electronics", "transaction_amount": 1250.00},
                    {"transaction_id": 3, "card_network": "Mastercard", "merchant_name": "Corner Cafe", "transaction_amount": 2500.50},
                ],
            },
        },
        {
            "id": "node_3_scd2_current",
            "type": "skill",
            "title": "Querying a Slowly Changing Dimension: only the current row",
            "teach": {
                "sql": (
                    "SELECT account_id, card_network\n"
                    "FROM dim_accounts_scd2\n"
                    "WHERE is_current = true;"
                ),
                "note": (
                    "SCD Type 2 keeps every historical version of a dimension row instead of "
                    "overwriting it - each version gets its own valid_from/valid_to and an "
                    "is_current flag. A query that forgets the is_current filter double-counts an "
                    "account that's changed: here, account 101 has two rows (old network, new "
                    "network), and only one of them is current. The surrogate_key column (not "
                    "account_id) is the real primary key of this table - account_id deliberately "
                    "repeats across an account's historical versions, which is exactly what makes "
                    "history possible; any fact table that joins to this dimension must join on "
                    "the surrogate_key of the CORRECT version, not the natural account_id alone."
                ),
                "steps": [
                    {
                        "body": "When a customer's own attributes change, do you overwrite the "
                        "old value and lose history, or keep both versions? SCD Type 2 keeps both."
                    },
                    {
                        "body": "Every version gets a flag - filter to the current one:",
                        "sql": "SELECT key, value\nFROM dim_table\nWHERE is_current = true;",
                    },
                    {
                        "body": "Return each account's current card_network only:",
                        "sql": "SELECT account_id, card_network\nFROM dim_accounts_scd2\nWHERE is_current = true;",
                    },
                    {
                        "body": "A query that forgets the is_current filter double-counts an "
                        "account that's changed - here, account 101 has two rows (old network, "
                        "new network), and only one of them is current."
                    },
                    {
                        "body": "This is why the surrogate_key column exists at all, separate "
                        "from account_id: account_id is the natural/business key and deliberately "
                        "repeats across versions (that repetition IS the history), while "
                        "surrogate_key is a synthetic, always-unique identifier for one specific "
                        "VERSION of one account. A fact table joins to surrogate_key, not "
                        "account_id, precisely so each transaction's fact row can point at the "
                        "dimension version that was actually current when the transaction happened."
                    },
                    {
                        "body": "SCD Type 2 isn't the only option - SCD Type 1 just overwrites "
                        "the old value in place (simpler, no history, right choice when nobody "
                        "will ever need to know what the value used to be), and SCD Type 3 adds a "
                        "single 'previous value' column instead of full row history (cheap, but "
                        "only remembers one change back, not an unbounded history). Type 2's extra "
                        "complexity here buys the ability to answer 'what was true as of any past "
                        "date', which Types 1 and 3 can't."
                    },
                    {
                        "body": "SCD Type 2 keeps every historical version of a row instead of "
                        "overwriting it. Try it yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Return each account's current card_network only - not its historical versions.",
                "table_name": "dim_accounts_scd2",
                "schema": [
                    {"column": "surrogate_key", "type": "bigint"},
                    {"column": "account_id", "type": "bigint"},
                    {"column": "card_network", "type": "text"},
                    {"column": "valid_from", "type": "date"},
                    {"column": "valid_to", "type": "date"},
                    {"column": "is_current", "type": "boolean"},
                ],
                "example_rows": [
                    {"surrogate_key": 1, "account_id": 101, "card_network": "Visa Classic", "valid_from": "2025-01-01", "valid_to": "2026-03-01", "is_current": False},
                    {"surrogate_key": 2, "account_id": 101, "card_network": "Visa Signature", "valid_from": "2026-03-01", "valid_to": None, "is_current": True},
                    {"surrogate_key": 3, "account_id": 102, "card_network": "Mastercard", "valid_from": "2025-01-01", "valid_to": None, "is_current": True},
                ],
                "expected_output_rows": [
                    {"account_id": 101, "card_network": "Visa Signature"},
                    {"account_id": 102, "card_network": "Mastercard"},
                ],
            },
        },
        {
            "id": "node_4_fact_aggregate",
            "type": "skill",
            "title": "Analytics queries: the whole reason the star schema exists",
            "teach": {
                "sql": (
                    "SELECT a.card_network, SUM(f.transaction_amount) AS total_spent\n"
                    "FROM fact_transactions f\n"
                    "JOIN dim_accounts a ON a.id = f.account_id\n"
                    "GROUP BY a.card_network\n"
                    "ORDER BY total_spent DESC;"
                ),
                "note": (
                    "Total spend by card network is one JOIN and one GROUP BY against a star "
                    "schema - the same question against raw OLTP tables would need to untangle "
                    "accounts, cards, and transactions across several more joins. This is the "
                    "payoff for the grain decision back in node 1. It's also why fact tables are "
                    "built as additive measures whenever possible (SUM works safely across any "
                    "slice) rather than, say, a pre-computed ratio or average - an average stored "
                    "directly in a fact row can't be correctly re-aggregated across accounts "
                    "without the underlying count and sum, so warehouses store the raw additive "
                    "components and compute ratios/averages at query time instead."
                ),
                "steps": [
                    {
                        "body": "This is the actual payoff for everything so far: a star schema "
                        "turns a real business question into one JOIN and one GROUP BY."
                    },
                    {
                        "body": "Join to a dimension, then aggregate by its attribute:",
                        "sql": "SELECT d.attribute, SUM(f.amount)\nFROM fact f\nJOIN dim d ON d.id = f.dim_id\nGROUP BY d.attribute;",
                    },
                    {
                        "body": "Total transaction amount by card_network, highest spender first:",
                        "sql": (
                            "SELECT a.card_network, SUM(f.transaction_amount) AS total_spent\n"
                            "FROM fact_transactions f\n"
                            "JOIN dim_accounts a ON a.id = f.account_id\n"
                            "GROUP BY a.card_network\n"
                            "ORDER BY total_spent DESC;"
                        ),
                    },
                    {
                        "body": "The same question against raw OLTP tables would need to "
                        "untangle accounts, cards, and transactions across several more joins - "
                        "this is the payoff for the grain decision back in node 1."
                    },
                    {
                        "body": "Not every measure behaves this well under GROUP BY, though. "
                        "Kimball's own classification splits facts into additive (SUM works across "
                        "any dimension - transaction_amount here), semi-additive (SUM works across "
                        "some dimensions but not others - an account balance can be summed across "
                        "accounts but NOT across time, since yesterday's balance plus today's "
                        "balance isn't a meaningful number), and non-additive (a ratio or "
                        "percentage - never safe to SUM directly; recompute it from its additive "
                        "components after aggregating those)."
                    },
                    {
                        "body": "Analytics-shaped questions are one JOIN and one GROUP BY away "
                        "on a star schema. Try it yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Total transaction amount by card_network, highest spender first.",
                "tables": [
                    {
                        "name": "fact_transactions",
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
                        "name": "dim_accounts",
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
                    {"card_network": "Mastercard", "total_spent": 2500.50},
                    {"card_network": "Visa", "total_spent": 1295.00},
                ],
            },
        },
        {
            "id": "node_5_degenerate_dimension",
            "type": "skill",
            "title": "Degenerate dimensions: a key with no dimension table of its own",
            "teach": {
                "sql": "SELECT id, account_id, invoice_number FROM fact_transactions;",
                "note": (
                    "Not every identifier needs its own dimension table. invoice_number is a "
                    "real business key - useful for grouping or looking up a specific invoice's "
                    "line items - but it has no descriptive attributes of its own to warehouse in "
                    "a separate dim_invoices table, so Kimball's own advice is to leave it sitting "
                    "directly on the fact row instead: a 'degenerate dimension'. Forcing a "
                    "dim_invoices table to exist anyway, with nothing in it but an invoice_number "
                    "column and a surrogate key, would just add a JOIN that buys you nothing - "
                    "every column you'd ever want from it is already on the fact table itself."
                ),
                "steps": [
                    {
                        "body": "invoice_number identifies a specific invoice, the same way "
                        "account_id identifies a specific account - so why doesn't it get its "
                        "own dim_invoices table the way account_id gets dim_accounts?"
                    },
                    {
                        "body": "A degenerate dimension just lives directly on the fact row:",
                        "sql": "SELECT id, dimension_key_with_no_table, amount\nFROM fact_table;",
                    },
                    {
                        "body": "Return each transaction's invoice_number straight off the fact table:",
                        "sql": "SELECT id, account_id, invoice_number FROM fact_transactions;",
                    },
                    {
                        "body": "invoice_number is a real business key - useful for grouping or "
                        "looking up a specific invoice's line items - but it has no descriptive "
                        "attributes of its own worth warehousing separately, so it stays right on "
                        "the fact row instead of spawning a table with nothing in it."
                    },
                    {
                        "body": "The test for 'does this deserve its own dimension table' is "
                        "exactly that: does the key carry other DESCRIPTIVE attributes alongside "
                        "it (the way account_id carries card_network, open_date, owner_name)? "
                        "account_id earns dim_accounts because of everything attached to it; "
                        "invoice_number doesn't carry anything beyond itself, so a dim_invoices "
                        "table would just add a JOIN that buys you nothing."
                    },
                    {
                        "body": "Order numbers, check numbers, and ticket numbers are the other "
                        "classic degenerate-dimension examples across different domains - in "
                        "every case the pattern is the same: a real, queryable business "
                        "identifier that simply has nowhere descriptive left to point to."
                    },
                    {
                        "body": "A degenerate dimension is a business key with no attributes of "
                        "its own to warehouse separately, so it stays on the fact table. Try it "
                        "yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Return id, account_id, and invoice_number straight off the fact table - no JOIN needed.",
                "table_name": "fact_transactions",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "account_id", "type": "bigint"},
                    {"column": "invoice_number", "type": "text"},
                    {"column": "transaction_amount", "type": "numeric"},
                ],
                "example_rows": [
                    {"id": 1, "account_id": 101, "invoice_number": "INV-1001", "transaction_amount": 45.00},
                    {"id": 2, "account_id": 101, "invoice_number": "INV-1002", "transaction_amount": 1250.00},
                    {"id": 3, "account_id": 102, "invoice_number": "INV-2001", "transaction_amount": 60.00},
                ],
                "expected_output_rows": [
                    {"id": 1, "account_id": 101, "invoice_number": "INV-1001"},
                    {"id": 2, "account_id": 101, "invoice_number": "INV-1002"},
                    {"id": 3, "account_id": 102, "invoice_number": "INV-2001"},
                ],
            },
        },
        {
            "id": "node_6_role_playing_dimension",
            "type": "skill",
            "title": "Role-playing dimensions: one dimension table, joined twice",
            "teach": {
                "sql": (
                    "SELECT f.id AS order_id, od.calendar_date::text AS order_date,\n"
                    "  sd.calendar_date::text AS ship_date, f.order_amount\n"
                    "FROM fact_orders f\n"
                    "JOIN dim_dates od ON od.id = f.order_date_id\n"
                    "JOIN dim_dates sd ON sd.id = f.ship_date_id;"
                ),
                "note": (
                    "A single dim_dates table can play more than one role against the same fact "
                    "table - order_date and ship_date are both 'just a date', so they share one "
                    "dimension table rather than needing dim_order_dates and dim_ship_dates built "
                    "separately. Each JOIN gets its own alias (od, sd) and its own foreign key "
                    "(order_date_id, ship_date_id), which is what lets the SAME underlying "
                    "dim_dates row be reached twice in one query, playing two logically distinct "
                    "roles at once."
                ),
                "steps": [
                    {
                        "body": "An order has both an order_date and a ship_date - two "
                        "different dates, but both are still just 'a date'. Do you really need "
                        "two separate date dimension tables?"
                    },
                    {
                        "body": "Join the same dimension table twice, under different aliases:",
                        "sql": "SELECT f.id, d1.attr, d2.attr\nFROM fact f\nJOIN dim d1 ON d1.id = f.key_a\nJOIN dim d2 ON d2.id = f.key_b;",
                    },
                    {
                        "body": "Join dim_dates twice - once for order_date, once for ship_date:",
                        "sql": (
                            "SELECT f.id AS order_id, od.calendar_date::text AS order_date,\n"
                            "  sd.calendar_date::text AS ship_date, f.order_amount\n"
                            "FROM fact_orders f\n"
                            "JOIN dim_dates od ON od.id = f.order_date_id\n"
                            "JOIN dim_dates sd ON sd.id = f.ship_date_id;"
                        ),
                    },
                    {
                        "body": "A single dim_dates table can play more than one ROLE against "
                        "the same fact table - order_date and ship_date are both 'just a date', "
                        "so they share one dimension table instead of needing two separately-"
                        "built ones."
                    },
                    {
                        "body": "Each JOIN gets its own alias (od, sd) and its own foreign key "
                        "(order_date_id, ship_date_id) - that's what lets the same underlying "
                        "dim_dates row be reached twice in one query, playing two logically "
                        "distinct roles at once. Forgetting to alias both joins separately is the "
                        "common mistake here: without od/sd, Postgres has no way to tell which "
                        "dim_dates instance a given column reference means."
                    },
                    {
                        "body": "Role-playing isn't limited to dates either - a single "
                        "dim_employees table commonly plays both 'salesperson' and 'approved_by' "
                        "roles against the same fact table, for exactly the same reason: both "
                        "roles need the same descriptive attributes (name, region, hire_date), "
                        "just attached to a different foreign key on the fact row."
                    },
                    {
                        "body": "A role-playing dimension is one physical table joined more "
                        "than once, each join representing a different logical role. Try it "
                        "yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": (
                    "Join dim_dates twice to get both order_date and ship_date on each order. "
                    "Return order_id, order_date, ship_date, and order_amount."
                ),
                "tables": [
                    {
                        "name": "fact_orders",
                        "schema": [
                            {"column": "id", "type": "bigint"},
                            {"column": "order_date_id", "type": "bigint"},
                            {"column": "ship_date_id", "type": "bigint"},
                            {"column": "order_amount", "type": "numeric"},
                        ],
                        "rows": [
                            {"id": 1, "order_date_id": 1, "ship_date_id": 2, "order_amount": 100.00},
                            {"id": 2, "order_date_id": 2, "ship_date_id": 3, "order_amount": 200.00},
                        ],
                    },
                    {
                        "name": "dim_dates",
                        "schema": [
                            {"column": "id", "type": "bigint"},
                            {"column": "calendar_date", "type": "date"},
                        ],
                        "rows": [
                            {"id": 1, "calendar_date": "2026-01-01"},
                            {"id": 2, "calendar_date": "2026-01-03"},
                            {"id": 3, "calendar_date": "2026-01-05"},
                        ],
                    },
                ],
                "expected_output_rows": [
                    {"order_id": 1, "order_date": "2026-01-01", "ship_date": "2026-01-03", "order_amount": 100.00},
                    {"order_id": 2, "order_date": "2026-01-03", "ship_date": "2026-01-05", "order_amount": 200.00},
                ],
            },
        },
        {
            "id": "node_7_unknown_member",
            "type": "skill",
            "title": "The Unknown Member: keeping an orphaned fact row visible",
            "teach": {
                "sql": (
                    "SELECT f.id AS transaction_id, COALESCE(a.card_network, 'Unknown') AS card_network,\n"
                    "  f.transaction_amount\n"
                    "FROM fact_transactions f\n"
                    "LEFT JOIN dim_accounts a ON a.id = f.account_id;"
                ),
                "note": (
                    "A fact row referencing a deleted, not-yet-loaded, or simply bad account_id "
                    "is a real operational reality, not an edge case to wish away - node 2 already "
                    "flagged that an INNER JOIN would silently drop that fact row entirely. LEFT "
                    "JOIN plus COALESCE is the fix: every fact row survives, and any row whose "
                    "dimension lookup failed gets an explicit, visible 'Unknown' instead of simply "
                    "vanishing from the report. A real warehouse usually goes one step further and "
                    "inserts an actual Unknown Member ROW into dim_accounts itself (conventionally "
                    "at a reserved surrogate key like -1), so every fact row's FK always resolves "
                    "to something, and no report needs its own COALESCE to cover the gap."
                ),
                "steps": [
                    {
                        "body": "A transaction referencing a deleted or not-yet-loaded account is "
                        "a real operational reality - an INNER JOIN would silently drop that row "
                        "from every report built on top of it."
                    },
                    {
                        "body": "LEFT JOIN keeps every fact row; COALESCE fills in the gap:",
                        "sql": "SELECT f.id, COALESCE(d.attr, 'Unknown')\nFROM fact f\nLEFT JOIN dim d ON d.id = f.key;",
                    },
                    {
                        "body": "Keep every transaction, labeling unresolved accounts 'Unknown':",
                        "sql": (
                            "SELECT f.id AS transaction_id, COALESCE(a.card_network, 'Unknown') AS card_network,\n"
                            "  f.transaction_amount\n"
                            "FROM fact_transactions f\n"
                            "LEFT JOIN dim_accounts a ON a.id = f.account_id;"
                        ),
                    },
                    {
                        "body": "Every fact row survives the LEFT JOIN; any row whose dimension "
                        "lookup failed gets an explicit, visible 'Unknown' instead of simply "
                        "vanishing from the result - the gap is now something you can SEE and "
                        "investigate, rather than a silently shrinking row count."
                    },
                    {
                        "body": "A real warehouse usually goes one step further than a "
                        "query-time COALESCE: it inserts an actual Unknown Member ROW into "
                        "dim_accounts itself, conventionally at a reserved surrogate key like -1, "
                        "with card_network already set to 'Unknown'. Then a plain INNER JOIN "
                        "works correctly too, because every fact row's foreign key - even an "
                        "orphaned one, remapped to -1 at load time - always resolves to SOME row."
                    },
                    {
                        "body": "The query-time COALESCE and the load-time Unknown Member row "
                        "solve the same problem at different layers - COALESCE is the right fix "
                        "when you're querying a dimension you don't control the loading of; "
                        "owning the ETL yourself, the Unknown Member row is the more robust fix, "
                        "since it protects every future query, not just the one you remembered to "
                        "COALESCE."
                    },
                    {
                        "body": "An orphaned fact row needs a visible fallback, not a silent "
                        "disappearance. Try it yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": (
                    "Keep every transaction, even ones whose account_id has no matching dimension "
                    "row - label those 'Unknown' instead of dropping them."
                ),
                "tables": [
                    {
                        "name": "fact_transactions",
                        "schema": [
                            {"column": "id", "type": "bigint"},
                            {"column": "account_id", "type": "bigint"},
                            {"column": "transaction_amount", "type": "numeric"},
                        ],
                        "rows": [
                            {"id": 1, "account_id": 101, "transaction_amount": 45.00},
                            {"id": 2, "account_id": 999, "transaction_amount": 60.00},
                        ],
                    },
                    {
                        "name": "dim_accounts",
                        "schema": [
                            {"column": "id", "type": "bigint"},
                            {"column": "card_network", "type": "text"},
                        ],
                        "rows": [
                            {"id": 101, "card_network": "Visa"},
                        ],
                    },
                ],
                "expected_output_rows": [
                    {"transaction_id": 1, "card_network": "Visa", "transaction_amount": 45.00},
                    {"transaction_id": 2, "card_network": "Unknown", "transaction_amount": 60.00},
                ],
            },
        },
        {
            "id": "node_8_conformed_dimension",
            "type": "skill",
            "title": "Conformed dimensions: one dim_accounts, shared by two fact tables",
            "teach": {
                "sql": (
                    "SELECT a.card_network, SUM(x.amount) AS net_amount\n"
                    "FROM (\n"
                    "  SELECT account_id, amount FROM fact_transactions\n"
                    "  UNION ALL\n"
                    "  SELECT account_id, amount FROM fact_refunds\n"
                    ") x\n"
                    "JOIN dim_accounts a ON a.id = x.account_id\n"
                    "GROUP BY a.card_network;"
                ),
                "note": (
                    "A conformed dimension is a SINGLE shared dimension table that multiple fact "
                    "tables all join against with the same meaning - dim_accounts here describes "
                    "accounts identically whether you're looking at fact_transactions or "
                    "fact_refunds, rather than each fact table carrying its own separate, "
                    "possibly-inconsistent copy. UNION ALL stacks the two fact tables' relevant "
                    "columns into one combined row set first (ALL, not plain UNION, since a real "
                    "transaction and a real refund should both survive even if their amounts "
                    "happen to coincide - UNION would silently deduplicate them away as if they "
                    "were the same event); only then does the single JOIN against the one "
                    "conformed dim_accounts run, giving a combined net_amount across both fact "
                    "tables' money movements."
                ),
                "steps": [
                    {
                        "body": "fact_transactions and fact_refunds are two different fact "
                        "tables, but both reference the exact same accounts - should each one get "
                        "its own account dimension, or can they share?"
                    },
                    {
                        "body": "Stack the fact tables first, then join the one shared dimension:",
                        "sql": "SELECT d.attr, SUM(x.amount)\nFROM (\n  SELECT key, amount FROM fact_a\n  UNION ALL\n  SELECT key, amount FROM fact_b\n) x\nJOIN dim d ON d.id = x.key\nGROUP BY d.attr;",
                    },
                    {
                        "body": "Combine transactions and refunds, net amount by card_network:",
                        "sql": (
                            "SELECT a.card_network, SUM(x.amount) AS net_amount\n"
                            "FROM (\n"
                            "  SELECT account_id, amount FROM fact_transactions\n"
                            "  UNION ALL\n"
                            "  SELECT account_id, amount FROM fact_refunds\n"
                            ") x\n"
                            "JOIN dim_accounts a ON a.id = x.account_id\n"
                            "GROUP BY a.card_network;"
                        ),
                    },
                    {
                        "body": "A conformed dimension is a SINGLE shared dimension table that "
                        "multiple fact tables all join against with the same meaning - dim_accounts "
                        "describes accounts identically for both fact_transactions and "
                        "fact_refunds, rather than each fact table carrying its own possibly-"
                        "inconsistent copy."
                    },
                    {
                        "body": "UNION ALL, not plain UNION, is the deliberate choice here: a "
                        "real transaction and a real refund should both survive even if their "
                        "amounts happen to coincide exactly. Plain UNION would silently "
                        "deduplicate identical rows away, treating two genuinely different events "
                        "as if they were the same one - a quiet undercount with no error raised."
                    },
                    {
                        "body": "Conforming a dimension across fact tables is also a real design "
                        "commitment, not just a query-time convenience: it means every fact table "
                        "that references accounts MUST use account_id with exactly the same "
                        "meaning and grain as every other one. A fact_refunds table that secretly "
                        "used a different account identifier scheme would silently produce wrong "
                        "joins here, with no error - conformance has to be enforced at design "
                        "time, upstream of any single query."
                    },
                    {
                        "body": "A conformed dimension lets more than one fact table share "
                        "identical descriptive context through one JOIN target. Try it yourself "
                        "in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": (
                    "Combine transactions and refunds and compute net_amount by card_network, "
                    "joining both against the one shared dim_accounts table."
                ),
                "tables": [
                    {
                        "name": "fact_transactions",
                        "schema": [
                            {"column": "id", "type": "bigint"},
                            {"column": "account_id", "type": "bigint"},
                            {"column": "amount", "type": "numeric"},
                        ],
                        "rows": [
                            {"id": 1, "account_id": 101, "amount": 45.00},
                        ],
                    },
                    {
                        "name": "fact_refunds",
                        "schema": [
                            {"column": "id", "type": "bigint"},
                            {"column": "account_id", "type": "bigint"},
                            {"column": "amount", "type": "numeric"},
                        ],
                        "rows": [
                            {"id": 1, "account_id": 101, "amount": -10.00},
                        ],
                    },
                    {
                        "name": "dim_accounts",
                        "schema": [
                            {"column": "id", "type": "bigint"},
                            {"column": "card_network", "type": "text"},
                        ],
                        "rows": [
                            {"id": 101, "card_network": "Visa"},
                        ],
                    },
                ],
                "expected_output_rows": [
                    {"card_network": "Visa", "net_amount": 35.00},
                ],
            },
        },
        {
            "id": "node_9_grain_violation",
            "type": "skill",
            "title": "Catching a grain violation before it reaches a report",
            "teach": {
                "sql": (
                    "SELECT account_id, COUNT(*) AS row_count\n"
                    "FROM dim_accounts_candidate\n"
                    "GROUP BY account_id\n"
                    "HAVING COUNT(*) > 1;"
                ),
                "note": (
                    "Node 1 declared the grain; this query is how you actually VERIFY a table "
                    "still honors it. If dim_accounts promises 'one row per account', then any "
                    "account_id appearing more than once is a broken promise - this exact GROUP "
                    "BY + HAVING shape (group by the declared grain key, keep only groups with "
                    "more than one row) is the standard data-quality check for that, and it's "
                    "cheap enough to run routinely rather than only when something's already gone "
                    "wrong downstream. An empty result here is itself the good outcome - it means "
                    "the grain is intact, not that nothing interesting happened."
                ),
                "steps": [
                    {
                        "body": "A dimension table promised one row per account_id back in node "
                        "1 - but promises drift. How do you actually check whether that's still "
                        "true, right now?"
                    },
                    {
                        "body": "Group by the declared grain key, keep only the groups over 1:",
                        "sql": "SELECT grain_key, COUNT(*) AS n\nFROM table\nGROUP BY grain_key\nHAVING COUNT(*) > 1;",
                    },
                    {
                        "body": "Find every account_id with more than one dimension row:",
                        "sql": (
                            "SELECT account_id, COUNT(*) AS row_count\n"
                            "FROM dim_accounts_candidate\n"
                            "GROUP BY account_id\n"
                            "HAVING COUNT(*) > 1;"
                        ),
                    },
                    {
                        "body": "If dim_accounts promises 'one row per account', any account_id "
                        "appearing more than once is a broken promise - this GROUP BY + HAVING "
                        "shape is the standard check for exactly that, and it's cheap enough to "
                        "run routinely, not just when a report already looks wrong."
                    },
                    {
                        "body": "An empty result here is itself the good outcome - it confirms "
                        "the grain is intact. This is the opposite of most queries you've "
                        "written in this track, where an empty result usually means something "
                        "went wrong; here it means the table is honoring its own contract."
                    },
                    {
                        "body": "When this check DOES find duplicates, the fix isn't usually "
                        "this query - it's realizing the table's actual grain is finer than its "
                        "declared one (the exact trap node 1 warned about: two rows sharing an "
                        "account_id with a genuinely different card_network, from a mid-stream "
                        "reissue). The honest fix is either tightening the grain declaration to "
                        "match reality, or building a proper SCD2 table (node 3) that's designed "
                        "to hold more than one row per account on purpose."
                    },
                    {
                        "body": "Verifying a grain promise is just grouping by the declared key "
                        "and checking nothing grouped to more than one row. Try it yourself in "
                        "the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Find every account_id that has more than one row in this candidate dimension table.",
                "table_name": "dim_accounts_candidate",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "account_id", "type": "bigint"},
                    {"column": "card_network", "type": "text"},
                ],
                "example_rows": [
                    {"id": 1, "account_id": 101, "card_network": "Visa"},
                    {"id": 2, "account_id": 101, "card_network": "Visa Signature"},
                    {"id": 3, "account_id": 102, "card_network": "Mastercard"},
                ],
                "expected_output_rows": [
                    {"account_id": 101, "row_count": 2},
                ],
            },
        },
        {
            "id": "node_10_junk_dimension",
            "type": "skill",
            "title": "Junk dimensions: bundling small flags instead of scattering them",
            "teach": {
                "sql": (
                    "SELECT f.id AS transaction_id, j.is_disputed, j.is_recurring, f.transaction_amount\n"
                    "FROM fact_transactions f\n"
                    "JOIN dim_transaction_flags j ON j.id = f.junk_dim_id;"
                ),
                "note": (
                    "is_disputed and is_recurring are both small, low-cardinality boolean flags - "
                    "individually too trivial to deserve their own dimension tables, but leaving "
                    "them as loose boolean COLUMNS directly on the fact table bloats every fact "
                    "row with flag columns instead of foreign keys. A junk dimension bundles "
                    "several such flags into one small lookup table (here, every combination of "
                    "is_disputed x is_recurring gets exactly one row), and the fact table carries "
                    "a single junk_dim_id pointing at the right combination - one FK instead of N "
                    "separate flag columns."
                ),
                "steps": [
                    {
                        "body": "is_disputed and is_recurring are both small true/false flags - "
                        "too trivial to deserve their own dimension tables, but you still don't "
                        "want them scattered as loose columns directly on the fact table."
                    },
                    {
                        "body": "Bundle several flags into one small combinations table:",
                        "sql": "SELECT f.id, j.flag_a, j.flag_b\nFROM fact f\nJOIN dim_junk j ON j.id = f.junk_dim_id;",
                    },
                    {
                        "body": "Join each transaction to its bundled dispute/recurring flags:",
                        "sql": (
                            "SELECT f.id AS transaction_id, j.is_disputed, j.is_recurring, f.transaction_amount\n"
                            "FROM fact_transactions f\n"
                            "JOIN dim_transaction_flags j ON j.id = f.junk_dim_id;"
                        ),
                    },
                    {
                        "body": "A junk dimension bundles several low-cardinality flags into "
                        "one small lookup table - every combination of is_disputed x is_recurring "
                        "gets exactly one row - so the fact table carries a single junk_dim_id "
                        "instead of N separate flag columns."
                    },
                    {
                        "body": "The name is deliberately self-deprecating: 'junk' means these "
                        "flags don't share any real business relationship with each other the way "
                        "a true dimension's columns do (card_network and issuing_bank both "
                        "describe 'the account' coherently; is_disputed and is_recurring just "
                        "happen to both be small booleans) - they're bundled together purely for "
                        "the mechanical convenience of one FK instead of several loose columns."
                    },
                    {
                        "body": "The tradeoff worth knowing: a junk dimension table's row count "
                        "grows combinatorially with how many flags you cram into it - 2 boolean "
                        "flags means up to 4 rows, but 5 boolean flags means up to 32, and most of "
                        "those combinations may never actually occur in real data. A junk "
                        "dimension works best with a handful of flags, not as a dumping ground for "
                        "every miscellaneous boolean a schema accumulates over time."
                    },
                    {
                        "body": "A junk dimension trades several loose flag columns on the fact "
                        "table for one small combinations table and a single FK. Try it yourself "
                        "in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Join each transaction to its bundled is_disputed/is_recurring flags via the junk dimension.",
                "tables": [
                    {
                        "name": "fact_transactions",
                        "schema": [
                            {"column": "id", "type": "bigint"},
                            {"column": "junk_dim_id", "type": "bigint"},
                            {"column": "transaction_amount", "type": "numeric"},
                        ],
                        "rows": [
                            {"id": 1, "junk_dim_id": 1, "transaction_amount": 45.00},
                            {"id": 2, "junk_dim_id": 2, "transaction_amount": 1250.00},
                        ],
                    },
                    {
                        "name": "dim_transaction_flags",
                        "schema": [
                            {"column": "id", "type": "bigint"},
                            {"column": "is_disputed", "type": "boolean"},
                            {"column": "is_recurring", "type": "boolean"},
                        ],
                        "rows": [
                            {"id": 1, "is_disputed": False, "is_recurring": True},
                            {"id": 2, "is_disputed": True, "is_recurring": False},
                        ],
                    },
                ],
                "expected_output_rows": [
                    {"transaction_id": 1, "is_disputed": False, "is_recurring": True, "transaction_amount": 45.00},
                    {"transaction_id": 2, "is_disputed": True, "is_recurring": False, "transaction_amount": 1250.00},
                ],
            },
        },
        {
            "id": "review",
            "type": "review",
            "title": "Review: grain, star JOINs, SCD2, fact aggregation, degenerate/role-playing/conformed/junk dimensions, grain validation",
            "prompt": (
                "A quick recap of Kimball's four-step process in SQL form before moving into the "
                "Warehouse capstone, which builds this same star schema for real - against the "
                "actual fintech feed, on real Spark + Delta, with a real SCD2 re-run."
            ),
        },
    ],
}
