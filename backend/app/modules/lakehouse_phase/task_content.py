"""Module 19 rewrite of Module 10's exercise description for PySpark/
Delta instead of DuckDB + the `deltalake` Python library
(ARCHITECTURE_DECISIONS.md §3.1). Real content changes, verified by
actually running every statement against a real session first (see
MODULE_19_PLAN.md):
- No more `pg.`-qualified source tables - plain unqualified
  raw_transaction_events, same reasoning as the warehouse/lake phases.
- DuckDB's `payload::JSON->>'field'` becomes Spark SQL's
  `get_json_object(payload, '$.field')`.
- `TRY_CAST(... AS TIMESTAMPTZ)` alone cannot recover the
  malformed_ambiguous_date fault's real DD/MM/YYYY-only string on this
  engine - needs an explicit fallback format, same fix as the lake phase:
  `COALESCE(TRY_CAST(ts AS TIMESTAMP), try_to_timestamp(ts, 'dd/MM/yyyy'))`.
- No more `delta_scan('<path>')` - clean_transactions is now a real
  Spark-catalog table (committed via `saveAsTable`, not a bare path), so
  it's just referenced directly by name, including for time travel
  (`clean_transactions VERSION AS OF 0`) and history
  (`DESCRIBE HISTORY clean_transactions`) - both confirmed working
  directly on a catalog (not just path-based) Delta table.
- Late arrivals are kept, not dropped past the 48-hour watermark - same
  platform-wide fix applied to the Postgres and Lake phases, for the
  same reason (see MODULE_19_PLAN.md: the curriculum and the shared
  grader disagreed about this; confirmed with the user which was
  intended). Rows missing currency or timestamp entirely are still
  explicitly rejected, the same reject-and-log policy as every other
  required field."""

