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
}
