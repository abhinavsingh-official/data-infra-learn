"""Module 9's exercise description. Content, not logic - same pattern as
the other phases' task_content modules."""

LAKE_PHASE_TASK = {
    "title": "Partition the raw feed as Parquet, then read it back schema-on-read",
    "summary": (
        "The same raw transaction feed from the relational phase - public.raw_transaction_events - "
        "but this time you own the storage layer yourself: write it out as partitioned Parquet "
        "files, then build clean_transactions by reading those files back and interpreting each "
        "row's payload AT READ TIME, not at write time. That's the actual difference between a "
        "lake and a warehouse: schema-on-read instead of schema-on-write."
    ),
    "source": "pg.raw_transaction_events - attached automatically, same raw JSONB feed as the relational phase.",
    "your_output_directory": (
        "A real, absolute local directory reserved just for this session - given back to you as "
        "output_dir when you create a session. Use it literally in your COPY TO statement."
    ),
    "workflow": [
        "1. Write: COPY the raw feed into your output directory as Parquet, PARTITION_BY a date "
        "derived from received_at - keep payload as a raw string/JSON column, don't flatten its "
        "inner fields into separate Parquet columns (that would just move schema-on-write "
        "somewhere else, not avoid it).",
        "2. Read: build clean_transactions from read_parquet(your_output_dir + '/**/*.parquet', "
        "hive_partitioning=true, union_by_name=true) - parse payload's JSON at query time and "
        "handle every edge case (nulls, duplicates, late arrivals, schema drift, malformed IDs/dates).",
        "3. Grade with POST /lake-phase/sessions/{id}/grade.",
    ],
    "required_output": {
        "table": "clean_transactions",
        "columns": {
            "event_id": "text, unique, not null",
            "amount": "numeric, not null",
            "merchant": "text",
            "currency": "text",
            "event_timestamp": "timestamptz",
        },
    },
    "hints": [
        "DuckDB's -> operator binds looser than IS NOT NULL - `payload->'amount' IS NOT NULL` "
        "parses as `payload -> ('amount' IS NOT NULL)` and fails to bind. Parenthesize: "
        "(payload->'amount') IS NOT NULL.",
        "DuckDB's ::TIMESTAMPTZ cast is strict about format and throws on the ambiguous regional "
        "date strings this feed contains - use TRY_CAST(... AS TIMESTAMPTZ), not a bare cast, "
        "the same way you'd use TRY_CAST for the same fault type anywhere else.",
        "A single COPY TO with no LIMIT/WHERE and PARTITION_BY on a date column is enough - you "
        "don't need to loop day-by-day yourself.",
    ],
    "dataset_stats": [
        {"label": "Raw feed rows", "value": "51,495", "hint": "pg.raw_transaction_events"},
        {"label": "Injected faults", "value": "~7,753", "hint": "roughly 15% of rows carry an edge case"},
        {"label": "Known-good result size", "value": "49,246 rows", "hint": "clean_transactions, once every edge case is handled"},
        {"label": "Partition granularity", "value": "Daily", "hint": "PARTITION_BY a date derived from received_at"},
    ],
    "starter_sql": (
        "-- 1. Write: partition the raw feed out as Parquet, payload untouched:\n"
        "-- COPY (\n"
        "--   SELECT id, received_at, source_delivery_id, payload,\n"
        "--          received_at::DATE AS event_date\n"
        "--   FROM pg.raw_transaction_events\n"
        "-- ) TO '<your output directory>' (FORMAT PARQUET, PARTITION_BY (event_date));\n\n"
        "-- 2. Read: parse payload back out at query time.\n"
        "SELECT id, received_at, payload\n"
        "FROM read_parquet('<your output directory>/**/*.parquet', hive_partitioning=true, union_by_name=true)\n"
        "LIMIT 20;\n"
    ),
    "reference_solution": {
        "sql": (
            "COPY (\n"
            "  SELECT id, received_at, source_delivery_id, payload,\n"
            "         received_at::DATE AS event_date\n"
            "  FROM pg.raw_transaction_events\n"
            ") TO '<your output directory>' (FORMAT PARQUET, PARTITION_BY (event_date));\n\n"
            "CREATE TABLE clean_transactions AS\n"
            "WITH raw AS (\n"
            "  SELECT id, received_at, payload::JSON AS payload\n"
            "  FROM read_parquet('<your output directory>/**/*.parquet', hive_partitioning=true, union_by_name=true)\n"
            "),\n"
            "normalized AS (\n"
            "  SELECT\n"
            "    COALESCE(payload->>'event_id', payload->>'id') AS event_id,\n"
            "    COALESCE(payload->>'merchant', payload->>'merchant_name') AS merchant,\n"
            "    payload->>'currency' AS currency,\n"
            "    CAST((payload->>'amount')::VARCHAR AS DOUBLE) AS amount,\n"
            "    TRY_CAST(payload->>'event_timestamp' AS TIMESTAMPTZ) AS event_timestamp,\n"
            "    received_at,\n"
            "    row_number() OVER (\n"
            "      PARTITION BY COALESCE(payload->>'event_id', payload->>'id')\n"
            "      ORDER BY received_at DESC\n"
            "    ) AS rn\n"
            "  FROM raw\n"
            "  WHERE (payload->'amount') IS NOT NULL AND ((payload->'merchant') IS NOT NULL OR (payload->'merchant_name') IS NOT NULL)\n"
            ")\n"
            "SELECT event_id, amount, merchant, currency, event_timestamp\n"
            "FROM normalized\n"
            "WHERE rn = 1\n"
            "  AND event_timestamp >= received_at - INTERVAL '48 hours';\n"
        ),
        "note": (
            "The write step keeps payload as a single raw column - flattening its inner fields into "
            "separate Parquet columns at write time would just move schema-on-write somewhere else. "
            "TRY_CAST (not a bare cast) handles the ambiguous regional date strings; the row_number() "
            "dedup and 48-hour watermark filter are the same logic as the relational phase's reference "
            "solution, just run against files instead of a live table. Excel-style ID corruption still "
            "needs its own repair step before this query."
        ),
        "steps": [
            {
                "title": "1. Write once, then read back assuming the feed is clean",
                "sql": (
                    "COPY (\n"
                    "  SELECT id, received_at, source_delivery_id, payload,\n"
                    "         received_at::DATE AS event_date\n"
                    "  FROM pg.raw_transaction_events\n"
                    ") TO '<your output directory>' (FORMAT PARQUET, PARTITION_BY (event_date));\n\n"
                    "CREATE TABLE clean_transactions AS\n"
                    "SELECT\n"
                    "  payload::JSON->>'event_id' AS event_id,\n"
                    "  (payload::JSON->>'amount')::DOUBLE AS amount,\n"
                    "  payload::JSON->>'merchant' AS merchant,\n"
                    "  payload::JSON->>'currency' AS currency,\n"
                    "  (payload::JSON->>'event_timestamp')::TIMESTAMPTZ AS event_timestamp\n"
                    "FROM read_parquet('<your output directory>/**/*.parquet', hive_partitioning=true, union_by_name=true);\n"
                ),
                "note": (
                    "The write half is already correct - payload stays untouched, partitioned only by a "
                    "derived date column. The read half is what's naive: a bare ::TIMESTAMPTZ cast throws "
                    "on this feed's ambiguous regional date strings, 'merchant' alone misses the renamed "
                    "field, and every redelivery and late arrival is read back as if it were a distinct, "
                    "on-time row."
                ),
            },
            {
                "title": "2. + absorb renamed fields and skip rows missing a required one",
                "sql": (
                    "CREATE TABLE clean_transactions AS\n"
                    "WITH raw AS (\n"
                    "  SELECT id, received_at, payload::JSON AS payload\n"
                    "  FROM read_parquet('<your output directory>/**/*.parquet', hive_partitioning=true, union_by_name=true)\n"
                    ")\n"
                    "SELECT\n"
                    "  COALESCE(payload->>'event_id', payload->>'id') AS event_id,\n"
                    "  COALESCE(payload->>'merchant', payload->>'merchant_name') AS merchant,\n"
                    "  payload->>'currency' AS currency,\n"
                    "  CAST((payload->>'amount')::VARCHAR AS DOUBLE) AS amount,\n"
                    "  (payload->>'event_timestamp')::TIMESTAMPTZ AS event_timestamp\n"
                    "FROM raw\n"
                    "WHERE (payload->'amount') IS NOT NULL AND ((payload->'merchant') IS NOT NULL OR (payload->'merchant_name') IS NOT NULL);\n"
                ),
                "note": (
                    "Same COALESCE-plus-WHERE idea as the relational phase, with one DuckDB-specific catch: "
                    "the -> operator binds looser than IS NOT NULL, so `payload->'amount' IS NOT NULL` "
                    "silently misparses as `payload -> ('amount' IS NOT NULL)` - the parentheses around "
                    "each (payload->'field') are load-bearing here, not stylistic."
                ),
            },
            {
                "title": "3. + dedupe redelivered events",
                "sql": (
                    "-- add to the raw/normalized CTE from step 2:\n"
                    "row_number() OVER (\n"
                    "  PARTITION BY COALESCE(payload->>'event_id', payload->>'id')\n"
                    "  ORDER BY received_at DESC\n"
                    ") AS rn\n"
                    "-- ... then filter the final SELECT to WHERE rn = 1\n"
                ),
                "note": (
                    "Reading from files instead of a live table changes nothing about redeliveries - the "
                    "same event_id can still appear multiple times across partitions. row_number() over "
                    "the business event_id, keeping the most recently received copy, is identical logic to "
                    "the relational phase, just evaluated at read time over Parquet instead of a table."
                ),
            },
            {
                "title": "4. + drop arrivals past the 48-hour watermark",
                "sql": (
                    "-- same normalized CTE as step 3, plus one more filter on the final SELECT:\n"
                    "WHERE rn = 1\n"
                    "  AND event_timestamp >= received_at - INTERVAL '48 hours';\n"
                ),
                "note": (
                    "Still the same watermark rule as the relational phase - compare each event's own "
                    "event_timestamp against received_at, not against 'now'. Schema-on-read doesn't change "
                    "what counts as late, only when the check happens."
                ),
            },
            {
                "title": "5. Final: + TRY_CAST instead of a bare cast for the ambiguous date strings",
                "sql": (
                    "COPY (\n"
                    "  SELECT id, received_at, source_delivery_id, payload,\n"
                    "         received_at::DATE AS event_date\n"
                    "  FROM pg.raw_transaction_events\n"
                    ") TO '<your output directory>' (FORMAT PARQUET, PARTITION_BY (event_date));\n\n"
                    "CREATE TABLE clean_transactions AS\n"
                    "WITH raw AS (\n"
                    "  SELECT id, received_at, payload::JSON AS payload\n"
                    "  FROM read_parquet('<your output directory>/**/*.parquet', hive_partitioning=true, union_by_name=true)\n"
                    "),\n"
                    "normalized AS (\n"
                    "  SELECT\n"
                    "    COALESCE(payload->>'event_id', payload->>'id') AS event_id,\n"
                    "    COALESCE(payload->>'merchant', payload->>'merchant_name') AS merchant,\n"
                    "    payload->>'currency' AS currency,\n"
                    "    CAST((payload->>'amount')::VARCHAR AS DOUBLE) AS amount,\n"
                    "    TRY_CAST(payload->>'event_timestamp' AS TIMESTAMPTZ) AS event_timestamp,\n"
                    "    received_at,\n"
                    "    row_number() OVER (\n"
                    "      PARTITION BY COALESCE(payload->>'event_id', payload->>'id')\n"
                    "      ORDER BY received_at DESC\n"
                    "    ) AS rn\n"
                    "  FROM raw\n"
                    "  WHERE (payload->'amount') IS NOT NULL AND ((payload->'merchant') IS NOT NULL OR (payload->'merchant_name') IS NOT NULL)\n"
                    ")\n"
                    "SELECT event_id, amount, merchant, currency, event_timestamp\n"
                    "FROM normalized\n"
                    "WHERE rn = 1\n"
                    "  AND event_timestamp >= received_at - INTERVAL '48 hours';\n"
                ),
                "note": (
                    "The last wrinkle: DuckDB's ::TIMESTAMPTZ cast is strict about format and throws on "
                    "this feed's ambiguous regional date strings. TRY_CAST turns that hard failure into a "
                    "null instead, so one malformed date doesn't take down the whole read. This matches the "
                    "top-level solution above - Excel-style ID corruption still needs its own repair step "
                    "before this query, left to you."
                ),
            },
        ],
    },
}
