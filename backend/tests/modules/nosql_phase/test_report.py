import secrets

from psycopg.rows import dict_row

from app.core.db import get_admin_connection, get_mongo_admin_client
from app.modules.nosql_phase.report import grade_submission
from app.modules.nosql_phase.session_provisioning import (
    deprovision_mongo_session,
    deprovision_pg_readonly_session,
    mongo_db_name,
    provision_mongo_session,
    provision_pg_readonly_session,
)


def _new_session():
    session_id = secrets.token_hex(16)
    with get_admin_connection() as pg_conn:
        provision_pg_readonly_session(pg_conn, session_id)
    with get_mongo_admin_client() as mongo_client:
        provision_mongo_session(mongo_client, session_id)
    return session_id


def _teardown(session_id):
    with get_admin_connection() as pg_conn:
        deprovision_pg_readonly_session(pg_conn, session_id)
    with get_mongo_admin_client() as mongo_client:
        deprovision_mongo_session(mongo_client, session_id)


def test_incomplete_submission_flags_missing_and_mismatched_profiles():
    session_id = _new_session()
    try:
        with get_mongo_admin_client() as mongo_client:
            db = mongo_client[mongo_db_name(session_id)]
            db["account_profiles"].insert_one(
                {"_id": "1", "owner": {"name": "wrong", "email": "wrong@example.com"}}
            )

        with get_admin_connection() as pg_conn, get_mongo_admin_client() as mongo_client:
            report = grade_submission(pg_conn, mongo_client, session_id)

        assert report.passed is False
        assert report.total_profiles == 1
        assert report.total_accounts > 1
        error_codes = {f.error_code for f in report.findings}
        assert "ERR_MISSING_ACCOUNT_PROFILE" in error_codes
        assert "ERR_OWNER_NOT_EMBEDDED" in error_codes
    finally:
        _teardown(session_id)


def test_complete_submission_computed_independently_passes_with_zero_findings():
    """Builds account_profiles from an independent SQL computation (not
    by reusing report.py's own ground-truth query) so this test can't
    pass just because both sides share the same bug. Regression for the
    real bug found by testing: next_due_date submitted as an ISO string
    (a perfectly reasonable Mongo representation) used to always fail
    against Postgres's `date` object due to a bare type mismatch, not an
    actual data error."""
    session_id = _new_session()
    try:
        docs = {}
        with get_admin_connection() as pg_conn:
            with pg_conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT a.id, u.full_name, u.email, a.current_balance, a.credit_limit "
                    "FROM accounts a JOIN users u ON a.user_id = u.id"
                )
                for row in cur.fetchall():
                    docs[str(row["id"])] = {
                        "_id": str(row["id"]),
                        "owner": {"name": row["full_name"], "email": row["email"]},
                        "balance_cents": round(float(row["current_balance"]) * 100),
                        "credit_limit_cents": round(float(row["credit_limit"]) * 100),
                        "recent_transactions": [],
                        "reward_summary": {"total_points": 0.0, "event_count": 0},
                        "repayment_status": {"outstanding_cents": 0, "next_due_date": None},
                    }

                cur.execute(
                    """
                    SELECT account_id, retrieval_reference_number, transaction_amount, merchant_name,
                           transaction_timestamp
                    FROM (
                        SELECT account_id, retrieval_reference_number, transaction_amount, merchant_name,
                               transaction_timestamp,
                               ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY transaction_timestamp DESC) AS rn
                        FROM transactions
                    ) ranked WHERE rn <= 20 ORDER BY account_id, transaction_timestamp DESC
                    """
                )
                for row in cur.fetchall():
                    doc = docs.get(str(row["account_id"]))
                    if doc is not None:
                        doc["recent_transactions"].append(
                            {
                                "event_id": row["retrieval_reference_number"],
                                "amount_cents": round(float(row["transaction_amount"]) * 100),
                                "merchant": row["merchant_name"],
                                "occurred_at": row["transaction_timestamp"].isoformat(),
                            }
                        )

                cur.execute(
                    "SELECT account_id, SUM(points_earned) AS total_points, COUNT(*) AS event_count "
                    "FROM reward_events GROUP BY account_id"
                )
                for row in cur.fetchall():
                    doc = docs.get(str(row["account_id"]))
                    if doc is not None:
                        doc["reward_summary"] = {
                            "total_points": float(row["total_points"]),
                            "event_count": row["event_count"],
                        }

                cur.execute(
                    "SELECT account_id, SUM(amount_due - amount_paid) AS outstanding, "
                    "MIN(due_date) FILTER (WHERE amount_paid < amount_due) AS next_due "
                    "FROM repayments GROUP BY account_id"
                )
                for row in cur.fetchall():
                    doc = docs.get(str(row["account_id"]))
                    if doc is not None:
                        doc["repayment_status"] = {
                            "outstanding_cents": round(float(row["outstanding"]) * 100),
                            # Deliberately an ISO string, not a BSON datetime - the
                            # exact representation that triggered the real bug.
                            "next_due_date": row["next_due"].isoformat() if row["next_due"] else None,
                        }

        with get_mongo_admin_client() as mongo_client:
            db = mongo_client[mongo_db_name(session_id)]
            docs_list = list(docs.values())
            for i in range(0, len(docs_list), 2000):
                db["account_profiles"].insert_many(docs_list[i : i + 2000])

        with get_admin_connection() as pg_conn, get_mongo_admin_client() as mongo_client:
            report = grade_submission(pg_conn, mongo_client, session_id)

        assert report.findings == []
        assert report.passed is True
        assert report.total_profiles == report.total_accounts
    finally:
        _teardown(session_id)
