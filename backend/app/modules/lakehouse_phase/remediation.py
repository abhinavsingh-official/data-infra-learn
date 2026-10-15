"""Module 10.4: remediation for the three lakehouse-specific structural
checks. Everything fault-type-specific (nulls, duplicates, late arrival,
schema drift, malformed IDs/dates) reuses grading.remediation directly
via grading.report.grade_clean_transactions - the required output
contract and ground truth are identical to the relational phase's, so
that text is identical too, not re-authored here."""

REMEDIATION = {
    "ERR_LAKEHOUSE_NOT_DELTA": {
        "why": (
            "clean_transactions doesn't exist in this session's catalog at all - nothing was "
            "committed. Since only the platform's own commit-batch endpoint can create it, this "
            "means commit-batch was never called successfully."
        ),
        "fix": "Submit your cleaning SELECT to POST /lakehouse-phase/sessions/{id}/commit-batch, not a raw CREATE TABLE via /execute.",
        "tradeoffs": "N/A - this is the only way this phase's required output can exist.",
    },
    "ERR_LAKEHOUSE_NOT_INCREMENTAL": {
        "why": (
            "The Delta table's own commit history shows fewer than 2 write operations - the real "
            "point of this phase (incremental batch commits) wasn't demonstrated. Either "
            "commit-batch was only called once, or one call somehow reprocessed everything at once."
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
            "the whole table every time new data arrives."
        ),
    },
    "ERR_LAKEHOUSE_TIME_TRAVEL_INCORRECT": {
        "why": (
            "Reading the Delta table at the version recorded right after batch 1's commit "
            "returned batch-2 rows (or was missing batch-1 rows) - the commit boundaries aren't "
            "real, which means either the two commits didn't actually happen as separate "
            "transactions, or something rewrote earlier history instead of appending."
        ),
        "fix": "Use mode='append' (the platform's own commit-batch always does this) - never overwrite or recreate the table for a later batch.",
        "tradeoffs": "N/A - a correctness bug in how the commits were structured, not a design choice.",
    },
}
