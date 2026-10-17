"""Remediation for the two lake-specific structural checks. Everything
fault-type-specific (nulls, duplicates, late arrival, schema drift,
malformed IDs/dates) reuses grading.remediation directly via
grading.report.grade_clean_transactions - the required output contract
and ground truth are identical to the relational phase's, so that text
is identical too, not re-authored here."""

REMEDIATION = {
    "ERR_LAKE_NOT_PARTITIONED": {
        "why": (
            "Your output directory has one file (or files with no partition folders), not "
            "multiple event_date=... partitions - either PARTITIONED BY was omitted, or every row "
            "landed in the same partition value. Partitioning is encoded directly into the "
            "directory structure itself (event_date=2026-01-01/part-0000.parquet, ...), which is "
            "what lets a query engine prune entire directories that can't match a filter, without "
            "even opening the files inside them."
        ),
        "fix": "Partition the write by a date derived from received_at, producing one directory per day.",
        "fix_sql": (
            "CREATE TABLE lake_output USING PARQUET PARTITIONED BY (event_date) LOCATION '<output_dir>' AS\n"
            "SELECT id, received_at, source_delivery_id, payload,\n"
            "       CAST(received_at AS DATE) AS event_date\n"
            "FROM raw_transaction_events;"
        ),
        "tradeoffs": (
            "Finer partitioning (daily, here) means more small files and metadata; coarser "
            "partitioning (monthly/yearly) means fewer, bigger files but a query for one day still "
            "scans a whole month's file. Daily suits this dataset's size, not every dataset - the "
            "right granularity is always driven by what a typical query filters on, not a fixed "
            "convention."
        ),
    },
    "ERR_LAKE_PAYLOAD_PREFLATTENED": {
        "why": (
            "Your written Parquet files don't have a payload column - the inner JSON fields were "
            "flattened into separate typed Parquet columns at write time, which just moves "
            "schema-on-write to a new storage format instead of deferring interpretation to read "
            "time. Choosing a concrete Parquet type (e.g. DOUBLE for amount) at write time forces "
            "every row to conform to it then and there."
        ),
        "fix": "Write payload as-is, a raw string column; parse it at read time inside the query that builds clean_transactions.",
        "fix_sql": (
            "-- write: payload untouched\n"
            "-- CREATE TABLE lake_output ... AS SELECT id, received_at, source_delivery_id, payload, ... ;\n\n"
            "-- read: parse at query time\n"
            "SELECT get_json_object(payload, '$.event_id') AS event_id,\n"
            "       CAST(get_json_object(payload, '$.amount') AS DOUBLE) AS amount\n"
            "FROM parquet.`<output_dir>`;"
        ),
        "tradeoffs": (
            "Schema-on-write (flattening at write time) is faster to query later and catches "
            "malformed data immediately, at the cost of failing writes when the schema doesn't "
            "match. Schema-on-read (this task's approach) accepts anything at write time and pays "
            "the interpretation cost on every read instead - ingestion never blocks on a data "
            "quality problem, but every consumer has to be prepared to handle one."
        ),
    },
}
