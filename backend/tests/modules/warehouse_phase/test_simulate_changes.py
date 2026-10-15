import secrets

from app.core.db import get_admin_connection
from app.modules.warehouse_phase.session_provisioning import deprovision_session, provision_session
from app.modules.warehouse_phase.simulate_changes import apply_mutations, load_mutations


def _new_session():
    session_id = secrets.token_hex(16)
    with get_admin_connection() as conn:
        session_spark, _password = provision_session(conn, session_id)
    return session_id, session_spark


def _teardown(session_id):
    with get_admin_connection() as conn:
        deprovision_session(conn, session_id)


def test_apply_mutations_matches_what_spark_actually_stored():
    """Regression: mutation ground truth used to be recomputed
    independently in Python (`round(float(x) * 0.5, 2)`), which disagreed
    with the engine's own DECIMAL arithmetic for the identical computation
    on some rows by a cent (first found against DuckDB, re-verified here
    against Spark/Delta rather than assumed to still hold) - found by
    grading a genuinely correct submission and getting false failures.
    Ground truth must come from reading the actual post-UPDATE value back,
    not recomputing it."""
    session_id, session_spark = _new_session()
    try:
        mutations = apply_mutations(session_spark, session_id)
        assert len(mutations) > 0

        for mutation in mutations[:50]:
            row = session_spark.sql(
                f"SELECT account_status, credit_limit FROM source_accounts_snapshot WHERE id = {mutation.account_id}"
            ).collect()[0]
            assert row["account_status"] == mutation.new_status
            assert float(row["credit_limit"]) == mutation.new_credit_limit
    finally:
        _teardown(session_id)


def test_apply_mutations_is_idempotent():
    session_id, session_spark = _new_session()
    try:
        first = apply_mutations(session_spark, session_id)
        second = apply_mutations(session_spark, session_id)
        assert first == second
        assert load_mutations(session_id) == first
    finally:
        _teardown(session_id)
