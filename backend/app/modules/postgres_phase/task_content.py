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
    "required_output": {
        "table": "clean_transactions",
        "note": (
            "Any intermediate tables you create are entirely up to you - only this one output table's "
            "shape is fixed, since grading needs something concrete to check."
        ),
        "columns": {
            "event_id": "text, unique, not null",
            "amount": "numeric, not null",
            "merchant": "text",
            "currency": "text",
            "event_timestamp": "timestamptz",
        },
    },
    "dataset_stats": [
        {"label": "Raw feed rows", "value": "51,495", "hint": "public.raw_transaction_events"},
        {"label": "Injected faults", "value": "~7,753", "hint": "roughly 15% of rows carry an edge case"},
        {"label": "Known-good result size", "value": "46,238 rows", "hint": "clean_transactions from the reference query above - before also repairing Excel-corrupted IDs and ambiguous dates, which climbs higher still"},
        {"label": "Users / accounts already loaded", "value": "10,000 / 15,000", "hint": "reference tables you can join against"},
    ],
    "starter_sql": (
        "-- Start by looking at the shape of the raw payload:\n"
        "SELECT id, received_at, source_delivery_id, payload\n"
        "FROM public.raw_transaction_events\n"
        "LIMIT 20;\n\n"
        "-- Then design clean_transactions and load it, e.g.:\n"
        "-- CREATE TABLE clean_transactions (\n"
        "--   event_id text PRIMARY KEY,\n"
        "--   amount numeric NOT NULL,\n"
        "--   merchant text,\n"
        "--   currency text,\n"
        "--   event_timestamp timestamptz\n"
        "-- );\n"
    ),
    "reference_solution": {
        "sql": (
            "CREATE TABLE clean_transactions (\n"
            "  event_id text PRIMARY KEY,\n"
            "  amount numeric NOT NULL,\n"
            "  merchant text,\n"
            "  currency text,\n"
            "  event_timestamp timestamptz\n"
            ");\n\n"
            "WITH normalized AS (\n"
            "  SELECT\n"
            "    COALESCE(payload->>'event_id', payload->>'id') AS event_id,\n"
            "    COALESCE(payload->>'merchant', payload->>'merchant_name') AS merchant,\n"
            "    payload->>'currency' AS currency,\n"
            "    CASE\n"
            "      WHEN payload->>'amount' ~ '^[0-9]+$'\n"
            "        AND (payload ? 'amount_is_minor_unit' OR length(payload->>'amount') > 4)\n"
            "        THEN (payload->>'amount')::numeric / 100\n"
            "      ELSE (payload->>'amount')::numeric\n"
            "    END AS amount,\n"
            "    (payload->>'timestamp')::timestamptz AS event_timestamp,\n"
            "    received_at,\n"
            "    row_number() OVER (\n"
            "      PARTITION BY COALESCE(payload->>'event_id', payload->>'id')\n"
            "      ORDER BY received_at DESC\n"
            "    ) AS rn\n"
            "  FROM public.raw_transaction_events\n"
            "  WHERE payload ? 'amount' AND (payload ? 'merchant' OR payload ? 'merchant_name')\n"
            ")\n"
            "INSERT INTO clean_transactions (event_id, amount, merchant, currency, event_timestamp)\n"
            "SELECT event_id, amount, merchant, currency, event_timestamp\n"
            "FROM normalized\n"
            "WHERE rn = 1\n"
            "  AND event_timestamp >= received_at - interval '48 hours';\n"
        ),
        "note": (
            "Key ideas: COALESCE handles the renamed field and missing-field cases together; "
            "row_number() over the business event_id (not source_delivery_id) dedupes redeliveries, "
            "keeping the most recently received copy; the watermark filter drops anything that arrived "
            "more than 48 hours after its own event_timestamp. Excel-style ID corruption and ambiguous "
            "date strings still need their own repair step before this query - that part is left to you."
        ),
        "steps": [
            {
                "title": "1. Naive load - assume the feed is clean",
                "sql": (
                    "CREATE TABLE clean_transactions (\n"
                    "  event_id text PRIMARY KEY,\n"
                    "  amount numeric NOT NULL,\n"
                    "  merchant text,\n"
                    "  currency text,\n"
                    "  event_timestamp timestamptz\n"
                    ");\n\n"
                    "INSERT INTO clean_transactions (event_id, amount, merchant, currency, event_timestamp)\n"
                    "SELECT\n"
                    "  payload->>'event_id' AS event_id,\n"
                    "  (payload->>'amount')::numeric AS amount,\n"
                    "  payload->>'merchant' AS merchant,\n"
                    "  payload->>'currency' AS currency,\n"
                    "  (payload->>'timestamp')::timestamptz AS event_timestamp\n"
                    "FROM public.raw_transaction_events;\n"
                ),
                "note": (
                    "This is the query you'd write if the feed really were clean. It isn't - run it "
                    "for real and it crashes almost immediately, though which error you hit first "
                    "depends on row order: a duplicate event_id from a redelivery violating the "
                    "primary key, a NULL amount violating NOT NULL, or a cast error on a malformed "
                    "value. Every step below fixes one specific way it breaks."
                ),
            },
            {
                "title": "2. + absorb renamed fields and skip rows missing a required one",
                "sql": (
                    "INSERT INTO clean_transactions (event_id, amount, merchant, currency, event_timestamp)\n"
                    "SELECT\n"
                    "  COALESCE(payload->>'event_id', payload->>'id') AS event_id,\n"
                    "  (payload->>'amount')::numeric AS amount,\n"
                    "  COALESCE(payload->>'merchant', payload->>'merchant_name') AS merchant,\n"
                    "  payload->>'currency' AS currency,\n"
                    "  (payload->>'timestamp')::timestamptz AS event_timestamp\n"
                    "FROM public.raw_transaction_events\n"
                    "WHERE payload ? 'amount' AND (payload ? 'merchant' OR payload ? 'merchant_name');\n"
                ),
                "note": (
                    "COALESCE absorbs the 'merchant_name' rename for free - no branching needed, just a "
                    "fallback column. The WHERE clause is the other half: a row still missing amount or "
                    "any merchant field gets skipped instead of throwing a cast error."
                ),
            },
            {
                "title": "3. + dedupe redelivered events",
                "sql": (
                    "WITH normalized AS (\n"
                    "  SELECT\n"
                    "    COALESCE(payload->>'event_id', payload->>'id') AS event_id,\n"
                    "    (payload->>'amount')::numeric AS amount,\n"
                    "    COALESCE(payload->>'merchant', payload->>'merchant_name') AS merchant,\n"
                    "    payload->>'currency' AS currency,\n"
                    "    (payload->>'timestamp')::timestamptz AS event_timestamp,\n"
                    "    received_at,\n"
                    "    row_number() OVER (\n"
                    "      PARTITION BY COALESCE(payload->>'event_id', payload->>'id')\n"
                    "      ORDER BY received_at DESC\n"
                    "    ) AS rn\n"
                    "  FROM public.raw_transaction_events\n"
                    "  WHERE payload ? 'amount' AND (payload ? 'merchant' OR payload ? 'merchant_name')\n"
                    ")\n"
                    "INSERT INTO clean_transactions (event_id, amount, merchant, currency, event_timestamp)\n"
                    "SELECT event_id, amount, merchant, currency, event_timestamp\n"
                    "FROM normalized\n"
                    "WHERE rn = 1;\n"
                ),
                "note": (
                    "row_number() partitions by the business event_id hidden inside the payload - NOT "
                    "source_delivery_id, which is different on every redelivery by design. Ordering by "
                    "received_at DESC and keeping rn = 1 keeps the most recently received copy of each "
                    "event and silently drops the rest."
                ),
            },
            {
                "title": "4. + drop arrivals past the 48-hour watermark",
                "sql": (
                    "-- same normalized CTE as step 3, plus one more filter on the final SELECT:\n"
                    "SELECT event_id, amount, merchant, currency, event_timestamp\n"
                    "FROM normalized\n"
                    "WHERE rn = 1\n"
                    "  AND event_timestamp >= received_at - interval '48 hours';\n"
                ),
                "note": (
                    "A late-arriving event isn't malformed - it's just too old to trust by the time it "
                    "showed up. Comparing received_at against the event's own event_timestamp (not "
                    "against 'now') is what makes this watermark check replay-safe."
                ),
            },
            {
                "title": "5. Final: also handle the minor-unit amount and known column shapes",
                "sql": (
                    "CREATE TABLE clean_transactions (\n"
                    "  event_id text PRIMARY KEY,\n"
                    "  amount numeric NOT NULL,\n"
                    "  merchant text,\n"
                    "  currency text,\n"
                    "  event_timestamp timestamptz\n"
                    ");\n\n"
                    "WITH normalized AS (\n"
                    "  SELECT\n"
                    "    COALESCE(payload->>'event_id', payload->>'id') AS event_id,\n"
                    "    COALESCE(payload->>'merchant', payload->>'merchant_name') AS merchant,\n"
                    "    payload->>'currency' AS currency,\n"
                    "    CASE\n"
                    "      WHEN payload->>'amount' ~ '^[0-9]+$'\n"
                    "        AND (payload ? 'amount_is_minor_unit' OR length(payload->>'amount') > 4)\n"
                    "        THEN (payload->>'amount')::numeric / 100\n"
                    "      ELSE (payload->>'amount')::numeric\n"
                    "    END AS amount,\n"
                    "    (payload->>'timestamp')::timestamptz AS event_timestamp,\n"
                    "    received_at,\n"
                    "    row_number() OVER (\n"
                    "      PARTITION BY COALESCE(payload->>'event_id', payload->>'id')\n"
                    "      ORDER BY received_at DESC\n"
                    "    ) AS rn\n"
                    "  FROM public.raw_transaction_events\n"
                    "  WHERE payload ? 'amount' AND (payload ? 'merchant' OR payload ? 'merchant_name')\n"
                    ")\n"
                    "INSERT INTO clean_transactions (event_id, amount, merchant, currency, event_timestamp)\n"
                    "SELECT event_id, amount, merchant, currency, event_timestamp\n"
                    "FROM normalized\n"
                    "WHERE rn = 1\n"
                    "  AND event_timestamp >= received_at - interval '48 hours';\n"
                ),
                "note": (
                    "The last real-world wrinkle: some amounts arrive as integer minor units (cents) "
                    "instead of a decimal string, caught here by a length/flag heuristic. This is the "
                    "same query as the top-level solution above - Excel-style ID corruption and "
                    "ambiguous date strings still need their own repair step before this, left to you."
                ),
            },
        ],
    },
}
