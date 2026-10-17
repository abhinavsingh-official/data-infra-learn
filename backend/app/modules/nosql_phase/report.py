"""NoSQL-phase grading report generator. Fetches the user's
account_profiles documents (as the session's own scoped user - not the
admin client, so grading never silently benefits from an access level
the user themselves wouldn't have) and compares them against the real
ground truth computed directly from the relational source tables. Every
failure gets a why/fix/tradeoffs writeup, never just pass/fail."""

from dataclasses import dataclass, field
from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row
from pymongo import MongoClient

from app.modules.nosql_phase.remediation import REMEDIATION
from app.modules.nosql_phase.session_provisioning import mongo_db_name

RECENT_TRANSACTIONS_CAP = 20


@dataclass
class Finding:
    error_code: str
    account_id: str
    detail: str
    why: str
    fix: str
    fix_sql: str
    tradeoffs: str


@dataclass
class GradingReport:
    total_profiles: int
    total_accounts: int
    findings: list[Finding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.findings and self.total_profiles == self.total_accounts


def _make_finding(error_code: str, account_id: str, detail: str) -> Finding:
    text = REMEDIATION.get(error_code, {"why": "Unrecognized error code.", "fix": "N/A", "fix_sql": "N/A", "tradeoffs": "N/A"})
    return Finding(error_code=error_code, account_id=account_id, detail=detail, **text)


def _to_cents(amount: Any) -> int:
    return round(float(amount) * 100)


def _normalize_date(value: Any) -> str | None:
    """MongoDB has no native date-only type - a correct submission might
    reasonably store next_due_date as an ISO string OR a BSON datetime
    (which pymongo returns as a Python datetime, not a date). Ground
    truth from Postgres comes back as a real `date` object. Comparing
    those directly fails on a type mismatch even when the data itself is
    correct, so normalize all three shapes to an ISO date string before
    comparing."""
    if value is None:
        return None
    if hasattr(value, "date") and callable(value.date):
        value = value.date()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _fetch_ground_truth(pg_conn: Connection) -> dict[str, dict[str, Any]]:
    """One pass over the real relational source, computed directly - not
    a copy of what the user is expected to produce. Keyed by account_id
    (as a string, matching the document contract's _id)."""
    ground_truth: dict[str, dict[str, Any]] = {}

    with pg_conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT a.id, u.full_name, u.email, a.current_balance, a.credit_limit
            FROM accounts a JOIN users u ON a.user_id = u.id
            """
        )
        for row in cur.fetchall():
            ground_truth[str(row["id"])] = {
                "owner": {"name": row["full_name"], "email": row["email"]},
                "balance_cents": _to_cents(row["current_balance"]),
                "credit_limit_cents": _to_cents(row["credit_limit"]),
                "recent_transactions": [],
                "total_points": 0.0,
                "event_count": 0,
                "outstanding_cents": 0,
                "next_due_date": None,
            }

        cur.execute(
            """
            SELECT account_id, retrieval_reference_number, transaction_amount, merchant_name, transaction_timestamp
            FROM (
                SELECT account_id, retrieval_reference_number, transaction_amount, merchant_name,
                       transaction_timestamp,
                       ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY transaction_timestamp DESC) AS rn
                FROM transactions
            ) ranked
            WHERE rn <= %s
            ORDER BY account_id, transaction_timestamp DESC
            """,
            (RECENT_TRANSACTIONS_CAP,),
        )
        for row in cur.fetchall():
            account = ground_truth.get(str(row["account_id"]))
            if account is not None:
                account["recent_transactions"].append(
                    {
                        "event_id": row["retrieval_reference_number"],
                        "amount_cents": _to_cents(row["transaction_amount"]),
                        "merchant": row["merchant_name"],
                        "occurred_at": row["transaction_timestamp"],
                    }
                )

        cur.execute(
            "SELECT account_id, SUM(points_earned) AS total_points, COUNT(*) AS event_count "
            "FROM reward_events GROUP BY account_id"
        )
        for row in cur.fetchall():
            account = ground_truth.get(str(row["account_id"]))
            if account is not None:
                account["total_points"] = float(row["total_points"])
                account["event_count"] = row["event_count"]

        cur.execute(
            "SELECT account_id, SUM(amount_due - amount_paid) AS outstanding, "
            "MIN(due_date) FILTER (WHERE amount_paid < amount_due) AS next_due "
            "FROM repayments GROUP BY account_id"
        )
        for row in cur.fetchall():
            account = ground_truth.get(str(row["account_id"]))
            if account is not None:
                account["outstanding_cents"] = _to_cents(row["outstanding"])
                account["next_due_date"] = row["next_due"]

    return ground_truth


def _fetch_submitted_profiles(mongo_client: MongoClient, session_id: str) -> dict[str, dict[str, Any]]:
    db = mongo_client[mongo_db_name(session_id)]
    return {str(doc["_id"]): doc for doc in db["account_profiles"].find({})}


def _check_profile(account_id: str, truth: dict[str, Any], profile: dict[str, Any] | None) -> list[Finding]:
    findings: list[Finding] = []
    if profile is None:
        return [_make_finding("ERR_MISSING_ACCOUNT_PROFILE", account_id, "No document exists for this account.")]

    owner = profile.get("owner") or {}
    if owner.get("name") != truth["owner"]["name"] or owner.get("email") != truth["owner"]["email"]:
        findings.append(
            _make_finding("ERR_OWNER_NOT_EMBEDDED", account_id, f"owner does not match the source user: {owner!r}")
        )

    if profile.get("balance_cents") != truth["balance_cents"] or profile.get("credit_limit_cents") != truth[
        "credit_limit_cents"
    ]:
        findings.append(
            _make_finding(
                "ERR_BALANCE_MISMATCH",
                account_id,
                f"balance_cents={profile.get('balance_cents')!r}, credit_limit_cents={profile.get('credit_limit_cents')!r}",
            )
        )

    recent = profile.get("recent_transactions") or []
    if len(recent) > RECENT_TRANSACTIONS_CAP:
        findings.append(
            _make_finding(
                "ERR_UNBOUNDED_ARRAY", account_id, f"recent_transactions has {len(recent)} items, cap is {RECENT_TRANSACTIONS_CAP}"
            )
        )
    else:
        submitted_ids = [item.get("event_id") for item in recent]
        expected_ids = [item["event_id"] for item in truth["recent_transactions"]]
        if submitted_ids != expected_ids:
            findings.append(
                _make_finding(
                    "ERR_RECENT_TRANSACTIONS_MISMATCH",
                    account_id,
                    "recent_transactions doesn't match the account's real most-recent transactions, in order.",
                )
            )

    reward_summary = profile.get("reward_summary") or {}
    if reward_summary.get("event_count") != truth["event_count"] or round(
        float(reward_summary.get("total_points", -1)), 2
    ) != round(truth["total_points"], 2):
        findings.append(
            _make_finding(
                "ERR_REWARD_SUMMARY_MISMATCH",
                account_id,
                f"reward_summary={reward_summary!r}, expected total_points={truth['total_points']}, event_count={truth['event_count']}",
            )
        )

    repayment_status = profile.get("repayment_status") or {}
    submitted_due_date = _normalize_date(repayment_status.get("next_due_date"))
    truth_due_date = _normalize_date(truth["next_due_date"])
    if repayment_status.get("outstanding_cents") != truth["outstanding_cents"] or submitted_due_date != truth_due_date:
        findings.append(
            _make_finding(
                "ERR_REPAYMENT_STATUS_MISMATCH",
                account_id,
                f"repayment_status={repayment_status!r}, expected outstanding_cents="
                f"{truth['outstanding_cents']}, next_due_date={truth['next_due_date']}",
            )
        )

    return findings


def grade_submission(pg_conn: Connection, mongo_client: MongoClient, session_id: str) -> GradingReport:
    ground_truth = _fetch_ground_truth(pg_conn)
    profiles = _fetch_submitted_profiles(mongo_client, session_id)

    report = GradingReport(total_profiles=len(profiles), total_accounts=len(ground_truth))
    for account_id, truth in ground_truth.items():
        report.findings.extend(_check_profile(account_id, truth, profiles.get(account_id)))
    return report
