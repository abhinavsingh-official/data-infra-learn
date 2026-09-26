import secrets
from collections import Counter

from app.core.db import get_admin_connection
from app.modules.warehouse_phase.duckdb_execution import execute_submission
from app.modules.warehouse_phase.report import grade_submission
from app.modules.warehouse_phase.session_provisioning import (
    deprovision_session,
    pg_role_name,
    provision_session,
)
from app.modules.warehouse_phase.simulate_changes import apply_mutations

_DIM_USERS_SQL = (
    "CREATE TABLE dim_users AS SELECT external_user_id AS user_key, external_user_id, "
    "full_name, email, kyc_status, country, is_active FROM pg.users"
)
_DIM_ACCOUNTS_DAY1_SQL = (
    "CREATE TABLE dim_accounts AS SELECT row_number() OVER () AS account_key, id AS account_id, "
    "card_network, account_status, credit_limit, current_timestamp AS valid_from, "
    "NULL::TIMESTAMP AS valid_to, true AS is_current FROM source_accounts_snapshot"
)
_FACT_TRANSACTIONS_SQL = """
CREATE TABLE fact_transactions AS
SELECT t.retrieval_reference_number AS transaction_key, da.account_key, du.user_key,
       t.transaction_amount AS amount, t.merchant_name AS merchant, t.transaction_timestamp
FROM pg.transactions t
JOIN pg.accounts pa ON pa.id = t.account_id
JOIN pg.users pu ON pu.id = pa.user_id
JOIN dim_accounts da ON da.account_id = t.account_id AND da.is_current
JOIN dim_users du ON du.external_user_id = pu.external_user_id
"""


def _run(session_id, role, password, sql, label=""):
    result = execute_submission(session_id, role, password, sql)
    assert result.success, f"{label}: {result.error_code} {result.error_message}"
    return result


def _new_session():
    session_id = secrets.token_hex(16)
    with get_admin_connection() as conn:
        password = provision_session(conn, session_id)
    return session_id, pg_role_name(session_id), password


def _teardown(session_id):
    with get_admin_connection() as conn:
        deprovision_session(conn, session_id)


def test_incomplete_submission_flags_real_gaps():
    session_id, role, password = _new_session()
    try:
        _run(
            session_id,
            role,
            password,
            "CREATE TABLE dim_accounts AS SELECT id AS account_key, id AS account_id, card_network, "
            "account_status, credit_limit, current_timestamp AS valid_from, NULL::TIMESTAMP AS valid_to, "
            "true AS is_current FROM source_accounts_snapshot LIMIT 100",
        )
        apply_mutations(session_id)

        report = grade_submission(session_id, password)
        assert report.passed is False
        error_codes = {f.error_code for f in report.findings}
        assert "ERR_MISSING_DIM_ACCOUNT_ROW" in error_codes
        assert "ERR_MISSING_DIM_USER_ROW" in error_codes
        assert "ERR_MISSING_FACT_ROW" in error_codes
    finally:
        _teardown(session_id)


def test_correct_scd2_submission_passes_with_zero_findings():
    session_id, role, password = _new_session()
    try:
        _run(session_id, role, password, _DIM_USERS_SQL, "dim_users")
        _run(session_id, role, password, _DIM_ACCOUNTS_DAY1_SQL, "dim_accounts day1")
        _run(session_id, role, password, _FACT_TRANSACTIONS_SQL, "fact_transactions day1")

        mutations = apply_mutations(session_id)
        assert len(mutations) > 0

        _run(
            session_id,
            role,
            password,
            "UPDATE dim_accounts SET valid_to = current_timestamp, is_current = false "
            "WHERE is_current AND account_id IN ("
            "  SELECT da.account_id FROM dim_accounts da JOIN source_accounts_snapshot s "
            "  ON s.id = da.account_id WHERE da.is_current AND "
            "  (da.account_status != s.account_status OR da.credit_limit != s.credit_limit))",
            "close changed rows",
        )
        _run(
            session_id,
            role,
            password,
            "INSERT INTO dim_accounts SELECT (SELECT COALESCE(MAX(account_key), 0) FROM dim_accounts) "
            "+ row_number() OVER (), s.id, s.card_network, s.account_status, s.credit_limit, "
            "current_timestamp, NULL, true FROM source_accounts_snapshot s WHERE s.id IN "
            "(SELECT account_id FROM dim_accounts WHERE NOT is_current) AND s.id NOT IN "
            "(SELECT account_id FROM dim_accounts WHERE is_current)",
            "insert new versions",
        )
        _run(session_id, role, password, "DROP TABLE fact_transactions", "drop fact")
        _run(session_id, role, password, _FACT_TRANSACTIONS_SQL, "rebuild fact")

        report = grade_submission(session_id, password)
        assert report.findings == []
        assert report.passed is True
    finally:
        _teardown(session_id)


def test_naive_overwrite_loses_scd_history():
    """A day-2 ETL that just UPDATEs dim_accounts in place (SCD Type 1
    behavior applied to a column meant to be SCD Type 2) gets the current
    values right but destroys history - must be flagged, not passed."""
    session_id, role, password = _new_session()
    try:
        _run(session_id, role, password, _DIM_USERS_SQL, "dim_users")
        _run(session_id, role, password, _DIM_ACCOUNTS_DAY1_SQL, "dim_accounts day1")
        _run(session_id, role, password, _FACT_TRANSACTIONS_SQL, "fact_transactions day1")

        mutations = apply_mutations(session_id)
        assert len(mutations) > 0

        _run(
            session_id,
            role,
            password,
            "UPDATE dim_accounts SET account_status = "
            "(SELECT account_status FROM source_accounts_snapshot s WHERE s.id = dim_accounts.account_id), "
            "credit_limit = (SELECT credit_limit FROM source_accounts_snapshot s WHERE s.id = dim_accounts.account_id)",
            "naive overwrite",
        )

        report = grade_submission(session_id, password)
        assert report.passed is False
        error_codes = Counter(f.error_code for f in report.findings)
        assert error_codes["ERR_SCD_HISTORY_NOT_PRESERVED"] == len(mutations)
        assert "ERR_SCD_STALE_CURRENT_VALUES" not in error_codes  # values ARE right, just not versioned
    finally:
        _teardown(session_id)


def test_naive_always_insert_creates_unnecessary_duplicates():
    """A day-2 ETL that inserts a new version for every account, whether
    or not anything changed, must be flagged for the untouched accounts."""
    session_id, role, password = _new_session()
    try:
        _run(session_id, role, password, _DIM_USERS_SQL, "dim_users")
        _run(session_id, role, password, _DIM_ACCOUNTS_DAY1_SQL, "dim_accounts day1")
        _run(session_id, role, password, _FACT_TRANSACTIONS_SQL, "fact_transactions day1")

        apply_mutations(session_id)

        _run(
            session_id,
            role,
            password,
            "UPDATE dim_accounts SET valid_to = current_timestamp, is_current = false WHERE is_current",
            "close all rows",
        )
        _run(
            session_id,
            role,
            password,
            "INSERT INTO dim_accounts SELECT (SELECT COALESCE(MAX(account_key), 0) FROM dim_accounts) "
            "+ row_number() OVER (), s.id, s.card_network, s.account_status, s.credit_limit, "
            "current_timestamp, NULL, true FROM source_accounts_snapshot s",
            "insert a new version for every account, unconditionally",
        )

        report = grade_submission(session_id, password)
        assert report.passed is False
        unnecessary = [f for f in report.findings if f.error_code == "ERR_SCD_UNNECESSARY_NEW_ROW"]
        assert len(unnecessary) > 0
    finally:
        _teardown(session_id)
