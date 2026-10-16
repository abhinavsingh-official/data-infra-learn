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
            "title": "Pipeline Architecture: the discipline underneath every approach",
            "body": (
                "Schema drift, retried deliveries, late-arriving data, and the need to actually "
                "notice when a pipeline is failing - these aren't Postgres problems or Mongo "
                "problems, they're pipeline-engineering problems that show up in every approach "
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
                    "idempotent when re-running it produces the same result, not an extra copy. "
                    "The strongest version of this is making the WRITE itself idempotent (an "
                    "upsert keyed on the idempotency key, or an INSERT ... ON CONFLICT DO NOTHING) "
                    "rather than only deduplicating on read - a read-time dedupe like the "
                    "ROW_NUMBER() below is correct but means every single query has to remember to "
                    "re-apply it; an idempotent write means the table itself never had the "
                    "duplicate in the first place."
                ),
                "steps": [
                    {
                        "body": "A real webhook sender retries a delivery it isn't sure "
                        "succeeded - so how does the receiver avoid processing the same payment "
                        "twice?"
                    },
                    {
                        "body": "Keep only the first attempt per idempotency key:",
                        "sql": "SELECT *, ROW_NUMBER() OVER (PARTITION BY idempotency_key ORDER BY attempt) AS rn\nFROM deliveries;",
                    },
                    {
                        "body": "Keep only the first attempt of each idempotency_key:",
                        "sql": (
                            "SELECT idempotency_key, amount\n"
                            "FROM (\n"
                            "  SELECT *, ROW_NUMBER() OVER (PARTITION BY idempotency_key ORDER BY attempt) AS rn\n"
                            "  FROM webhook_deliveries\n"
                            ") t\n"
                            "WHERE rn = 1;"
                        ),
                    },
                    {
                        "body": "An idempotency key is how the receiver recognizes 'I've "
                        "already seen this exact attempt' regardless of how many times it "
                        "arrives - re-running an idempotent pipeline produces the same result, "
                        "not an extra copy."
                    },
                    {
                        "body": "A subtle trap: the idempotency key has to be something the "
                        "SENDER generates and keeps stable across retries - a key the receiver "
                        "generates itself (like an auto-incrementing id on insert, or the current "
                        "timestamp) defeats the whole purpose, because a genuine retry would get a "
                        "brand new key every time and look like a brand new event. This is also "
                        "why the real task's source_delivery_id is explicitly the WRONG key to "
                        "dedupe on - it's assigned per transport-layer attempt, not per business "
                        "event, so two deliveries of the same real event get two different "
                        "source_delivery_id values by design."
                    },
                    {
                        "body": "ON CONFLICT DO NOTHING (or DO UPDATE, for an idempotent upsert) "
                        "pushes this guarantee down into the database itself, enforced by a unique "
                        "constraint on the idempotency key - safe even under concurrent retries "
                        "racing each other, which a read-then-check-then-insert application-level "
                        "check is not.",
                        "sql": (
                            "INSERT INTO processed_payments (idempotency_key, amount)\n"
                            "VALUES ('idem_1', 50.00)\n"
                            "ON CONFLICT (idempotency_key) DO NOTHING;"
                        ),
                    },
                    {
                        "body": "Idempotent means safe to retry, by construction. Try it "
                        "yourself in the Practice tab."
                    },
                ],
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
                    "rather than breaking the moment the old field disappears. This is the schema "
                    "evolution version of the same backward-compatibility principle that governs "
                    "API versioning: a consumer written to tolerate both the old and new shape "
                    "never needs a synchronized 'flag day' deploy with the producer, which is "
                    "rarely achievable in practice across independently-deployed systems."
                ),
                "steps": [
                    {
                        "body": "A pipeline that's been running for months has survived at "
                        "least one schema change upstream - a field gets renamed, and old rows "
                        "never get backfilled."
                    },
                    {
                        "body": "Read across both historical shapes at once:",
                        "sql": "SELECT COALESCE(new_field, old_field) AS field\nFROM events;",
                    },
                    {
                        "body": "Unify customer_name_v1 (the old field name) and full_name_v2 (the new one):",
                        "sql": "SELECT id, COALESCE(full_name_v2, customer_name_v1) AS customer_name\nFROM customer_events;",
                    },
                    {
                        "body": "A production-grade pipeline reads across both historical "
                        "shapes at once, rather than breaking the moment the old field "
                        "disappears."
                    },
                    {
                        "body": "Renaming is the mildest form of schema drift - the two other "
                        "common shapes are an added field (harmless if your extraction reads "
                        "fields by name rather than SELECT *, since an unread field is just "
                        "ignored) and a changed type (the dangerous one: an 'amount' field that "
                        "silently switches from a decimal string to an integer-cents number "
                        "produces a value that's still a valid number, just a wrong one by a "
                        "factor of 100 - no error, no NULL, just quietly incorrect data unless the "
                        "type is explicitly checked at read time, e.g. with jsonb_typeof())."
                    },
                    {
                        "body": "The real discipline this points to is a schema registry or "
                        "explicit field-mapping config maintained as a first-class artifact, not "
                        "tribal knowledge in someone's head about 'oh yeah, that field got "
                        "renamed in March' - COALESCE-across-names is a fine tactical fix for one "
                        "rename, but it doesn't scale past a handful of known historical shapes."
                    },
                    {
                        "body": "Schema evolution means yesterday's field isn't today's field - "
                        "and your pipeline has to read both. Try it yourself in the Practice tab."
                    },
                ],
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
                    "guarantee, and designing the pipeline to still include it. 'Batch vs. "
                    "streaming' isn't really a binary choice either - the honest framing is a "
                    "spectrum of latency vs. complexity: a nightly batch job is simplest to reason "
                    "about but slowest to reflect new data; a true streaming system processes "
                    "events within seconds but has to solve watermarks, exactly-once semantics, "
                    "and out-of-order arrival as first-class problems instead of being able to "
                    "ignore them."
                ),
                "steps": [
                    {
                        "body": "'Arrive' and 'happen' are different timestamps - an event can "
                        "be real and correct while showing up well after the window meant to "
                        "cover it."
                    },
                    {
                        "body": "A late arrival still belongs in the output:",
                        "sql": "SELECT * FROM events;  -- no cutoff on processed_at",
                    },
                    {
                        "body": "Event 2 happened on time but wasn't processed until 4 days "
                        "later - include it anyway:",
                        "sql": "SELECT id, amount FROM stream_events;",
                    },
                    {
                        "body": "The fix isn't a stricter cutoff - it's accepting that a "
                        "watermark is a tradeoff, not a hard guarantee, and designing the "
                        "pipeline to still include a late arrival once it does show up."
                    },
                    {
                        "body": "This is the same tension as choosing event_time vs. "
                        "processing_time as the basis for a window in any real stream processor "
                        "(Spark Structured Streaming, Flink, etc.) - windowing by processing_time "
                        "is simpler to implement but produces a window whose membership silently "
                        "depends on network/queue delays rather than when things actually "
                        "happened; windowing by event_time is what you actually want, but it "
                        "requires explicitly deciding how long to wait for stragglers (the "
                        "watermark) before declaring a window 'closed' and finalizing its result."
                    },
                    {
                        "body": "A common mistake is treating the watermark as correctness "
                        "logic rather than a performance/finality tradeoff - a batch job that "
                        "simply drops anything past its watermark (instead of reprocessing late "
                        "data on a later run) is choosing speed over completeness without saying "
                        "so out loud, which is a defensible choice only if it's a documented one."
                    },
                    {
                        "body": "A late event is late, not invalid. Try it yourself in the "
                        "Practice tab."
                    },
                ],
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
                    "query shape behind a real pipeline dashboard or alert. Counting errors is the "
                    "easy half of monitoring; the harder half is deciding the threshold that turns "
                    "a count into an alert someone gets paged for - too sensitive and real "
                    "incidents drown in noise nobody reads anymore, too loose and a real outage "
                    "sits unnoticed for hours."
                ),
                "steps": [
                    {
                        "body": "Every reject-and-log decision a pipeline makes only pays off if "
                        "something actually counts and surfaces those rejections."
                    },
                    {
                        "body": "Count errors, worst offender first:",
                        "sql": "SELECT error_code, COUNT(*) AS n\nFROM errors\nGROUP BY error_code\nORDER BY n DESC;",
                    },
                    {
                        "body": "Count errors by error_code, worst offender first:",
                        "sql": (
                            "SELECT error_code, COUNT(*) AS error_count\n"
                            "FROM pipeline_errors\n"
                            "GROUP BY error_code\n"
                            "ORDER BY error_count DESC;"
                        ),
                    },
                    {
                        "body": "This is the exact query shape behind a real pipeline "
                        "dashboard or alert - a null required field, a duplicate delivery, a "
                        "malformed date all show up the same way here."
                    },
                    {
                        "body": "A raw count by itself is also a weak signal on its own - 50 "
                        "null-field errors means something very different on a 100-row batch than "
                        "on a 5-million-row batch. Real monitoring tracks an error RATE (errors / "
                        "total rows processed) and alerts on a rate that deviates from its own "
                        "historical baseline, not on a fixed absolute count that was only ever "
                        "calibrated for one particular data volume."
                    },
                    {
                        "body": "The other half of 'can't fix what you can't see' is freshness, "
                        "not just error counts - a pipeline that silently stops running entirely "
                        "produces zero errors (there's nothing left to fail) while also producing "
                        "zero fresh data, which looks identical to 'everything's fine' on an "
                        "error-count dashboard alone. A real monitoring setup also tracks "
                        "'time since last successful run' as its own independent signal."
                    },
                    {
                        "body": "You can't fix what you can't see. Try it yourself in the "
                        "Practice tab."
                    },
                ],
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
            "id": "node_5_data_quality_gates",
            "type": "skill",
            "title": "Data quality gates: reject bad rows before they reach a report",
            "teach": {
                "sql": (
                    "SELECT id, account_id, amount\n"
                    "FROM raw_orders\n"
                    "WHERE account_id IS NOT NULL AND amount > 0;"
                ),
                "note": (
                    "A validation rule is just a WHERE clause expressing what 'valid' means for "
                    "this feed - here, every row needs a real account_id and a positive amount. "
                    "Filtering rows out silently is only half of a real data quality gate, though: "
                    "the honest version doesn't just drop a bad row, it ALSO routes it somewhere "
                    "visible (a dead-letter table, node 8) and counts it (node 4's monitoring "
                    "query) - a validation rule nobody can see the rejections from is "
                    "indistinguishable from data quietly going missing."
                ),
                "steps": [
                    {
                        "body": "A raw feed has rows with a missing account_id, or a negative "
                        "amount that makes no business sense - what counts as a 'valid' row here, "
                        "exactly?"
                    },
                    {
                        "body": "A validation rule is a WHERE clause expressing 'valid':",
                        "sql": "SELECT *\nFROM raw_table\nWHERE required_field IS NOT NULL AND numeric_field > 0;",
                    },
                    {
                        "body": "Keep only rows with a real account_id and a positive amount:",
                        "sql": (
                            "SELECT id, account_id, amount\n"
                            "FROM raw_orders\n"
                            "WHERE account_id IS NOT NULL AND amount > 0;"
                        ),
                    },
                    {
                        "body": "Each condition here encodes one business rule about what "
                        "'valid' means for this specific feed - a different feed would have "
                        "different rules, there's no universal definition of 'valid data'."
                    },
                    {
                        "body": "Filtering rows out silently is only half of a real data quality "
                        "gate. The honest version doesn't just drop a bad row - it ALSO routes it "
                        "somewhere visible (a dead-letter table, node 8 of this same track) and "
                        "counts it (the monitoring query from node 4). A WHERE clause that quietly "
                        "shrinks a feed with no record of what got excluded is indistinguishable "
                        "from data silently going missing."
                    },
                    {
                        "body": "A common mistake: writing the validation rule and the "
                        "transformation logic as one tangled query, so that a row failing "
                        "validation and a row that's merely edge-case-shaped get the same "
                        "treatment (dropped, with no distinction). Keeping validation as its own "
                        "explicit, nameable step - not an incidental side effect of some other "
                        "WHERE clause - is what makes it possible to report on later."
                    },
                    {
                        "body": "A data quality gate is a WHERE clause that encodes what 'valid' "
                        "means for one specific feed. Try it yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Keep only rows with a non-null account_id and a positive amount.",
                "table_name": "raw_orders",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "account_id", "type": "bigint"},
                    {"column": "amount", "type": "numeric"},
                ],
                "example_rows": [
                    {"id": 1, "account_id": 101, "amount": 45.00},
                    {"id": 2, "account_id": None, "amount": 20.00},
                    {"id": 3, "account_id": 102, "amount": -5.00},
                    {"id": 4, "account_id": 103, "amount": 60.00},
                ],
                "expected_output_rows": [
                    {"id": 1, "account_id": 101, "amount": 45.00},
                    {"id": 4, "account_id": 103, "amount": 60.00},
                ],
            },
        },
        {
            "id": "node_6_incremental_watermark",
            "type": "skill",
            "title": "Incremental extraction: only pull what changed since last time",
            "teach": {
                "sql": "SELECT id, value FROM source_records WHERE updated_at > '2026-01-03T00:00:00+00';",
                "note": (
                    "Re-reading an entire source table on every single run works, but it's "
                    "wasteful and gets slower as the table grows - a watermark (the updated_at "
                    "value of the last row successfully processed last time) lets a pipeline pull "
                    "only what's new instead. This is a genuinely different concern from node 3's "
                    "late-arriving-event problem: that node was about whether a late row still "
                    "belongs in the OUTPUT once it shows up; this node is about the bookkeeping a "
                    "pipeline keeps, between runs, to know what it hasn't read yet."
                ),
                "steps": [
                    {
                        "body": "Re-reading an entire source table from scratch on every single "
                        "run works, but it's wasteful and gets slower as the table grows - how do "
                        "you pull only what's NEW since last time?"
                    },
                    {
                        "body": "A watermark is the cutoff remembered from the last run:",
                        "sql": "SELECT *\nFROM source\nWHERE updated_at > :last_watermark;",
                    },
                    {
                        "body": "Pull only records updated after the last watermark:",
                        "sql": "SELECT id, value FROM source_records WHERE updated_at > '2026-01-03T00:00:00+00';",
                    },
                    {
                        "body": "The watermark - here, the updated_at of the last row "
                        "successfully processed last run - is state the PIPELINE itself keeps "
                        "between runs, not something derived from the data alone; after this "
                        "run finishes, the new watermark becomes the max updated_at it just saw."
                    },
                    {
                        "body": "This is a genuinely different concern from the late-arriving-"
                        "event problem (a different node in this same track): that one asks "
                        "whether a late row still belongs in the OUTPUT once it finally shows up. "
                        "This one asks what a pipeline should remember, between runs, about what "
                        "it has and hasn't already read - a bookkeeping problem, not an "
                        "output-completeness one."
                    },
                    {
                        "body": "The sharp failure mode: if a row's updated_at can be backdated "
                        "or corrected after the fact to a time BEFORE the current watermark, "
                        "incremental extraction will never see that correction - `updated_at > "
                        "watermark` only looks forward from where it already was. Guarding against "
                        "this usually means either re-scanning a trailing overlap window "
                        "periodically, or using a strictly-increasing ingestion sequence number "
                        "instead of a business timestamp as the watermark itself."
                    },
                    {
                        "body": "A watermark lets a pipeline pull only what's changed since its "
                        "own last successful run. Try it yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Pull only the records updated after the watermark 2026-01-03T00:00:00+00.",
                "table_name": "source_records",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "updated_at", "type": "timestamptz"},
                    {"column": "value", "type": "numeric"},
                ],
                "example_rows": [
                    {"id": 1, "updated_at": "2026-01-01T00:00:00+00", "value": 10.00},
                    {"id": 2, "updated_at": "2026-01-05T00:00:00+00", "value": 20.00},
                    {"id": 3, "updated_at": "2026-01-10T00:00:00+00", "value": 30.00},
                ],
                "expected_output_rows": [
                    {"id": 2, "value": 20.00},
                    {"id": 3, "value": 30.00},
                ],
            },
        },
        {
            "id": "node_7_change_data_capture",
            "type": "skill",
            "title": "Change Data Capture: reconstructing current state from an event log",
            "teach": {
                "sql": (
                    "SELECT record_id, value\n"
                    "FROM (\n"
                    "  SELECT *, ROW_NUMBER() OVER (PARTITION BY record_id ORDER BY sequence_num DESC) AS rn\n"
                    "  FROM cdc_log\n"
                    ") t\n"
                    "WHERE rn = 1;"
                ),
                "note": (
                    "A CDC log records every insert/update/delete as its own append-only event, "
                    "with a sequence number establishing order - it never overwrites anything in "
                    "place. Reconstructing 'what's true right now' for a given record means "
                    "finding its LATEST event, which is exactly what ROW_NUMBER() PARTITION BY "
                    "record_id ORDER BY sequence_num DESC does: rank each record's events newest-"
                    "first, then keep only rn = 1. This is the same ROW_NUMBER() shape node 1's "
                    "idempotency node used, pointed at a different problem - there it kept the "
                    "FIRST attempt per key, here it keeps the LATEST event per record."
                ),
                "steps": [
                    {
                        "body": "A CDC log never overwrites anything - every insert, update, "
                        "and delete is its own event, appended in order. So how do you ask 'what's "
                        "true for this record RIGHT NOW'?"
                    },
                    {
                        "body": "Rank each record's events newest-first, keep only the top one:",
                        "sql": "SELECT *, ROW_NUMBER() OVER (PARTITION BY record_id ORDER BY sequence_num DESC) AS rn\nFROM cdc_log;",
                    },
                    {
                        "body": "Reconstruct the current value for each record_id:",
                        "sql": (
                            "SELECT record_id, value\n"
                            "FROM (\n"
                            "  SELECT *, ROW_NUMBER() OVER (PARTITION BY record_id ORDER BY sequence_num DESC) AS rn\n"
                            "  FROM cdc_log\n"
                            ") t\n"
                            "WHERE rn = 1;"
                        ),
                    },
                    {
                        "body": "ROW_NUMBER() PARTITION BY record_id ORDER BY sequence_num DESC "
                        "ranks each record's own events newest-first; keeping only rn = 1 per "
                        "record_id reconstructs 'what's true right now', from an append-only log "
                        "that never updates anything in place."
                    },
                    {
                        "body": "This is the same ROW_NUMBER() shape the idempotent-pipelines "
                        "node (elsewhere in this track) used, pointed at a different problem: "
                        "there, ORDER BY attempt with rn = 1 kept the FIRST attempt per "
                        "idempotency_key; here, ORDER BY sequence_num DESC with rn = 1 keeps the "
                        "LATEST event per record_id. Same window-function tool, opposite ordering, "
                        "because the two questions ('what happened first' vs. 'what's true now') "
                        "are genuinely different."
                    },
                    {
                        "body": "A sharp gotcha: an 'op' column (insert/update/delete) on each "
                        "CDC event matters just as much as its value - if the latest event for a "
                        "record_id has op = 'delete', the correct reconstruction is that the "
                        "record no longer exists at all, not that its value is whatever the "
                        "delete event happened to carry. A naive version of this query that "
                        "ignores 'op' entirely will keep resurrecting deleted records."
                    },
                    {
                        "body": "CDC reconstructs current state by keeping only the newest event "
                        "per record from an append-only log. Try it yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Reconstruct the current value for each record_id from this CDC log (latest event wins).",
                "table_name": "cdc_log",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "record_id", "type": "bigint"},
                    {"column": "op", "type": "text"},
                    {"column": "value", "type": "numeric"},
                    {"column": "sequence_num", "type": "int"},
                ],
                "example_rows": [
                    {"id": 1, "record_id": 1, "op": "insert", "value": 10.00, "sequence_num": 1},
                    {"id": 2, "record_id": 1, "op": "update", "value": 15.00, "sequence_num": 2},
                    {"id": 3, "record_id": 2, "op": "insert", "value": 20.00, "sequence_num": 1},
                ],
                "expected_output_rows": [
                    {"record_id": 1, "value": 15.00},
                    {"record_id": 2, "value": 20.00},
                ],
            },
        },
        {
            "id": "node_8_dead_letter_queue",
            "type": "skill",
            "title": "Dead-letter queues: quarantine, don't discard",
            "teach": {
                "sql": "SELECT id, failure_reason FROM dead_letter_queue WHERE resolved = false;",
                "note": (
                    "A row that fails validation (node 5) shouldn't just vanish - routing it to a "
                    "dead-letter table instead keeps it inspectable, with a recorded "
                    "failure_reason and a resolved flag for whether someone's already dealt with "
                    "it. Querying 'what's still unresolved' is the operational half of this "
                    "pattern - the half that turns 'we reject bad rows somewhere' into an actual "
                    "worklist a human (or an automated reprocessing job) can act on."
                ),
                "steps": [
                    {
                        "body": "A row that fails validation shouldn't just vanish into the "
                        "ether - but it also can't be allowed to break the rest of the pipeline. "
                        "Where does it go?"
                    },
                    {
                        "body": "Query a dead-letter table for what's still unresolved:",
                        "sql": "SELECT *\nFROM dead_letter_queue\nWHERE resolved = false;",
                    },
                    {
                        "body": "Find every unresolved quarantined row and why it failed:",
                        "sql": "SELECT id, failure_reason FROM dead_letter_queue WHERE resolved = false;",
                    },
                    {
                        "body": "A dead-letter table keeps a rejected row inspectable, with a "
                        "recorded failure_reason and a resolved flag for whether someone's "
                        "already dealt with it - routing it here instead of discarding it is what "
                        "makes a rejection recoverable rather than a silent loss."
                    },
                    {
                        "body": "This is the operational half of node 5's data quality gate: "
                        "the WHERE clause that rejects a bad row is only half the job. The other "
                        "half is this query - the worklist of what's still unresolved, which is "
                        "what a human (or an automated reprocessing job) actually acts on."
                    },
                    {
                        "body": "A common mistake: reprocessing the SAME dead-letter row over "
                        "and over without ever marking it resolved, so it clogs every future "
                        "worklist query forever even after it's been fixed - or the opposite "
                        "mistake, marking a row resolved automatically just because it was "
                        "retried, whether or not the retry actually succeeded. The resolved flag "
                        "needs to be set deliberately, tied to confirmed success, not to the mere "
                        "act of trying again."
                    },
                    {
                        "body": "A dead-letter queue turns a rejection into a recoverable, "
                        "inspectable worklist instead of a silent loss. Try it yourself in the "
                        "Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Find every unresolved dead-letter row and its failure_reason.",
                "table_name": "dead_letter_queue",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "payload", "type": "text"},
                    {"column": "failure_reason", "type": "text"},
                    {"column": "resolved", "type": "boolean"},
                ],
                "example_rows": [
                    {"id": 1, "payload": "{\"amount\": -5}", "failure_reason": "negative_amount", "resolved": False},
                    {"id": 2, "payload": "{\"amount\": 10}", "failure_reason": "missing_account", "resolved": True},
                    {"id": 3, "payload": "{\"amount\": 20}", "failure_reason": "missing_account", "resolved": False},
                ],
                "expected_output_rows": [
                    {"id": 1, "failure_reason": "negative_amount"},
                    {"id": 3, "failure_reason": "missing_account"},
                ],
            },
        },
        {
            "id": "node_9_backfill_reprocessing",
            "type": "skill",
            "title": "Backfills: safely reprocessing a historical window",
            "teach": {
                "sql": (
                    "SELECT id, batch_date::text AS batch_date, amount\n"
                    "FROM fact_daily_loads\n"
                    "WHERE batch_date BETWEEN '2026-01-01' AND '2026-01-02';"
                ),
                "note": (
                    "A backfill reprocesses a specific historical date range - usually because a "
                    "bug was found and fixed, and every day it affected needs to be rerun with the "
                    "corrected logic. A date-range WHERE clause is step one of a real backfill; "
                    "step two (not shown in the query itself, but essential) is making sure the "
                    "write that follows is idempotent for that same range - an upsert keyed on "
                    "(batch_date, some natural key), or a DELETE of the old range followed by a "
                    "fresh INSERT - so rerunning the backfill twice doesn't double the data for "
                    "those days, the same idempotency concern from node 1, now applied to a "
                    "whole historical window instead of one retried request."
                ),
                "steps": [
                    {
                        "body": "A bug gets found and fixed - now every day it affected needs to "
                        "be reprocessed with the corrected logic, without touching days the bug "
                        "never reached."
                    },
                    {
                        "body": "A date-range filter scopes a backfill to exactly the affected window:",
                        "sql": "SELECT *\nFROM fact_table\nWHERE batch_date BETWEEN :start AND :end;",
                    },
                    {
                        "body": "Select the specific historical window that needs reprocessing:",
                        "sql": (
                            "SELECT id, batch_date::text AS batch_date, amount\n"
                            "FROM fact_daily_loads\n"
                            "WHERE batch_date BETWEEN '2026-01-01' AND '2026-01-02';"
                        ),
                    },
                    {
                        "body": "The date-range WHERE clause is step one of a real backfill - "
                        "it scopes exactly which rows get touched, leaving every day the bug "
                        "never reached untouched."
                    },
                    {
                        "body": "Step two matters just as much, even though it isn't visible in "
                        "this SELECT: the WRITE that follows a backfill has to be idempotent for "
                        "that same range - an upsert keyed on (batch_date, some natural key), or "
                        "a DELETE of the old range followed by a fresh INSERT - the same "
                        "idempotency concern as node 1's webhook retries, now applied to a whole "
                        "historical window instead of one retried request. Running a backfill "
                        "twice without that guarantee silently doubles the affected days' data."
                    },
                    {
                        "body": "A common mistake: scoping the backfill's date range too "
                        "narrowly, matching only the days someone REMEMBERS the bug affecting, "
                        "rather than deriving the range from when the buggy code was actually "
                        "deployed and when the fix landed - the honest range is a deployment-"
                        "timestamp question, not a recollection."
                    },
                    {
                        "body": "A backfill reprocesses a scoped historical window, paired with "
                        "an idempotent write so rerunning it twice is still safe. Try it yourself "
                        "in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Select the rows for the affected backfill window: batch_date between 2026-01-01 and 2026-01-02 inclusive.",
                "table_name": "fact_daily_loads",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "batch_date", "type": "date"},
                    {"column": "amount", "type": "numeric"},
                ],
                "example_rows": [
                    {"id": 1, "batch_date": "2026-01-01", "amount": 10.00},
                    {"id": 2, "batch_date": "2026-01-02", "amount": 20.00},
                    {"id": 3, "batch_date": "2026-01-05", "amount": 30.00},
                ],
                "expected_output_rows": [
                    {"id": 1, "batch_date": "2026-01-01", "amount": 10.00},
                    {"id": 2, "batch_date": "2026-01-02", "amount": 20.00},
                ],
            },
        },
        {
            "id": "node_10_data_lineage",
            "type": "skill",
            "title": "Data lineage: knowing where a row actually came from",
            "teach": {
                "sql": "SELECT id, source_system, value FROM ingested_records WHERE source_system = 'new_kafka_feed';",
                "note": (
                    "Lineage starts with the simplest possible audit column: recording which "
                    "upstream source_system produced each row, alongside when it was ingested. "
                    "Once a pipeline merges data from more than one source (a legacy batch API "
                    "being migrated to a new Kafka feed, say), that column is what lets you answer "
                    "'did this number come from the system we trust, or the one we're mid-"
                    "migration away from' - a question that's unanswerable after the fact if the "
                    "source was never recorded on the row itself."
                ),
                "steps": [
                    {
                        "body": "Once a pipeline merges rows from more than one upstream system, "
                        "a natural question becomes unanswerable unless you planned for it: "
                        "which system did THIS particular row actually come from?"
                    },
                    {
                        "body": "An audit column records a row's own origin:",
                        "sql": "SELECT *\nFROM ingested_records\nWHERE source_system = 'the_system_i_care_about';",
                    },
                    {
                        "body": "Find every row that came from the new Kafka feed specifically:",
                        "sql": "SELECT id, source_system, value FROM ingested_records WHERE source_system = 'new_kafka_feed';",
                    },
                    {
                        "body": "source_system is the simplest possible audit column - "
                        "recording which upstream source produced each row, right alongside the "
                        "row itself, rather than relying on tribal knowledge about which pipeline "
                        "run touched what."
                    },
                    {
                        "body": "This matters most exactly during a migration - a legacy batch "
                        "API being phased out in favor of a new Kafka feed, say - where the SAME "
                        "logical record might temporarily be produced by either system. Without a "
                        "source_system column, there's no way to answer 'did this number come "
                        "from the system we trust, or the one we're migrating away from' after "
                        "the fact."
                    },
                    {
                        "body": "A real lineage setup usually pairs source_system with an "
                        "ingested_at timestamp too, so you can answer both 'where did this come "
                        "from' and 'when did we first see it' - the second question is what "
                        "distinguishes a genuinely stale row (ingested long ago, never updated) "
                        "from a fresh one, independent of what the row's own business-level "
                        "timestamp claims."
                    },
                    {
                        "body": "An audit column like source_system records a row's own origin, "
                        "answerable long after the pipeline run that created it has finished. Try "
                        "it yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Find every row that came from the new_kafka_feed source system.",
                "table_name": "ingested_records",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "source_system", "type": "text"},
                    {"column": "ingested_at", "type": "timestamptz"},
                    {"column": "value", "type": "numeric"},
                ],
                "example_rows": [
                    {"id": 1, "source_system": "legacy_api", "ingested_at": "2026-01-01T00:00:00+00", "value": 10.00},
                    {"id": 2, "source_system": "new_kafka_feed", "ingested_at": "2026-01-02T00:00:00+00", "value": 20.00},
                ],
                "expected_output_rows": [
                    {"id": 2, "source_system": "new_kafka_feed", "value": 20.00},
                ],
            },
        },
        {
            "id": "review",
            "type": "review",
            "title": "Review: where these ten ideas already live, for real",
            "prompt": (
                "Idempotency is the Postgres/Lake/Lakehouse dedup logic you've already written. "
                "Schema evolution is the 'renamed field' edge case from the Postgres capstone. "
                "Batch vs. streaming is the watermark check in Postgres, Lake, and the Warehouse "
                "SCD2 re-run. Monitoring is every fault_type_summary a grading report has ever "
                "returned. Data quality gates, dead-letter routing, and incremental watermarks "
                "are the reject/log/dedup logic behind every one of those same fault checks. CDC, "
                "backfills, and lineage are how the real capstones recover once something's "
                "already gone wrong upstream. This track just gave the discipline a name - the "
                "five real capstones are where it actually gets exercised at scale."
            ),
        },
    ],
}
