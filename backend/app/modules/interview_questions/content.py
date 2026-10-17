"""Static, hand-curated reference content - publicly-known, commonly-asked
data engineering interview questions, grouped by topic. Unlike every other
module in this app, nothing here is gradable or dynamic: it's a reading
reference, so it's just a plain nested data structure with no backend
logic beyond serving it."""

TOPICS = [
    {
        "topic": "SQL",
        "questions": [
            {
                "q": "What's the difference between WHERE and HAVING?",
                "a": (
                    "WHERE filters individual rows before grouping/aggregation happens; HAVING "
                    "filters groups after GROUP BY has produced them. You can't reference an "
                    "aggregate like COUNT(*) in WHERE because no aggregation has happened yet at "
                    "that point in query execution - that's exactly what HAVING is for."
                ),
            },
            {
                "q": "What is the difference between INNER, LEFT, RIGHT, and FULL OUTER JOIN?",
                "a": (
                    "INNER JOIN keeps only rows with a match on both sides. LEFT JOIN keeps every "
                    "row from the left table, filling unmatched right-side columns with NULL. "
                    "RIGHT JOIN is the mirror image. FULL OUTER JOIN keeps every row from both "
                    "sides, NULL-filling whichever side didn't match - effectively a LEFT JOIN "
                    "UNION a RIGHT JOIN with duplicates removed."
                ),
            },
            {
                "q": "What's the difference between RANK(), DENSE_RANK(), and ROW_NUMBER()?",
                "a": (
                    "All three are window functions that number rows within a PARTITION BY/ORDER "
                    "BY window. ROW_NUMBER() always assigns distinct sequential numbers, even to "
                    "tied rows. RANK() gives tied rows the same number but then skips ahead (1, 2, "
                    "2, 4). DENSE_RANK() gives tied rows the same number without skipping (1, 2, 2, "
                    "3). The classic use case for deciding between them: deduping to 'one row per "
                    "group' wants ROW_NUMBER(); a leaderboard usually wants RANK()."
                ),
            },
            {
                "q": "How do you find duplicate rows in a table, and how do you delete all but one copy of each?",
                "a": (
                    "Find them with GROUP BY the key columns plus HAVING COUNT(*) > 1. To delete "
                    "all but one copy, the common pattern is a CTE with ROW_NUMBER() OVER "
                    "(PARTITION BY <key columns> ORDER BY <tiebreaker, often id>) and then DELETE "
                    "WHERE row_number > 1 - keeping the first row per partition and removing the "
                    "rest in one statement, without a self-join."
                ),
            },
            {
                "q": "What is a CTE, and when would you use a recursive CTE?",
                "a": (
                    "A CTE (WITH clause) is a named, inline temporary result set, useful for "
                    "breaking a complex query into readable stages or reusing the same subquery "
                    "without repeating it. A recursive CTE references itself and is the standard "
                    "SQL tool for traversing hierarchical or graph-shaped data - an org chart, a "
                    "bill-of-materials, or walking a parent_id chain up to a root - by starting "
                    "from an anchor query and repeatedly UNION ALL-ing a recursive term until it "
                    "stops producing new rows."
                ),
            },
            {
                "q": "What's the difference between a clustered and a non-clustered index?",
                "a": (
                    "A clustered index determines the physical on-disk order of the table's rows - "
                    "there can only be one per table (often the primary key). A non-clustered "
                    "index is a separate structure that stores the indexed column(s) plus a "
                    "pointer back to the actual row, so a table can have many of them. Looking up "
                    "via a non-clustered index that doesn't cover the query ('covering index') "
                    "means an extra lookup back to the base table for any column not in the index."
                ),
            },
            {
                "q": "What's a slowly changing dimension (SCD), and what's the difference between Type 1 and Type 2?",
                "a": (
                    "An SCD is a dimension table whose rows' attributes legitimately change over "
                    "time (a customer's address, a product's category). Type 1 just overwrites the "
                    "old value in place, losing history - simplest, but you can't ask what was true "
                    "as of a past date. Type 2 instead inserts a new row for every change, keeping "
                    "the old row with an end-dated validity window (effective_from/effective_to "
                    "and usually an is_current flag), preserving full history at the cost of a "
                    "larger table and queries that must explicitly filter for the row valid as of "
                    "a given point in time."
                ),
            },
            {
                "q": "How do you find the second-highest salary in a table, without using LIMIT/OFFSET?",
                "a": (
                    "A portable approach: SELECT MAX(salary) FROM employees WHERE salary < (SELECT "
                    "MAX(salary) FROM employees). This avoids ties incorrectly counting as "
                    "'second' the way an OFFSET-based approach can, and works across engines that "
                    "don't support LIMIT/OFFSET or FETCH the same way. The window-function "
                    "alternative is DENSE_RANK() OVER (ORDER BY salary DESC) filtered to rank = 2, "
                    "which generalizes cleanly to 'Nth highest.'"
                ),
            },
            {
                "q": "What's the N+1 query problem, and how do you avoid it?",
                "a": (
                    "It's when code loops over N parent rows and issues one extra query per row to "
                    "fetch related child data (N+1 total queries) instead of fetching everything in "
                    "a constant number of round trips. The fix is almost always a single JOIN, or a "
                    "single query with an IN (...) / WHERE parent_id = ANY(...) that batches the "
                    "child lookups, then grouping the results back together in application code."
                ),
            },
            {
                "q": "What are transaction isolation levels, and what is a phantom read?",
                "a": (
                    "Isolation levels trade correctness guarantees for concurrency. READ "
                    "UNCOMMITTED allows dirty reads (seeing another transaction's uncommitted "
                    "changes); READ COMMITTED prevents that but allows non-repeatable reads (a row "
                    "you read twice in the same transaction can change between reads); REPEATABLE "
                    "READ prevents that too but can still allow phantom reads (a repeated range "
                    "query can return new rows inserted by another committed transaction); "
                    "SERIALIZABLE prevents all of the above by making transactions behave as if "
                    "run one at a time, at the cost of the most contention/retries."
                ),
            },
        ],
        "coding": [
            {
                "prompt": "Given orders(id, customer_id, amount), write a query that returns each "
                "customer's total spend and their rank from highest to lowest spender.",
                "solution": (
                    "SELECT customer_id, SUM(amount) AS total_spent,\n"
                    "       RANK() OVER (ORDER BY SUM(amount) DESC) AS spend_rank\n"
                    "FROM orders\n"
                    "GROUP BY customer_id\n"
                    "ORDER BY total_spent DESC;"
                ),
                "note": (
                    "GROUP BY collapses to one row per customer; RANK() OVER an ORDER BY on the "
                    "aggregate assigns the rank in the same pass, so ties share a rank and the next "
                    "rank skips ahead - no separate subquery needed."
                ),
            },
            {
                "prompt": "Given orders(id, customer_id, order_date), write a query that returns "
                "customers who placed orders in at least 2 different calendar months.",
                "solution": (
                    "SELECT customer_id\n"
                    "FROM orders\n"
                    "GROUP BY customer_id\n"
                    "HAVING COUNT(DISTINCT date_trunc('month', order_date)) >= 2;"
                ),
                "note": (
                    "date_trunc('month', ...) collapses every date in the same month to the same "
                    "value, so COUNT(DISTINCT ...) counts distinct months, not distinct dates - "
                    "HAVING filters on that aggregate the way WHERE never could."
                ),
            },
            {
                "prompt": "Given orders(id, customer_id, order_date), write a query that returns "
                "each customer's single earliest order, without a correlated subquery.",
                "solution": (
                    "SELECT DISTINCT ON (customer_id) customer_id, id, order_date\n"
                    "FROM orders\n"
                    "ORDER BY customer_id, order_date ASC;"
                ),
                "note": (
                    "Postgres's DISTINCT ON keeps the first row per group after an explicit ORDER "
                    "BY - the ORDER BY's leading column must match DISTINCT ON's column so 'first' "
                    "is unambiguous. On engines without DISTINCT ON, ROW_NUMBER() OVER (PARTITION BY "
                    "customer_id ORDER BY order_date) filtered to rn = 1 is the portable equivalent."
                ),
            },
        ],
    },
    {
        "topic": "Data Modeling & Warehousing",
        "questions": [
            {
                "q": "What's the difference between a star schema and a snowflake schema?",
                "a": (
                    "A star schema has one central fact table joined directly to fully "
                    "denormalized dimension tables (one hop). A snowflake schema normalizes those "
                    "dimensions further into sub-dimensions (e.g. dim_product splitting out "
                    "dim_category), trading some storage/redundancy savings for extra JOINs and "
                    "more complex queries. Star schemas are generally preferred in practice because "
                    "storage is cheap and query simplicity/performance usually wins."
                ),
            },
            {
                "q": "What does 'declaring the grain' mean in dimensional modeling, and why does it come first?",
                "a": (
                    "The grain is the precise definition of what one row in a fact table "
                    "represents - 'one row per line item per order,' not just 'one row per order.' "
                    "Kimball's design process insists on declaring it before identifying dimensions "
                    "or facts, because every later decision (what counts as 'the same' dimension "
                    "row, what's safe to SUM) depends on already knowing what a row means. Getting "
                    "the grain wrong doesn't error loudly - it silently produces numbers that are "
                    "subtly too big or too small, usually caught much later."
                ),
            },
            {
                "q": "What's a degenerate dimension?",
                "a": (
                    "An identifier that lives in the fact table itself with no dimension table of "
                    "its own - typically a transaction/invoice/order number. It has no useful "
                    "descriptive attributes to warrant a separate table, but is still useful for "
                    "grouping and filtering, so it stays as a plain column on the fact row instead "
                    "of being normalized out."
                ),
            },
            {
                "q": "What's the difference between OLTP and OLAP systems?",
                "a": (
                    "OLTP (online transaction processing) systems are optimized for many small, "
                    "fast reads/writes of individual records - a normalized schema, strong "
                    "consistency, row-oriented storage (a typical production Postgres app "
                    "database). OLAP (online analytical processing) systems are optimized for "
                    "scanning and aggregating large volumes of historical data - denormalized star "
                    "schemas, column-oriented storage, built to answer 'what happened' questions "
                    "across millions of rows rather than fetch one row fast."
                ),
            },
            {
                "q": "What's a conformed dimension, and why does it matter?",
                "a": (
                    "A dimension table (e.g. dim_accounts) shared by multiple fact tables with "
                    "exactly the same meaning and keys in both, instead of each fact table getting "
                    "its own slightly-different copy. It's what lets you drill across subject "
                    "areas consistently - joining fact_transactions and fact_disputes to the same "
                    "dim_accounts and trusting that 'account 101' means the same thing in both - "
                    "which is one of Kimball's core architectural principles (the 'bus matrix')."
                ),
            },
            {
                "q": "What is data partitioning, and what's partition pruning?",
                "a": (
                    "Partitioning splits a large table into smaller physical segments, usually by "
                    "date or a high-cardinality key, so that both maintenance (loads, deletes) and "
                    "queries can target one segment instead of the whole table. Partition pruning "
                    "is the query planner recognizing that a WHERE clause's filter maps to specific "
                    "partitions and skipping the rest entirely - turning a full scan into a scan of "
                    "only the relevant subset, often the single biggest lever for warehouse query "
                    "performance on large time-series tables."
                ),
            },
            {
                "q": "What's a fact table that only stores changes/deltas versus one that's additive?",
                "a": (
                    "Most fact tables are additive - every measure (amount, quantity) can be "
                    "safely SUMmed across any dimension, which is what makes star schemas so easy "
                    "to query. Some measures are semi-additive (a balance can be summed across "
                    "accounts but not across time - you'd sum ending balances of different accounts "
                    "on the same day, not sum one account's balance across days) or non-additive "
                    "(a ratio or percentage can't be meaningfully summed at all and has to be "
                    "recomputed from its additive components)."
                ),
            },
            {
                "q": "What's the Unknown Member pattern in dimensional modeling?",
                "a": (
                    "A placeholder row (often key = -1 or 0) inserted into a dimension table to "
                    "represent 'no match found' or 'not yet known,' so fact rows whose foreign key "
                    "doesn't resolve to a real dimension row can still point at something valid "
                    "instead of becoming orphaned or requiring a NULL foreign key. It keeps "
                    "referential integrity intact and lets those rows still show up (as 'Unknown') "
                    "in aggregate reports instead of silently disappearing from an INNER JOIN."
                ),
            },
        ],
        "coding": [
            {
                "prompt": "Given fact_sales(id, product_id, amount) and dim_products(id, category), "
                "write a query that returns total revenue per product category, highest first.",
                "solution": (
                    "SELECT d.category, SUM(f.amount) AS revenue\n"
                    "FROM fact_sales f\n"
                    "JOIN dim_products d ON d.id = f.product_id\n"
                    "GROUP BY d.category\n"
                    "ORDER BY revenue DESC;"
                ),
                "note": (
                    "The textbook star-schema query: one JOIN from fact to dimension, GROUP BY the "
                    "dimension's descriptive attribute (not its key), SUM the fact's measure."
                ),
            },
            {
                "prompt": "Given a Type-2 SCD dim_customers(customer_id, tier, effective_from, "
                "effective_to), write a query returning each customer's tier as it stood on "
                "2026-02-15 (effective_to is NULL for the current row).",
                "solution": (
                    "SELECT customer_id, tier\n"
                    "FROM dim_customers\n"
                    "WHERE effective_from <= '2026-02-15'\n"
                    "  AND (effective_to IS NULL OR effective_to > '2026-02-15')\n"
                    "ORDER BY customer_id;"
                ),
                "note": (
                    "The two-sided range check is the whole trick of querying an SCD2 table 'as of' "
                    "a date - effective_from <= the date catches rows that started in time, and the "
                    "NULL-or-after check on effective_to catches both the still-current row and any "
                    "row that hadn't yet been superseded on that date."
                ),
            },
            {
                "prompt": "Given fact_monthly_revenue(month, revenue), write a query computing each "
                "month's percentage revenue growth over the previous month.",
                "solution": (
                    "SELECT month, revenue,\n"
                    "  ROUND((revenue - LAG(revenue) OVER (ORDER BY month))\n"
                    "        / LAG(revenue) OVER (ORDER BY month) * 100, 1) AS pct_growth\n"
                    "FROM fact_monthly_revenue\n"
                    "ORDER BY month;"
                ),
                "note": (
                    "LAG() reaches back one row (by month order) without a self-join - the first "
                    "month has no prior row to compare to, so its pct_growth is correctly NULL "
                    "rather than zero or an error."
                ),
            },
        ],
    },
    {
        "topic": "NoSQL & Document Databases",
        "questions": [
            {
                "q": "When would you choose a document database (e.g. MongoDB) over a relational database?",
                "a": (
                    "When the data is naturally nested/hierarchical and usually read or written as "
                    "a whole unit (a user profile with embedded addresses, an order with embedded "
                    "line items), denormalizing into one document avoids JOINs and matches the "
                    "application's access pattern. It also fits better when the schema varies "
                    "across records or evolves quickly, since documents don't require a rigid "
                    "upfront schema the way a relational table does. It's a worse fit when you need "
                    "multi-record ACID transactions across many collections, or strong relational "
                    "integrity enforced by the database itself."
                ),
            },
            {
                "q": "What's the difference between embedding and referencing in document modeling?",
                "a": (
                    "Embedding nests related data directly inside the parent document - fast single-"
                    "read access, but the embedded data duplicates across documents if shared, and "
                    "documents can grow unbounded (a problem for data that grows without limit, "
                    "like comments on a post). Referencing stores just an id and requires a second "
                    "lookup (or $lookup aggregation stage) to join - more normalized, better for "
                    "data that's shared across many parents or grows unbounded, at the cost of an "
                    "extra round trip."
                ),
            },
            {
                "q": "What is eventual consistency, and why do many NoSQL systems accept it?",
                "a": (
                    "In a distributed, replicated system, eventual consistency means that after a "
                    "write, different replicas may briefly disagree, but will converge to the same "
                    "value if no further writes happen - as opposed to strong consistency, where "
                    "every read immediately reflects the latest write. Many NoSQL systems default "
                    "to it because enforcing strong consistency across replicas costs latency and "
                    "availability (per the CAP theorem, you can't maximize consistency, "
                    "availability, and partition tolerance simultaneously), and many workloads "
                    "(social feeds, product catalogs) can tolerate a brief staleness window in "
                    "exchange for faster, more available writes."
                ),
            },
            {
                "q": "What's the $lookup aggregation stage in MongoDB, and how is it different from a SQL JOIN?",
                "a": (
                    "$lookup performs a left-outer-join-style match between two collections inside "
                    "an aggregation pipeline, attaching matched documents from the 'foreign' "
                    "collection as an array field on each document from the pipeline. Unlike a SQL "
                    "JOIN, it's not the primary way documents relate to each other (embedding "
                    "usually is) - it's reached for when you specifically need to combine data that "
                    "was deliberately kept in separate collections, and it tends to be more "
                    "expensive than a well-indexed SQL JOIN since it isn't the storage engine's "
                    "native access pattern."
                ),
            },
            {
                "q": "How do you handle a document schema that needs to change over time (schema evolution) in MongoDB?",
                "a": (
                    "Since MongoDB doesn't enforce a schema at the database level, the common "
                    "approaches are: write application/read code that tolerates both the old and "
                    "new shape (checking for a field's presence, defaulting missing fields); run a "
                    "one-time migration script that rewrites existing documents into the new shape; "
                    "or add a schema_version field to each document so readers know which shape "
                    "to expect without guessing. Optional JSON Schema validation rules can also be "
                    "layered on a collection to catch writes that violate an agreed-upon shape "
                    "going forward, without forcing a rigid relational schema."
                ),
            },
        ],
        "coding": [
            {
                "prompt": "Given an orders collection with customer_id and amount fields, write an "
                "aggregation pipeline returning each customer's total spend, sorted descending.",
                "solution": (
                    "db.orders.aggregate([\n"
                    "  { $group: { _id: \"$customer_id\", total_spent: { $sum: \"$amount\" } } },\n"
                    "  { $sort: { total_spent: -1 } },\n"
                    "])"
                ),
                "note": (
                    "$group with a $sum accumulator is Mongo's GROUP BY/SUM; grouping on "
                    "\"$customer_id\" collapses to one document per customer, then $sort orders the "
                    "already-grouped result - no second pass over the raw documents needed."
                ),
            },
            {
                "prompt": "Given the same orders collection with an order_date field, write an "
                "aggregation pipeline returning each customer's single most recent order.",
                "solution": (
                    "db.orders.aggregate([\n"
                    "  { $sort: { order_date: -1 } },\n"
                    "  { $group: { _id: \"$customer_id\",\n"
                    "              most_recent_order: { $first: \"$order_date\" },\n"
                    "              amount: { $first: \"$amount\" } } },\n"
                    "])"
                ),
                "note": (
                    "$first inside $group only works correctly because the $sort stage runs first - "
                    "$group preserves the incoming order within each group, so sorting newest-first "
                    "before grouping means the 'first' document $group sees per customer is the most "
                    "recent one."
                ),
            },
            {
                "prompt": "Write a Mongo update that increments a user document's login_count field "
                "by 1 without reading the document first.",
                "solution": "db.users.updateOne({ _id: \"u1\" }, { $inc: { login_count: 1 } })",
                "note": (
                    "$inc is applied atomically server-side - no read-modify-write race between two "
                    "concurrent logins, unlike reading login_count into application code, adding 1, "
                    "and writing it back."
                ),
            },
        ],
    },
    {
        "topic": "Data Lake & Lakehouse",
        "questions": [
            {
                "q": "What's the difference between schema-on-write and schema-on-read?",
                "a": (
                    "Schema-on-write (the relational-database default) validates and enforces a "
                    "structure at the moment data is written, rejecting anything that doesn't fit. "
                    "Schema-on-read stores raw data as-is and only interprets/validates its "
                    "structure at query time. This makes a data lake far more flexible for ingesting "
                    "varied, fast-changing, or semi-structured sources, but it pushes the cost of "
                    "catching bad or malformed data from write time to read time, which is slower "
                    "to notice and often messier to fix."
                ),
            },
            {
                "q": "Why does a data lake typically store files as Parquet instead of CSV or JSON?",
                "a": (
                    "Parquet is columnar and self-describing (it carries its own schema and "
                    "per-column type info), which lets an analytical query read only the columns it "
                    "needs instead of the whole row, and lets the query engine skip entire files or "
                    "row groups using embedded min/max statistics. It also compresses much better "
                    "than row-oriented text formats like CSV/JSON because similar values are stored "
                    "together. The tradeoff is that it's a binary format - not human-readable, and "
                    "not well suited to appending single rows one at a time."
                ),
            },
            {
                "q": "What's the medallion architecture (bronze/silver/gold)?",
                "a": (
                    "A common lake/lakehouse layering convention: bronze holds raw data exactly as "
                    "ingested (for full lineage and replayability); silver holds cleaned, "
                    "deduplicated, conformed data (nulls handled, types fixed, schema agreed-upon); "
                    "gold holds business-level, often aggregated tables ready for direct "
                    "consumption by BI/reporting. Each layer is a real materialized step, not just "
                    "a naming convention, so a bug caught downstream can be traced back to exactly "
                    "which layer introduced it."
                ),
            },
            {
                "q": "What does a table format like Delta Lake or Apache Iceberg add on top of a plain data lake?",
                "a": (
                    "A plain lake is just files in a directory - no atomicity, no schema "
                    "enforcement, no way to see a consistent snapshot while a write is in progress. "
                    "A table format adds a transaction log that makes multi-file writes atomic "
                    "(readers either see all of a commit or none of it), enforces/tracks schema "
                    "over time (with controlled evolution), and records enough metadata to let you "
                    "query an older version of the table (time travel) or roll back a bad write - "
                    "essentially giving a lake the ACID guarantees a database has always had."
                ),
            },
            {
                "q": "What is time travel in a lakehouse table format, and what's it useful for?",
                "a": (
                    "Because every commit is recorded in an append-only transaction log rather than "
                    "overwriting data in place, you can query the table as it existed at a specific "
                    "earlier version or timestamp. That's useful for auditing ('what did this table "
                    "look like before yesterday's bad job ran'), reproducing a report exactly as it "
                    "was generated, and recovering from a bad write by rolling back to the last-good "
                    "version instead of needing a separate backup."
                ),
            },
            {
                "q": "What's the small-file problem, and how is it solved?",
                "a": (
                    "Streaming or frequent micro-batch writes tend to produce many small files "
                    "instead of fewer large ones. Query engines pay a fixed per-file overhead (open, "
                    "read metadata/footer, close), so lots of tiny files slow reads down far more "
                    "than their total data volume would suggest, and can overwhelm a metastore. The "
                    "fix is compaction - a periodic job (OPTIMIZE in Delta, or a manual rewrite) "
                    "that merges many small files into fewer larger ones, which table formats can "
                    "do safely as an atomic operation without disrupting concurrent readers."
                ),
            },
            {
                "q": "How does a lakehouse table format handle concurrent writers?",
                "a": (
                    "Through optimistic concurrency control on the transaction log: a writer reads "
                    "the current table version, prepares its change, and then tries to commit the "
                    "next version number. If another writer already committed that version first, "
                    "the commit is rejected and the writer must re-read and retry rather than "
                    "silently corrupting the table - avoiding the need for a heavy, shared lock on "
                    "every write at the cost of occasional retries under contention."
                ),
            },
        ],
        "coding": [
            {
                "prompt": "Given a date-partitioned events(id, event_date, payload) table, write a "
                "query that only touches the 2026-02-02 partition.",
                "solution": "SELECT * FROM events WHERE event_date = '2026-02-02';",
                "note": (
                    "On a real partitioned table (or a lake laid out as date=.../ directories), this "
                    "exact filter is what lets the engine prune every other partition/file entirely "
                    "instead of scanning the full table - the query doesn't need to 'know' about "
                    "partitioning, the planner exploits it automatically from the WHERE clause."
                ),
            },
            {
                "prompt": "Given accounts(account_id PRIMARY KEY, balance), write the SQL equivalent "
                "of a Delta/Iceberg MERGE that inserts a new account or updates its balance if the "
                "account already exists.",
                "solution": (
                    "INSERT INTO accounts (account_id, balance) VALUES (101, 500)\n"
                    "ON CONFLICT (account_id) DO UPDATE SET balance = EXCLUDED.balance;"
                ),
                "note": (
                    "Running this exact statement a second time with a different balance updates the "
                    "existing row in place rather than inserting a duplicate - verified against a "
                    "real table: two runs with balance 500 then 650 leave exactly one row, "
                    "(101, 650), which is the whole point of an idempotent upsert."
                ),
            },
            {
                "prompt": "Given an append-only commit_log(committed_at, value) table recording a "
                "value at every commit, write a query returning the value as it stood at or before "
                "2026-01-02 00:00:00 - a poor-man's time travel query.",
                "solution": (
                    "SELECT value FROM commit_log\n"
                    "WHERE committed_at <= '2026-01-02 00:00:00'\n"
                    "ORDER BY committed_at DESC\n"
                    "LIMIT 1;"
                ),
                "note": (
                    "This is exactly what a lakehouse table format's time travel does under the "
                    "hood - every commit is a new row in an append-only log, so 'what was true as of "
                    "T' is just the latest commit at or before T, never an in-place overwrite."
                ),
            },
        ],
    },
    {
        "topic": "ETL / Pipeline Architecture",
        "questions": [
            {
                "q": "What's the difference between ETL and ELT?",
                "a": (
                    "ETL (Extract, Transform, Load) transforms data in a separate processing step "
                    "before loading it into the target system, so the target only ever holds clean, "
                    "modeled data. ELT (Extract, Load, Transform) loads raw data into the target "
                    "first and transforms it there using the target's own compute (common with "
                    "modern cloud warehouses like Snowflake/BigQuery that have cheap, scalable "
                    "compute) - trading the simplicity of 'target is always clean' for flexibility "
                    "to re-derive different transformations from the same raw data later without "
                    "re-extracting from the source."
                ),
            },
            {
                "q": "What does idempotency mean in a data pipeline, and why does it matter?",
                "a": (
                    "An idempotent pipeline produces the same end result no matter how many times "
                    "it's re-run with the same input - re-running it doesn't duplicate rows or "
                    "double-count values. It matters because failures and retries are inevitable "
                    "(a job crashes halfway, a network blip causes a webhook to be redelivered); "
                    "without idempotency, every retry risks corrupting the data instead of safely "
                    "recovering. Common techniques: upserts keyed on a natural/dedup key instead of "
                    "blind inserts, or a full overwrite-partition pattern instead of an append."
                ),
            },
            {
                "q": "What's the difference between at-least-once, at-most-once, and exactly-once delivery?",
                "a": (
                    "At-least-once guarantees a message is delivered but may be delivered more than "
                    "once (duplicates possible, no data loss) - the most common and easiest to "
                    "build. At-most-once delivers zero or one times (no duplicates, but data can be "
                    "silently lost) - rarely what you want. Exactly-once is the hardest to actually "
                    "guarantee end-to-end and usually means 'effectively-once' in practice: "
                    "at-least-once delivery combined with idempotent processing (dedup keys, "
                    "transactional writes) on the consumer side, since true exactly-once delivery "
                    "across a distributed system without that is generally considered impossible."
                ),
            },
            {
                "q": "What is a watermark in stream/late-arriving-data processing?",
                "a": (
                    "A watermark is a heuristic marking roughly how far event-time processing has "
                    "progressed - 'we believe we've seen all events up to time T, give or take some "
                    "lateness allowance.' It lets a system decide when it's safe to finalize a "
                    "windowed aggregation (e.g. close out 'orders per hour' for the 2pm hour) while "
                    "still tolerating some amount of late-arriving data, instead of waiting forever "
                    "for every possible straggler or closing windows the instant the clock ticks "
                    "over and getting incomplete results."
                ),
            },
            {
                "q": "What's a dead-letter queue, and when is it used?",
                "a": (
                    "A separate place (queue or table) where messages/records that fail processing "
                    "are routed instead of being silently dropped or endlessly retried and blocking "
                    "the main pipeline. It's used so one malformed record (bad JSON, violates a "
                    "constraint, fails validation) doesn't halt an entire batch or stream - it gets "
                    "quarantined with enough context to debug and reprocess later, while everything "
                    "else keeps flowing."
                ),
            },
            {
                "q": "How do you detect and handle schema drift in an incoming data feed?",
                "a": (
                    "Detect it by validating incoming records/batches against an expected schema "
                    "(a declared schema registry, or a lightweight check comparing column names/"
                    "types against the last known-good batch) before loading, rather than letting a "
                    "downstream query fail cryptically. Handling it depends on the kind of drift: a "
                    "new optional field can often be absorbed by defaulting it; a renamed or "
                    "retyped field usually needs an explicit mapping/cast step; a genuinely breaking "
                    "change should route the affected records to a dead-letter path and alert, "
                    "rather than silently loading bad data."
                ),
            },
            {
                "q": "What's a backfill, and what makes backfilling a pipeline risky?",
                "a": (
                    "A backfill re-runs a pipeline over a past date range - to fix a bug's historical "
                    "damage, populate a newly-added column for old data, or recover from an outage. "
                    "It's risky because a backfill often runs at a different scale/concurrency than "
                    "normal incremental runs (hitting rate limits or resource limits the daily job "
                    "never would), and because a backfill that isn't idempotent can double-write "
                    "data that was never actually missing in the first place - so a safe backfill "
                    "design almost always depends on the same idempotency guarantees as normal runs."
                ),
            },
            {
                "q": "What's data lineage, and why do data platforms track it?",
                "a": (
                    "Data lineage is the record of where a piece of data came from and what "
                    "transformations it passed through to reach its current form - which source "
                    "table, which job, which version of which transformation logic. It matters for "
                    "debugging ('this number looks wrong, which upstream table or job caused it'), "
                    "for impact analysis before changing a shared upstream table ('what breaks if I "
                    "rename this column'), and for compliance/audit requirements that need to prove "
                    "exactly how a reported number was derived."
                ),
            },
            {
                "q": "How would you design monitoring/alerting for a batch data pipeline?",
                "a": (
                    "At minimum: did the job run and finish (freshness/completion checks), did row "
                    "counts land in an expected range (volume anomaly detection, catching a source "
                    "outage or a runaway duplicate job), and do key data-quality invariants hold "
                    "(no unexpected nulls in required fields, no duplicate primary keys, "
                    "referential integrity against dimension tables). Good monitoring alerts on the "
                    "data itself, not just job success/failure - a job can finish 'successfully' and "
                    "still silently load zero rows or garbage data if upstream changed underneath it."
                ),
            },
        ],
        "coding": [
            {
                "prompt": "Given raw_events(id, event_id, received_at), write a query that "
                "deduplicates redelivered webhook events by event_id, keeping only the "
                "earliest-received copy of each.",
                "solution": (
                    "SELECT id, event_id, received_at FROM (\n"
                    "  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY received_at ASC) AS rn\n"
                    "  FROM raw_events\n"
                    ") t\n"
                    "WHERE rn = 1;"
                ),
                "note": (
                    "PARTITION BY event_id restarts the row count for every distinct event_id; "
                    "ordering each partition by received_at ASC makes row 1 the earliest copy, so "
                    "filtering to rn = 1 keeps exactly one row per event_id with no GROUP BY (which "
                    "can't return non-aggregated columns like id cleanly) and no self-join."
                ),
            },
            {
                "prompt": "Given stream_events(id, event_time), write a query that only returns "
                "events safely before a watermark of 2026-01-02 00:00:00, leaving later "
                "(possibly-incomplete) events for the next run.",
                "solution": "SELECT id FROM stream_events WHERE event_time < '2026-01-02 00:00:00';",
                "note": (
                    "The watermark itself is just a WHERE boundary applied by whatever orchestrates "
                    "the run - the query doesn't need special syntax for it, the discipline is in "
                    "choosing when it's safe to treat everything before that boundary as complete."
                ),
            },
            {
                "prompt": "Given transactions(id, amount), write a query that flags rows failing a "
                "basic data-quality check (a negative amount) instead of silently dropping them.",
                "solution": "SELECT id, amount, (amount < 0) AS quarantine FROM transactions ORDER BY id;",
                "note": (
                    "Flagging in-place (or routing flagged rows to a separate quarantine table) keeps "
                    "every row visible and auditable - a pipeline that silently WHERE-filters out bad "
                    "rows instead makes a swallowed data-quality failure indistinguishable from the "
                    "data simply never having arrived."
                ),
            },
        ],
    },
]
