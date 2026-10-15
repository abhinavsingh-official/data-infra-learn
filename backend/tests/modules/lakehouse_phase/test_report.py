import secrets
from collections import Counter

from app.core.db import get_admin_connection
from app.modules.lakehouse_phase.commit_batch import commit_batch
from app.modules.lakehouse_phase.report import grade_submission
from app.modules.lakehouse_phase.session_provisioning import deprovision_session, provision_session, release_batch_two

_CLEAN_SQL_TEMPLATE = """
WITH normalized AS (
  SELECT
    COALESCE(get_json_object(payload, '$.event_id'), get_json_object(payload, '$.id')) AS event_id,
    COALESCE(get_json_object(payload, '$.merchant'), get_json_object(payload, '$.merchant_name')) AS merchant,
    get_json_object(payload, '$.currency') AS currency,
    CAST(get_json_object(payload, '$.amount') AS DOUBLE) AS amount,
    COALESCE(TRY_CAST(get_json_object(payload, '$.timestamp') AS TIMESTAMP), try_to_timestamp(get_json_object(payload, '$.timestamp'), 'dd/MM/yyyy')) AS event_timestamp,
    received_at,
    row_number() OVER (
      PARTITION BY COALESCE(get_json_object(payload, '$.event_id'), get_json_object(payload, '$.id'))
      ORDER BY received_at DESC
    ) AS rn
  FROM {table}
  WHERE get_json_object(payload, '$.amount') IS NOT NULL
    AND (get_json_object(payload, '$.merchant') IS NOT NULL OR get_json_object(payload, '$.merchant_name') IS NOT NULL)
    AND get_json_object(payload, '$.currency') IS NOT NULL
    AND get_json_object(payload, '$.timestamp') IS NOT NULL
)
SELECT event_id, amount, merchant, currency, event_timestamp
FROM normalized
WHERE rn = 1
"""

_ANTI_JOIN_SQL = """
WITH normalized AS (
  SELECT
    COALESCE(get_json_object(payload, '$.event_id'), get_json_object(payload, '$.id')) AS event_id,
    COALESCE(get_json_object(payload, '$.merchant'), get_json_object(payload, '$.merchant_name')) AS merchant,
    get_json_object(payload, '$.currency') AS currency,
    CAST(get_json_object(payload, '$.amount') AS DOUBLE) AS amount,
    COALESCE(TRY_CAST(get_json_object(payload, '$.timestamp') AS TIMESTAMP), try_to_timestamp(get_json_object(payload, '$.timestamp'), 'dd/MM/yyyy')) AS event_timestamp,
    received_at,
    row_number() OVER (
      PARTITION BY COALESCE(get_json_object(payload, '$.event_id'), get_json_object(payload, '$.id'))
      ORDER BY received_at DESC
    ) AS rn
  FROM batch_2_events
  WHERE get_json_object(payload, '$.amount') IS NOT NULL
    AND (get_json_object(payload, '$.merchant') IS NOT NULL OR get_json_object(payload, '$.merchant_name') IS NOT NULL)
    AND get_json_object(payload, '$.currency') IS NOT NULL
    AND get_json_object(payload, '$.timestamp') IS NOT NULL
)
SELECT n.event_id, n.amount, n.merchant, n.currency, n.event_timestamp
FROM normalized n
LEFT JOIN clean_transactions existing ON existing.event_id = n.event_id
WHERE n.rn = 1 AND existing.event_id IS NULL
"""


def _new_session():
    session_id = secrets.token_hex(16)
    with get_admin_connection() as conn:
        session_spark, _password = provision_session(conn, session_id)
    return session_id, session_spark


def _teardown(session_id):
    with get_admin_connection() as conn:
        deprovision_session(conn, session_id)


def test_only_one_commit_flags_not_incremental():
    session_id, session_spark = _new_session()
    try:
        result = commit_batch(session_spark, session_id, _CLEAN_SQL_TEMPLATE.format(table="batch_1_events"))
        assert result.success, result.error_message

        report = grade_submission(session_spark)
        assert report.passed is False
        error_codes = {f.error_code for f in report.structural_findings}
        assert "ERR_LAKEHOUSE_NOT_INCREMENTAL" in error_codes
    finally:
        _teardown(session_id)


def test_naive_per_batch_dedup_leaves_real_cross_batch_duplicates():
    """The real, empirically-confirmed lesson this phase teaches: some
    genuine event_ids have rows spanning BOTH batches, so deduplicating
    within each batch alone is not enough - this is the actual point of
    the module, not an edge case to route around."""
    session_id, session_spark = _new_session()
    try:
        r1 = commit_batch(session_spark, session_id, _CLEAN_SQL_TEMPLATE.format(table="batch_1_events"))
        assert r1.success, r1.error_message
        release_batch_two(session_spark, session_id)
        r2 = commit_batch(session_spark, session_id, _CLEAN_SQL_TEMPLATE.format(table="batch_2_events"))
        assert r2.success, r2.error_message

        report = grade_submission(session_spark)
        assert report.passed is False
        counts = Counter(f.error_code for f in report.structural_findings)
        assert counts["ERR_DUPLICATE_DELIVERY"] > 0
        # the naive submission still committed twice, correctly - incrementality itself is fine
        assert "ERR_LAKEHOUSE_NOT_INCREMENTAL" not in counts
        # and time travel is still correct, even though duplicates leaked through
        assert "ERR_LAKEHOUSE_TIME_TRAVEL_INCORRECT" not in counts
    finally:
        _teardown(session_id)


def test_cross_batch_aware_dedup_passes_with_zero_findings():
    session_id, session_spark = _new_session()
    try:
        r1 = commit_batch(session_spark, session_id, _CLEAN_SQL_TEMPLATE.format(table="batch_1_events"))
        assert r1.success, r1.error_message
        release_batch_two(session_spark, session_id)

        r2 = commit_batch(session_spark, session_id, _ANTI_JOIN_SQL)
        assert r2.success, r2.error_message

        report = grade_submission(session_spark)
        assert report.structural_findings == []
        assert report.fault_findings == []
        assert report.passed is True
        assert report.total_clean_rows > 0
    finally:
        _teardown(session_id)
