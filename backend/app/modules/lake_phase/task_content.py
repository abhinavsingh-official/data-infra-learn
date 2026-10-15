"""Module 19 rewrite of Module 9's exercise description for PySpark/Spark
SQL instead of DuckDB (ARCHITECTURE_DECISIONS.md §3.1). Real content
changes, verified by actually running every statement against a real
session first (see MODULE_19_PLAN.md):
- No more `pg.`-qualified source table - plain unqualified
  raw_transaction_events, same reasoning as the warehouse phase.
- DuckDB's single `COPY (...) TO '<dir>' (FORMAT PARQUET, PARTITION_BY
  (...))` statement becomes `CREATE TABLE ... USING PARQUET PARTITIONED
  BY (...) LOCATION '<dir>' AS SELECT ...` - still one statement, still
  writes real Hive-partitioned Parquet files to the same real directory.
- DuckDB's `read_parquet('<dir>/**/*.parquet', hive_partitioning=true,
  union_by_name=true)` becomes Spark SQL's path-based table reference,
  `` parquet.`<dir>` `` - confirmed directly that Spark auto-discovers the
  Hive partition column from the directory names, same as DuckDB's
  hive_partitioning=true did.
- DuckDB's `payload::JSON->>'field'` becomes Spark SQL's
  `get_json_object(payload, '$.field')` - Spark has no bare `->`/`->>`
  JSON operators or a `::JSON` cast; this is its real equivalent.
- DuckDB has no distinct TIMESTAMPTZ type to TRY_CAST into - Spark's
  plain TIMESTAMP already carries timezone behavior at the session level,
  so this content uses `TRY_CAST(... AS TIMESTAMP)` for the normal ISO
  case.
- The ambiguous-date fault (`malformed_ambiguous_date`) isn't actually
  recoverable by TRY_CAST alone on this engine - confirmed directly that
  Spark's TRY_CAST rejects the fault's real DD/MM/YYYY-only string
  outright (no time component, slash-separated - not an ISO format at
  all), unlike DuckDB's more permissive cast. The real fix needs an
  explicit format: `COALESCE(TRY_CAST(ts AS TIMESTAMP), try_to_timestamp(ts,
  'dd/MM/yyyy'))` - try the normal ISO parse first, fall back to the
  known ambiguous-date shape only when that fails."""

