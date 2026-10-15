"""Module 9.4: remediation for the two lake-specific structural checks.
Everything fault-type-specific (nulls, duplicates, late arrival, schema
drift, malformed IDs/dates) reuses grading.remediation directly via
grading.report.grade_clean_transactions - the required output contract
and ground truth are identical to the relational phase's, so that text
is identical too, not re-authored here."""

REMEDIATION = {
    "ERR_LAKE_NOT_PARTITIONED": {
        "why": (
            "Your output directory has one file (or files with no partition folders), not "
            "multiple event_date=... partitions - either PARTITION_BY was omitted, or every row "
            "ended up in the same partition value."
        ),
        "fix": "COPY (...) TO 'your_output_dir' (FORMAT PARQUET, PARTITION_BY (event_date)), with event_date derived from received_at::DATE.",
        "tradeoffs": (
            "Finer partitioning (daily, here) means more small files and more metadata to plan "
            "around; coarser partitioning (monthly/yearly) means fewer, bigger files but a query "
            "for one specific day still has to scan a whole month's file. Daily is the right "
            "granularity for this dataset's size, not a universal rule."
        ),
    },
    "ERR_LAKE_PAYLOAD_PREFLATTENED": {
        "why": (
            "Your written Parquet files don't have a payload column - the inner JSON fields were "
            "flattened into separate typed Parquet columns at write time. This defeats the actual "
            "point of the exercise: it just moves schema-on-write to a new storage format instead "
            "of deferring interpretation to read time."
        ),
        "fix": "Write payload as-is (a raw string column) at write time; parse it with get_json_object(payload, '$.field') at read time, inside the query that builds clean_transactions.",
        "tradeoffs": (
            "Schema-on-write (flattening at write time) is faster to query later and catches "
            "malformed data immediately, at the cost of failing/rejecting writes when the schema "
            "doesn't match. Schema-on-read (this task's approach) accepts anything at write time "
            "and pays the interpretation cost on every read instead - the real tradeoff a lake "
            "makes on purpose, which is exactly what this task is testing."
        ),
    },
}
