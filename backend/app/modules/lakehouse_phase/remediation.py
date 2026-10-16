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
            "committed. Since only the platform's own commit-batch endpoint can create it, this "
            "means commit-batch was never called successfully. This check exists specifically "
            "because a lakehouse's core promise - real ACID transactions and time travel, not "
            "just files sitting in a directory - only holds for a table that went through the "
            "Delta transaction log at creation; a table created any other way wouldn't have that "
            "log, and none of the guarantees this phase is testing would actually apply to it."
        ),
        "fix": "Submit your cleaning SELECT to POST /lakehouse-phase/sessions/{id}/commit-batch, not a raw CREATE TABLE via /execute.",
        "tradeoffs": "N/A - this is the only way this phase's required output can exist.",
    },
    "ERR_LAKEHOUSE_NOT_INCREMENTAL": {
        "why": (
            "The Delta table's own commit history shows fewer than 2 write operations - the real "
            "point of this phase (incremental batch commits) wasn't demonstrated. Either "
            "commit-batch was only called once, or one call somehow reprocessed everything at once. "
            "A single-commit table that happens to contain the right final rows can look "
            "indistinguishable from a correctly incremental one by querying its current state "
            "alone - which is exactly why this check reads the table's own commit history "
            "(DESCRIBE HISTORY) rather than just checking the data, the same 'don't just check the "
            "end state, check how it got there' principle as the warehouse phase's SCD2 history checks."
        ),
        "fix": (
            "Call commit-batch once against batch_1_events, then again - after "
            "release-batch-2 - against batch_2_events ONLY, not a UNION of both. Two real "
            "incremental appends, not one big rebuild split across two API calls."
        ),
        "tradeoffs": (
            "A full reprocess-and-overwrite on every batch is simpler to reason about (no "
            "cross-batch duplicate risk - see the fault-type findings below) but defeats the "
            "actual point of a lakehouse: cheap, atomic, incremental commits instead of rewriting "
            "the whole table every time new data arrives. At real scale, rewriting the entire "
            "table on every new batch becomes prohibitively expensive as the table grows - the "
            "whole economic case for a lakehouse's incremental-append model is that the cost of "
            "ingesting one new batch stays roughly constant, rather than growing with the size of "
            "everything already committed."
        ),
    },
    "ERR_LAKEHOUSE_TIME_TRAVEL_INCORRECT": {
        "why": (
            "Reading the Delta table at the version recorded right after batch 1's commit "
            "returned batch-2 rows (or was missing batch-1 rows) - the commit boundaries aren't "
            "real, which means either the two commits didn't actually happen as separate "
            "transactions, or something rewrote earlier history instead of appending. Real time "
            "travel works because each Delta commit adds an immutable, numbered entry to the "
            "transaction log recording exactly which data files were added (and removed) in that "
            "commit - querying 'as of version N' simply replays the log up to that entry; if that "
            "replay produces the wrong rows, the log itself doesn't actually describe two distinct "
            "atomic commits the way it should."
        ),
        "fix": "Use mode='append' (the platform's own commit-batch always does this) - never overwrite or recreate the table for a later batch.",
        "tradeoffs": "N/A - a correctness bug in how the commits were structured, not a design choice.",
    },
}
