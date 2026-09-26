import secrets
from collections import Counter

from app.core.db import get_admin_connection
from app.modules.lakehouse_phase.commit_batch import commit_batch
from app.modules.lakehouse_phase.report import grade_submission
from app.modules.lakehouse_phase.session_provisioning import (
    delta_table_dir,
    deprovision_session,
    pg_role_name,
    provision_session,
    release_batch_two,
)

_CLEAN_SQL_TEMPLATE = """
SELECT DISTINCT ON (payload_json->>'event_id')
  payload_json->>'event_id' AS event_id,
  CASE WHEN json_type(payload_json->'amount') = 'VARCHAR' THEN TRY_CAST(payload_json->>'amount' AS DOUBLE)
       WHEN (payload_json->'amount') IS NOT NULL THEN TRY_CAST(payload_json->>'amount' AS DOUBLE) / 100
       ELSE 1 END AS amount,
  COALESCE(payload_json->>'merchant', payload_json->>'merchant_name', 'UNKNOWN') AS merchant,
  COALESCE(payload_json->>'currency', 'USD') AS currency,
  COALESCE(TRY_CAST(NULLIF(payload_json->>'timestamp', '') AS TIMESTAMPTZ), received_at) AS event_timestamp
FROM (SELECT received_at, payload::JSON AS payload_json FROM {table}) t
WHERE payload_json->>'event_id' IS NOT NULL
ORDER BY payload_json->>'event_id', received_at ASC
"""

_ANTI_JOIN_SQL_TEMPLATE = """
SELECT DISTINCT ON (t.eid)
  t.eid AS event_id,
  CASE WHEN json_type(t.payload_json->'amount') = 'VARCHAR' THEN TRY_CAST(t.payload_json->>'amount' AS DOUBLE)
       WHEN (t.payload_json->'amount') IS NOT NULL THEN TRY_CAST(t.payload_json->>'amount' AS DOUBLE) / 100
       ELSE 1 END AS amount,
  COALESCE(t.payload_json->>'merchant', t.payload_json->>'merchant_name', 'UNKNOWN') AS merchant,
  COALESCE(t.payload_json->>'currency', 'USD') AS currency,
  COALESCE(TRY_CAST(NULLIF(t.payload_json->>'timestamp', '') AS TIMESTAMPTZ), t.received_at) AS event_timestamp
FROM (SELECT received_at, payload::JSON AS payload_json, (payload::JSON)->>'event_id' AS eid FROM batch_2_events) t
LEFT JOIN delta_scan('{delta_path}') d ON d.event_id = t.eid
WHERE t.eid IS NOT NULL AND d.event_id IS NULL
ORDER BY t.eid, t.received_at ASC
"""


def _new_session():
    session_id = secrets.token_hex(16)
    with get_admin_connection() as conn:
        password = provision_session(conn, session_id)
    return session_id, pg_role_name(session_id), password


def _teardown(session_id):
    with get_admin_connection() as conn:
        deprovision_session(conn, session_id)


def test_only_one_commit_flags_not_incremental():
    session_id, role, password = _new_session()
    try:
        result = commit_batch(session_id, role, password, _CLEAN_SQL_TEMPLATE.format(table="batch_1_events"))
        assert result.success, result.error_message

        report = grade_submission(session_id)
        assert report.passed is False
        error_codes = {f.error_code for f in report.structural_findings}
        assert "ERR_LAKEHOUSE_NOT_INCREMENTAL" in error_codes
    finally:
        _teardown(session_id)


def test_naive_per_batch_dedup_leaves_real_cross_batch_duplicates():
    """The real, empirically-confirmed lesson this phase teaches: some
    genuine event_ids have rows spanning BOTH batches (confirmed
    directly against real seeded data), so deduplicating within each
    batch alone is not enough - this is the actual point of the module,
    not an edge case to route around."""
    session_id, role, password = _new_session()
    try:
        r1 = commit_batch(session_id, role, password, _CLEAN_SQL_TEMPLATE.format(table="batch_1_events"))
        assert r1.success, r1.error_message
        release_batch_two(session_id, role, password)
        r2 = commit_batch(session_id, role, password, _CLEAN_SQL_TEMPLATE.format(table="batch_2_events"))
        assert r2.success, r2.error_message

        report = grade_submission(session_id)
        assert report.passed is False
        counts = Counter(f.error_code for f in report.structural_findings)
        assert counts["ERR_DUPLICATE_DELIVERY"] > 0
        # the naive submission still committed twice, correctly - incrementality itself is fine
        assert "ERR_LAKEHOUSE_NOT_INCREMENTAL" not in counts
        # and time travel is still correct, even though duplicates leaked through -
        # the earlier false-positive bug this test also guards against
        assert "ERR_LAKEHOUSE_TIME_TRAVEL_INCORRECT" not in counts
    finally:
        _teardown(session_id)


def test_cross_batch_aware_dedup_passes_with_zero_findings():
    session_id, role, password = _new_session()
    try:
        r1 = commit_batch(session_id, role, password, _CLEAN_SQL_TEMPLATE.format(table="batch_1_events"))
        assert r1.success, r1.error_message
        release_batch_two(session_id, role, password)

        delta_path = str(delta_table_dir(session_id))
        r2 = commit_batch(session_id, role, password, _ANTI_JOIN_SQL_TEMPLATE.format(delta_path=delta_path))
        assert r2.success, r2.error_message

        report = grade_submission(session_id)
        assert report.structural_findings == []
        assert report.fault_findings == []
        assert report.passed is True
        assert report.total_clean_rows > 0
    finally:
        _teardown(session_id)
