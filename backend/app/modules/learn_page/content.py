"""Aggregates existing remediation content from every phase (each
`REMEDIATION` dict carries its own why/fix/tradeoffs) plus the
cross-platform comparison content, into one explainer page. Nothing here
is new content - it imports and displays what already exists, so the
only real risk is wiring the wrong dict to the wrong phase label, not
re-derived correctness."""

from app.modules.comparison_view.content import COMPARISON
from app.modules.grading.remediation import REMEDIATION as POSTGRES_REMEDIATION
from app.modules.lake_phase.remediation import REMEDIATION as LAKE_REMEDIATION
from app.modules.lakehouse_phase.remediation import REMEDIATION as LAKEHOUSE_REMEDIATION
from app.modules.nosql_phase.remediation import REMEDIATION as NOSQL_REMEDIATION
from app.modules.warehouse_phase.remediation import REMEDIATION as WAREHOUSE_REMEDIATION

OVERVIEW = (
    "One fintech company's data, five storage approaches. Each phase asks you to handle the "
    "same underlying ETL edge cases - nulls, duplicate deliveries, late arrivals, schema drift, "
    "malformed IDs/dates - through that approach's own real mechanics, and grades your submission "
    "with a remediation-first report: why it broke, how to fix it, and the tradeoffs where more "
    "than one valid approach exists. This page collects every one of those remediation writeups "
    "in one place, plus the cross-platform comparison from the same underlying operation."
)

PHASES = [
    {
        "phase": "Postgres (relational)",
        "one_liner": "Load a raw JSONB webhook feed into a clean, constrained schema.",
        "remediation": POSTGRES_REMEDIATION,
    },
    {
        "phase": "NoSQL (MongoDB)",
        "one_liner": "Remodel the same data as a denormalized document, not a row.",
        "remediation": NOSQL_REMEDIATION,
    },
    {
        "phase": "Data Warehouse (PySpark, SCD Type 2)",
        "one_liner": "A real Kimball star schema, proven against an actual dimension change.",
        "remediation": WAREHOUSE_REMEDIATION,
    },
    {
        "phase": "Data Lake (PySpark, partitioned Parquet)",
        "one_liner": "Genuine schema-on-read - the raw payload is interpreted only at query time.",
        "remediation": LAKE_REMEDIATION,
    },
    {
        "phase": "Lakehouse (PySpark, real Delta table)",
        "one_liner": "Real ACID: schema enforcement, atomic commits, and time travel - not just files.",
        "remediation": LAKEHOUSE_REMEDIATION,
    },
]


def _entries(remediation: dict) -> list[dict]:
    return [
        {"error_code": code, "why": text["why"], "fix": text["fix"], "tradeoffs": text["tradeoffs"]}
        for code, text in remediation.items()
    ]


def build_learn_content() -> dict:
    return {
        "overview": OVERVIEW,
        "phases": [
            {"phase": p["phase"], "one_liner": p["one_liner"], "entries": _entries(p["remediation"])}
            for p in PHASES
        ],
        "comparison": COMPARISON,
    }
