"""Module 10's exercise description. Content, not logic - same pattern
as the other phases' task_content modules."""

LAKEHOUSE_PHASE_TASK = {
    "title": "Commit two real incremental batches to a Delta table",
    "summary": (
        "The same raw feed as the lake phase, but this time your output is a real Delta table - "
        "not just Parquet. You submit the cleaning SQL (same job as every other phase); the "
        "platform commits your query's result as a genuine, atomic Delta transaction, since "
        "DuckDB itself can't write Delta and this project deliberately doesn't run arbitrary "
        "user code to do it either (see MODULE_10_PLAN.md). Two commits, not one - this phase is "
        "about incremental batch arrival and real ACID guarantees, not a single big load."
    ),
    "source": {
        "batch_1_events": "available immediately - half the raw feed (deterministic, not random)",
        "batch_2_events": "created only after you call release-batch-2 - simulates a new batch arriving later",
    },
    "workflow": [
        "1. Write a SELECT against batch_1_events that parses payload and handles every edge case "
        "(same required shape as the relational/lake phases: event_id, amount, merchant, currency, "
        "event_timestamp). Submit it to POST /lakehouse-phase/sessions/{id}/commit-batch - the "
        "platform runs it and commits the result as Delta version 0.",
        "2. POST /lakehouse-phase/sessions/{id}/release-batch-2 - batch_2_events now exists.",
        "3. Write a SECOND SELECT against batch_2_events ONLY (not a re-processing of batch 1 - "
        "that's the actual incremental-append point) and commit-batch it again.",
        "4. Grade with POST /lakehouse-phase/sessions/{id}/grade.",
    ],
    "required_output": {
        "table": "clean_transactions (a real Delta table, committed via commit-batch - not created by hand)",
        "columns": {
            "event_id": "text, unique, not null",
            "amount": "numeric, not null",
            "merchant": "text",
            "currency": "text",
            "event_timestamp": "timestamptz",
        },
    },
    "hints": [
        "Deduplicating within each batch (e.g. DISTINCT ON per commit) does NOT guarantee global "
        "uniqueness across batches - if the same event_id's rows happen to land in different "
        "batches, a per-batch dedup misses it entirely. Real incremental pipelines handle this "
        "with a merge/upsert against the target table, not just a clean SELECT per batch - worth "
        "checking your grading report's duplicate_delivery findings even if each batch looked clean.",
        "You can inspect your Delta table (and its history) through the normal /execute endpoint: "
        "delta_scan('<path>') for the current state, delta_scan('<path>', version=N) for an "
        "earlier one. Your session's own path is returned when you create the session.",
        "Same DuckDB gotchas as the lake phase apply here too: parenthesize (payload->'field') "
        "before IS NOT NULL, and use TRY_CAST for the ambiguous-date fault, not a bare cast.",
        "Filtering batch 2 with `event_id NOT IN (SELECT event_id FROM delta_scan(...))` fails "
        "with a cryptic cast error at this dataset's real size (confirmed directly, reproducible) "
        "- use a LEFT JOIN against delta_scan(...) and check the joined column IS NULL instead; "
        "it does the same anti-join and works reliably.",
    ],
    "dataset_stats": [
        {"label": "Raw feed rows", "value": "51,495", "hint": "split deterministically across both batches"},
        {"label": "Batch 1 rows", "value": "25,747", "hint": "batch_1_events - id % 2 = 0"},
        {"label": "Batch 2 rows", "value": "25,748", "hint": "batch_2_events - id % 2 = 1, released on request"},
        {"label": "Known-good result size", "value": "49,246 rows", "hint": "clean_transactions across both commits combined"},
    ],
    "starter_sql": (
        "-- Commit 1: parse batch_1_events and handle every edge case.\n"
        "SELECT id, received_at, payload::JSON AS payload\n"
        "FROM batch_1_events\n"
        "LIMIT 20;\n\n"
        "-- Then submit a full SELECT (event_id, amount, merchant, currency, event_timestamp)\n"
        "-- against batch_1_events to commit-batch. Once release-batch-2 is called, do the same\n"
        "-- against batch_2_events ONLY for the second commit.\n"
    ),
    "reference_solution": {
        "sql": (
            "-- Commit 1 (against batch_1_events):\n"
            "WITH normalized AS (\n"
            "  SELECT\n"
            "    COALESCE(payload::JSON->>'event_id', payload::JSON->>'id') AS event_id,\n"
            "    COALESCE(payload::JSON->>'merchant', payload::JSON->>'merchant_name') AS merchant,\n"
            "    payload::JSON->>'currency' AS currency,\n"
            "    CAST((payload::JSON->>'amount')::VARCHAR AS DOUBLE) AS amount,\n"
            "    TRY_CAST(payload::JSON->>'event_timestamp' AS TIMESTAMPTZ) AS event_timestamp,\n"
            "    received_at,\n"
            "    row_number() OVER (\n"
            "      PARTITION BY COALESCE(payload::JSON->>'event_id', payload::JSON->>'id')\n"
            "      ORDER BY received_at DESC\n"
            "    ) AS rn\n"
            "  FROM batch_1_events\n"
            "  WHERE (payload::JSON->'amount') IS NOT NULL\n"
            ")\n"
            "SELECT event_id, amount, merchant, currency, event_timestamp\n"
            "FROM normalized\n"
            "WHERE rn = 1 AND event_timestamp >= received_at - INTERVAL '48 hours';\n\n"
            "-- Commit 2 (against batch_2_events only, after release-batch-2), anti-joined against\n"
            "-- what commit 1 already wrote so a redelivery spanning both batches isn't duplicated:\n"
            "WITH normalized AS (\n"
            "  SELECT event_id, amount, merchant, currency, event_timestamp\n"
            "  FROM (/* same normalization as above, against batch_2_events */) t\n"
            ")\n"
            "SELECT n.*\n"
            "FROM normalized n\n"
            "LEFT JOIN delta_scan('<your delta table path>') existing ON existing.event_id = n.event_id\n"
            "WHERE existing.event_id IS NULL;\n"
        ),
        "note": (
            "Deduplicating within each batch isn't enough - the same event_id's rows can legitimately "
            "land in different batches, so a per-batch dedup misses it. The LEFT JOIN anti-join against "
            "delta_scan() at commit-2 time checks global uniqueness against what's already committed; "
            "`NOT IN (SELECT ... FROM delta_scan(...))` fails with a cryptic cast error at this dataset's "
            "real size, confirmed directly - the anti-join form is the one that actually works."
        ),
    },
}
