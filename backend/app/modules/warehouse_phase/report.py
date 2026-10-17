"""Warehouse-phase grading report generator, running against the
session's own Spark session object. Every check runs as SQL inside the
engine - Spark SQL's join engine is the right tool here, same as it
would be against any other SQL engine."""

from dataclasses import dataclass, field

from app.modules.warehouse_phase.remediation import REMEDIATION
from app.modules.warehouse_phase.simulate_changes import AccountMutation, load_mutations


@dataclass
class Finding:
    error_code: str
    entity_id: str
    detail: str
    why: str
    fix: str
    fix_sql: str
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
    text = REMEDIATION.get(error_code, {"why": "Unrecognized error code.", "fix": "N/A", "fix_sql": "N/A", "tradeoffs": "N/A"})
    return Finding(error_code=error_code, entity_id=str(entity_id), detail=detail, **text)


def _table_exists(session_spark, table: str) -> bool:
    return session_spark.catalog.tableExists(table)


def _check_dim_users(session_spark, findings: list[Finding]) -> None:
    missing = session_spark.sql(
        "SELECT u.external_user_id FROM users u "
        "LEFT JOIN dim_users du ON u.external_user_id = du.external_user_id "
        "WHERE du.external_user_id IS NULL"
    ).collect()
    for row in missing:
        findings.append(_make_finding("ERR_MISSING_DIM_USER_ROW", row["external_user_id"], "No dim_users row for this user."))

    mismatched = session_spark.sql(
        "SELECT u.external_user_id FROM users u JOIN dim_users du ON u.external_user_id = du.external_user_id "
        "WHERE du.full_name != u.full_name OR du.email != u.email OR du.kyc_status != u.kyc_status "
        "OR du.country != u.country OR du.is_active != u.is_active"
    ).collect()
    for row in mismatched:
        findings.append(
            _make_finding("ERR_DIM_USER_MISMATCH", row["external_user_id"], "dim_users row doesn't match users.")
        )


def _check_dim_accounts(session_spark, mutations: list[AccountMutation], findings: list[Finding]) -> None:
    missing = session_spark.sql(
        "SELECT s.id FROM source_accounts_snapshot s "
        "LEFT JOIN (SELECT DISTINCT account_id FROM dim_accounts) da ON s.id = da.account_id "
        "WHERE da.account_id IS NULL"
    ).collect()
    for row in missing:
        findings.append(_make_finding("ERR_MISSING_DIM_ACCOUNT_ROW", row["id"], "No dim_accounts row for this account."))

    bad_current_counts = session_spark.sql(
        "SELECT account_id, SUM(CASE WHEN is_current THEN 1 ELSE 0 END) AS current_count "
        "FROM dim_accounts GROUP BY account_id HAVING SUM(CASE WHEN is_current THEN 1 ELSE 0 END) != 1"
    ).collect()
    for row in bad_current_counts:
        findings.append(
            _make_finding(
                "ERR_DIM_ACCOUNT_CURRENT_ROW_COUNT",
                row["account_id"],
                f"{row['current_count']} is_current rows for this account, expected exactly 1.",
            )
        )

    mutated_ids = {m.account_id for m in mutations}
    row_counts = {
        row["account_id"]: row["count"]
        for row in session_spark.sql("SELECT account_id, COUNT(*) AS count FROM dim_accounts GROUP BY account_id").collect()
    }
    current_rows = {
        row["account_id"]: {"account_status": row["account_status"], "credit_limit": float(row["credit_limit"])}
        for row in session_spark.sql(
            "SELECT account_id, account_status, credit_limit FROM dim_accounts WHERE is_current"
        ).collect()
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


def _check_fact_transactions(session_spark, findings: list[Finding]) -> None:
    missing = session_spark.sql(
        "SELECT t.retrieval_reference_number FROM transactions t "
        "LEFT JOIN fact_transactions ft ON t.retrieval_reference_number = ft.transaction_key "
        "WHERE ft.transaction_key IS NULL"
    ).collect()
    for row in missing:
        findings.append(
            _make_finding("ERR_MISSING_FACT_ROW", row["retrieval_reference_number"], "No fact_transactions row for this transaction.")
        )

    mismatched = session_spark.sql(
        """
        WITH account_owner AS (
            SELECT a.id AS account_id, a.external_account_id, u.external_user_id
            FROM accounts a JOIN users u ON a.user_id = u.id
        )
        SELECT t.retrieval_reference_number
        FROM transactions t
        JOIN account_owner ao ON ao.account_id = t.account_id
        JOIN fact_transactions ft ON ft.transaction_key = t.retrieval_reference_number
        JOIN dim_accounts da ON da.account_id = t.account_id AND da.is_current
        JOIN dim_users du ON du.external_user_id = ao.external_user_id
        WHERE ft.account_key != da.account_key
           OR ft.user_key != du.user_key
           OR ft.amount != t.transaction_amount
           OR ft.merchant != t.merchant_name
        """
    ).collect()
    for row in mismatched:
        findings.append(
            _make_finding(
                "ERR_FACT_ROW_MISMATCH", row["retrieval_reference_number"], "fact_transactions row doesn't resolve/match correctly."
            )
        )


def grade_submission(session_spark, session_id: str) -> GradingReport:
    mutations = load_mutations(session_id)

    total_accounts = session_spark.sql("SELECT COUNT(*) AS n FROM source_accounts_snapshot").collect()[0]["n"]
    total_users = session_spark.sql("SELECT COUNT(*) AS n FROM users").collect()[0]["n"]
    total_transactions = session_spark.sql("SELECT COUNT(*) AS n FROM transactions").collect()[0]["n"]

    findings: list[Finding] = []
    if not _table_exists(session_spark, "dim_users"):
        findings.append(_make_finding("ERR_MISSING_DIM_USER_ROW", "*", "dim_users table doesn't exist."))
    else:
        _check_dim_users(session_spark, findings)

    if not _table_exists(session_spark, "dim_accounts"):
        findings.append(_make_finding("ERR_MISSING_DIM_ACCOUNT_ROW", "*", "dim_accounts table doesn't exist."))
    else:
        _check_dim_accounts(session_spark, mutations, findings)

    if not _table_exists(session_spark, "fact_transactions"):
        findings.append(_make_finding("ERR_MISSING_FACT_ROW", "*", "fact_transactions table doesn't exist."))
    elif _table_exists(session_spark, "dim_users") and _table_exists(session_spark, "dim_accounts"):
        _check_fact_transactions(session_spark, findings)

    return GradingReport(
        total_accounts=total_accounts,
        total_users=total_users,
        total_transactions=total_transactions,
        findings=findings,
    )
