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
            "into your clean table unless you check for it. Mechanically this is Postgres's jsonb "
            "`->>` operator behaving exactly as documented: looking up a key that isn't present in "
            "the object returns NULL rather than raising an error, which is the correct behavior "
            "for `->>` in general but means a missing-key bug and a present-but-null-value bug are "
            "indistinguishable downstream unless you check `payload ? 'amount'` (key existence) "
            "separately from `payload->>'amount' IS NULL` (value nullness)."
        ),
        "fix": (
            "Either reject-and-log the row (INSERT INTO a rejects table alongside clean_transactions, "
            "so it's visible rather than silently dropped) or apply a documented default (e.g. amount "
            "defaults to 0 and gets flagged for manual review) - both are valid, pick one and be explicit. "
            "In either case, the decision belongs in one place in the pipeline (the load step itself), "
            "not scattered across every downstream query that happens to touch the field - a query "
            "three joins away from the raw payload shouldn't have to independently rediscover that "
            "amount can be missing and decide what to do about it."
        ),
        "tradeoffs": (
            "Reject-and-log keeps clean_transactions strictly correct but means real revenue/events "
            "are missing until someone reviews the rejects. Defaulting keeps every event represented "
            "but risks a wrong default masquerading as real data if nobody checks the review flag. "
            "The choice also depends on what the field is for: a missing `currency` is usually safe "
            "to default (a fintech feed is overwhelmingly one currency in practice), while a missing "
            "`amount` almost never is - defaulting a dollar amount to 0 means a real transaction "
            "silently reports as free, which is a far worse failure mode than simply not having the "
            "row yet."
        ),
    },
    "ERR_DUPLICATE_DELIVERY": {
        "why": (
            "The same event_id was delivered twice with two different source_delivery_id values - "
            "a real webhook retry, not a copy-paste duplicate. A naive `SELECT DISTINCT *` won't "
            "catch this, since the two rows differ in received_at and source_delivery_id. This is "
            "also why 'just add a UNIQUE constraint on id' doesn't help here - the raw table's own "
            "id is already unique per row by construction (it's a surrogate key assigned at "
            "insert); the duplication lives one level down, inside the payload, on a key the "
            "database has no built-in concept of until you explicitly extract and constrain on it."
        ),
        "fix": (
            "Deduplicate on the business key (event_id from the payload), not the raw table's own id "
            "or source_delivery_id - e.g. `DISTINCT ON (payload->>'event_id')` ordered by received_at, "
            "or a window function keeping the first-arrived row per event_id. For a load that runs "
            "repeatedly over time rather than once, the more robust version of this fix is a real "
            "UNIQUE constraint on the business key in the clean table itself, with ON CONFLICT DO "
            "NOTHING on insert - turning the dedup from a read-time query you have to remember to "
            "write correctly every time into a write-time guarantee the database enforces for you."
        ),
        "tradeoffs": (
            "Keeping the first-arrived row is simplest and matches most real payment systems' semantics. "
            "Keeping the last-arrived row is defensible too if a resend could plausibly carry corrected "
            "data - the wrong choice silently is worse than either choice made deliberately. A third, "
            "sometimes-overlooked option is to keep both and record the fact that a redelivery "
            "happened (via an audit/rejects table) rather than discarding the second row entirely - "
            "useful when the resend pattern itself is operationally interesting, e.g. for detecting "
            "an upstream sender that's retrying far more than it should be."
        ),
    },
    "ERR_LATE_ARRIVAL": {
        "why": (
            "received_at is well past the 48-hour watermark relative to the event's own timestamp. "
            "A pipeline that only processes a rolling window (e.g. 'today's events') would miss this "
            "row entirely if it isn't specifically re-scanned for late arrivals. The root cause is "
            "almost always outside your own system - a merchant's payment processor queued the "
            "webhook, a network partition delayed delivery, or an upstream retry backed off for "
            "hours before finally succeeding - which is exactly why 'late' has to be designed for "
            "as a normal case, not treated as an anomaly to investigate case by case."
        ),
        "fix": (
            "Don't filter on received_at falling in a fixed window - either reprocess late arrivals "
            "explicitly, or design the load to scan by the raw table's own id/insertion order rather "
            "than a time window that a late arrival can fall outside of after the fact. A load keyed "
            "off 'every row not yet loaded' (e.g. an anti-join against the clean table, or a "
            "high-water-mark on the raw table's own id) is immune to this failure mode by "
            "construction, because it never relies on a time-based cutoff in the first place."
        ),
        "tradeoffs": (
            "A wider window catches more late data but delays when you can consider a batch 'final' "
            "and increases how much needs re-scanning; a narrower window finalizes faster but silently "
            "drops legitimately late data unless explicitly reprocessed. There's no watermark width "
            "that eliminates this tradeoff entirely - even a very wide window just moves the goalpost "
            "for 'how late is too late', it doesn't remove the underlying tension between speed and "
            "completeness."
        ),
    },
    "ERR_SCHEMA_DRIFT_ADDED_FIELD": {
        "why": (
            "The payload has a 'risk_flag' key that earlier events never had. This shouldn't break "
            "anything if your extraction only reads the keys it expects, but a `SELECT *`-style "
            "approach or a strict schema check can choke on the unexpected key. In jsonb terms this "
            "is almost never a real break in Postgres itself - jsonb happily stores arbitrary extra "
            "keys - the actual breakage, when it happens, is usually one level up: a downstream "
            "consumer with a strict JSON-schema validator, or a typed deserializer (a Pydantic model "
            "with `extra = 'forbid'`, for instance) that was never told the new field was coming."
        ),
        "fix": (
            "Extract fields by name (`payload->>'amount'`), not by assuming a fixed key set - an "
            "unexpected extra key should be ignored by construction, not cause an error. If the new "
            "field is actually useful (as risk_flag plausibly is), the real fix isn't just tolerating "
            "it silently forever - it's noticing it, deciding deliberately whether to start "
            "extracting it, and updating the pipeline's schema documentation to say so."
        ),
        "tradeoffs": (
            "Ignoring unknown fields is safe but means you could be silently missing a genuinely "
            "useful new field (like risk_flag) for months. A stricter pipeline that alerts on any "
            "unrecognized key catches that faster but adds noise for truly harmless additions - "
            "the practical middle ground many real pipelines use is monitoring the SET of distinct "
            "top-level keys seen over a rolling window and diffing it against the known schema "
            "periodically, rather than either ignoring drift forever or alerting on every single "
            "occurrence."
        ),
    },
    "ERR_SCHEMA_DRIFT_RENAMED_FIELD": {
        "why": (
            "'merchant' was renamed to 'merchant_name' partway through the feed. Code that only "
            "reads `payload->>'merchant'` sees NULL for these rows, not an error - the row loads "
            "successfully but with a silently missing merchant, which is worse than a visible failure. "
            "This is the single most dangerous category of the three schema-drift faults precisely "
            "because it's indistinguishable, downstream, from ERR_NULL_REQUIRED_FIELD - both produce "
            "a NULL where real data belongs, so without inspecting the raw payload directly you "
            "can't tell 'this field was genuinely never populated' from 'this field exists, just "
            "under a name I'm not looking for'."
        ),
        "fix": (
            "Coalesce both possible key names: `COALESCE(payload->>'merchant', payload->>'merchant_name')`. "
            "For a real production pipeline, this is exactly the kind of thing a schema registry or "
            "explicit field-mapping config would catch before it reaches this stage - ideally the "
            "rename is detected and the mapping updated the moment it happens upstream, not "
            "discovered retroactively because a report started showing unexplained NULLs."
        ),
        "tradeoffs": (
            "Coalescing both names is quick and unblocks the immediate load, but if the rename is "
            "permanent, you'll be maintaining that coalesce forever. The more correct long-term fix "
            "is updating the extraction to prefer the new name and treating the old one as deprecated - "
            "and explicitly logging whenever the OLD name is still seen in a new row, which is the "
            "signal that tells you it's finally safe to drop the coalesce and the old-name branch "
            "entirely."
        ),
    },
    "ERR_SCHEMA_DRIFT_TYPE_CHANGE": {
        "why": (
            "'amount' switched from a decimal string ('1234.56') to an integer in the smallest "
            "currency unit (123456, meaning cents). Naively casting both the same way either "
            "produces a 100x-too-large amount for the integer rows or a cast error. This is the one "
            "schema-drift fault that's actively dangerous rather than merely inconvenient: unlike a "
            "NULL, a 100x-too-large dollar amount is a plausible-looking number that passes every "
            "not-null check, every type check, and likely every sanity-bound check too, since "
            "$360,961.00 is a large but not impossible transaction amount."
        ),
        "fix": (
            "Branch on `jsonb_typeof(payload->'amount')`: if it's 'string', cast directly to numeric; "
            "if it's 'number', divide by 100 first. Don't assume a single representation for the "
            "whole feed - this is exactly why `jsonb_typeof` exists as a function at all: to let a "
            "query ask 'what shape is this value actually in' rather than assuming one shape and "
            "letting a mismatched cast fail loudly or, worse, succeed quietly with the wrong value."
        ),
        "tradeoffs": (
            "Detecting the type at load time handles both representations correctly but adds a branch "
            "to maintain. An alternative is normalizing at the source (upstream) so the feed is never "
            "mixed-type in the first place - not always possible if you don't control the upstream system. "
            "Whichever fix is chosen, this is also exactly the kind of error class that benefits from a "
            "post-load sanity check independent of the load logic itself - e.g. flagging any loaded "
            "amount above a documented outlier threshold for a second look, as a safety net against "
            "a type-detection bug nobody caught."
        ),
    },
    "ERR_MALFORMED_EXCEL_CORRUPTION": {
        "why": (
            "An ID-like field was corrupted the way Excel corrupts long numeric text - scientific "
            "notation (e.g. '100E+9' instead of the real 12-digit id) or a stripped leading zero. "
            "The original value is unrecoverable from the corrupted one alone. This happens because "
            "Excel auto-detects a column's type from its contents on open, with no way to opt out "
            "short of pre-formatting the column as Text before the data ever lands in it - a long "
            "digit string gets silently reinterpreted as a number, rounded to float precision, and "
            "re-rendered in scientific notation, and once that round-trip has happened, the exact "
            "original digits are simply gone, not merely hidden."
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
            "guesses numeric types, not something this load step alone can undo. In practice this "
            "means treating it as a process problem (whoever is hand-editing the export needs a "
            "different tool or a text-formatted column), not a query the pipeline can be made "
            "clever enough to work around - detection buys visibility, not recovery."
        ),
    },
    "ERR_MALFORMED_AMBIGUOUS_DATE": {
        "why": (
            "'timestamp' is a bare 'DD/MM/YYYY'-or-'MM/DD/YYYY' string with no way to tell which "
            "convention was used from the string alone - '03/04/2025' is March 4th or April 3rd "
            "depending on which system produced it. The genuinely hard part is that this fault is "
            "invisible for 12 of every 31 possible day values: any day number from 13-31 instantly "
            "reveals which convention is in play, but a day number from 1-12 is silently ambiguous - "
            "meaning a naive parser can look correct on most rows and be wrong specifically on the "
            "rows where it matters least to notice."
        ),
        "fix": (
            "There's no fully safe automatic fix - either pick a documented convention based on "
            "what's known about the upstream source and flag these rows as lower-confidence, or "
            "reject them for manual confirmation rather than guessing silently. If other fields in "
            "the same payload carry an unambiguous timestamp (an ISO 8601 string elsewhere, or a "
            "received_at you can bound the event against), use that as a cross-check before "
            "trusting a guessed interpretation of the ambiguous one."
        ),
        "tradeoffs": (
            "Guessing (even with a documented default convention) risks being systematically wrong "
            "for an entire batch if the assumption is wrong. Rejecting is always correct but means "
            "real events don't make it into clean_transactions without manual intervention. The "
            "real, durable fix doesn't live in this load step at all - it's requiring every "
            "timestamp a source system emits to be ISO 8601 (YYYY-MM-DD), which is unambiguous by "
            "construction and has no DD/MM-vs-MM/DD question to even ask; that's a data-contract "
            "fix to push upstream, not a parsing trick to get cleverer about downstream."
        ),
    },
}
