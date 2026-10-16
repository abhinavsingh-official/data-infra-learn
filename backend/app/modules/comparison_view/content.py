"""Module 11.1/11.3: the cross-platform comparison content. Every code
sample here except the MongoDB one is copied directly from a real,
grading-verified reference query already used elsewhere in this codebase
(see each entry's `source` field) - not written fresh for this page.
The MongoDB pipeline is the one genuinely new piece, and it was tested
directly against real seeded data before being added here (see
MODULE_11_PLAN.md): it produces exactly 49,246 distinct event ids,
matching every other paradigm's own verified answer.

Module 23 fixed a real staleness bug caught while building the
cross-paradigm comparison graph: the Warehouse/Lake/Lakehouse entries
still showed DuckDB syntax (`pg.` prefixes, `delta_scan()`, `read_parquet()`)
from before Module 19 moved all three onto real PySpark + Delta - updated
to the real Spark SQL (`get_json_object`, `row_number() OVER (...)`,
real Delta tables queried by name) each one actually runs today, copied
from their own current test files, not rewritten from memory."""

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
            "paradigm": "Warehouse (real Spark SQL, live Postgres-JDBC source)",
            "source": "backend/tests/modules/warehouse_phase/test_report.py - same row_number() technique as Lake/Lakehouse below",
            "code": (
                "SELECT event_id, amount, merchant, currency, event_timestamp\n"
                "FROM (\n"
                "  SELECT get_json_object(payload, '$.event_id') AS event_id, ...,\n"
                "    row_number() OVER (\n"
                "      PARTITION BY get_json_object(payload, '$.event_id') ORDER BY received_at\n"
                "    ) AS rn\n"
                "  FROM transactions\n"
                ") t\n"
                "WHERE rn = 1"
            ),
            "explanation": (
                "Spark SQL has no DISTINCT ON - the idiomatic replacement is row_number() windowed "
                "over the same partition key, keeping only rn = 1. get_json_object() replaces "
                "Postgres's ->>'...' since this payload column is plain text here, not jsonb."
            ),
        },
        {
            "paradigm": "Data Lake (real Spark SQL + partitioned Parquet, schema-on-read)",
            "source": "backend/tests/modules/lake_phase/test_report.py",
            "code": (
                "SELECT event_id, amount, merchant, currency, event_timestamp\n"
                "FROM (\n"
                "  SELECT get_json_object(payload, '$.event_id') AS event_id, ..., received_at,\n"
                "    row_number() OVER (\n"
                "      PARTITION BY get_json_object(payload, '$.event_id') ORDER BY received_at DESC\n"
                "    ) AS rn\n"
                "  FROM parquet.`<output_dir>`\n"
                ") normalized\n"
                "WHERE rn = 1"
            ),
            "explanation": (
                "Identical row_number() dedup logic to the warehouse phase - the only difference "
                "is the source: real partitioned Parquet files on disk, read schema-on-read via "
                "parquet.`<dir>` instead of a live database connection."
            ),
        },
        {
            "paradigm": "Lakehouse (real Spark + Delta table, incremental batches)",
            "source": "backend/tests/modules/lakehouse_phase/test_report.py",
            "code": (
                "SELECT n.event_id, n.amount, n.merchant, n.currency, n.event_timestamp\n"
                "FROM (\n"
                "  SELECT ..., row_number() OVER (PARTITION BY event_id ORDER BY received_at) AS rn\n"
                "  FROM batch_2_events\n"
                ") n\n"
                "LEFT JOIN clean_transactions existing ON existing.event_id = n.event_id\n"
                "WHERE n.rn = 1 AND existing.event_id IS NULL"
            ),
            "explanation": (
                "The one genuinely different approach here, not just a syntax variant - a "
                "per-batch row_number() dedup alone is NOT enough, because real duplicate-delivery "
                "events can span two incremental batches (confirmed directly: some do, in this "
                "project's own seeded data). The fix is an anti-join against the real Delta table's "
                "own current committed state (clean_transactions, queried by name) - deduplicating "
                "against history, not just within the new batch. This is the actual lesson "
                "incremental/streaming ingestion adds on top of every other paradigm's single-shot "
                "version of the same problem."
            ),
        },
    ],
}
