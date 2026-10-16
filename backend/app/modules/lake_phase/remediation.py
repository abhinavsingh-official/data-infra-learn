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
            "multiple event_date=... partitions - either PARTITION_BY was omitted, or every row "
            "ended up in the same partition value. Partitioning in a data lake isn't a performance "
            "knob applied after the fact - it's encoded directly into the directory structure "
            "itself (event_date=2026-01-01/part-0000.parquet, event_date=2026-01-02/..., and so on), "
            "which is what lets a query engine use Hive-style partition pruning: skip entire "
            "directories whose partition value can't match the query's filter, without even "
            "opening the files inside them."
        ),
        "fix": "COPY (...) TO 'your_output_dir' (FORMAT PARQUET, PARTITION_BY (event_date)), with event_date derived from received_at::DATE.",
        "tradeoffs": (
            "Finer partitioning (daily, here) means more small files and more metadata to plan "
            "around; coarser partitioning (monthly/yearly) means fewer, bigger files but a query "
            "for one specific day still has to scan a whole month's file. Daily is the right "
            "granularity for this dataset's size, not a universal rule - a lake ingesting "
            "millions of rows per hour might partition by hour instead, while a slow-moving "
            "reference dataset might reasonably partition by month or not at all. The right "
            "answer is always driven by 'what does a typical query filter on', not a fixed "
            "convention copied from another system."
        ),
    },
    "ERR_LAKE_PAYLOAD_PREFLATTENED": {
        "why": (
            "Your written Parquet files don't have a payload column - the inner JSON fields were "
            "flattened into separate typed Parquet columns at write time. This defeats the actual "
            "point of the exercise: it just moves schema-on-write to a new storage format instead "
            "of deferring interpretation to read time. Mechanically, flattening at write time means "
            "choosing a concrete Parquet column type (e.g. DOUBLE for amount) the moment the file "
            "is written - which forces every row to conform to that type then and there, exactly "
            "the schema-on-write behavior a lake is meant to defer."
        ),
        "fix": "Write payload as-is (a raw string column) at write time; parse it with get_json_object(payload, '$.field') at read time, inside the query that builds clean_transactions.",
        "tradeoffs": (
            "Schema-on-write (flattening at write time) is faster to query later and catches "
            "malformed data immediately, at the cost of failing/rejecting writes when the schema "
            "doesn't match. Schema-on-read (this task's approach) accepts anything at write time "
            "and pays the interpretation cost on every read instead - the real tradeoff a lake "
            "makes on purpose, which is exactly what this task is testing. In practice this means "
            "a data lake can ingest a malformed or unexpectedly-shaped payload without the write "
            "ever failing - the cost of that malformed data shows up later, as a parse error or a "
            "NULL at query time, which is a deliberate trade: ingestion never blocks on a data "
            "quality problem, but every consumer has to be prepared to handle one."
        ),
    },
}
