"""Module 4.4: the Postgres-phase exercise description. Content, not
logic - kept as a plain dict rather than a class hierarchy per
CODE_STANDARDS.md's "no premature abstraction"; Module 5's grader is
what actually checks the submission against the edge cases described
here, not this module."""

POSTGRES_PHASE_TASK = {
    "title": "Load the raw transaction feed into a clean schema",
    "summary": (
        "You've been given a raw, unparsed feed of transaction events - "
        "public.raw_transaction_events - exactly as a payment processor's "
        "webhook would actually deliver it. Your job: design your own "
        "table(s) in your session schema, then write SQL to load the raw "
        "feed into them, correctly handling every edge case it contains."
    ),
    "source_table": "public.raw_transaction_events",
    "source_columns": {
        "id": "bigint - the raw event's own id",
        "received_at": "timestamptz - when this event arrived",
        "source_delivery_id": "text - transport-layer delivery id (NOT the business event id)",
        "payload": "jsonb - the actual event body; shape varies row-to-row",
    },
    "edge_cases_to_handle": [
        "Some payloads are missing a required field entirely (amount, merchant, currency, or timestamp).",
        "Some events are redelivered - same event_id inside the payload, different source_delivery_id and received_at.",
        "Some events arrive well past a 48-hour watermark relative to their own event timestamp.",
        "Some payloads use a renamed field ('merchant_name' instead of 'merchant'), have an extra field not seen before ('risk_flag'), or represent 'amount' as an integer in the smallest currency unit instead of a decimal string.",
        "Some IDs are corrupted the way Excel corrupts long numeric text (scientific notation, stripped leading zeros), and some timestamps are ambiguous regional date strings instead of proper ISO timestamps.",
    ],
    "hint": (
        "Nothing here is randomly broken - every edge case is deliberate and it's fine to write "
        "multiple passes (one to normalize the payload shape, one to load it) rather than a single query."
    ),
}
