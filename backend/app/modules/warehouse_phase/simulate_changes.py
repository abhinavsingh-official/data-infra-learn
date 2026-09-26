"""Module 8's "day 2" simulation - the mechanism that makes an SCD Type 2
exercise possible against source data that has no real history in it (see
MODULE_8_PLAN.md). Mutates a deterministic ~10% of `source_accounts_
snapshot` (never the shared, real `accounts` table - this only ever
touches the session's own local DuckDB file) and persists exactly what
changed to a sidecar JSON file next to the session's .duckdb file - NOT
as a table inside it, where a curious `SELECT * FROM ...` through the
session's own execute() endpoint could find it. The sidecar file is
plain filesystem state the sandboxed execute() endpoint has no path to
reach, the same way injected_fault_log's protection in the relational
phase comes from Postgres's own role permissions rather than obscurity."""

import json
from dataclasses import asdict, dataclass

import duckdb

from app.modules.warehouse_phase.session_provisioning import db_path

# Deterministic, not random - every session mutates the exact same
# subset the exact same way, so grading and manual testing both know
# precisely what "correct" looks like. id % 10 = 0 is ~10% of accounts.
_MUTATION_CREDIT_LIMIT_FACTOR = 0.5


@dataclass
class AccountMutation:
    account_id: int
    old_status: str
    new_status: str
    old_credit_limit: float
    new_credit_limit: float


def mutations_path(session_id: str):
    return db_path(session_id).with_suffix(".mutations.json")


def load_mutations(session_id: str) -> list[AccountMutation]:
    path = mutations_path(session_id)
    if not path.exists():
        return []
    return [AccountMutation(**entry) for entry in json.loads(path.read_text())]


def apply_mutations(session_id: str) -> list[AccountMutation]:
    """Idempotent - only touches rows still in the pre-mutation ('active')
    state, so calling this again after it's already run finds no new
    candidates and returns the same full history as before, not a
    truncated or doubled one."""
    existing = load_mutations(session_id)

    con = duckdb.connect(str(db_path(session_id)))
    try:
        candidates = con.execute(
            "SELECT id, account_status, credit_limit "
            "FROM source_accounts_snapshot WHERE id % 10 = 0 AND account_status = 'active'"
        ).fetchall()
        candidate_ids = [row[0] for row in candidates]
        old_values = {row[0]: (row[1], float(row[2])) for row in candidates}

        new_mutations: list[AccountMutation] = []
        if candidate_ids:
            con.execute(
                "UPDATE source_accounts_snapshot "
                "SET account_status = 'delinquent', credit_limit = credit_limit * ? "
                "WHERE id % 10 = 0 AND account_status = 'active'",
                [_MUTATION_CREDIT_LIMIT_FACTOR],
            )
            # Read the mutation's ground truth back from what DuckDB
            # actually stored, rather than recomputing it independently in
            # Python - found by testing a real correct submission: Python's
            # `round(float(x) * 0.5, 2)` and DuckDB's own DECIMAL
            # arithmetic for the identical `credit_limit * 0.5` disagreed
            # by a cent on some rows (float vs. decimal rounding), which
            # made grading falsely flag genuinely-correct submissions -
            # the same class of cross-boundary type/precision mismatch as
            # Module 5's Decimal/float bug and Module 7's date-type bug.
            new_rows = con.execute(
                "SELECT id, credit_limit FROM source_accounts_snapshot WHERE id IN "
                f"({', '.join('?' for _ in candidate_ids)})",
                candidate_ids,
            ).fetchall()
            new_credit_limits = {row[0]: float(row[1]) for row in new_rows}
            new_mutations = [
                AccountMutation(
                    account_id=account_id,
                    old_status=old_values[account_id][0],
                    new_status="delinquent",
                    old_credit_limit=old_values[account_id][1],
                    new_credit_limit=new_credit_limits[account_id],
                )
                for account_id in candidate_ids
            ]
    finally:
        con.close()

    merged = existing + new_mutations
    mutations_path(session_id).write_text(json.dumps([asdict(m) for m in merged]))
    return merged
