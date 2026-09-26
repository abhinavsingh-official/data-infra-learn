"""Module 11.1/11.3: the cross-platform comparison content. Every code
sample here except the MongoDB one is copied directly from a real,
grading-verified reference query already used elsewhere in this codebase
(see each entry's `source` field) - not written fresh for this page.
The MongoDB pipeline is the one genuinely new piece, and it was tested
directly against real seeded data before being written here (see
MODULE_11_PLAN.md): it produces exactly 49,246 distinct event ids,
matching every other paradigm's own verified answer."""

COMPARISON = {
    "operation": "Deduplicate transaction events by event_id, keeping the first-arrived delivery",
    "why_this_operation": (
        "duplicate_delivery is a fault type every single phase has to handle - a real webhook-"
        "retry pattern (Module 3), not a toy example picked for this page. Four of the five "
        "entries below are copied directly from this project's own passing tests, not written "
        "fresh - only the MongoDB pipeline is new, and it was verified against real data before "
        "being added here (see MODULE_11_PLAN.md)."
    ),
    "entries": [
        {
            "paradigm": "Postgres (relational)",
            "source": "backend/tests/modules/grading/test_report.py",
            "code": (
                "SELECT DISTINCT ON (payload->>'event_id')\n"
                "  payload->>'event_id', ...\n"
                "FROM public.raw_transaction_events\n"
                "WHERE payload ? 'event_id'\n"
                "ORDER BY payload->>'event_id', received_at ASC"
            ),
            "explanation": (
                "Postgres's own DISTINCT ON keeps the first row per group after an explicit "
                "ORDER BY - a single-statement, single-table answer, since everything lives in "
                "one row-store table already."
            ),
        },
        {
            "paradigm": "NoSQL (MongoDB)",
            "source": "written for this page - verified directly against real seeded data (see MODULE_11_PLAN.md)",
            "code": (
                "db.raw_events.aggregate([\n"
                "  { $match: { \"payload.event_id\": { $exists: true } } },\n"
                "  { $sort: { received_at: 1 } },\n"
                "  { $group: { _id: \"$payload.event_id\", doc: { $first: \"$$ROOT\" } } },\n"
                "  { $replaceRoot: { newRoot: \"$doc\" } }\n"
                "])"
            ),
            "explanation": (
                "No DISTINCT ON in Mongo's query language - the idiomatic equivalent is an "
                "aggregation pipeline: sort first so $first is deterministic, $group by the "
                "business key, then $replaceRoot to flatten the grouped document back out."
            ),
        },
        {
            "paradigm": "Warehouse (DuckDB, live-attached Postgres source)",
            "source": "backend/app/modules/lake_phase - the same pattern reused for the warehouse phase's own ETL",
            "code": (
                "SELECT DISTINCT ON (payload_json->>'event_id')\n"
                "  payload_json->>'event_id', ...\n"
                "FROM (SELECT payload::JSON AS payload_json FROM pg.raw_transaction_events) t\n"
                "WHERE payload_json->>'event_id' IS NOT NULL\n"
                "ORDER BY payload_json->>'event_id', received_at ASC"
            ),
            "explanation": (
                "Same DISTINCT ON idea as Postgres, but DuckDB doesn't have a native jsonb type - "
                "payload has to be cast to JSON explicitly first, and DuckDB's own operator-"
                "precedence and cast-strictness gotchas apply (see MODULE_9_PLAN.md)."
            ),
        },
        {
            "paradigm": "Data Lake (DuckDB + partitioned Parquet, schema-on-read)",
            "source": "backend/tests/modules/lake_phase/test_report.py",
            "code": (
                "SELECT DISTINCT ON (payload_json->>'event_id')\n"
                "  payload_json->>'event_id', ...\n"
                "FROM (\n"
                "  SELECT payload::JSON AS payload_json\n"
                "  FROM read_parquet('<output_dir>/**/*.parquet', hive_partitioning=true, union_by_name=true)\n"
                ") t\n"
                "WHERE payload_json->>'event_id' IS NOT NULL\n"
                "ORDER BY payload_json->>'event_id', received_at ASC"
            ),
            "explanation": (
                "Identical dedup logic to the warehouse phase - the only difference is the "
                "source: partitioned files on disk instead of a live-attached table, read schema-"
                "on-read via read_parquet() instead of a database connection."
            ),
        },
        {
            "paradigm": "Lakehouse (DuckDB + real Delta table, incremental batches)",
            "source": "backend/tests/modules/lakehouse_phase/test_report.py",
            "code": (
                "SELECT DISTINCT ON (t.eid) t.eid, ...\n"
                "FROM (SELECT payload::JSON AS pj, (payload::JSON)->>'event_id' AS eid FROM batch_2_events) t\n"
                "LEFT JOIN delta_scan('<delta_path>') d ON d.event_id = t.eid\n"
                "WHERE t.eid IS NOT NULL AND d.event_id IS NULL\n"
                "ORDER BY t.eid, t.received_at ASC"
            ),
            "explanation": (
                "The one genuinely different approach here, not just a syntax variant - a "
                "per-batch DISTINCT ON alone is NOT enough, because real duplicate-delivery "
                "events can span two incremental batches (confirmed directly: some do, in this "
                "project's own seeded data). The fix is an anti-join against the table's own "
                "current committed state via delta_scan(...) - deduplicating against history, "
                "not just within the new batch. This is the actual lesson incremental/streaming "
                "ingestion adds on top of every other paradigm's single-shot version of the "
                "same problem."
            ),
        },
    ],
}
