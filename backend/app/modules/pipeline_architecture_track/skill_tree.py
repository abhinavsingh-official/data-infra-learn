"""The "Pipeline Architecture" track - a cross-cutting track covering
scheduling, data quality, schema evolution, batch vs. streaming,
idempotent pipelines, and monitoring. These topics don't map to any
single storage paradigm; they show up as edge-case fault types scattered
across the other phases (schema drift, redelivery dedup, watermark
checks) rather than being presented as their own discipline, so this
track pulls them together explicitly.

Unlike the other fundamentals tracks, this one has no sibling "phase"
with a real capstone dataset - it's cross-cutting by design, so there's
no capstone node here, same as sql_databases_track has none (its capstone
lives in the sibling postgres_phase tree instead). This track's "capstone"
is conceptual: the review node points back at where each concept already
shows up for real, across the five existing capstones.

Every example row and expected output below was captured by creating
these exact tables and running these exact queries against real
Postgres."""

PIPELINE_ARCHITECTURE_SKILL_TREE = {
    "paradigm": "pipeline-architecture",
    "nodes": [
        {
            "id": "intro",
            "type": "intro",
            "title": "Pipeline Architecture: the discipline underneath every paradigm",
            "body": (
                "Schema drift, retried deliveries, late-arriving data, and the need to actually "
                "notice when a pipeline is failing - these aren't Postgres problems or Mongo "
                "problems, they're pipeline-engineering problems that show up in every paradigm "
                "this platform teaches. This track names them explicitly and practices each one "
                "once, on its own, before you've seen them (and will keep seeing them) baked into "
                "every real capstone."
            ),
        },
        {
            "id": "node_1_idempotent_pipelines",
            "type": "skill",
            "title": "Idempotent pipelines: safe to retry, by construction",
            "teach": {
                "sql": (
                    "SELECT idempotency_key, amount\n"
                    "FROM (\n"
                    "  SELECT *, ROW_NUMBER() OVER (PARTITION BY idempotency_key ORDER BY attempt) AS rn\n"
                    "  FROM webhook_deliveries\n"
                    ") t\n"
                    "WHERE rn = 1;"
                ),
                "note": (
                    "A real webhook sender will retry a delivery it isn't sure succeeded - an "
                    "idempotency key is how the receiver recognizes 'I've already seen this "
                    "exact attempt' regardless of how many times it arrives. A pipeline is "
                    "idempotent when re-running it produces the same result, not an extra copy."
                ),
            },
            "practice": {
                "prompt": "Keep only the first attempt of each idempotency_key.",
                "table_name": "webhook_deliveries",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "idempotency_key", "type": "text"},
                    {"column": "attempt", "type": "int"},
                    {"column": "amount", "type": "numeric"},
                ],
                "example_rows": [
                    {"id": 1, "idempotency_key": "idem_1", "attempt": 1, "amount": 50.00},
                    {"id": 2, "idempotency_key": "idem_1", "attempt": 2, "amount": 50.00},
                    {"id": 3, "idempotency_key": "idem_2", "attempt": 1, "amount": 75.00},
                ],
                "expected_output_rows": [
                    {"idempotency_key": "idem_1", "amount": 50.00},
                    {"idempotency_key": "idem_2", "amount": 75.00},
                ],
            },
        },
        {
            "id": "node_2_schema_evolution",
            "type": "skill",
            "title": "Schema evolution: yesterday's field isn't today's field",
            "teach": {
                "sql": (
                    "SELECT id, COALESCE(full_name_v2, customer_name_v1) AS customer_name\n"
                    "FROM customer_events;"
                ),
                "note": (
                    "A pipeline that's been running for months has survived at least one schema "
                    "change upstream - a field gets renamed, and old rows never get backfilled. "
                    "A production-grade pipeline reads across both historical shapes at once, "
                    "rather than breaking the moment the old field disappears."
                ),
            },
            "practice": {
                "prompt": "Unify customer_name_v1 (the old field name) and full_name_v2 (the new one) into one customer_name.",
                "table_name": "customer_events",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "customer_name_v1", "type": "text"},
                    {"column": "full_name_v2", "type": "text"},
                ],
                "example_rows": [
                    {"id": 1, "customer_name_v1": "Alice Smith", "full_name_v2": None},
                    {"id": 2, "customer_name_v1": None, "full_name_v2": "Bob Jones"},
                ],
                "expected_output_rows": [
                    {"id": 1, "customer_name": "Alice Smith"},
                    {"id": 2, "customer_name": "Bob Jones"},
                ],
            },
        },
        {
            "id": "node_3_batch_vs_streaming",
            "type": "skill",
            "title": "Batch vs. streaming: a late event is late, not invalid",
            "teach": {
                "sql": "SELECT id, amount FROM stream_events;",
                "note": (
                    "Streaming systems process events as they arrive, but 'arrive' and 'happen' "
                    "are different timestamps - an event can be real and correct while showing "
                    "up well after the batch window that was supposed to cover it. The fix isn't "
                    "a stricter cutoff, it's accepting that a watermark is a tradeoff, not a hard "
                    "guarantee, and designing the pipeline to still include it."
                ),
            },
            "practice": {
                "prompt": (
                    "Event 2 happened on time but wasn't processed until 4 days later - include "
                    "it anyway, it's late, not invalid."
                ),
                "table_name": "stream_events",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "event_time", "type": "timestamptz"},
                    {"column": "processed_at", "type": "timestamptz"},
                    {"column": "amount", "type": "numeric"},
                ],
                "example_rows": [
                    {
                        "id": 1, "event_time": "2026-01-01T00:00:00+00",
                        "processed_at": "2026-01-01T00:05:00+00", "amount": 10.00,
                    },
                    {
                        "id": 2, "event_time": "2026-01-01T00:00:00+00",
                        "processed_at": "2026-01-05T00:00:00+00", "amount": 20.00,
                    },
                ],
                "expected_output_rows": [
                    {"id": 1, "amount": 10.00},
                    {"id": 2, "amount": 20.00},
                ],
            },
        },
        {
            "id": "node_4_monitoring_alerting",
            "type": "skill",
            "title": "Monitoring: you can't fix what you can't see",
            "teach": {
                "sql": (
                    "SELECT error_code, COUNT(*) AS error_count\n"
                    "FROM pipeline_errors\n"
                    "GROUP BY error_code\n"
                    "ORDER BY error_count DESC;"
                ),
                "note": (
                    "Every reject-and-log decision this platform's graders have made (a null "
                    "required field, a duplicate delivery, a malformed date) only pays off if "
                    "something actually counts and surfaces those rejections - this is the exact "
                    "query shape behind a real pipeline dashboard or alert."
                ),
            },
            "practice": {
                "prompt": "Count errors by error_code, worst offender first - the query behind a real ops dashboard.",
                "table_name": "pipeline_errors",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "error_code", "type": "text"},
                    {"column": "occurred_at", "type": "timestamptz"},
                ],
                "example_rows": [
                    {"id": 1, "error_code": "ERR_NULL_FIELD", "occurred_at": "2026-01-01T00:00:00+00"},
                    {"id": 2, "error_code": "ERR_NULL_FIELD", "occurred_at": "2026-01-01T00:01:00+00"},
                    {"id": 3, "error_code": "ERR_DUPLICATE", "occurred_at": "2026-01-01T00:02:00+00"},
                ],
                "expected_output_rows": [
                    {"error_code": "ERR_NULL_FIELD", "error_count": 2},
                    {"error_code": "ERR_DUPLICATE", "error_count": 1},
                ],
            },
        },
        {
            "id": "review",
            "type": "review",
            "title": "Review: where these four ideas already live, for real",
            "prompt": (
                "Idempotency is the Postgres/Lake/Lakehouse dedup logic you've already written. "
                "Schema evolution is the 'renamed field' edge case from the Postgres capstone. "
                "Batch vs. streaming is the watermark check in Postgres, Lake, and the Warehouse "
                "SCD2 re-run. Monitoring is every fault_type_summary a grading report has ever "
                "returned. This track just gave the discipline a name - the five real capstones "
                "are where it actually gets exercised at scale."
            ),
        },
    ],
}
