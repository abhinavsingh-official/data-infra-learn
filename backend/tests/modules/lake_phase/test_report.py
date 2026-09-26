import secrets

from app.core.db import get_admin_connection
from app.modules.lake_phase.duckdb_execution import execute_submission
from app.modules.lake_phase.report import grade_submission
from app.modules.lake_phase.session_provisioning import (
    deprovision_session,
    output_dir,
    pg_role_name,
    provision_session,
)


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


def test_unpartitioned_preflattened_incomplete_submission_flags_lake_specific_findings():
    session_id, role, password = _new_session()
    try:
        single_file = str(output_dir(session_id) / "single.parquet")
        _run(
            session_id,
            role,
            password,
            f"COPY (SELECT id, received_at, source_delivery_id, payload->>'event_id' AS event_id "
            f"FROM pg.raw_transaction_events LIMIT 100) TO '{single_file}' (FORMAT PARQUET)",
            "write single flattened file",
        )
        _run(
            session_id,
            role,
            password,
            f"CREATE TABLE clean_transactions AS SELECT event_id, 1.0 AS amount, 'x' AS merchant, "
            f"'USD' AS currency, received_at AS event_timestamp FROM read_parquet('{single_file}')",
            "build partial clean_transactions",
        )

        report = grade_submission(session_id, password)
        assert report.passed is False
        error_codes = {f.error_code for f in report.structural_findings}
        assert "ERR_LAKE_NOT_PARTITIONED" in error_codes
        assert "ERR_LAKE_PAYLOAD_PREFLATTENED" in error_codes
    finally:
        _teardown(session_id)


_CLEAN_TRANSACTIONS_SQL = """
CREATE TABLE clean_transactions AS
SELECT DISTINCT ON (payload_json->>'event_id')
  payload_json->>'event_id' AS event_id,
  CASE WHEN json_type(payload_json->'amount') = 'VARCHAR' THEN TRY_CAST(payload_json->>'amount' AS DOUBLE)
       WHEN (payload_json->'amount') IS NOT NULL THEN TRY_CAST(payload_json->>'amount' AS DOUBLE) / 100
       ELSE 1 END AS amount,
  COALESCE(payload_json->>'merchant', payload_json->>'merchant_name', 'UNKNOWN') AS merchant,
  COALESCE(payload_json->>'currency', 'USD') AS currency,
  COALESCE(TRY_CAST(NULLIF(payload_json->>'timestamp', '') AS TIMESTAMPTZ), received_at) AS event_timestamp
FROM (
    SELECT received_at, payload::JSON AS payload_json
    FROM read_parquet('{out}/**/*.parquet', hive_partitioning=true, union_by_name=true)
) t
WHERE payload_json->>'event_id' IS NOT NULL
ORDER BY payload_json->>'event_id', received_at ASC
"""


def test_correct_partitioned_schema_on_read_submission_passes_with_zero_findings():
    """Regression for two real bugs found while building this module: a
    DuckDB operator-precedence gotcha (`->` binds looser than IS NOT
    NULL - `x->'k' IS NOT NULL` misparses without parentheses) and
    DuckDB's ::TIMESTAMPTZ cast being stricter than Postgres's (throws on
    the malformed_ambiguous_date fault's regional date strings; TRY_CAST
    is required, not a bare cast)."""
    session_id, role, password = _new_session()
    out = str(output_dir(session_id))
    try:
        _run(
            session_id,
            role,
            password,
            f"COPY (SELECT id, received_at, source_delivery_id, payload::VARCHAR AS payload, "
            f"received_at::DATE AS event_date FROM pg.raw_transaction_events) TO '{out}' "
            f"(FORMAT PARQUET, PARTITION_BY (event_date), OVERWRITE_OR_IGNORE)",
            "write partitioned parquet",
        )
        _run(session_id, role, password, _CLEAN_TRANSACTIONS_SQL.format(out=out), "build clean_transactions")

        report = grade_submission(session_id, password)
        assert report.structural_findings == []
        assert report.fault_findings == []
        assert report.passed is True
        assert report.total_clean_rows > 0
    finally:
        _teardown(session_id)