LAKE_PHASE_TASK = {
    "title": "Partition the raw feed as Parquet, then read it back schema-on-read",
    "summary": (
        "The same raw transaction feed from the relational phase - raw_transaction_events - "
        "but this time you own the storage layer yourself: write it out as partitioned Parquet "
        "files, then build clean_transactions by reading those files back and interpreting each "
        "row's payload AT READ TIME, not at write time. That's the actual difference between a "
        "lake and a warehouse: schema-on-read instead of schema-on-write."
    ),
    "source": "raw_transaction_events - a live, read-only temp view, same raw JSONB-as-string feed as the relational phase.",
    "your_output_directory": (
        "A real, absolute local directory reserved just for this session - given back to you as "
        "output_dir when you create a session. Use it literally in your CREATE TABLE ... LOCATION "
        "and your parquet.`<dir>` reads."
    ),
    "workflow": [
        "1. Write: CREATE TABLE ... USING PARQUET PARTITIONED BY a date derived from received_at, "
        "LOCATION your output directory, AS SELECT from the raw feed - keep payload as a raw "
        "string column, don't flatten its inner fields into separate Parquet columns (that would "
        "just move schema-on-write somewhere else, not avoid it).",
        "2. Read: build clean_transactions by querying parquet.`your_output_dir` directly - parse "
        "payload's JSON at query time with get_json_object(...) and handle every edge case (nulls, "
        "duplicates, late arrivals, schema drift, malformed IDs/dates).",
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
        "Spark SQL has no bare -> / ->> JSON operators the way Postgres/DuckDB do - use "
        "get_json_object(payload, '$.field') to pull a field out of the raw JSON string at read "
        "time.",
        "TRY_CAST(... AS TIMESTAMP), not a bare CAST, avoids crashing on the ambiguous regional date "
        "strings this feed contains - but TRY_CAST alone just silently nulls them out, since it only "
        "recognizes ISO-shaped timestamps and this fault's string is a bare DD/MM/YYYY date. Actually "
        "recovering it needs an explicit fallback format: COALESCE(TRY_CAST(ts AS TIMESTAMP), "
        "try_to_timestamp(ts, 'dd/MM/yyyy')).",
        "A single CREATE TABLE ... PARTITIONED BY (...) AS SELECT with no LIMIT/WHERE is enough - "
        "you don't need to loop day-by-day yourself.",
    ],
    "dataset_stats": [
        {"label": "Raw feed rows", "value": "51,495", "hint": "raw_transaction_events"},
        {"label": "Injected faults", "value": "~7,753", "hint": "roughly 15% of rows carry an edge case"},
        {"label": "Known-good result size", "value": "47,755 rows", "hint": "clean_transactions, once every edge case is handled (late arrivals kept, not dropped)"},
        {"label": "Partition granularity", "value": "Daily", "hint": "PARTITIONED BY a date derived from received_at"},
    ],
    "starter_sql": (
        "-- 1. Write: partition the raw feed out as Parquet, payload untouched:\n"
        "-- CREATE TABLE lake_output USING PARQUET PARTITIONED BY (event_date)\n"
        "-- LOCATION '<your output directory>' AS\n"
        "-- SELECT id, received_at, source_delivery_id, payload,\n"
        "--        CAST(received_at AS DATE) AS event_date\n"
        "-- FROM raw_transaction_events;\n\n"
        "-- 2. Read: parse payload back out at query time.\n"
        "SELECT id, received_at, payload\n"
        "FROM parquet.`<your output directory>`\n"
        "LIMIT 20;\n"
    ),
    "reference_solution": {
        "sql": (
            "CREATE TABLE lake_output USING PARQUET PARTITIONED BY (event_date) LOCATION '<your output directory>' AS\n"
            "SELECT id, received_at, source_delivery_id, payload,\n"
            "       CAST(received_at AS DATE) AS event_date\n"
            "FROM raw_transaction_events;\n\n"
            "CREATE TABLE clean_transactions USING DELTA AS\n"
            "WITH raw AS (\n"
            "  SELECT id, received_at, payload\n"
            "  FROM parquet.`<your output directory>`\n"
            "),\n"
            "normalized AS (\n"
            "  SELECT\n"
            "    COALESCE(get_json_object(payload, '$.event_id'), get_json_object(payload, '$.id')) AS event_id,\n"
            "    COALESCE(get_json_object(payload, '$.merchant'), get_json_object(payload, '$.merchant_name')) AS merchant,\n"
            "    get_json_object(payload, '$.currency') AS currency,\n"
            "    CAST(get_json_object(payload, '$.amount') AS DOUBLE) AS amount,\n"
            "    COALESCE(TRY_CAST(get_json_object(payload, '$.timestamp') AS TIMESTAMP), try_to_timestamp(get_json_object(payload, '$.timestamp'), 'dd/MM/yyyy')) AS event_timestamp,\n"
            "    received_at,\n"
            "    row_number() OVER (\n"
            "      PARTITION BY COALESCE(get_json_object(payload, '$.event_id'), get_json_object(payload, '$.id'))\n"
            "      ORDER BY received_at DESC\n"
            "    ) AS rn\n"
            "  FROM raw\n"
            "  WHERE get_json_object(payload, '$.amount') IS NOT NULL\n"
            "    AND (get_json_object(payload, '$.merchant') IS NOT NULL OR get_json_object(payload, '$.merchant_name') IS NOT NULL)\n"
            "    AND get_json_object(payload, '$.currency') IS NOT NULL\n"
            "    AND get_json_object(payload, '$.timestamp') IS NOT NULL\n"
            ")\n"
            "SELECT event_id, amount, merchant, currency, event_timestamp\n"
            "FROM normalized\n"
            "WHERE rn = 1;\n"
        ),
        "note": (
            "The write step keeps payload as a single raw string column - flattening its inner fields "
            "into separate Parquet columns at write time would just move schema-on-write somewhere "
            "else. get_json_object(...) is Spark SQL's equivalent of Postgres/DuckDB's ->/->> JSON "
            "operators - there's no bare operator form here. The ambiguous regional date strings need "
            "more than a bare TRY_CAST on this engine - Spark's TRY_CAST only recognizes ISO-shaped "
            "timestamps, so the fault's real DD/MM/YYYY-only string needs an explicit fallback format "
            "(try_to_timestamp(ts, 'dd/MM/yyyy')) tried after the normal ISO parse fails; the row_number() "
            "dedup is the same logic as the relational phase's reference solution, just run against "
            "files instead of a live table - late arrivals (past the 48-hour watermark) stay in, same "
            "reasoning as the relational phase: late isn't invalid, and a load that scans the whole "
            "partitioned output rather than a rolling time window naturally keeps them. Excel-style ID corruption still needs its own repair step before "
            "this query. clean_transactions is USING DELTA here (not required by this exercise's own "
            "logic, but consistent with every other managed table this platform creates - see "
            "app.core.spark_sessions's module docstring on why a bare CREATE TABLE AS SELECT doesn't "
            "work at all without an explicit format)."
        ),
        "steps": [
            {
                "title": "1. Write once, then read back assuming the feed is clean",
                "sql": (
                    "CREATE TABLE lake_output USING PARQUET PARTITIONED BY (event_date) LOCATION '<your output directory>' AS\n"
                    "SELECT id, received_at, source_delivery_id, payload,\n"
                    "       CAST(received_at AS DATE) AS event_date\n"
                    "FROM raw_transaction_events;\n\n"
                    "CREATE TABLE clean_transactions USING DELTA AS\n"
                    "SELECT\n"
                    "  get_json_object(payload, '$.event_id') AS event_id,\n"
                    "  CAST(get_json_object(payload, '$.amount') AS DOUBLE) AS amount,\n"
                    "  get_json_object(payload, '$.merchant') AS merchant,\n"
                    "  get_json_object(payload, '$.currency') AS currency,\n"
                    "  CAST(get_json_object(payload, '$.timestamp') AS TIMESTAMP) AS event_timestamp\n"
                    "FROM parquet.`<your output directory>`;\n"
                ),
                "note": (
                    "The write half is already correct - payload stays untouched, partitioned only by a "
                    "derived date column. The read half is what's naive: a bare CAST throws on this "
                    "feed's ambiguous regional date strings, 'merchant' alone misses the renamed field, "
                    "and every redelivery and late arrival is read back as if it were a distinct, "
                    "on-time row."
                ),
            },
            {
                "title": "2. + absorb renamed fields and skip rows missing a required one",
                "sql": (
                    "CREATE TABLE clean_transactions USING DELTA AS\n"
                    "WITH raw AS (\n"
                    "  SELECT id, received_at, payload FROM parquet.`<your output directory>`\n"
                    ")\n"
                    "SELECT\n"
                    "  COALESCE(get_json_object(payload, '$.event_id'), get_json_object(payload, '$.id')) AS event_id,\n"
                    "  COALESCE(get_json_object(payload, '$.merchant'), get_json_object(payload, '$.merchant_name')) AS merchant,\n"
                    "  get_json_object(payload, '$.currency') AS currency,\n"
                    "  CAST(get_json_object(payload, '$.amount') AS DOUBLE) AS amount,\n"
                    "  CAST(get_json_object(payload, '$.timestamp') AS TIMESTAMP) AS event_timestamp\n"
                    "FROM raw\n"
                    "WHERE get_json_object(payload, '$.amount') IS NOT NULL\n"
                    "  AND (get_json_object(payload, '$.merchant') IS NOT NULL OR get_json_object(payload, '$.merchant_name') IS NOT NULL);\n"
                ),
                "note": (
                    "Same COALESCE-plus-WHERE idea as the relational phase. No operator-precedence "
                    "gotcha here the way DuckDB's -> had - get_json_object is a plain function call, so "
                    "IS NOT NULL applies to its return value unambiguously."
                ),
            },
            {
                "title": "3. + dedupe redelivered events",
                "sql": (
                    "-- add to the raw/normalized CTE from step 2:\n"
                    "row_number() OVER (\n"
                    "  PARTITION BY COALESCE(get_json_object(payload, '$.event_id'), get_json_object(payload, '$.id'))\n"
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
                "title": "4. Don't lose arrivals past the 48-hour watermark",
                "sql": (
                    "-- same normalized CTE as step 3, nothing changes in the query itself - the point "
                    "-- of this step is what NOT to add:\n"
                    "WHERE rn = 1;\n"
                ),
                "note": (
                    "Same lesson as the relational phase: the tempting mistake is adding a filter like "
                    "`event_timestamp >= received_at - INTERVAL '48 hours'` to 'clean up' late data - that "
                    "permanently and silently drops it instead of processing it late. Reading the whole "
                    "partitioned output (not a rolling received_at time window) is what keeps a late "
                    "arrival from being lost, same as scanning the whole raw table by id in the relational "
                    "phase."
                ),
            },
            {
                "title": "5. Final: + TRY_CAST instead of a bare cast for the ambiguous date strings",
                "sql": (
                    "CREATE TABLE lake_output USING PARQUET PARTITIONED BY (event_date) LOCATION '<your output directory>' AS\n"
                    "SELECT id, received_at, source_delivery_id, payload,\n"
                    "       CAST(received_at AS DATE) AS event_date\n"
                    "FROM raw_transaction_events;\n\n"
                    "CREATE TABLE clean_transactions USING DELTA AS\n"
                    "WITH raw AS (\n"
                    "  SELECT id, received_at, payload FROM parquet.`<your output directory>`\n"
                    "),\n"
                    "normalized AS (\n"
                    "  SELECT\n"
                    "    COALESCE(get_json_object(payload, '$.event_id'), get_json_object(payload, '$.id')) AS event_id,\n"
                    "    COALESCE(get_json_object(payload, '$.merchant'), get_json_object(payload, '$.merchant_name')) AS merchant,\n"
                    "    get_json_object(payload, '$.currency') AS currency,\n"
                    "    CAST(get_json_object(payload, '$.amount') AS DOUBLE) AS amount,\n"
                    "    COALESCE(TRY_CAST(get_json_object(payload, '$.timestamp') AS TIMESTAMP), try_to_timestamp(get_json_object(payload, '$.timestamp'), 'dd/MM/yyyy')) AS event_timestamp,\n"
                    "    received_at,\n"
                    "    row_number() OVER (\n"
                    "      PARTITION BY COALESCE(get_json_object(payload, '$.event_id'), get_json_object(payload, '$.id'))\n"
                    "      ORDER BY received_at DESC\n"
                    "    ) AS rn\n"
                    "  FROM raw\n"
                    "  WHERE get_json_object(payload, '$.amount') IS NOT NULL\n"
                    "    AND (get_json_object(payload, '$.merchant') IS NOT NULL OR get_json_object(payload, '$.merchant_name') IS NOT NULL)\n"
                    "    AND get_json_object(payload, '$.currency') IS NOT NULL\n"
                    "    AND get_json_object(payload, '$.timestamp') IS NOT NULL\n"
                    ")\n"
                    "SELECT event_id, amount, merchant, currency, event_timestamp\n"
                    "FROM normalized\n"
                    "WHERE rn = 1;\n"
                ),
                "note": (
                    "Also now rejecting rows missing currency or timestamp entirely, the same reject-and-log "
                    "policy already applied to amount/merchant - without the watermark filter's old side "
                    "effect of incidentally excluding a null event_timestamp, a missing timestamp needs its "
                    "own explicit guard or it would silently reach clean_transactions as a null. The last wrinkle: a bare CAST throws on this feed's ambiguous regional date strings, "
                    "and even TRY_CAST alone just turns that into a silent null - Spark's TRY_CAST only "
                    "recognizes ISO-shaped timestamps, and this fault's real string is a bare DD/MM/YYYY "
                    "date, not ISO. Recovering it (rather than just not crashing on it) needs an explicit "
                    "fallback format: try_to_timestamp(ts, 'dd/MM/yyyy'), tried only after the normal ISO "
                    "parse already failed. This matches the top-level solution above - Excel-style ID "
                    "corruption still needs its own repair step before this query, left to you."
                ),
            },
        ],
    },
}
