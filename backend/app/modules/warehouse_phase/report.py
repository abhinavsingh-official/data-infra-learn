"""Module 8.4: the warehouse-phase grading report generator. Every check
runs as SQL inside the session's own DuckDB file (with the Postgres
source re-attached for ground truth) - DuckDB's join engine is the right
tool for comparing a star schema against its source, not iterating rows
in Python the way the Postgres/Mongo phases' graders do, since those
compare a much smaller, already-fetched result set."""

from dataclasses import dataclass, field

import duckdb

from app.modules.warehouse_phase.remediation import REMEDIATION
from app.modules.warehouse_phase.session_provisioning import attach_postgres_source, db_path, pg_role_name
from app.modules.warehouse_phase.simulate_changes import AccountMutation, load_mutations


@dataclass
class Finding:
    error_code: str
    entity_id: str
    detail: str
    why: str
    fix: str
    tradeoffs: str


@dataclass
class GradingReport:
    total_accounts: int
    total_users: int
    total_transactions: int
    findings: list[Finding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.findings


def _make_finding(error_code: str, entity_id: str, detail: str) -> Finding:
    text = REMEDIATION.get(error_code, {"why": "Unrecognized error code.", "fix": "N/A", "tradeoffs": "N/A"})
    return Finding(error_code=error_code, entity_id=str(entity_id), detail=detail, **text)


def _table_exists(con: duckdb.DuckDBPyConnection, table: str) -> bool:
    return bool(
        con.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = ? AND table_schema = 'main'", [table]
        ).fetchone()
    )


def _check_dim_users(con: duckdb.DuckDBPyConnection, findings: list[Finding]) -> None:
    missing = con.execute(
        "SELECT u.external_user_id FROM pg.users u "
        "LEFT JOIN dim_users du ON u.external_user_id = du.external_user_id "
        "WHERE du.external_user_id IS NULL"
    ).fetchall()
    for row in missing:
        findings.append(_make_finding("ERR_MISSING_DIM_USER_ROW", row[0], "No dim_users row for this user."))

    mismatched = con.execute(
        "SELECT u.external_user_id FROM pg.users u JOIN dim_users du ON u.external_user_id = du.external_user_id "
        "WHERE du.full_name != u.full_name OR du.email != u.email OR du.kyc_status != u.kyc_status "
        "OR du.country != u.country OR du.is_active != u.is_active"
    ).fetchall()
    for row in mismatched:
        findings.append(_make_finding("ERR_DIM_USER_MISMATCH", row[0], "dim_users row doesn't match pg.users."))


def _check_dim_accounts(con: duckdb.DuckDBPyConnection, mutations: list[AccountMutation], findings: list[Finding]) -> None:
    missing = con.execute(
        "SELECT s.id FROM source_accounts_snapshot s "
        "LEFT JOIN (SELECT DISTINCT account_id FROM dim_accounts) da ON s.id = da.account_id "
        "WHERE da.account_id IS NULL"
    ).fetchall()
    for row in missing:
        findings.append(_make_finding("ERR_MISSING_DIM_ACCOUNT_ROW", row[0], "No dim_accounts row for this account."))

    bad_current_counts = con.execute(
        "SELECT account_id, SUM(CASE WHEN is_current THEN 1 ELSE 0 END) AS current_count "
        "FROM dim_accounts GROUP BY account_id HAVING SUM(CASE WHEN is_current THEN 1 ELSE 0 END) != 1"
    ).fetchall()
    for account_id, current_count in bad_current_counts:
        findings.append(
            _make_finding(
                "ERR_DIM_ACCOUNT_CURRENT_ROW_COUNT",
                account_id,
                f"{current_count} is_current rows for this account, expected exactly 1.",
            )
        )

    mutated_ids = {m.account_id for m in mutations}
    row_counts = dict(con.execute("SELECT account_id, COUNT(*) FROM dim_accounts GROUP BY account_id").fetchall())
    current_rows = {
        row[0]: {"account_status": row[1], "credit_limit": float(row[2])}
        for row in con.execute(
            "SELECT account_id, account_status, credit_limit FROM dim_accounts WHERE is_current"
        ).fetchall()
    }

    for mutation in mutations:
        if row_counts.get(mutation.account_id, 0) < 2:
            findings.append(
                _make_finding(
                    "ERR_SCD_HISTORY_NOT_PRESERVED",
                    mutation.account_id,
                    f"Only {row_counts.get(mutation.account_id, 0)} dim_accounts row(s) for a mutated account - history was overwritten, not versioned.",
                )
            )
            continue
        current = current_rows.get(mutation.account_id)
        if current is None:
            continue  # already reported by the current-row-count check above
        if current["account_status"] != mutation.new_status or round(current["credit_limit"], 2) != round(
            mutation.new_credit_limit, 2
        ):
            findings.append(
                _make_finding(
                    "ERR_SCD_STALE_CURRENT_VALUES",
                    mutation.account_id,
                    f"Current row shows {current!r}, expected status={mutation.new_status!r}, credit_limit={mutation.new_credit_limit}",
                )
            )

    for account_id, count in row_counts.items():
        if account_id not in mutated_ids and count > 1:
            findings.append(
                _make_finding(
                    "ERR_SCD_UNNECESSARY_NEW_ROW",
                    account_id,
                    f"{count} dim_accounts rows for an account that was never mutated - a new version was inserted unconditionally.",
                )
            )


