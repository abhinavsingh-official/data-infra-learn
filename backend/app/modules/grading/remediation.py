"""Hand-authored remediation writeups, one per injected fault error code.
This is the platform's actual teaching mechanism: every entry states why
it broke, at least one concrete fix, and the tradeoffs between valid
approaches where more than one exists - never just detection."""

REMEDIATION = {
    "ERR_NULL_REQUIRED_FIELD": {
        "why": (
            "A required field (amount, merchant, currency, or timestamp) is missing from the "
            "payload entirely - not empty, not zero, the JSON key itself doesn't exist. A naive "
            "`payload->>'amount'` returns SQL NULL for these rows and that NULL silently propagates "
            "downstream unless checked. `payload ? 'amount'` (key existence) and `payload->>'amount' "
            "IS NULL` (value nullness) are two different questions that look identical once the "
            "value has already been extracted."
        ),
        "fix": (
            "Reject-and-log the row into a rejects table, or apply a documented default - make the "
            "decision once at load time, not downstream."
        ),
        "fix_sql": (
            "INSERT INTO rejected_transactions (raw_event_id, reason)\n"
            "SELECT id, 'missing required field: amount'\n"
            "FROM raw_transaction_events\n"
            "WHERE NOT (payload ? 'amount') OR payload->>'amount' IS NULL;"
        ),
        "tradeoffs": (
            "Reject-and-log keeps clean_transactions strictly correct but leaves real events missing "
            "until someone reviews the rejects; defaulting keeps every event represented but risks a "
            "wrong default passing as real data. The right call depends on the field: a missing "
            "`currency` is usually safe to default, while a missing `amount` almost never is - "
            "defaulting it to 0 makes a real transaction silently report as free."
        ),
    },
    "ERR_DUPLICATE_DELIVERY": {
        "why": (
            "The same event_id was delivered twice with two different source_delivery_id values - "
            "a real webhook retry, not a copy-paste duplicate. A naive `SELECT DISTINCT *` won't "
            "catch this, since the two rows differ in received_at and source_delivery_id. The raw "
            "table's own id is already unique per row by construction, so the duplication lives one "
            "level down, inside the payload, on a key the database has no built-in concept of."
        ),
        "fix": (
            "Deduplicate on the business key (event_id from the payload), not the raw table's own id "
            "or source_delivery_id."
        ),
        "fix_sql": (
            "SELECT DISTINCT ON (payload->>'event_id')\n"
            "  payload->>'event_id' AS event_id, payload, received_at\n"
            "FROM raw_transaction_events\n"
            "ORDER BY payload->>'event_id', received_at ASC;"
        ),
        "tradeoffs": (
            "Keeping the first-arrived row is simplest and matches most real payment systems' "
            "semantics; keeping the last-arrived row is defensible too if a resend could carry "
            "corrected data. A load that runs repeatedly should go further and add a real UNIQUE "
            "constraint on the business key with ON CONFLICT DO NOTHING, turning the dedup from a "
            "read-time query into a write-time guarantee."
        ),
    },
    "ERR_LATE_ARRIVAL": {
        "why": (
            "received_at is well past the 48-hour watermark relative to the event's own timestamp. "
            "A pipeline that only processes a rolling window (e.g. 'today's events') misses this row "
            "entirely unless it's specifically re-scanned. The root cause is almost always outside "
            "your own system - a delayed webhook or a backed-off retry - which is why 'late' has to "
            "be designed for as a normal case, not an anomaly."
        ),
        "fix": (
            "Don't filter on received_at falling in a fixed window - load every row the clean table "
            "doesn't have yet, regardless of when it arrived."
        ),
        "fix_sql": (
            "SELECT r.id\n"
            "FROM raw_transaction_events r\n"
            "LEFT JOIN clean_transactions c ON c.raw_event_id = r.id\n"
            "WHERE c.raw_event_id IS NULL;"
        ),
        "tradeoffs": (
            "A wider time-based window catches more late data but delays when a batch can be "
            "considered 'final'; a narrower one finalizes faster but silently drops legitimately "
            "late data. An anti-join/high-water-mark load like the one above sidesteps the tradeoff "
            "entirely by never relying on a time cutoff in the first place."
        ),
    },
    "ERR_SCHEMA_DRIFT_ADDED_FIELD": {
        "why": (
            "The payload has a 'risk_flag' key that earlier events never had. jsonb happily stores "
            "arbitrary extra keys, so this is rarely a break in Postgres itself - the breakage, when "
            "it happens, is one level up: a `SELECT *`-style extraction, a strict JSON-schema "
            "validator, or a typed deserializer with `extra = 'forbid'` that was never told the new "
            "field was coming."
        ),
        "fix": "Extract fields by name, not by assuming a fixed key set - an unexpected extra key should be ignored by construction.",
        "fix_sql": (
            "SELECT\n"
            "  payload->>'event_id' AS event_id,\n"
            "  (payload->>'amount')::numeric AS amount\n"
            "FROM raw_transaction_events;  -- 'risk_flag' is simply never referenced"
        ),
        "tradeoffs": (
            "Ignoring unknown fields is safe but means a genuinely useful new field (like risk_flag) "
            "could go unused for months. A stricter pipeline that alerts on any unrecognized key "
            "catches that faster but adds noise - the practical middle ground is periodically "
            "diffing the set of observed top-level keys against the known schema, rather than "
            "ignoring drift forever or alerting on every occurrence."
        ),
    },
    "ERR_SCHEMA_DRIFT_RENAMED_FIELD": {
        "why": (
            "'merchant' was renamed to 'merchant_name' partway through the feed. Code that only "
            "reads `payload->>'merchant'` sees NULL, not an error - the row loads successfully but "
            "with a silently missing merchant. This is the most dangerous schema-drift case because "
            "it's indistinguishable downstream from ERR_NULL_REQUIRED_FIELD: both produce a NULL "
            "where real data belongs."
        ),
        "fix": "Coalesce both possible key names so either feed shape resolves to the same column.",
        "fix_sql": "SELECT COALESCE(payload->>'merchant', payload->>'merchant_name') AS merchant FROM raw_transaction_events;",
        "tradeoffs": (
            "Coalescing both names unblocks the load quickly, but if the rename is permanent you'll "
            "be maintaining that coalesce forever. The more correct long-term fix is updating "
            "extraction to prefer the new name and logging whenever the old name is still seen - "
            "that signal is what tells you it's finally safe to drop the coalesce."
        ),
    },
    "ERR_SCHEMA_DRIFT_TYPE_CHANGE": {
        "why": (
            "'amount' switched from a decimal string ('1234.56') to an integer in the smallest "
            "currency unit (123456, meaning cents). Casting both the same way produces either a "
            "100x-too-large amount or a cast error. This is the one schema-drift fault that's "
            "actively dangerous rather than inconvenient - a 100x-too-large dollar amount is a "
            "plausible-looking number that passes every not-null, type, and sanity-bound check."
        ),
        "fix": "Branch on the JSON value's own type and convert each representation correctly, rather than assuming one shape for the whole feed.",
        "fix_sql": (
            "SELECT CASE jsonb_typeof(payload->'amount')\n"
            "  WHEN 'string' THEN (payload->>'amount')::numeric\n"
            "  WHEN 'number' THEN (payload->>'amount')::numeric / 100\n"
            "END AS amount\n"
            "FROM raw_transaction_events;"
        ),
        "tradeoffs": (
            "Detecting the type at load time handles both representations correctly but adds a "
            "branch to maintain; normalizing at the source instead removes the branch but isn't "
            "always possible if you don't control the upstream system. Either way, this error class "
            "benefits from a post-load sanity check (flagging amounts above a documented outlier "
            "threshold) as a safety net against a type-detection bug nobody caught."
        ),
    },
    "ERR_MALFORMED_EXCEL_CORRUPTION": {
        "why": (
            "An ID-like field was corrupted the way Excel corrupts long numeric text - scientific "
            "notation (e.g. '1.00E+11') or a stripped leading zero - because Excel auto-detects a "
            "column's type on open, with no opt-out short of pre-formatting it as Text. Once that "
            "round-trip happens, the original digits are gone, not merely hidden; they can't be "
            "recovered from the corrupted value alone."
        ),
        "fix": "Detect the corrupted shape and route the row to a rejects table rather than silently accepting a wrong id.",
        "fix_sql": (
            "INSERT INTO rejected_transactions (raw_event_id, reason)\n"
            "SELECT id, 'excel-corrupted event_id'\n"
            "FROM raw_transaction_events\n"
            "WHERE payload->>'event_id' ~ '^[0-9.]+E\\+[0-9]+$';"
        ),
        "tradeoffs": (
            "Rejecting means the event is missing from clean_transactions until someone finds the "
            "source of the corruption (usually: someone opened the source export in Excel and "
            "re-saved it). The real fix is upstream - never let ID-like fields pass through anything "
            "that guesses numeric types - detection here only buys visibility, not recovery."
        ),
    },
    "ERR_MALFORMED_AMBIGUOUS_DATE": {
        "why": (
            "'timestamp' is a bare 'DD/MM/YYYY'-or-'MM/DD/YYYY' string with no way to tell which "
            "convention was used from the string alone - '03/04/2025' is March 4th or April 3rd "
            "depending on which system produced it. The fault is invisible for 12 of every 31 "
            "possible day values: a day number from 13-31 reveals the convention, but 1-12 stays "
            "silently ambiguous, so a naive parser looks correct on most rows and wrong on the ones "
            "where it matters least to notice."
        ),
        "fix": "There's no fully safe automatic fix - flag these rows as lower-confidence under a documented convention, or reject them for manual confirmation.",
        "fix_sql": (
            "INSERT INTO rejected_transactions (raw_event_id, reason)\n"
            "SELECT id, 'ambiguous DD/MM vs MM/DD date: ' || (payload->>'timestamp')\n"
            "FROM raw_transaction_events\n"
            "WHERE payload->>'timestamp' ~ '^\\d{2}/\\d{2}/\\d{4}$';"
        ),
        "tradeoffs": (
            "Guessing a convention risks being systematically wrong for an entire batch; rejecting "
            "is always correct but keeps real events out of clean_transactions without manual "
            "intervention. The durable fix is upstream, not in this load step: require every "
            "timestamp a source system emits to be ISO 8601, which has no DD/MM-vs-MM/DD question "
            "to even ask."
        ),
    },
}
