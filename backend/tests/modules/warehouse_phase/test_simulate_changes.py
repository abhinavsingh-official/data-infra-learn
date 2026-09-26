import secrets

import duckdb

from app.core.db import get_admin_connection
from app.modules.warehouse_phase.session_provisioning import db_path, deprovision_session, provision_session
from app.modules.warehouse_phase.simulate_changes import apply_mutations, load_mutations


def _new_session():
    session_id = secrets.token_hex(16)
    with get_admin_connection() as conn:
        provision_session(conn, session_id)
    return session_id


def _teardown(session_id):
    with get_admin_connection() as conn:
        deprovision_session(conn, session_id)


def test_apply_mutations_matches_what_duckdb_actually_stored():
    """Regression: mutation ground truth used to be recomputed
    independently in Python (`round(float(x) * 0.5, 2)`), which disagreed
    with DuckDB's own DECIMAL arithmetic for the identical computation on
    some rows by a cent - found by grading a genuinely correct
    submission and getting false failures. Ground truth must come from
    reading the actual post-UPDATE value back, not recomputing it."""
    session_id = _new_session()
    try:
        mutations = apply_mutations(session_id)
        assert len(mutations) > 0

        con = duckdb.connect(str(db_path(session_id)))
        try:
            for mutation in mutations[:50]:
                row = con.execute(
                    "SELECT account_status, credit_limit FROM source_accounts_snapshot WHERE id = ?",
                    [mutation.account_id],
                ).fetchone()
                assert row[0] == mutation.new_status
                assert float(row[1]) == mutation.new_credit_limit
        finally:
            con.close()
    finally:
        _teardown(session_id)


def test_apply_mutations_is_idempotent():
    session_id = _new_session()
    try:
        first = apply_mutations(session_id)
        second = apply_mutations(session_id)
        assert first == second
        assert load_mutations(session_id) == first
    finally:
        _teardown(session_id)