def _check_fact_transactions(con: duckdb.DuckDBPyConnection, findings: list[Finding]) -> None:
    missing = con.execute(
        "SELECT t.retrieval_reference_number FROM pg.transactions t "
        "LEFT JOIN fact_transactions ft ON t.retrieval_reference_number = ft.transaction_key "
        "WHERE ft.transaction_key IS NULL"
    ).fetchall()
    for row in missing:
        findings.append(_make_finding("ERR_MISSING_FACT_ROW", row[0], "No fact_transactions row for this transaction."))

    mismatched = con.execute(
        """
        WITH account_owner AS (
            SELECT a.id AS account_id, a.external_account_id, u.external_user_id
            FROM pg.accounts a JOIN pg.users u ON a.user_id = u.id
        )
        SELECT t.retrieval_reference_number
        FROM pg.transactions t
        JOIN account_owner ao ON ao.account_id = t.account_id
        JOIN fact_transactions ft ON ft.transaction_key = t.retrieval_reference_number
        JOIN dim_accounts da ON da.account_id = t.account_id AND da.is_current
        JOIN dim_users du ON du.external_user_id = ao.external_user_id
        WHERE ft.account_key != da.account_key
           OR ft.user_key != du.user_key
           OR ft.amount != t.transaction_amount
           OR ft.merchant != t.merchant_name
        """
    ).fetchall()
    for row in mismatched:
        findings.append(_make_finding("ERR_FACT_ROW_MISMATCH", row[0], "fact_transactions row doesn't resolve/match correctly."))


def grade_submission(session_id: str, pg_password: str) -> GradingReport:
    mutations = load_mutations(session_id)
    con = duckdb.connect(str(db_path(session_id)))
    try:
        attach_postgres_source(con, pg_role_name(session_id), pg_password)

        total_accounts = con.execute("SELECT COUNT(*) FROM source_accounts_snapshot").fetchone()[0]
        total_users = con.execute("SELECT COUNT(*) FROM pg.users").fetchone()[0]
        total_transactions = con.execute("SELECT COUNT(*) FROM pg.transactions").fetchone()[0]

        findings: list[Finding] = []
        if not _table_exists(con, "dim_users"):
            findings.append(_make_finding("ERR_MISSING_DIM_USER_ROW", "*", "dim_users table doesn't exist."))
        else:
            _check_dim_users(con, findings)

        if not _table_exists(con, "dim_accounts"):
            findings.append(_make_finding("ERR_MISSING_DIM_ACCOUNT_ROW", "*", "dim_accounts table doesn't exist."))
        else:
            _check_dim_accounts(con, mutations, findings)

        if not _table_exists(con, "fact_transactions"):
            findings.append(_make_finding("ERR_MISSING_FACT_ROW", "*", "fact_transactions table doesn't exist."))
        elif _table_exists(con, "dim_users") and _table_exists(con, "dim_accounts"):
            _check_fact_transactions(con, findings)

        return GradingReport(
            total_accounts=total_accounts,
            total_users=total_users,
            total_transactions=total_transactions,
            findings=findings,
        )
    finally:
        con.close()
