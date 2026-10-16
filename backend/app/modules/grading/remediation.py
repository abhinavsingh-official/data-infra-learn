"""Hand-authored remediation writeups, one per injected fault error code.
This is the platform's actual teaching mechanism: every entry states why
it broke, at least one concrete fix, and the tradeoffs between valid
approaches where more than one exists - never just detection."""

REMEDIATION = {
    "ERR_NULL_REQUIRED_FIELD": {
        "why": (
            "A required field (amount, merchant, currency, or timestamp) is missing from the "
            "payload entirely - not empty, not zero, the JSON key itself doesn't exist. A naive "
            "`payload->>'amount'` returns SQL NULL for these rows, which then silently propagates "
            "into your clean table unless you check for it."
        ),
        "fix": (
            "Either reject-and-log the row (INSERT INTO a rejects table alongside clean_transactions, "
            "so it's visible rather than silently dropped) or apply a documented default (e.g. amount "
            "defaults to 0 and gets flagged for manual review) - both are valid, pick one and be explicit."
        ),
        "tradeoffs": (
            "Reject-and-log keeps clean_transactions strictly correct but means real revenue/events "
            "are missing until someone reviews the rejects. Defaulting keeps every event represented "
            "but risks a wrong default masquerading as real data if nobody checks the review flag."
        ),
    },
    "ERR_DUPLICATE_DELIVERY": {
        "why": (
            "The same event_id was delivered twice with two different source_delivery_id values - "
            "a real webhook retry, not a copy-paste duplicate. A naive `SELECT DISTINCT *` won't "
            "catch this, since the two rows differ in received_at and source_delivery_id."
        ),
        "fix": (
            "Deduplicate on the business key (event_id from the payload), not the raw table's own id "
            "or source_delivery_id - e.g. `DISTINCT ON (payload->>'event_id')` ordered by received_at, "
            "or a window function keeping the first-arrived row per event_id."
        ),
        "tradeoffs": (
            "Keeping the first-arrived row is simplest and matches most real payment systems' semantics. "
            "Keeping the last-arrived row is defensible too if a resend could plausibly carry corrected "
            "data - the wrong choice silently is worse than either choice made deliberately."
        ),
    },
    "ERR_LATE_ARRIVAL": {
        "why": (
            "received_at is well past the 48-hour watermark relative to the event's own timestamp. "
            "A pipeline that only processes a rolling window (e.g. 'today's events') would miss this "
            "row entirely if it isn't specifically re-scanned for late arrivals."
        ),
        "fix": (
            "Don't filter on received_at falling in a fixed window - either reprocess late arrivals "
            "explicitly, or design the load to scan by the raw table's own id/insertion order rather "
            "than a time window that a late arrival can fall outside of after the fact."
        ),
        "tradeoffs": (
            "A wider window catches more late data but delays when you can consider a batch 'final' "
            "and increases how much needs re-scanning; a narrower window finalizes faster but silently "
            "drops legitimately late data unless explicitly reprocessed."
        ),
    },
    "ERR_SCHEMA_DRIFT_ADDED_FIELD": {
        "why": (
            "The payload has a 'risk_flag' key that earlier events never had. This shouldn't break "
            "anything if your extraction only reads the keys it expects, but a `SELECT *`-style "
            "approach or a strict schema check can choke on the unexpected key."
        ),
        "fix": (
            "Extract fields by name (`payload->>'amount'`), not by assuming a fixed key set - an "
            "unexpected extra key should be ignored by construction, not cause an error."
        ),
        "tradeoffs": (
            "Ignoring unknown fields is safe but means you could be silently missing a genuinely "
            "useful new field (like risk_flag) for months. A stricter pipeline that alerts on any "
            "unrecognized key catches that faster but adds noise for truly harmless additions."
        ),
    },
    "ERR_SCHEMA_DRIFT_RENAMED_FIELD": {
        "why": (
            "'merchant' was renamed to 'merchant_name' partway through the feed. Code that only "
            "reads `payload->>'merchant'` sees NULL for these rows, not an error - the row loads "
            "successfully but with a silently missing merchant, which is worse than a visible failure."
        ),
        "fix": (
            "Coalesce both possible key names: `COALESCE(payload->>'merchant', payload->>'merchant_name')`. "
            "For a real production pipeline, this is exactly the kind of thing a schema registry or "
            "explicit field-mapping config would catch before it reaches this stage."
        ),
        "tradeoffs": (
            "Coalescing both names is quick and unblocks the immediate load, but if the rename is "
            "permanent, you'll be maintaining that coalesce forever. The more correct long-term fix "
            "is updating the extraction to prefer the new name and treating the old one as deprecated."
        ),
    },
    "ERR_SCHEMA_DRIFT_TYPE_CHANGE": {
        "why": (
            "'amount' switched from a decimal string ('1234.56') to an integer in the smallest "
            "currency unit (123456, meaning cents). Naively casting both the same way either "
            "produces a 100x-too-large amount for the integer rows or a cast error."
        ),
        "fix": (
            "Branch on `jsonb_typeof(payload->'amount')`: if it's 'string', cast directly to numeric; "
            "if it's 'number', divide by 100 first. Don't assume a single representation for the "
            "whole feed."
        ),
        "tradeoffs": (
            "Detecting the type at load time handles both representations correctly but adds a branch "
            "to maintain. An alternative is normalizing at the source (upstream) so the feed is never "
            "mixed-type in the first place - not always possible if you don't control the upstream system."
        ),
    },
    "ERR_MALFORMED_EXCEL_CORRUPTION": {
        "why": (
            "An ID-like field was corrupted the way Excel corrupts long numeric text - scientific "
            "notation (e.g. '100E+9' instead of the real 12-digit id) or a stripped leading zero. "
            "The original value is unrecoverable from the corrupted one alone."
        ),
        "fix": (
            "Detect the corrupted shape (matches a scientific-notation pattern, or is suspiciously "
            "short for an ID field) and route to a rejects table rather than silently accepting a "
            "wrong id - there's no way to reconstruct the original value after this kind of corruption."
        ),
        "tradeoffs": (
            "Rejecting means the event is missing from clean_transactions until someone finds the "
            "source of the corruption (usually: someone opened the source CSV in Excel and re-saved "
            "it). The real fix is upstream - never let ID-like fields pass through anything that "
            "guesses numeric types, not something this load step alone can undo."
        ),
    },
    "ERR_MALFORMED_AMBIGUOUS_DATE": {
        "why": (
            "'timestamp' is a bare 'DD/MM/YYYY'-or-'MM/DD/YYYY' string with no way to tell which "
            "convention was used from the string alone - '03/04/2025' is March 4th or April 3rd "
            "depending on which system produced it."
        ),
        "fix": (
            "There's no fully safe automatic fix - either pick a documented convention based on "
            "what's known about the upstream source and flag these rows as lower-confidence, or "
            "reject them for manual confirmation rather than guessing silently."
        ),
        "tradeoffs": (
            "Guessing (even with a documented default convention) risks being systematically wrong "
            "for an entire batch if the assumption is wrong. Rejecting is always correct but means "
            "real events don't make it into clean_transactions without manual intervention."
        ),
    },
}
