"""Postgres-phase skill tree - content and data model only, no
grading/UI yet. Each skill node's `teach` block reuses
`reference_solution.steps` from `task_content.py` (not duplicated
logic, same source of truth); each node's `practice`/`combine` example
rows are real rows pulled directly from this project's own seeded
database, not invented. The capstone node references
POSTGRES_PHASE_TASK itself rather than repeating it."""

from app.modules.postgres_phase.task_content import POSTGRES_PHASE_TASK

_STEPS = POSTGRES_PHASE_TASK["reference_solution"]["steps"]

_SCHEMA = [
    {"column": "id", "type": "bigint", "note": "the raw event's own id"},
    {"column": "received_at", "type": "timestamptz", "note": "when this event arrived"},
    {"column": "source_delivery_id", "type": "text", "note": "transport-layer id (not the business event id)"},
    {"column": "payload", "type": "jsonb", "note": "the actual event body; shape varies row-to-row"},
]

POSTGRES_SKILL_TREE = {
    "paradigm": "postgres",
    "nodes": [
        {
            "id": "intro",
            "type": "intro",
            "title": "Relational storage: schema-on-write",
            "body": (
                "Postgres enforces a schema the moment you write a row - a NOT NULL violation or a "
                "bad cast fails immediately, at insert time, not whenever someone later reads the data. "
                "That's the whole shape of this tree: every lesson is really about deciding, up front, "
                "what a row must look like before it's allowed to exist."
            ),
        },
        {
            "id": "node_1_base_load",
            "type": "skill",
            "title": _STEPS[0]["title"],
            "teach": {"sql": _STEPS[0]["sql"], "note": _STEPS[0]["note"]},
            "practice": {
                "prompt": "Load this one clean event into clean_transactions.",
                "schema": _SCHEMA,
                "example_rows": [
                    {
                        "id": 1,
                        "received_at": "2026-02-06T05:55:09.495480+00",
                        "source_delivery_id": "dlv_100000249073",
                        "payload": {
                            "event_id": "100000249073", "amount": "1503.52", "merchant": "Sanders-Jones",
                            "currency": "USD", "timestamp": "2026-02-06T05:55:09.495480+00:00",
                            "channel": "ATM", "card_last4": "3463",
                        },
                    }
                ],
                "expected_output_rows": [
                    {
                        "event_id": "100000249073", "amount": 1503.52, "merchant": "Sanders-Jones",
                        "currency": "USD", "event_timestamp": "2026-02-06T05:55:09.495480+00",
                    }
                ],
                "starter_sql": POSTGRES_PHASE_TASK["starter_sql"],
            },
        },
        {
            "id": "node_2_renamed_missing",
            "type": "skill",
            "title": _STEPS[1]["title"],
            "teach": {"sql": _STEPS[1]["sql"], "note": _STEPS[1]["note"]},
            "practice": {
                "prompt": (
                    "One of these two payloads uses 'merchant_name' instead of 'merchant'; the other "
                    "is missing 'amount' entirely. Load only the row(s) that belong in clean_transactions."
                ),
                "schema": _SCHEMA,
                "example_rows": [
                    {
                        "id": 87,
                        "received_at": "2025-02-05T04:38:40.308291+00",
                        "source_delivery_id": "dlv_100000245633",
                        "payload": {
                            "event_id": "100000245633", "amount": "4886.42", "merchant_name": "Hill, Perkins and Austin",
                            "currency": "USD", "timestamp": "2025-02-03T07:38:40.308291+00:00",
                            "channel": "online", "card_last4": "2317",
                        },
                    },
                    {
                        "id": 9194,
                        "received_at": "2025-06-04T11:58:02.131217+00",
                        "source_delivery_id": None,
                        "payload": {
                            "event_id": "100000544764", "merchant_name": "Blair, Avila and Rivers",
                            "currency": "USD", "timestamp": "2025-06-04T11:58:02.131217+00:00",
                            "channel": "online", "card_last4": "8065",
                        },
                    },
                ],
                "expected_output_rows": [
                    {
                        "event_id": "100000245633", "amount": 4886.42, "merchant": "Hill, Perkins and Austin",
                        "currency": "USD", "event_timestamp": "2025-02-03T07:38:40.308291+00",
                    }
                    # id 9194 is correctly excluded - no 'amount' key at all, nothing to recover.
                ],
            },
            "combine": {
                "prompt": "Same as above, but now mixed in with the clean row from the last lesson.",
                "note": "Running total so far: 1 clean row in, 2 edge-case rows in (1 kept, 1 correctly dropped).",
            },
        },
        {
            "id": "node_3_dedupe",
            "type": "skill",
            "title": _STEPS[2]["title"],
            "teach": {"sql": _STEPS[2]["sql"], "note": _STEPS[2]["note"]},
            "practice": {
                "prompt": (
                    "These two rows are the same business event, redelivered - same event_id inside "
                    "the payload, different source_delivery_id and received_at. Load exactly one row."
                ),
                "schema": _SCHEMA,
                "example_rows": [
                    {
                        "id": 8048,
                        "received_at": "2025-08-20T22:13:44.251956+00",
                        "source_delivery_id": "dlv_100000647435",
                        "payload": {
                            "event_id": "100000647435", "amount": "1786.53", "merchant": "Rogers and Sons",
                            "currency": "EUR", "timestamp": "2025-08-19T15:13:44.251956+00:00",
                            "channel": "online", "card_last4": "5060",
                        },
                    },
                    {
                        "id": 8049,
                        "received_at": "2025-08-20T22:21:30.251956+00",
                        "source_delivery_id": "7ea2268dc42b45408c00abff8e7ebc3b",
                        "payload": {
                            "event_id": "100000647435", "amount": "1786.53", "merchant": "Rogers and Sons",
                            "currency": "EUR", "timestamp": "2025-08-19T15:13:44.251956+00:00",
                            "channel": "online", "card_last4": "5060",
                        },
                    },
                ],
                "expected_output_rows": [
                    {
                        "event_id": "100000647435", "amount": 1786.53, "merchant": "Rogers and Sons",
                        "currency": "EUR", "event_timestamp": "2025-08-19T15:13:44.251956+00",
                    }
                ],
            },
            "combine": {
                "prompt": "All of node 1 and node 2's rows, plus this redelivered pair, in one load.",
                "note": "Running total: 4 distinct business events in, one redelivery correctly collapsed to one row.",
            },
        },
        {
            "id": "node_4_watermark",
            "type": "skill",
            "title": _STEPS[3]["title"],
            "teach": {"sql": _STEPS[3]["sql"], "note": _STEPS[3]["note"]},
            "practice": {
                "prompt": (
                    "This event's own timestamp is 2026-07-27T04:59:08+00, but it wasn't received "
                    "until 2026-07-29T09:59:08+00 - about 53 hours later, past the 48-hour watermark. "
                    "It's late, not invalid - it should still appear in clean_transactions."
                ),
                "schema": _SCHEMA,
                "example_rows": [
                    {
                        "id": 14,
                        "received_at": "2026-07-29T09:59:08.256386+00",
                        "source_delivery_id": "dlv_100000233768",
                        "payload": {
                            "event_id": "100000233768", "amount": "3142.77", "merchant": "Mcintosh, Rodriguez and Greene",
                            "currency": "USD", "timestamp": "2026-07-27T04:59:08.256386+00:00",
                            "channel": "ATM", "card_last4": "6006",
                        },
                    }
                ],
                "expected_output_rows": [
                    {
                        "event_id": "100000233768", "amount": 3142.77, "merchant": "Mcintosh, Rodriguez and Greene",
                        "currency": "USD", "event_timestamp": "2026-07-27T04:59:08.256386+00",
                    }
                ],
            },
            "combine": {
                "prompt": "Everything so far, plus this late arrival, which still belongs in the output.",
                "note": "Running total: 4 rows out - the late arrival is included, not silently dropped.",
            },
        },
        {
            "id": "node_5_minor_unit",
            "type": "skill",
            "title": _STEPS[4]["title"],
            "teach": {"sql": _STEPS[4]["sql"], "note": _STEPS[4]["note"]},
            "practice": {
                "prompt": (
                    "This payload's 'amount' is 360961 - an integer, in cents, not a decimal string. "
                    "Load it with the amount correctly converted to dollars."
                ),
                "schema": _SCHEMA,
                "example_rows": [
                    {
                        "id": 39,
                        "received_at": "2026-03-19T17:01:33.242074+00",
                        "source_delivery_id": "dlv_100000752427",
                        "payload": {
                            "event_id": "100000752427", "amount": 360961, "merchant": "Roman LLC",
                            "currency": "USD", "timestamp": "2026-03-19T17:01:33.242074+00:00",
                            "channel": "POS", "card_last4": "4463",
                        },
                    }
                ],
                "expected_output_rows": [
                    {
                        "event_id": "100000752427", "amount": 3609.61, "merchant": "Roman LLC",
                        "currency": "USD", "event_timestamp": "2026-03-19T17:01:33.242074+00",
                    }
                ],
            },
            "combine": {
                "prompt": "The full mixed set from every lesson in this tree, loaded in one pass.",
                "note": (
                    "Running total: 6 rows out of 7 input rows - this is the same shape as the real "
                    "task, just seven rows instead of 51,495."
                ),
            },
        },
        {
            "id": "review",
            "type": "review",
            "title": "Review: all five edge cases, mixed",
            "prompt": (
                "Spaced-repetition checkpoint - same seven example rows as node 5's combine drill, "
                "unlocked once, then re-surfaced later on a simple schedule."
            ),
        },
        {
            "id": "capstone",
            "type": "capstone",
            "title": POSTGRES_PHASE_TASK["title"],
            "task_ref": "postgres",
            "note": (
                "The real task, at real scale (51,495 rows) - everything the five skill nodes above "
                "taught in isolation, now combined against the actual feed. Same grading engine, "
                "same remediation reports as today - no backend grading changes for this node."
            ),
        },
    ],
}
