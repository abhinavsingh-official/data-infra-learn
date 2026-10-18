"""PySpark session infrastructure shared across the Warehouse, Lake, and
Lakehouse phases.

One shared, long-lived SparkSession per process (JVM startup is
expensive), with per-exercise isolation via `SparkSession.newSession()`
for temp views/current-database - but NOT for managed tables, which
share one catalog, so each session also gets its own database
(`session_<id>`) via `USE`. Every managed table needs `USING DELTA`
explicitly (a bare CTAS tries Hive's SerDe and fails; vanilla OSS Spark
doesn't get Databricks' implicit-Delta default). Source tables are
exposed as plain `users`/`accounts`/etc. temp views, not `pg.`-qualified
like DuckDB's ATTACH gave."""

import os
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from psycopg import Connection

from app.core.config import get_settings
from app.core.pg_readonly_sessions import (
    READABLE_SOURCE_TABLES,
    deprovision_pg_readonly_session,
    make_role_name,
    provision_pg_readonly_session,
)
from app.core.session_ids import validate_session_id

MAX_RETURNED_ROWS = 1000

# Keyed by "<phase>:<session_id>" - different phases generate ids independently.
session_locks: dict[str, threading.Lock] = defaultdict(threading.Lock)

_global_spark = None
_global_spark_lock = threading.Lock()


def _set_java_and_python_env() -> None:
    """Must run before the JVM/py4j subprocess launches, or PySpark's
    workers inherit whatever bare `python3` resolves to on PATH instead
    of this venv's interpreter, and crash with PYTHON_VERSION_MISMATCH."""
    import sys

    settings = get_settings()
    os.environ.setdefault("JAVA_HOME", settings.spark_java_home)
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)


def _build_global_spark():
    _set_java_and_python_env()
    # Imported after the env vars above are set - pyspark reads JAVA_HOME
    # when it launches the JVM, not at import time, but no reason to rely
    # on that.
    from delta import configure_spark_with_delta_pip
    from pyspark.sql import SparkSession

    settings = get_settings()
    settings.spark_warehouse_dir.mkdir(parents=True, exist_ok=True)
    builder = (
        SparkSession.builder.appName("data-infra-learn")
        .master("local[*]")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.warehouse.dir", str(settings.spark_warehouse_dir))
        .config("spark.ui.enabled", "false")
        # 200 is tuned for a real cluster, not this process's tiny data.
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.driver.memory", "2g")
        # Otherwise defaults to the JVM's local timezone, shifting every
        # JDBC-read Postgres TIMESTAMPTZ out of sync with the rest of
        # the project, which is all UTC.
        .config("spark.sql.session.timeZone", "UTC")
    )
    # configure_spark_with_delta_pip overwrites spark.jars.packages
    # rather than merging it, so the Postgres JDBC driver has to go in
    # via its own extra_packages param, not an earlier .config() call.
    builder = configure_spark_with_delta_pip(
        builder, extra_packages=["org.postgresql:postgresql:42.7.4"]
    )
    return builder.getOrCreate()


def get_global_spark():
    """Builds the shared SparkSession on first use; double-checked
    locking so concurrent first requests don't race to build two."""
    global _global_spark
    if _global_spark is None:
        with _global_spark_lock:
            if _global_spark is None:
                _global_spark = _build_global_spark()
                _global_spark.sparkContext.setLogLevel("ERROR")
    return _global_spark


def session_db_name(phase_prefix: str, session_id: str) -> str:
    validate_session_id(session_id)
    return f"{phase_prefix}_{session_id}"


def session_lock(phase_prefix: str, session_id: str) -> threading.Lock:
    return session_locks[f"{phase_prefix}:{session_id}"]


def pg_role_name(phase_prefix: str, session_id: str) -> str:
    return make_role_name(f"{phase_prefix}_session_", session_id)