LAKEHOUSE_PHASE_TASK = {
    "title": "Commit two real incremental batches to a Delta table",
    "summary": (
        "The same raw feed as the lake phase, but this time your output is a real Delta table - "
        "not just Parquet. You submit the cleaning SQL (same job as every other phase); the "
        "platform commits your query's result as a genuine, atomic Delta transaction via Spark's "
        "own writer. Two commits, not one - this phase is about incremental batch arrival and "
        "real ACID guarantees, not a single big load."
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
        "Deduplicating within each batch does NOT guarantee global uniqueness across batches - if "
        "the same event_id's rows happen to land in different batches, a per-batch dedup misses it "
        "entirely. Real incremental pipelines handle this with a merge/anti-join against the target "
        "table, not just a clean SELECT per batch.",
        "You can inspect your Delta table (and its history) through the normal /execute endpoint, by "
        "name: clean_transactions for the current state, clean_transactions VERSION AS OF 0 for an "
        "earlier one, DESCRIBE HISTORY clean_transactions for the full commit log.",
        "Same Spark SQL gotchas as the lake phase apply here too: get_json_object(payload, "
        "'$.field') instead of a bare -> operator, and COALESCE(TRY_CAST(...), try_to_timestamp(..., "
        "'dd/MM/yyyy')) for the ambiguous-date fault.",
        "A LEFT JOIN anti-join (keep rows with no match) against clean_transactions is the reliable "
        "way to check what's already committed before batch 2's commit - simpler to reason about "
        "than a NOT IN subquery once the target table has real volume.",
    ],
    "dataset_stats": [
        {"label": "Raw feed rows", "value": "51,495", "hint": "split deterministically across both batches"},
        {"label": "Batch 1 rows", "value": "25,747", "hint": "batch_1_events - id % 2 = 0"},
        {"label": "Batch 2 rows", "value": "25,748", "hint": "batch_2_events - id % 2 = 1, released on request"},
        {"label": "Known-good result size", "value": "47,755 rows", "hint": "clean_transactions across both commits combined (late arrivals kept, not dropped)"},
    ],
    "starter_sql": (
        "-- Commit 1: parse batch_1_events and handle every edge case.\n"
        "SELECT id, received_at, payload\n"
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
            "    COALESCE(get_json_object(payload, '$.event_id'), get_json_object(payload, '$.id')) AS event_id,\n"
            "    COALESCE(get_json_object(payload, '$.merchant'), get_json_object(payload, '$.merchant_name')) AS merchant,\n"
            "    get_json_object(payload, '$.currency') AS currency,\n"
            "    CAST(get_json_object(payload, '$.amount') AS DOUBLE) AS amount,\n"
            "    COALESCE(TRY_CAST(get_json_object(payload, '$.timestamp') AS TIMESTAMP), try_to_timestamp(get_json_object(payload, '$.timestamp'), 'dd/MM/yyyy')) AS event_timestamp,\n"
            "    received_at,\n"
            "    row_number() OVER (\n"
            "      PARTITION BY COALESCE(get_json_object(payload, '$.event_id'), get_json_object(payload, '$.id'))\n"
            "      ORDER BY received_at DESC\n"
            "    ) AS rn\n"
            "  FROM batch_1_events\n"
            "  WHERE get_json_object(payload, '$.amount') IS NOT NULL\n"
            "    AND (get_json_object(payload, '$.merchant') IS NOT NULL OR get_json_object(payload, '$.merchant_name') IS NOT NULL)\n"
            "    AND get_json_object(payload, '$.currency') IS NOT NULL\n"
            "    AND get_json_object(payload, '$.timestamp') IS NOT NULL\n"
            ")\n"
            "SELECT event_id, amount, merchant, currency, event_timestamp\n"
            "FROM normalized\n"
            "WHERE rn = 1;\n\n"
            "-- Commit 2 (against batch_2_events only, after release-batch-2), anti-joined against\n"
            "-- what commit 1 already wrote so a redelivery spanning both batches isn't duplicated:\n"
            "WITH normalized AS (\n"
            "  SELECT\n"
            "    COALESCE(get_json_object(payload, '$.event_id'), get_json_object(payload, '$.id')) AS event_id,\n"
            "    COALESCE(get_json_object(payload, '$.merchant'), get_json_object(payload, '$.merchant_name')) AS merchant,\n"
            "    get_json_object(payload, '$.currency') AS currency,\n"
            "    CAST(get_json_object(payload, '$.amount') AS DOUBLE) AS amount,\n"
            "    COALESCE(TRY_CAST(get_json_object(payload, '$.timestamp') AS TIMESTAMP), try_to_timestamp(get_json_object(payload, '$.timestamp'), 'dd/MM/yyyy')) AS event_timestamp,\n"
            "    row_number() OVER (\n"
            "      PARTITION BY COALESCE(get_json_object(payload, '$.event_id'), get_json_object(payload, '$.id'))\n"
            "      ORDER BY received_at DESC\n"
            "    ) AS rn\n"
            "  FROM batch_2_events\n"
            "  WHERE get_json_object(payload, '$.amount') IS NOT NULL\n"
            "    AND (get_json_object(payload, '$.merchant') IS NOT NULL OR get_json_object(payload, '$.merchant_name') IS NOT NULL)\n"
            "    AND get_json_object(payload, '$.currency') IS NOT NULL\n"
            "    AND get_json_object(payload, '$.timestamp') IS NOT NULL\n"
            ")\n"
            "SELECT n.event_id, n.amount, n.merchant, n.currency, n.event_timestamp\n"
            "FROM normalized n\n"
            "LEFT JOIN clean_transactions existing ON existing.event_id = n.event_id\n"
            "WHERE n.rn = 1 AND existing.event_id IS NULL;\n"
        ),
        "note": (
            "Deduplicating within each batch isn't enough - the same event_id's rows can legitimately "
            "land in different batches, so a per-batch dedup misses it. The LEFT JOIN anti-join against "
            "clean_transactions at commit-2 time checks global uniqueness against what's already "
            "committed - a plain table reference now, not a path-based delta_scan(), since "
            "clean_transactions is a real catalog table once commit 1 has run."
        ),
        "steps": [
            {
                "title": "1. Naive - commit batch 1 with no in-batch dedup at all",
                "sql": (
                    "SELECT\n"
                    "  COALESCE(get_json_object(payload, '$.event_id'), get_json_object(payload, '$.id')) AS event_id,\n"
                    "  CAST(get_json_object(payload, '$.amount') AS DOUBLE) AS amount,\n"
                    "  COALESCE(get_json_object(payload, '$.merchant'), get_json_object(payload, '$.merchant_name')) AS merchant,\n"
                    "  get_json_object(payload, '$.currency') AS currency,\n"
                    "  TRY_CAST(get_json_object(payload, '$.timestamp') AS TIMESTAMP) AS event_timestamp\n"
                    "FROM batch_1_events\n"
                    "WHERE get_json_object(payload, '$.amount') IS NOT NULL;\n"
                ),
                "note": (
                    "This parses every row's payload correctly but assumes batch_1_events itself has no "
                    "internal repeats. It doesn't hold - the raw feed still contains redelivered events, "
                    "and this commit would insert every copy of one as a separate row in the Delta table."
                ),
            },
            {
                "title": "2. + dedupe within the batch (still misses cross-batch duplicates)",
                "sql": (
                    "WITH normalized AS (\n"
                    "  SELECT\n"
                    "    COALESCE(get_json_object(payload, '$.event_id'), get_json_object(payload, '$.id')) AS event_id,\n"
                    "    COALESCE(get_json_object(payload, '$.merchant'), get_json_object(payload, '$.merchant_name')) AS merchant,\n"
                    "    get_json_object(payload, '$.currency') AS currency,\n"
                    "    CAST(get_json_object(payload, '$.amount') AS DOUBLE) AS amount,\n"
                    "    TRY_CAST(get_json_object(payload, '$.timestamp') AS TIMESTAMP) AS event_timestamp,\n"
                    "    received_at,\n"
                    "    row_number() OVER (\n"
                    "      PARTITION BY COALESCE(get_json_object(payload, '$.event_id'), get_json_object(payload, '$.id'))\n"
                    "      ORDER BY received_at DESC\n"
                    "    ) AS rn\n"
                    "  FROM batch_1_events\n"
                    "  WHERE get_json_object(payload, '$.amount') IS NOT NULL\n"
                    ")\n"
                    "SELECT event_id, amount, merchant, currency, event_timestamp\n"
                    "FROM normalized\n"
                    "WHERE rn = 1;\n"
                ),
                "note": (
                    "This is a fully correct commit for batch 1 on its own - row_number() dedupes within "
                    "the batch. It's still not the whole story: if a redelivery of the same event_id "
                    "happens to fall in batch 2 instead of batch 1, this per-batch query has no way to "
                    "see that from inside batch 1's commit."
                ),
            },
            {
                "title": "3. Commit batch 2 the same way - and expose the gap",
                "sql": (
                    "-- same normalized CTE as step 2, run against batch_2_events instead:\n"
                    "SELECT event_id, amount, merchant, currency, event_timestamp\n"
                    "FROM normalized\n"
                    "WHERE rn = 1;\n"
                ),
                "note": (
                    "Committing batch 2 with the identical per-batch-clean query is the naive version of "
                    "incremental append - and it's exactly where the gap in step 2 becomes real: any "
                    "event_id whose redelivery split across both batches now exists as two separate rows "
                    "in the Delta table, one from each commit, and neither commit's own dedup ever saw both."
                ),
            },
            {
                "title": "4. Final: + anti-join batch 2 against what's already committed",
                "sql": (
                    "-- same normalized CTE as step 2/3, plus one more join on the final SELECT:\n"
                    "SELECT n.event_id, n.amount, n.merchant, n.currency, n.event_timestamp\n"
                    "FROM normalized n\n"
                    "LEFT JOIN clean_transactions existing ON existing.event_id = n.event_id\n"
                    "WHERE n.rn = 1 AND existing.event_id IS NULL;\n"
                ),
                "note": (
                    "The fix is a global check, not a better per-batch dedup: LEFT JOIN batch 2's cleaned "
                    "rows against clean_transactions (what commit 1 already wrote), and keep only the "
                    "ones with no match - a reliable anti-join, not a NOT IN subquery that gets harder to "
                    "reason about as the target table grows."
                ),
            },
        ],
    },
}
