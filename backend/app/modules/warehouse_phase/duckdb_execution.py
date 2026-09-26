"""Module 8's submission mechanism. DuckDB is embedded, not a network
service, so there's no persistent per-session connection to hold open the
way Postgres/Mongo phases do - every submission opens the session's own
file, re-attaches the Postgres source (see session_provisioning.py on why
that doesn't persist across connections), runs exactly one statement, and
closes. Same resilience contract as the other phases: any failure comes
back as a structured result, never an unhandled 500."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import duckdb

from app.modules.warehouse_phase.session_provisioning import attach_postgres_source, db_path

MAX_RETURNED_ROWS = 1000


@dataclass
class DuckDbExecutionResult:
    success: bool
    columns: list[str] = field(default_factory=list)
    rows: list[tuple[Any, ...]] = field(default_factory=list)
    truncated: bool = False
    error_code: str | None = None
    error_message: str | None = None


def _contains_multiple_statements(sql_text: str) -> bool:
    """Same heuristic as postgres_phase.sql_execution, for the same
    reason - not a real SQL parser, but multi-statement submissions
    against a stateless single-execute() endpoint risk losing a later
    statement's results silently."""
    return ";" in sql_text.strip().rstrip(";")


def _jsonable_row(row: tuple[Any, ...]) -> tuple[Any, ...]:
    """Same fix as postgres_phase.sql_execution's - confirmed directly
    that DuckDB's driver returns Python Decimal for DECIMAL columns too,
    which FastAPI's bare `-> dict` response serialization renders as a
    quoted JSON string instead of a number. Applied here proactively
    rather than waiting to rediscover the same bug a third time."""
    return tuple(float(value) if isinstance(value, Decimal) else value for value in row)


def execute_submission(session_id: str, pg_role: str, pg_password: str, sql_text: str) -> DuckDbExecutionResult:
    if _contains_multiple_statements(sql_text):
        return DuckDbExecutionResult(
            success=False,
            error_code="MULTIPLE_STATEMENTS",
            error_message="Submit one SQL statement per request.",
        )
    con = duckdb.connect(str(db_path(session_id)))
    try:
        attach_postgres_source(con, pg_role, pg_password)
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
