import secrets

from app.core.db import get_admin_connection
from app.modules.lake_phase.report import grade_submission
from app.modules.lake_phase.session_provisioning import (
    deprovision_session,
    execute,
    output_dir,
    provision_session,
)


def _run(session_spark, session_id, sql, label=""):
    result = execute(session_spark, session_id, sql)
    assert result.success, f"{label}: {result.error_code} {result.error_message}"
    return result


def _new_session():
    session_id = secrets.token_hex(16)
    with get_admin_connection() as conn:
        session_spark, _password = provision_session(conn, session_id)
    return session_id, session_spark


def _teardown(session_id):
    with get_admin_connection() as conn:
        deprovision_session(conn, session_id)


def test_unpartitioned_preflattened_incomplete_submission_flags_lake_specific_findings():
    session_id, session_spark = _new_session()
    try:
        single_file = str(output_dir(session_id) / "single")
        _run(
            session_spark,
            session_id,
            f"CREATE TABLE lake_single USING PARQUET LOCATION '{single_file}' AS "
            f"SELECT id, received_at, source_delivery_id, get_json_object(payload, '$.event_id') AS event_id "
            f"FROM raw_transaction_events LIMIT 100",
            "write single flattened file",
        )
        _run(
            session_spark,
            session_id,
            f"CREATE TABLE clean_transactions USING DELTA AS SELECT event_id, 1.0 AS amount, 'x' AS merchant, "
            f"'USD' AS currency, received_at AS event_timestamp FROM parquet.`{single_file}`",
            "build partial clean_transactions",
        )

        report = grade_submission(session_spark, session_id)
        assert report.passed is False
        error_codes = {f.error_code for f in report.structural_findings}
        assert "ERR_LAKE_NOT_PARTITIONED" in error_codes
        assert "ERR_LAKE_PAYLOAD_PREFLATTENED" in error_codes
    finally:
        _teardown(session_id)


_WRITE_SQL = (
    "CREATE TABLE lake_output USING PARQUET PARTITIONED BY (event_date) LOCATION '{out}' AS "
    "SELECT id, received_at, source_delivery_id, payload, CAST(received_at AS DATE) AS event_date "
    "FROM raw_transaction_events"
)

_CLEAN_TRANSACTIONS_SQL = """
CREATE TABLE clean_transactions USING DELTA AS
WITH raw AS (
  SELECT id, received_at, payload FROM parquet.`{out}`
),
normalized AS (
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
  FROM raw
  WHERE get_json_object(payload, '$.amount') IS NOT NULL
    AND (get_json_object(payload, '$.merchant') IS NOT NULL OR get_json_object(payload, '$.merchant_name') IS NOT NULL)
    AND get_json_object(payload, '$.currency') IS NOT NULL
    AND get_json_object(payload, '$.timestamp') IS NOT NULL
)
SELECT event_id, amount, merchant, currency, event_timestamp
FROM normalized
WHERE rn = 1
"""


def test_correct_partitioned_schema_on_read_submission_passes_with_zero_findings():
    """Regression for two real bugs found while building this module: a
    DuckDB operator-precedence gotcha (`->` binds looser than IS NOT
    NULL - fixed by porting to Spark's get_json_object(), a plain
    function call with no such gotcha) and a strict bare CAST throwing on
    the malformed_ambiguous_date fault's regional date strings - TRY_CAST
    is required, not a bare cast, on this engine too."""
    session_id, session_spark = _new_session()
    out = str(output_dir(session_id))
    try:
        _run(session_spark, session_id, _WRITE_SQL.format(out=out), "write partitioned parquet")
        _run(session_spark, session_id, _CLEAN_TRANSACTIONS_SQL.format(out=out), "build clean_transactions")

        report = grade_submission(session_spark, session_id)
        assert report.structural_findings == []
        assert report.fault_findings == []
        assert report.passed is True
        assert report.total_clean_rows > 0
    finally:
        _teardown(session_id)
