"""Postgres-phase skill tree. Each node's `teach` block reuses
`reference_solution.steps` from `task_content.py` rather than
duplicating it; `practice`/`combine` example rows are pulled from this
project's own seeded database, not invented."""

from app.modules.postgres_phase.task_content import POSTGRES_PHASE_TASK

_STEPS = POSTGRES_PHASE_TASK["reference_solution"]["steps"]

# A short hook + recap per step, wrapping each step's own real sql/note
# (never retyped - pulled directly from _STEPS below) into the stepped
# Teach format. Lighter than the fundamentals tracks' 5-step breakdown
# since these are genuinely bigger chunks of real SQL with substantial
# explanatory notes already - this is the deep-internals track, not a
# bite-sized one, so the steps stay honest about that instead of forcing
# artificial granularity onto content that doesn't split that way.
_HOOKS = [
    "What if the feed really were clean? Try the obvious query first and see how it actually breaks.",
    "Two small fixes handle both a renamed field and a row that's missing one entirely.",
    "The payload hides the real event id - that's the key a dedupe has to partition on, not the delivery id.",
    "This step changes nothing in the query itself - the lesson is entirely about what NOT to add.",
    "One last real-world wrinkle: some amounts arrive as integers, in cents, not as a decimal string.",
]
_RECAPS = [
    "Run the naive version for real before trusting it - this is why every step after exists.",
    "COALESCE and a WHERE clause absorb a rename and skip an unrecoverable row, without a branch.",
    "row_number() partitioned by the real event id, ordered by received_at DESC, keeps the latest copy.",
    "Scanning the raw table by its own id, not a rolling time window, is what keeps a late arrival from being lost.",
    "A length/flag heuristic catches integer-cents amounts before they're miscounted as whole dollars.",
]

# A concrete "here's what actually breaks if you skip this step" callout per
# node - the honest failure mode, not a restatement of the fix. These are
# prose-only (no new practice data), grounded in the same real fault types
# the capstone's own grader and remediation.py already check for.
_FAILURE_MODES = [
    "Skip this step and the naive query still runs without erroring - it just silently produces "
    "wrong output the moment the feed stops being perfectly clean, which in a 51,495-row real "
    "feed is almost immediately. There's no stack trace to point you at the problem; the first "
    "sign is usually a row count or a total that's subtly off from what a human expects.",
    "Forgetting the COALESCE means every renamed-field row loads with merchant = NULL instead of "
    "the real name - not an error, just a quietly incomplete row sitting in clean_transactions "
    "looking exactly as valid as every other row. Forgetting the WHERE-clause guard on amount "
    "means the unrecoverable row either fails the whole batch load or, worse, loads with a "
    "fabricated amount that was never in the source payload at all.",
    "Deduping on source_delivery_id instead of the payload's own event_id is the single most "
    "common mistake here - it looks like a dedup, it runs without error, and it does nothing at "
    "all, because every redelivery already has a unique source_delivery_id by construction. The "
    "duplicate event_id sails straight through, double-counted in every downstream aggregate.",
    "A rolling-window load (e.g. 'process everything received today') looks correct on every "
    "ordinary day and silently drops the one late arrival a day it actually matters - the failure "
    "is invisible until someone notices a specific real transaction is simply missing, usually "
    "much later, during a reconciliation against an external source of truth.",
    "Casting every amount the same way either throws a type error on the integer-cents rows (if "
    "the cast assumes a decimal string) or, worse, silently treats 360961 cents as $360,961.00 "
    "instead of $3,609.61 - a 100x error that passes every NULL check and every schema check, "
    "because the value is a perfectly valid-looking number, just the wrong one.",
]

# What makes each step matter once it's not seven toy rows but 51,495 real
# ones - the honest "why does this scale" note, distinct from the mechanics
# already covered by the step's own sql/note.
_SCALE_NOTES = [
    "At seven rows you could eyeball whether the output 'looks right'; at 51,495 rows you "
    "can't - which is exactly why the real task is graded against a precomputed ground truth "
    "rather than by inspection, and why building the habit of verifying against a known-good "
    "answer (not just 'it ran without error') matters more as volume grows, not less.",
    "A hand-written COALESCE works fine for one known historical rename - a real feed that's "
    "been running for years may carry three or four renamed-field generations at once, which is "
    "why production pipelines usually externalize this mapping into a schema registry or config "
    "table instead of hardcoding each old name directly into the query.",
    "Deduping with ROW_NUMBER() OVER (PARTITION BY ...) is cheap at seven rows and still "
    "perfectly fine at 51,495 - Postgres can sort-and-window a dataset this size in milliseconds. "
    "The real cost only shows up at much larger scale, where a partition-by-business-key window "
    "function becomes expensive enough that some pipelines prefer an upsert (ON CONFLICT) at "
    "write time instead of a dedup pass at read time.",
    "A 48-hour watermark was chosen deliberately, not arbitrarily - wide enough to catch "
    "realistic network/processing delays, narrow enough that 'final' output is still available "
    "within a reasonable time. Every watermark is this same tradeoff: wider catches more "
    "stragglers but delays finality; the 48-hour figure here isn't a universal constant, it's "
    "this task's own documented choice.",
    "This heuristic (checking the JSON value's type/length to infer cents vs. decimal) is a "
    "pragmatic fix for a feed that mixes both representations - the more robust long-term fix is "
    "never letting a source emit amounts in two different units to begin with, which is a data-"
    "contract problem to raise with whoever owns the upstream feed, not something a downstream "
    "query should have to keep guessing around forever.",
]


def _teach_steps(index: int) -> list[dict]:
    step = _STEPS[index]
    return [
        {"body": _HOOKS[index]},
        {"body": "The real query for this step:", "sql": step["sql"]},
        {"body": step["note"]},
        {"body": _FAILURE_MODES[index]},
        {"body": _SCALE_NOTES[index]},
        {"body": f"{_RECAPS[index]} Try it yourself in the Practice tab."},
    ]

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
            "teach": {"sql": _STEPS[0]["sql"], "note": _STEPS[0]["note"], "steps": _teach_steps(0)},
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
            "teach": {"sql": _STEPS[1]["sql"], "note": _STEPS[1]["note"], "steps": _teach_steps(1)},
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
            "teach": {"sql": _STEPS[2]["sql"], "note": _STEPS[2]["note"], "steps": _teach_steps(2)},
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
            "teach": {"sql": _STEPS[3]["sql"], "note": _STEPS[3]["note"], "steps": _teach_steps(3)},
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
            "teach": {"sql": _STEPS[4]["sql"], "note": _STEPS[4]["note"], "steps": _teach_steps(4)},
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
