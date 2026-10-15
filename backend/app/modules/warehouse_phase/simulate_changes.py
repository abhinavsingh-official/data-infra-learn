"""Module 19 rewrite of Module 8's "day 2" simulation, now against the
session's own Spark/Delta `source_accounts_snapshot` table instead of a
DuckDB file (see MODULE_8_PLAN.md for why this exists at all, and
app.core.spark_sessions for why UPDATE needs a Delta-format table).
Mutation history is still kept out of band from a sidecar file next to
the per-session Delta table directory, same reasoning as before -
plain filesystem state the sandboxed execute() endpoint's SQL has no
path to reach, not a table the exercise's own SELECT * could stumble on."""

import json
from dataclasses import asdict, dataclass

from app.core.config import get_settings
from app.core.session_ids import validate_session_id
from app.modules.warehouse_phase.session_provisioning import session_lock

_MUTATION_CREDIT_LIMIT_FACTOR = 0.5


@dataclass
class AccountMutation:
    account_id: int
    old_status: str
    new_status: str
    old_credit_limit: float
    new_credit_limit: float


def _mutations_path(session_id: str):
    validate_session_id(session_id)
    settings = get_settings()
    settings.warehouse_sessions_dir.mkdir(parents=True, exist_ok=True)
    return settings.warehouse_sessions_dir / f"{session_id}.mutations.json"


def load_mutations(session_id: str) -> list[AccountMutation]:
    path = _mutations_path(session_id)
    if not path.exists():
        return []
    return [AccountMutation(**entry) for entry in json.loads(path.read_text())]


def apply_mutations(session_spark, session_id: str) -> list[AccountMutation]:
    """Idempotent - only touches rows still in the pre-mutation ('active')
    state, so calling this again after it's already run finds no new
    candidates."""
    existing = load_mutations(session_id)

    with session_lock(session_id):
        candidates = session_spark.sql(
            "SELECT id, account_status, credit_limit FROM source_accounts_snapshot "
            "WHERE id % 10 = 0 AND account_status = 'active'"
        ).collect()
        candidate_ids = [row["id"] for row in candidates]
        old_values = {row["id"]: (row["account_status"], float(row["credit_limit"])) for row in candidates}

        new_mutations: list[AccountMutation] = []
        if candidate_ids:
            session_spark.sql(
                f"UPDATE source_accounts_snapshot SET account_status = 'delinquent', "
                f"credit_limit = credit_limit * {_MUTATION_CREDIT_LIMIT_FACTOR} "
                "WHERE id % 10 = 0 AND account_status = 'active'"
            )
            # Read the mutation's ground truth back from what Spark/Delta
            # actually stored, rather than recomputing it independently in
            # Python - the same cross-boundary float/decimal precision
            # lesson as Module 8's original DuckDB version of this file
            # (and Module 5/7's own versions of it), reapplied here on
            # the new engine rather than assumed to not apply anymore.
            ids_literal = ", ".join(str(i) for i in candidate_ids)
            new_rows = session_spark.sql(
                f"SELECT id, credit_limit FROM source_accounts_snapshot WHERE id IN ({ids_literal})"
            ).collect()
            new_credit_limits = {row["id"]: float(row["credit_limit"]) for row in new_rows}
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

    merged = existing + new_mutations
    _mutations_path(session_id).write_text(json.dumps([asdict(m) for m in merged]))
    return merged
