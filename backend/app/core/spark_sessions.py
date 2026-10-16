"""PySpark session infrastructure shared across the Warehouse, Lake, and
Lakehouse phases.

Architecture notes:

- **One shared, long-lived SparkSession per backend process.** JVM
  startup is real and expensive, so it's paid once rather than per
  visitor.
- **Per-exercise-session isolation via `SparkSession.newSession()`.** It
  gives a genuinely separate temp-view namespace and current-database
  setting per session object, while sharing the one underlying
  SparkContext/JVM.
- **Managed tables and databases are NOT session-isolated the way temp
  views are.** The catalog (CREATE DATABASE/CREATE TABLE) is shared
  across every session sharing one SparkContext, same as two sessions
  sharing one Postgres instance. Isolation instead comes from giving
  every exercise session its own uniquely-named database
  (`session_<id>`) and switching to it with `USE` once at provisioning -
  the same "shared instance, separate namespace per tenant" pattern the
  Postgres phases use with per-session schemas.
- **Every managed table needs `USING DELTA` explicitly.** A vanilla
  CREATE TABLE AS SELECT with no USING clause tries Hive's SerDe path
  and fails outright under this setup (no Hive support configured), and
  even `spark.sql.sources.default = delta` doesn't make Databricks'
  implicit-Delta behavior happen on vanilla OSS Spark - that default is
  a Databricks-managed-runtime behavior, not something delta-spark alone
  provides. UPDATE/DELETE/MERGE only work on Delta tables anyway (not
  plain parquet), so every exercise needing them has a concrete reason
  to say USING DELTA, not just a workaround.
- **No `pg.*`-qualified names like DuckDB's ATTACH gave.** Spark temp
  views are always single-part names (no schema qualification), so the
  live source tables are exposed as plain `users`/`accounts`/
  `transactions`/`reward_events`/`repayments` temp views instead of
  `pg.users` etc."""

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

# Keyed by "<phase>:<session_id>", same reasoning as duckdb_sessions'
# session_locks - different phases generate ids independently.
session_locks: dict[str, threading.Lock] = defaultdict(threading.Lock)

_global_spark = None
_global_spark_lock = threading.Lock()


def _set_java_and_python_env() -> None:
    """Must happen before the JVM/py4j subprocess ever launches - PySpark's
    worker processes otherwise inherit whatever bare `python3` resolves
    to on PATH (this machine's system Python, 3.14), not the venv
    interpreter actually running this process, and crash with
    PYTHON_VERSION_MISMATCH."""
    import sys

    settings = get_settings()
    os.environ.setdefault("JAVA_HOME", settings.spark_java_home)
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)


def _build_global_spark():
    _set_java_and_python_env()
    # Imported after the env vars above are set, not at module load time -
    # pyspark reads JAVA_HOME when it actually launches the JVM, not at
    # import time, but keeping the order explicit here avoids relying on
    # exactly when that happens.
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
        # The default 200 shuffle partitions is tuned for a real cluster,
        # not a single local process grading hand-sized exercise data.
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.driver.memory", "2g")
        # Spark's default session timezone is the JVM's local timezone,
        # not UTC. Left unset, every JDBC-read Postgres TIMESTAMPTZ
        # silently shifts by this machine's local offset relative to
        # anything computed natively in Spark, corrupting any comparison
        # between the two. Postgres/DuckDB/the rest of this project all
        # operate in UTC; Spark must too.
        .config("spark.sql.session.timeZone", "UTC")
    )
    # configure_spark_with_delta_pip sets spark.jars.packages itself,
    # overwriting rather than merging any prior value - setting the
    # Postgres JDBC driver package via .config() before this call gets
    # silently clobbered, failing every JDBC source read with
    # ClassNotFoundException. extra_packages is delta-spark's own
    # documented way to add more packages alongside Delta's own.
    builder = configure_spark_with_delta_pip(
        builder, extra_packages=["org.postgresql:postgresql:42.7.4"]
    )
    return builder.getOrCreate()


def get_global_spark():
    """Lazily builds the one shared SparkSession on first use (real JVM
    startup cost, paid once per backend process, not per request) -
    double-checked locking so concurrent first requests don't race to
    build two."""
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
    """Builds the exact SELECT this table's JDBC read uses, converting
    every `timestamptz` column to a UTC-naive timestamp server-side via
    `AT TIME ZONE 'UTC'`.

    This is load-bearing, not cosmetic. Setting `spark.sql.session.
    timeZone = "UTC"`, a JDBC `sessionInitStatement` of `SET TIME ZONE
    'UTC'`, the JVM system property `-Duser.timezone=UTC`, and disabling
    the PGJDBC driver's binary transfer all fail to prevent an unfiltered
    full-table read of a timestamptz column coming back shifted by the
    local machine's UTC offset (a single-row, server-side-filtered read
    of the same column is unaffected). Converting the column server-side,
    before the driver ever serializes it, sidesteps whatever client-side
    ambiguity causes that.

    Introspects the real column list via information_schema rather than
    hardcoding every table's columns by hand (6 tables, ~60 columns
    combined) - self-updating if a table's schema changes, only needs to
    know the engine-level fact that timestamptz columns need this
    treatment, not memorize the schema."""
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
    """Registers the five shared relational source tables as live,
    read-only temp views. Spark's JDBC data source re-queries Postgres on
    demand rather than copying once, the equivalent of a DuckDB ATTACH
    minus the `pg.` qualifier (see module docstring)."""
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
    """Shared provisioning core: a read-only Postgres role (reusing
    pg_readonly_sessions.py unchanged - it's engine-agnostic), a fresh
    per-session database in the shared SparkSession's catalog, and the
    five source tables registered as live temp views. Returns (spark_
    session, pg_password); the caller's own phase-specific provisioning
    does whatever additional per-phase setup it needs (e.g. warehouse
    phase's source_accounts_snapshot bronze copy) on top of this."""
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
    # A throwaway session for the DROP - dropping the database doesn't
    # need the original session's own temp-view state, just catalog
    # access, and the original session object may already be gone from
    # the caller's registry by the time this runs.
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
    """Same heuristic and same reasoning as every other phase's execution
    layer (Postgres/DuckDB) - a stateless single-execute()-per-request
    endpoint risks silently losing a later statement's results."""
    return ";" in sql_text.strip().rstrip(";")


def _jsonable_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    return value


def execute_spark_submission(session_spark, lock: threading.Lock, sql_text: str) -> SparkExecutionResult:
    """Runs exactly one SQL statement against the session's own Spark-
    session object (already USE'd into its own database at provisioning,
    a setting that persists on that session object across calls)."""
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
        except Exception as e:  # noqa: BLE001 - Spark raises its own broad exception hierarchy, same
            # resilience contract as every other phase's execute(): a bad
            # submission must come back structured, never crash the request.
            return SparkExecutionResult(success=False, error_code=type(e).__name__, error_message=str(e).strip())
