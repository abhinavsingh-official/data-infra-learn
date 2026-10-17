"""Remediation for the three lakehouse-specific structural checks.
Everything fault-type-specific (nulls, duplicates, late arrival, schema
drift, malformed IDs/dates) reuses grading.remediation directly via
grading.report.grade_clean_transactions - the required output contract
and ground truth are identical to the relational phase's, so that text
is identical too, not re-authored here."""

REMEDIATION = {
    "ERR_LAKEHOUSE_NOT_DELTA": {
        "why": (
            "clean_transactions doesn't exist in this session's catalog at all - nothing was "
            "committed, since only the platform's commit-batch endpoint can create it. A "
            "lakehouse's core promise - real ACID transactions and time travel - only holds for a "
            "table that went through the Delta transaction log at creation; a table created any "
            "other way wouldn't have that log."
        ),
        "fix": "Submit your cleaning SELECT to the commit-batch endpoint, not a raw CREATE TABLE.",
        "fix_sql": (
            "-- via POST /lakehouse-phase/sessions/{id}/commit-batch, body = your SELECT:\n"
            "SELECT event_id, amount, merchant, currency, event_timestamp\n"
            "FROM normalized WHERE rn = 1;  -- the platform commits this result as Delta version 0"
        ),
        "tradeoffs": "N/A - this is the only way this phase's required output can exist.",
    },
    "ERR_LAKEHOUSE_NOT_INCREMENTAL": {
        "why": (
            "The Delta table's own commit history shows fewer than 2 write operations - the real "
            "point of this phase wasn't demonstrated. A single-commit table containing the right "
            "final rows looks indistinguishable from a correctly incremental one by querying its "
            "current state alone, which is why this check reads DESCRIBE HISTORY instead."
        ),
        "fix": "Call commit-batch once against batch_1_events, then again - after release-batch-2 - against batch_2_events ONLY, never a UNION of both.",
        "fix_sql": (
            "-- commit 1: POST .../commit-batch with a SELECT against batch_1_events\n"
            "-- commit 2 (after release-batch-2): POST .../commit-batch with a SELECT against\n"
            "-- batch_2_events only\n"
            "DESCRIBE HISTORY clean_transactions;  -- should show 2 write operations"
        ),
        "tradeoffs": (
            "A full reprocess-and-overwrite on every batch is simpler to reason about but defeats "
            "the point of a lakehouse: cheap, atomic, incremental commits instead of rewriting the "
            "whole table every time new data arrives. At real scale, the economic case for "
            "incremental append is that ingesting one new batch stays roughly constant cost, "
            "rather than growing with everything already committed."
        ),
    },
    "ERR_LAKEHOUSE_TIME_TRAVEL_INCORRECT": {
        "why": (
            "Reading the Delta table at the version recorded right after batch 1's commit returned "
            "batch-2 rows (or was missing batch-1 rows) - the commit boundaries aren't real, "
            "meaning the two commits didn't happen as separate transactions, or something rewrote "
            "earlier history instead of appending."
        ),
        "fix": "Always append, never overwrite or recreate the table for a later batch - the platform's own commit-batch does this for you.",
        "fix_sql": (
            "SELECT COUNT(*) FROM clean_transactions VERSION AS OF 0;  -- batch 1's rows only\n"
            "SELECT COUNT(*) FROM clean_transactions VERSION AS OF 1;  -- batch 1 + batch 2 combined"
        ),
        "tradeoffs": "N/A - a correctness bug in how the commits were structured, not a design choice.",
    },
}
