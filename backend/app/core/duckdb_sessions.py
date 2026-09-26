"""DuckDB session helpers shared across every DuckDB-based phase module -
first written for warehouse_phase (Module 8), extracted here once
lake_phase (Module 9) needed the identical mechanism. A third real
caller (lakehouse_phase, Module 10) is expected too, which is the actual
threshold CODE_STANDARDS.md's "duplication is fine for phase modules"
guidance is about avoiding invented generality *before*, not after."""

import threading
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

import duckdb

from app.core.config import get_settings

MAX_RETURNED_ROWS = 1000

# Keyed by "<phase>:<session_id>", not session_id alone - different phase
# modules generate session ids independently and could theoretically
# collide; the phase prefix keeps their locks from colliding too, same
# reasoning as the Postgres role-name prefixes in pg_readonly_sessions.
session_locks: dict[str, threading.Lock] = defaultdict(threading.Lock)


def open_duckdb_file(path: Path) -> duckdb.DuckDBPyConnection:
    """The one place any session's DuckDB file gets opened - DuckDB's
    default progress bar (meant for an interactive CLI) writes directly
    to the server process's stdout for any multi-second query, which
    every grading/mutation query in these phases is. Disabled once,
    here, rather than at each call site (found by testing directly -
    confirmed via warehouse_phase's Module 8 review)."""
    con = duckdb.connect(str(path))
    con.execute("SET enable_progress_bar = false;")
    return con


def attach_postgres_source(con: duckdb.DuckDBPyConnection, role: str, password: str, alias: str = "pg") -> None:
    """ATTACH doesn't persist across a DuckDB file's connections (confirmed
    by testing directly - reopening a file with a schema previously
    attached raises CatalogException) - every caller that opens a
    session's file needs to redo this, not just provisioning.

    IF NOT EXISTS, not a bare ATTACH: found by testing concurrent
    requests against the same session directly - DuckDB's Python client
    shares one underlying database instance/catalog across every
    connection opened to the same file path within a single process, so
    a second concurrent connection sees the alias already attached by
    the first and a bare ATTACH raises BinderException (confirmed: 7 of
    8 concurrent requests failed this way in Module 8's review before
    this fix, and callers must ALSO serialize on `session_locks` - IF
    NOT EXISTS alone isn't race-free against truly concurrent connects)."""
    settings = get_settings()
    con.execute("INSTALL postgres; LOAD postgres;")
    conninfo = settings.postgres_attach_conninfo(role, password)
    con.execute(f"ATTACH IF NOT EXISTS '{conninfo}' AS {alias} (TYPE postgres, READ_ONLY)")


@dataclass
class DuckDbExecutionResult:
    success: bool
    columns: list[str] = field(default_factory=list)
    rows: list[tuple[Any, ...]] = field(default_factory=list)
    truncated: bool = False
    error_code: str | None = None
    error_message: str | None = None


def contains_multiple_statements(sql_text: str) -> bool:
    """Not a real SQL parser, but multi-statement submissions against a
    stateless single-execute() endpoint risk losing a later statement's
    results silently (confirmed for Postgres in Module 4 - psycopg3's
    simple-query-protocol multi-statement execution left cur.description
    as None even when the last statement was a SELECT)."""
    return ";" in sql_text.strip().rstrip(";")


def _jsonable_row(row: tuple[Any, ...]) -> tuple[Any, ...]:
    """FastAPI's response serialization for a bare `-> dict` return
    annotation renders a raw Decimal as a quoted JSON string, not a
    number (confirmed directly for both psycopg's Postgres NUMERIC and
    DuckDB's DECIMAL - see Module 4/7's and Module 8's reviews)."""
    return tuple(float(value) if isinstance(value, Decimal) else value for value in row)


def execute_duckdb_submission(
    session_id: str,
    open_session_db: Callable[[str], duckdb.DuckDBPyConnection],
    lock: threading.Lock,
    pg_role: str,
    pg_password: str,
    sql_text: str,
    pg_alias: str = "pg",
) -> DuckDbExecutionResult:
    """The reusable core behind every DuckDB-based phase's execute()
    endpoint: open the session's file, re-attach Postgres, run exactly
    one statement, close. `open_session_db` is the phase's own file-path
    resolver and `lock` its own phase-prefixed session_locks entry (each
    phase keeps its own sessions directory and lock-key prefix), passed
    in rather than assumed, since those are the two things that differ
    per-phase."""
    if contains_multiple_statements(sql_text):
        return DuckDbExecutionResult(
            success=False,
            error_code="MULTIPLE_STATEMENTS",
            error_message="Submit one SQL statement per request.",
        )
    with lock:
        con = open_session_db(session_id)
        try:
            attach_postgres_source(con, pg_role, pg_password, alias=pg_alias)
            result = con.execute(sql_text)
            if result.description is not None:
                columns = [d[0] for d in result.description]
                rows = result.fetchmany(MAX_RETURNED_ROWS + 1)
                truncated = len(rows) > MAX_RETURNED_ROWS
                if truncated:
                    rows = rows[:MAX_RETURNED_ROWS]
                rows = [_jsonable_row(row) for row in rows]
            else:
                columns, rows, truncated = [], [], False
            return DuckDbExecutionResult(success=True, columns=columns, rows=rows, truncated=truncated)
        except duckdb.Error as e:
            return DuckDbExecutionResult(success=False, error_code=type(e).__name__, error_message=str(e).strip())
        finally:
            con.close()
