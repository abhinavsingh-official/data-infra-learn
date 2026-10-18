"""The "Lake Databases" track - data-lake fundamentals (schema-on-read,
columnar storage, partitioning, schema drift, dedup, medallion
architecture, small files, late arrivals, data skipping) taught via
small Postgres tables, paired with the real lake_phase capstone
(Spark/Delta at scale) the same way sql_databases_track pairs with
postgres_phase. Every example row/expected output was captured by
actually running these queries against Postgres, not hand-typed."""

LAKE_DATABASES_SKILL_TREE = {
    "paradigm": "lake-databases",
    "nodes": [
        {
            "id": "intro",
            "type": "intro",
            "title": "A data lake: cheap storage first, structure later",
            "body": (
                "A data lake stores raw files (JSON, CSV, Parquet) directly in cheap object "
                "storage, with no upfront schema enforced at write time - structure gets applied "
                "when something reads the data, not when it lands. That single inversion (schema-"
                "on-read instead of schema-on-write) is the root of everything else in this track: "
                "why columnar formats matter, why partitioning and partition pruning exist, why "
                "schema drift has to be handled at query time, and why a raw/bronze zone needs its "
                "own deduplication and lateness handling before anything trusts it. This track walks "
                "through the SQL consequence of each of those ideas on small, hand-sized data - the "
                "Lake capstone right after does the same thing for real, against real object storage "
                "and Spark at full scale."
            ),
        },
        {
            "id": "node_1_schema_on_read",
            "type": "skill",
            "title": "Schema-on-read: structure applied at query time, not write time",
            "teach": {
                "sql": (
                    "SELECT payload->>'user_id' AS user_id, payload->>'action' AS action\n"
                    "FROM raw_user_events;"
                ),
                "note": (
                    "A data warehouse enforces its schema before a row is ever written - a bad row "
                    "gets rejected at load time. A data lake does the opposite: it accepts whatever "
                    "shape a producer sends (here, modeled as a JSONB payload column) and defers "
                    "deciding what the data 'means' until a query actually reads it. That deferral is "
                    "schema-on-read's whole value proposition - new fields show up in the raw feed "
                    "immediately usable, with no schema migration standing in the way - and also its "
                    "whole cost: every reader has to independently agree on how to interpret the "
                    "payload, since there's no single enforced contract doing that for them."
                ),
                "steps": [
                    {
                        "body": "A warehouse checks a row's shape before it's written. A lake "
                        "accepts the row as-is and defers 'what does this mean' to query time - "
                        "that's schema-on-read."
                    },
                    {
                        "body": "Pull fields straight out of a JSON-shaped payload column:",
                        "sql": "SELECT payload->>'field_a' AS field_a\nFROM raw_events;",
                    },
                    {
                        "body": "Extract user_id and action from this raw event feed:",
                        "sql": "SELECT payload->>'user_id' AS user_id, payload->>'action' AS action\nFROM raw_user_events;",
                    },
                    {
                        "body": "Nothing about raw_user_events' table definition says what "
                        "'user_id' or 'action' mean, or even that every row has them - the ->> "
                        "operator just returns NULL if a key is missing. The schema lives in the "
                        "query, not the table."
                    },
                    {
                        "body": "This is also why a lake can ingest a brand-new field the instant "
                        "a producer starts sending it, with zero coordination: there's no table "
                        "definition to ALTER first. The tradeoff is that nothing catches a typo'd "
                        "key name either - payload->>'usr_id' silently returns NULL instead of "
                        "erroring, the same way a missing field would."
                    },
                    {
                        "body": "Schema-on-write and schema-on-read aren't a strict better/worse - "
                        "a warehouse's upfront enforcement is exactly right when every consumer "
                        "needs the same guaranteed shape; a lake's deferred enforcement is right "
                        "when producers evolve faster than any single shared schema could keep up "
                        "with."
                    },
                    {
                        "body": "Schema-on-read means the table makes no promises about shape - "
                        "every query decides for itself what to pull out. Try it yourself in the "
                        "Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Extract user_id and action from this raw JSON-shaped event feed.",
                "table_name": "raw_user_events",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "payload", "type": "jsonb"},
                ],
                "example_rows": [
                    {"id": 1, "payload": {"user_id": "u1", "action": "login"}},
                    {"id": 2, "payload": {"user_id": "u2", "action": "purchase", "amount": 42.50}},
                    {"id": 3, "payload": {"user_id": "u1", "action": "logout"}},
                ],
                "expected_output_rows": [
                    {"user_id": "u1", "action": "login"},
                    {"user_id": "u2", "action": "purchase"},
                    {"user_id": "u1", "action": "logout"},
                ],
            },
        },
        {
            "id": "node_2_columnar_storage",
            "type": "skill",
            "title": "Why columnar storage beats row storage for analytics",
            "teach": {
                "sql": "SELECT user_id, page_url FROM clickstream_wide;",
                "note": (
                    "A row-oriented format (CSV) stores every column of a row together on disk, so "
                    "reading even two columns means reading - and decompressing - the entire row, "
                    "every column of it, for every row. A columnar format (Parquet) stores each "
                    "column contiguously instead, so a query touching 2 columns out of 10 only reads "
                    "roughly a fifth of the data off disk. Nothing about this SELECT's syntax looks "
                    "special - the win is entirely about how much data physically has to be read to "
                    "answer it, which only shows up at real file-storage scale, not against an "
                    "in-memory Postgres table - but the query pattern itself (narrow column lists "
                    "against wide tables) is exactly what columnar storage is built to reward."
                ),
                "steps": [
                    {
                        "body": "clickstream_wide has 10 columns. This query only needs 2 of "
                        "them. How much data should reading it actually require?"
                    },
                    {
                        "body": "Select only the columns you need, not SELECT *:",
                        "sql": "SELECT col_a, col_b FROM wide_table;",
                    },
                    {
                        "body": "Return just user_id and page_url from this wide table:",
                        "sql": "SELECT user_id, page_url FROM clickstream_wide;",
                    },
                    {
                        "body": "In a row-oriented format (CSV), every column of a row sits "
                        "together on disk - reading 2 columns out of 10 still means reading all 10, "
                        "for every row. A columnar format (Parquet) stores each column contiguously, "
                        "so this same query only touches roughly a fifth of the data."
                    },
                    {
                        "body": "This is specifically an analytics-workload win, not a universal "
                        "one: an OLTP system that reads and writes one whole row at a time (fetch "
                        "order #4521, update its status) gains nothing from columnar storage and "
                        "loses write-amplification, since updating one field still means touching "
                        "every column file that row's data split across."
                    },
                    {
                        "body": "SELECT * defeats this advantage even on a Parquet lake - it "
                        "forces every column to be read regardless of storage format, so the habit "
                        "of naming only the columns a query actually needs isn't just style, it's "
                        "the entire mechanism columnar pruning depends on."
                    },
                    {
                        "body": "Columnar storage rewards queries that touch few columns across "
                        "many rows - exactly analytics' usual shape. Try it yourself in the "
                        "Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Return just user_id and page_url from this wide clickstream table - not every column.",
                "table_name": "clickstream_wide",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "user_id", "type": "text"},
                    {"column": "event_type", "type": "text"},
                    {"column": "country", "type": "text"},
                    {"column": "device", "type": "text"},
                    {"column": "browser", "type": "text"},
                    {"column": "os", "type": "text"},
                    {"column": "referrer", "type": "text"},
                    {"column": "session_id", "type": "text"},
                    {"column": "page_url", "type": "text"},
                ],
                "example_rows": [
                    {"id": 1, "user_id": "u1", "event_type": "click", "country": "US", "device": "mobile", "browser": "Chrome", "os": "iOS", "referrer": "google.com", "session_id": "s1", "page_url": "/home"},
                    {"id": 2, "user_id": "u2", "event_type": "view", "country": "IN", "device": "desktop", "browser": "Firefox", "os": "Linux", "referrer": "direct", "session_id": "s2", "page_url": "/pricing"},
                ],
                "expected_output_rows": [
                    {"user_id": "u1", "page_url": "/home"},
                    {"user_id": "u2", "page_url": "/pricing"},
                ],
            },
        },
        {
            "id": "node_3_partitioning",
            "type": "skill",
            "title": "Partitioning by date: filtering to one slice of the lake",
            "teach": {
                "sql": "SELECT id, user_id, event_type\nFROM raw_events_by_day\nWHERE event_date = '2026-02-02';",
                "note": (
                    "A real lake physically lays raw files out in date-named directories - "
                    "events/event_date=2026-02-01/, events/event_date=2026-02-02/, and so on - so "
                    "that a query for one day only has to open that one directory's files, not "
                    "every file the table has ever accumulated. event_date here is the Postgres "
                    "stand-in for that partition key: filtering on it is the same access pattern "
                    "as asking a real lake to read one partition directory instead of the whole "
                    "table."
                ),
                "steps": [
                    {
                        "body": "A lake's raw files physically live in date-named folders, one "
                        "folder per day - a query that only needs one day shouldn't have to touch "
                        "every folder the table has ever accumulated."
                    },
                    {
                        "body": "Filter on the partition column, exactly like any other WHERE:",
                        "sql": "SELECT id FROM events\nWHERE partition_date = '2026-01-01';",
                    },
                    {
                        "body": "Return every event from 2026-02-02 only:",
                        "sql": "SELECT id, user_id, event_type\nFROM raw_events_by_day\nWHERE event_date = '2026-02-02';",
                    },
                    {
                        "body": "event_date is the Postgres stand-in for a real lake's partition "
                        "key - filtering on it here is the same access pattern as asking a real "
                        "lake engine to open one partition's directory instead of the whole table."
                    },
                    {
                        "body": "Partitioning has a cost too: pick a key that's too fine-grained "
                        "(partition by exact timestamp instead of by day) and the lake ends up with "
                        "an enormous number of tiny partitions, each holding very little data - "
                        "which is exactly the small-file problem node 8 covers."
                    },
                    {
                        "body": "The partition key is usually chosen to match the column queries "
                        "filter on most often - a date column for time-series data, a tenant_id or "
                        "region for multi-tenant data - precisely so that the common-case query "
                        "gets to skip the most data."
                    },
                    {
                        "body": "Filtering on a partition column is how a query skips folders it "
                        "doesn't need instead of scanning the whole table. Try it yourself in the "
                        "Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Return every event from 2026-02-02 only.",
                "table_name": "raw_events_by_day",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "event_date", "type": "date"},
                    {"column": "user_id", "type": "text"},
                    {"column": "event_type", "type": "text"},
                ],
                "example_rows": [
                    {"id": 1, "event_date": "2026-02-01", "user_id": "u1", "event_type": "login"},
                    {"id": 2, "event_date": "2026-02-02", "user_id": "u2", "event_type": "purchase"},
                    {"id": 3, "event_date": "2026-02-02", "user_id": "u3", "event_type": "login"},
                    {"id": 4, "event_date": "2026-02-03", "user_id": "u1", "event_type": "logout"},
                ],
                "expected_output_rows": [
                    {"id": 2, "user_id": "u2", "event_type": "purchase"},
                    {"id": 3, "user_id": "u3", "event_type": "login"},
                ],
            },
        },
        {
            "id": "node_4_partition_pruning",
            "type": "skill",
            "title": "Partition pruning: a range that still skips most of the lake",
            "teach": {
                "sql": (
                    "SELECT id, amount\n"
                    "FROM sales_by_day\n"
                    "WHERE sale_date >= '2026-02-02' AND sale_date < '2026-02-05';"
                ),
                "note": (
                    "Partition pruning is the query planner's own job, not something you ask for "
                    "explicitly: given a WHERE clause on the partition column, it figures out which "
                    "partitions could possibly contain a match and skips opening the rest entirely, "
                    "whether that's one partition (node 3's exact match) or a contiguous range of "
                    "them, as here. The sale_date >= ... AND sale_date < ... range only needs "
                    "partitions 02-02 through 02-04 opened - 02-01 and 02-05 are never touched, not "
                    "because the engine checked their contents and found no matches, but because it "
                    "never had to look at them in the first place."
                ),
                "steps": [
                    {
                        "body": "A query doesn't have to match exactly one partition to benefit - "
                        "a date RANGE can still skip every partition outside it, without the "
                        "engine ever opening them."
                    },
                    {
                        "body": "A half-open range on the partition column prunes everything outside it:",
                        "sql": "SELECT id FROM events\nWHERE partition_date >= '2026-01-01' AND partition_date < '2026-01-04';",
                    },
                    {
                        "body": "Return sales strictly between 2026-02-02 and 2026-02-05:",
                        "sql": (
                            "SELECT id, amount\n"
                            "FROM sales_by_day\n"
                            "WHERE sale_date >= '2026-02-02' AND sale_date < '2026-02-05';"
                        ),
                    },
                    {
                        "body": "This range only needs the 02-02, 02-03, and 02-04 partitions "
                        "opened - 02-01 and 02-05 are never touched, not because the engine checked "
                        "their contents and found no matches, but because it never had to look at "
                        "them at all. That's the difference between pruning and filtering."
                    },
                    {
                        "body": "Partition pruning is purely about the WHERE clause's shape - it "
                        "has to reference the partition column directly with a comparison the "
                        "planner can reason about statically. Wrapping the partition column in a "
                        "function (WHERE EXTRACT(month FROM sale_date) = 2) usually defeats "
                        "pruning entirely, forcing every partition open to evaluate the function "
                        "row by row."
                    },
                    {
                        "body": "This is exactly why the SQL functions-on-filtered-columns gotcha "
                        "matters more on a lake than on a small OLTP table: on a lake, that mistake "
                        "is the difference between scanning megabytes and scanning terabytes."
                    },
                    {
                        "body": "A range on the partition column prunes every partition outside "
                        "it, without the engine ever opening them. Try it yourself in the Practice "
                        "tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Return sales strictly between 2026-02-02 and 2026-02-05 (inclusive of 02-02, exclusive of 02-05).",
                "table_name": "sales_by_day",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "sale_date", "type": "date"},
                    {"column": "amount", "type": "numeric"},
                ],
                "example_rows": [
                    {"id": 1, "sale_date": "2026-02-01", "amount": 100.00},
                    {"id": 2, "sale_date": "2026-02-02", "amount": 200.00},
                    {"id": 3, "sale_date": "2026-02-03", "amount": 300.00},
                    {"id": 4, "sale_date": "2026-02-05", "amount": 400.00},
                ],
                "expected_output_rows": [
                    {"id": 2, "amount": 200.00},
                    {"id": 3, "amount": 300.00},
                ],
            },
        },
        {
            "id": "node_5_schema_drift",
            "type": "skill",
            "title": "Schema drift: a renamed field, handled at read time",
            "teach": {
                "sql": (
                    "SELECT id, user_id, COALESCE(full_name_v2, customer_name_v1) AS customer_name\n"
                    "FROM raw_profile_events;"
                ),
                "note": (
                    "A lake has no migration step that rewrites old files when a producer renames a "
                    "field - older rows keep the old field name (customer_name_v1), newer rows "
                    "arrive with the new one (full_name_v2), and both shapes sit side by side in the "
                    "same raw table forever. COALESCE picks whichever one is actually populated on a "
                    "given row, which is the standard read-time fix for exactly this: reconcile the "
                    "drift in the query, because there's no single write-time schema to have fixed "
                    "it upstream."
                ),
                "steps": [
                    {
                        "body": "A producer renames a field partway through - old rows have "
                        "customer_name_v1, new rows have full_name_v2. Nobody rewrote the old "
                        "files, so both shapes coexist in the same table forever."
                    },
                    {
                        "body": "COALESCE picks whichever version of the field is populated:",
                        "sql": "SELECT id, COALESCE(new_col, old_col) AS value\nFROM raw_table;",
                    },
                    {
                        "body": "Return each row's name under whichever column actually has it:",
                        "sql": (
                            "SELECT id, user_id, COALESCE(full_name_v2, customer_name_v1) AS customer_name\n"
                            "FROM raw_profile_events;"
                        ),
                    },
                    {
                        "body": "There's no migration step rewriting the old rows to the new "
                        "shape - a lake just accumulates both field names side by side, and every "
                        "reader has to reconcile that drift itself, in the query, since there's no "
                        "single write-time schema to have fixed it upstream."
                    },
                    {
                        "body": "COALESCE works cleanly when the old and new fields are "
                        "fully exclusive (never both populated on the same row) - if a producer "
                        "briefly double-writes both during a rollout, COALESCE's left-to-right "
                        "preference needs to be deliberately chosen to prefer the newer field, or "
                        "a mid-rollout row with a stale old value would win over a fresh new one."
                    },
                    {
                        "body": "The other common shape of drift is a source that changes which "
                        "TABLE it writes to entirely, not just a column name - handled the same way "
                        "node 8 (conformed dimensions) handles two fact tables: UNION ALL the "
                        "differently-shaped sources together first, then apply one consistent "
                        "column list on top."
                    },
                    {
                        "body": "Schema drift gets fixed at read time with COALESCE (or a UNION of "
                        "differently-shaped sources), never by rewriting history. Try it yourself "
                        "in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Return each row's name under whichever column actually has it - full_name_v2 if present, otherwise customer_name_v1.",
                "table_name": "raw_profile_events",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "user_id", "type": "text"},
                    {"column": "customer_name_v1", "type": "text"},
                    {"column": "full_name_v2", "type": "text"},
                ],
                "example_rows": [
                    {"id": 1, "user_id": "u1", "customer_name_v1": "Alice", "full_name_v2": None},
                    {"id": 2, "user_id": "u2", "customer_name_v1": None, "full_name_v2": "Bob Smith"},
                ],
                "expected_output_rows": [
                    {"id": 1, "user_id": "u1", "customer_name": "Alice"},
                    {"id": 2, "user_id": "u2", "customer_name": "Bob Smith"},
                ],
            },
        },
        {
            "id": "node_6_dedupe_redelivery",
            "type": "skill",
            "title": "Deduplicating redelivered events in the raw zone",
            "teach": {
                "sql": (
                    "SELECT event_id, amount FROM (\n"
                    "  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY received_at) AS rn\n"
                    "  FROM raw_bronze_events\n"
                    ") t WHERE rn = 1;"
                ),
                "note": (
                    "At-least-once delivery is the normal contract for most event sources feeding a "
                    "lake's raw/bronze zone - a producer or network retry can land the exact same "
                    "event_id twice. The raw zone is expected to capture every delivery attempt "
                    "as-is (that's what 'raw' means), so dedup happens downstream, at read time: "
                    "ROW_NUMBER() PARTITION BY the natural event key, keep rn = 1, and every repeat "
                    "delivery of the same event collapses to the one copy that should count."
                ),
                "steps": [
                    {
                        "body": "Most event sources only promise at-least-once delivery - the same "
                        "event_id can legitimately arrive twice. A raw/bronze zone is supposed to "
                        "capture every delivery attempt exactly as it arrived, duplicates included."
                    },
                    {
                        "body": "Number each group of duplicates, keep only the first:",
                        "sql": "SELECT key, val FROM (\n  SELECT *, ROW_NUMBER() OVER (PARTITION BY key ORDER BY received_at) AS rn\n  FROM raw_events\n) t WHERE rn = 1;",
                    },
                    {
                        "body": "Collapse redelivered events down to one copy per event_id:",
                        "sql": (
                            "SELECT event_id, amount FROM (\n"
                            "  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY received_at) AS rn\n"
                            "  FROM raw_bronze_events\n"
                            ") t WHERE rn = 1;"
                        ),
                    },
                    {
                        "body": "ROW_NUMBER() PARTITION BY event_id ORDER BY received_at numbers "
                        "every redelivery of the same event starting at 1 - keeping only rn = 1 "
                        "collapses any number of repeats down to exactly one row per event_id, "
                        "deterministically (always the earliest-received copy)."
                    },
                    {
                        "body": "This dedup happens downstream of the raw zone on purpose, never "
                        "by rejecting the duplicate write itself - the raw zone's whole job is to "
                        "be a faithful, unopinionated record of every delivery attempt, so any "
                        "future question about 'how many times did this event actually get sent' "
                        "can still be answered from it."
                    },
                    {
                        "body": "Picking ORDER BY received_at (earliest wins) vs. ORDER BY "
                        "received_at DESC (latest wins) is a real decision, not a default - the "
                        "right choice depends on whether a later redelivery might carry corrected "
                        "data (latest should win) or is just a dumb retry of identical data (either "
                        "choice is equivalent, so earliest is the conventional default)."
                    },
                    {
                        "body": "Redelivered events are dedup'd downstream of the raw zone with "
                        "ROW_NUMBER PARTITION BY the natural key, never by rejecting the duplicate "
                        "at write time. Try it yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Collapse redelivered events down to one copy per event_id, keeping the earliest-received copy.",
                "table_name": "raw_bronze_events",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "event_id", "type": "text"},
                    {"column": "amount", "type": "numeric"},
                    {"column": "received_at", "type": "timestamptz"},
                ],
                "example_rows": [
                    {"id": 1, "event_id": "evt-1", "amount": 50.00, "received_at": "2026-01-01T10:00:00+00"},
                    {"id": 2, "event_id": "evt-1", "amount": 50.00, "received_at": "2026-01-01T10:00:05+00"},
                    {"id": 3, "event_id": "evt-2", "amount": 20.00, "received_at": "2026-01-01T11:00:00+00"},
                ],
                "expected_output_rows": [
                    {"event_id": "evt-1", "amount": 50.00},
                    {"event_id": "evt-2", "amount": 20.00},
                ],
            },
        },
        {
            "id": "node_7_medallion_bronze_silver",
            "type": "skill",
            "title": "Medallion architecture: bronze raw data cleaned into silver",
            "teach": {
                "sql": "SELECT DISTINCT id, LOWER(TRIM(status)) AS status, customer_name\nFROM bronze_orders;",
                "note": (
                    "The medallion pattern names progressively cleaner zones: bronze is raw data "
                    "exactly as it arrived (messy casing, stray whitespace, exact duplicates and "
                    "all), silver is that same data cleaned, deduplicated, and reshaped into "
                    "something queryable, and gold (not exercised here) is further aggregated for "
                    "a specific business purpose. This query is a bronze-to-silver transform in "
                    "miniature: TRIM and LOWER normalize the messy status field, and DISTINCT drops "
                    "an exact-duplicate row that arrived twice - none of which the bronze table "
                    "itself is required to have handled."
                ),
                "steps": [
                    {
                        "body": "Bronze, silver, gold: the medallion pattern names progressively "
                        "cleaner zones a lake's data passes through, bronze being raw and "
                        "unopinionated, gold being purpose-built for one business question."
                    },
                    {
                        "body": "Normalize messy text and drop exact duplicates in one pass:",
                        "sql": "SELECT DISTINCT id, LOWER(TRIM(messy_col)) AS clean_col\nFROM bronze_table;",
                    },
                    {
                        "body": "Clean up the status field and drop any exact duplicate rows:",
                        "sql": "SELECT DISTINCT id, LOWER(TRIM(status)) AS status, customer_name\nFROM bronze_orders;",
                    },
                    {
                        "body": "TRIM strips the stray leading/trailing whitespace a raw feed "
                        "often carries, LOWER normalizes inconsistent casing ('SHIPPED' vs. "
                        "'shipped'), and DISTINCT removes a row that arrived as an exact duplicate "
                        "- three small cleaning steps, none of which bronze itself was ever "
                        "required to have already done."
                    },
                    {
                        "body": "This is a genuinely different kind of dedup from node 6's: there, "
                        "ROW_NUMBER collapsed rows that shared a key but might carry DIFFERENT "
                        "payloads (a redelivery with a corrected value). Here, DISTINCT only drops "
                        "rows that are byte-for-byte IDENTICAL already - the right tool depends on "
                        "whether 'duplicate' means 'same key' or 'same everything'."
                    },
                    {
                        "body": "A real medallion pipeline usually materializes silver as its own "
                        "table (a scheduled job writes bronze_orders -> silver_orders), rather than "
                        "re-running this cleaning query from scratch on every read - so downstream "
                        "consumers query silver directly, already clean, without needing to know "
                        "any of bronze's quirks at all."
                    },
                    {
                        "body": "A bronze-to-silver transform cleans and dedups raw data into "
                        "something safe for downstream consumers to query directly. Try it "
                        "yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Clean up the status field (trim whitespace, lowercase it) and drop any exact duplicate rows.",
                "table_name": "bronze_orders",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "status", "type": "text"},
                    {"column": "customer_name", "type": "text"},
                ],
                "example_rows": [
                    {"id": 1, "status": "  SHIPPED ", "customer_name": "Alice"},
                    {"id": 2, "status": "pending", "customer_name": "Bob"},
                    {"id": 2, "status": "pending", "customer_name": "Bob"},
                ],
                "expected_output_rows": [
                    {"id": 1, "status": "shipped", "customer_name": "Alice"},
                    {"id": 2, "status": "pending", "customer_name": "Bob"},
                ],
            },
        },
        {
            "id": "node_8_small_file_compaction",
            "type": "skill",
            "title": "The small-file problem: compacting many fragments into fewer rows",
            "teach": {
                "sql": (
                    "SELECT partition_key, SUM(row_count) AS total_rows, COUNT(*) AS file_count\n"
                    "FROM small_file_fragments\n"
                    "GROUP BY partition_key;"
                ),
                "note": (
                    "Frequent small writes (a streaming job flushing every few seconds, say) leave "
                    "a lake partition full of many tiny files instead of a few well-sized ones - "
                    "each one cheap to write but collectively expensive to read, since opening a "
                    "file has fixed overhead regardless of how little data it holds. Compaction "
                    "merges many small files into fewer, larger ones with the same total data. This "
                    "query models the before/after bookkeeping: grouping file-level fragments by "
                    "partition and summing their row counts is exactly the accounting a compaction "
                    "job does to decide which partitions are worth compacting."
                ),
                "steps": [
                    {
                        "body": "A streaming job that flushes every few seconds leaves a lake "
                        "partition full of many tiny files - cheap to write one at a time, "
                        "expensive to read collectively, since opening each file has fixed "
                        "overhead no matter how little data it holds."
                    },
                    {
                        "body": "Group small fragments by partition and total them up:",
                        "sql": "SELECT partition_key, SUM(row_count), COUNT(*)\nFROM fragments\nGROUP BY partition_key;",
                    },
                    {
                        "body": "Total rows and file count per partition, across these fragments:",
                        "sql": (
                            "SELECT partition_key, SUM(row_count) AS total_rows, COUNT(*) AS file_count\n"
                            "FROM small_file_fragments\n"
                            "GROUP BY partition_key;"
                        ),
                    },
                    {
                        "body": "This is exactly the accounting a compaction job runs before "
                        "doing anything: find partitions with a high file_count relative to their "
                        "total_rows (lots of tiny files), and rewrite just those as fewer, larger "
                        "files holding the same total_rows - compaction changes file layout, never "
                        "the logical data itself."
                    },
                    {
                        "body": "The small-file problem compounds with over-eager partitioning "
                        "(node 3's gotcha): partitioning by too fine a key multiplies the number of "
                        "directories, and a streaming write into each one multiplies the number of "
                        "small files inside each directory - the two problems feed each other."
                    },
                    {
                        "body": "Compaction is a maintenance operation run periodically (hourly, "
                        "nightly), not something that happens automatically on every write - "
                        "running it too rarely lets small files pile up and hurt read performance; "
                        "running it too often wastes compute rewriting data that was barely "
                        "fragmented to begin with."
                    },
                    {
                        "body": "Compaction trades many small files for fewer large ones holding "
                        "the identical total data. Try it yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Total the row_count and count the files for each partition_key.",
                "table_name": "small_file_fragments",
                "schema": [
                    {"column": "file_id", "type": "bigint"},
                    {"column": "partition_key", "type": "text"},
                    {"column": "row_count", "type": "bigint"},
                ],
                "example_rows": [
                    {"file_id": 1, "partition_key": "2026-02-01", "row_count": 10},
                    {"file_id": 2, "partition_key": "2026-02-01", "row_count": 5},
                    {"file_id": 3, "partition_key": "2026-02-01", "row_count": 7},
                    {"file_id": 4, "partition_key": "2026-02-02", "row_count": 20},
                ],
                "expected_output_rows": [
                    {"partition_key": "2026-02-01", "total_rows": 22, "file_count": 3},
                    {"partition_key": "2026-02-02", "total_rows": 20, "file_count": 1},
                ],
            },
        },
        {
            "id": "node_9_late_arriving_data",
            "type": "skill",
            "title": "Late-arriving data: catching events that showed up out of order",
            "teach": {
                "sql": (
                    "SELECT id, value\n"
                    "FROM raw_zone_events\n"
                    "WHERE ingested_at - event_time > interval '1 day';"
                ),
                "note": (
                    "event_time is when something actually happened; ingested_at is when the lake "
                    "actually received it - a mobile device offline for two days, or a retried "
                    "upload, can make those two timestamps diverge significantly. Comparing them "
                    "directly is how a raw zone flags late arrivals: any row where ingested_at is "
                    "far past event_time showed up out of order, which matters because a downstream "
                    "job that already ran and closed out 'yesterday's' results before this row "
                    "arrived would silently miss it unless something is watching for exactly this "
                    "gap."
                ),
                "steps": [
                    {
                        "body": "event_time is when something actually happened. ingested_at is "
                        "when the lake actually received it. An offline device or a retried upload "
                        "can make those drift far apart."
                    },
                    {
                        "body": "Compare the two timestamps to catch what arrived late:",
                        "sql": "SELECT id FROM events\nWHERE ingested_at - event_time > interval '1 day';",
                    },
                    {
                        "body": "Find every event whose arrival lagged its own event_time by over a day:",
                        "sql": (
                            "SELECT id, value\n"
                            "FROM raw_zone_events\n"
                            "WHERE ingested_at - event_time > interval '1 day';"
                        ),
                    },
                    {
                        "body": "Any row where ingested_at is far past event_time showed up out "
                        "of order - which matters because a downstream job that already closed out "
                        "'yesterday's' results before this row arrived would silently miss it "
                        "entirely unless something is explicitly watching for this gap."
                    },
                    {
                        "body": "This is the same event_time vs. ingested_at distinction a "
                        "watermark relies on (a watermark declares 'I will no longer wait for data "
                        "older than this event_time') - the threshold here (1 day) is effectively "
                        "asking how late is too late before a row needs special handling instead of "
                        "silently landing in whatever batch happens to be running when it arrives."
                    },
                    {
                        "body": "The usual fix isn't to reject late data - it's to reprocess "
                        "whichever downstream result already closed out before the late row "
                        "arrived (the same backfill/reprocessing concern pipeline_architecture's "
                        "own track covers), since the late row is still real data that deserves to "
                        "be counted somewhere."
                    },
                    {
                        "body": "Late-arriving data is caught by comparing when something "
                        "happened against when it was actually received. Try it yourself in the "
                        "Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Find every event whose ingested_at lagged its event_time by more than 1 day.",
                "table_name": "raw_zone_events",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "event_time", "type": "timestamptz"},
                    {"column": "ingested_at", "type": "timestamptz"},
                    {"column": "value", "type": "numeric"},
                ],
                "example_rows": [
                    {"id": 1, "event_time": "2026-01-01T10:00:00+00", "ingested_at": "2026-01-01T10:05:00+00", "value": 10.00},
                    {"id": 2, "event_time": "2026-01-01T09:00:00+00", "ingested_at": "2026-01-03T09:00:00+00", "value": 20.00},
                    {"id": 3, "event_time": "2026-01-02T08:00:00+00", "ingested_at": "2026-01-04T08:30:00+00", "value": 30.00},
                ],
                "expected_output_rows": [
                    {"id": 2, "value": 20.00},
                    {"id": 3, "value": 30.00},
                ],
            },
        },
        {
            "id": "node_10_data_skipping",
            "type": "skill",
            "title": "Data skipping: a WHERE clause file-level stats can exploit",
            "teach": {
                "sql": "SELECT id, chunk_id, amount\nFROM order_amounts\nWHERE amount > 1000;",
                "note": (
                    "A real lake file format keeps per-file (or per-chunk) metadata - the min and "
                    "max value of each column, written once when the file is created. Given WHERE "
                    "amount > 1000, the engine can check a file's own max(amount) against 1000 "
                    "before ever opening the file: if the file's max is below 1000, nothing inside "
                    "it can possibly match, so the whole file is skipped unread. This WHERE clause "
                    "is written exactly to be exploitable that way - a direct range comparison on a "
                    "single column, the simplest case data skipping is built for."
                ),
                "steps": [
                    {
                        "body": "A real lake file keeps per-file metadata - the min and max value "
                        "of each column, written once when the file is created."
                    },
                    {
                        "body": "A plain range filter is exactly what min/max stats can exploit:",
                        "sql": "SELECT id FROM table\nWHERE amount > 1000;",
                    },
                    {
                        "body": "Return every order over 1000, with its chunk_id:",
                        "sql": "SELECT id, chunk_id, amount\nFROM order_amounts\nWHERE amount > 1000;",
                    },
                    {
                        "body": "Given this WHERE clause, the engine can check a file's own "
                        "max(amount) against 1000 before ever opening the file - if max(amount) is "
                        "below 1000, nothing inside that file can match, so it's skipped unread, "
                        "exactly like a whole partition is skipped in node 3, just at the "
                        "individual-file level instead."
                    },
                    {
                        "body": "This only works because the filter is a direct comparison "
                        "against a plain column - the same gotcha as pruning (node 4) applies here "
                        "too: wrapping amount in a function or expression (WHERE amount * 1.1 > "
                        "1000) hides the comparison from the stats check, forcing every file open "
                        "regardless of its min/max."
                    },
                    {
                        "body": "Data skipping is strongest when a column's values cluster well "
                        "within files - if every file happens to contain a nearly identical spread "
                        "of amounts (every file has some values above and below 1000), the min/max "
                        "check can't rule any file out, even though the stats exist. This is "
                        "exactly the problem Z-ordering (covered in the Lakehouse track) is built "
                        "to fix, by physically clustering correlated values together before stats "
                        "are written."
                    },
                    {
                        "body": "A plain range comparison on an unwrapped column is what file-"
                        "level min/max stats are built to skip past entirely. Try it yourself in "
                        "the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Return every order over 1000, with its chunk_id.",
                "table_name": "order_amounts",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "chunk_id", "type": "bigint"},
                    {"column": "amount", "type": "numeric"},
                ],
                "example_rows": [
                    {"id": 1, "chunk_id": 1, "amount": 50.00},
                    {"id": 2, "chunk_id": 1, "amount": 80.00},
                    {"id": 3, "chunk_id": 2, "amount": 1500.00},
                    {"id": 4, "chunk_id": 2, "amount": 2000.00},
                ],
                "expected_output_rows": [
                    {"id": 3, "chunk_id": 2, "amount": 1500.00},
                    {"id": 4, "chunk_id": 2, "amount": 2000.00},
                ],
            },
        },
        {
            "id": "review",
            "type": "review",
            "title": "Review: schema-on-read, columnar storage, partitioning, drift, dedup, medallion, compaction, lateness, data skipping",
            "prompt": (
                "A quick recap of the schema-on-read lake's own mechanics in SQL form before moving "
                "into the Lake capstone, which builds this same bronze-zone pipeline for real - "
                "against the actual fintech feed, on real object storage and Spark, at full scale."
            ),
        },
    ],
}
