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
}