def _source_query(pg_conn: Connection, table: str) -> str:
    """Converts every `timestamptz` column to UTC server-side via
    `AT TIME ZONE 'UTC'` - an unfiltered JDBC full-table read otherwise
    comes back shifted by the local machine's UTC offset (confirmed: a
    session timezone config, a JDBC init statement, and a JVM property
    all failed to fix it; only converting server-side worked). Columns
    come from information_schema so this doesn't need hardcoding."""
    with pg_conn.cursor() as cur:
        cur.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = %s ORDER BY ordinal_position",
            (table,),
        )
        columns = cur.fetchall()
    select_list = ", ".join(
        f"\"{name}\" AT TIME ZONE 'UTC' AS \"{name}\"" if data_type == "timestamp with time zone" else f'"{name}"'
        for name, data_type in columns
    )
    return f"(SELECT {select_list} FROM public.{table}) t"


def provision_pg_source_views(spark_session, pg_conn: Connection, pg_role: str, pg_password: str) -> None:
    """Registers the shared source tables as live, read-only temp views -
    Spark's JDBC source re-queries Postgres on demand, not a one-time copy."""
    settings = get_settings()
    for table in READABLE_SOURCE_TABLES:
        df = (
            spark_session.read.format("jdbc")
            .option("url", settings.postgres_jdbc_url)
            .option("dbtable", _source_query(pg_conn, table))
            .option("user", pg_role)
            .option("password", pg_password)
            .option("driver", "org.postgresql.Driver")
            .load()
        )
        df.createOrReplaceTempView(table)


def provision_phase_session(pg_conn: Connection, phase_prefix: str, session_id: str):
    """Shared provisioning core: a read-only Postgres role, a fresh
    per-session database, and the source tables as temp views. Callers
    do their own phase-specific setup on top of this."""
    role = pg_role_name(phase_prefix, session_id)
    password = provision_pg_readonly_session(pg_conn, role)

    spark = get_global_spark()
    session_spark = spark.newSession()
    db = session_db_name(phase_prefix, session_id)
    session_spark.sql(f"CREATE DATABASE IF NOT EXISTS {db}")
    session_spark.sql(f"USE {db}")
    provision_pg_source_views(session_spark, pg_conn, role, password)
    return session_spark, password


def deprovision_phase_session(pg_conn: Connection, phase_prefix: str, session_id: str) -> None:
    deprovision_pg_readonly_session(pg_conn, pg_role_name(phase_prefix, session_id))
    spark = get_global_spark()
    db = session_db_name(phase_prefix, session_id)
    # A throwaway session for the DROP - the original session's state
    # isn't needed, and it may already be gone from the registry.
    spark.newSession().sql(f"DROP DATABASE IF EXISTS {db} CASCADE")


@dataclass
class SparkExecutionResult:
    success: bool
    columns: list[str] = field(default_factory=list)
    rows: list[tuple[Any, ...]] = field(default_factory=list)
    truncated: bool = False
    error_code: str | None = None
    error_message: str | None = None


def contains_multiple_statements(sql_text: str) -> bool:
    return ";" in sql_text.strip().rstrip(";")


def _jsonable_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    return value


def execute_spark_submission(session_spark, lock: threading.Lock, sql_text: str) -> SparkExecutionResult:
    if contains_multiple_statements(sql_text):
        return SparkExecutionResult(
            success=False,
            error_code="MULTIPLE_STATEMENTS",
            error_message="Submit one SQL statement per request.",
        )
    with lock:
        try:
            df = session_spark.sql(sql_text)
            columns = df.columns
            collected = df.take(MAX_RETURNED_ROWS + 1)
            truncated = len(collected) > MAX_RETURNED_ROWS
            if truncated:
                collected = collected[:MAX_RETURNED_ROWS]
            rows = [tuple(_jsonable_value(v) for v in row) for row in collected]
            return SparkExecutionResult(success=True, columns=columns, rows=rows, truncated=truncated)
        except Exception as e:  # noqa: BLE001 - a bad submission comes back structured, never crashes
            return SparkExecutionResult(success=False, error_code=type(e).__name__, error_message=str(e).strip())
