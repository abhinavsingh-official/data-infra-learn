"""Executes user-submitted SQL as the session's restricted role. A bad
submission (syntax error, timeout, permission violation) comes back as
a structured result, not an unhandled 500 - same approach as the
health-check endpoint's own error handling."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import psycopg

from app.core.config import get_settings

MAX_RETURNED_ROWS = 1000


@dataclass
class ExecutionResult:
    success: bool
    columns: list[str] = field(default_factory=list)
    rows: list[tuple[Any, ...]] = field(default_factory=list)
    truncated: bool = False
    error_code: str | None = None
    error_message: str | None = None


def _session_dsn(role: str, password: str) -> str:
    settings = get_settings()
    return f"postgresql://{role}:{password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"


def _jsonable_row(row: tuple[Any, ...]) -> tuple[Any, ...]:
    """FastAPI's response serialization for a bare `-> dict` return
    annotation (no Pydantic response_model) renders a raw Decimal as a
    quoted JSON string, not a number - unlike calling jsonable_encoder by
    hand, which does convert it to a float. Every NUMERIC column a user's
    SELECT returns (amount, balance, etc.) would otherwise come back
    type-wrong over the API, which also affects nosql_phase's
    query-source, since it reuses this function directly."""
    return tuple(float(value) if isinstance(value, Decimal) else value for value in row)


def _contains_multiple_statements(sql_text: str) -> bool:
    """Heuristic, not a real SQL parser - could false-positive on a
    single statement whose only string literal contains a semicolon.
    psycopg3's simple-query-protocol multi-statement execution leaves
    cur.description as None even when the last statement was a SELECT,
    so a multi-statement submission would silently return "success" with
    empty results instead of erroring. Rejecting multi-statement
    submissions with a clear message is safer than silently losing a
    result set the caller thinks it received."""
    return ";" in sql_text.strip().rstrip(";")


def execute_submission(role: str, password: str, sql_text: str) -> ExecutionResult:
    """Runs exactly one SQL statement as the session's own restricted
    role - never the admin connection. Any failure (syntax, timeout,
    permission, multi-statement rejection) comes back as a structured
    ExecutionResult, not a raised exception. Row-returning results are
    capped at MAX_RETURNED_ROWS - an unbounded SELECT against the raw
    feed can produce a multi-megabyte response in under a second, a real
    resource-exhaustion risk on a low-spec host."""
    if _contains_multiple_statements(sql_text):
        return ExecutionResult(
            success=False,
            error_code="MULTIPLE_STATEMENTS",
            error_message=(
                "Submit one SQL statement per request - a semicolon-separated multi-statement "
                "submission would silently lose the final statement's results."
            ),
        )
    try:
        with psycopg.connect(_session_dsn(role, password)) as conn:
            with conn.cursor() as cur:
                cur.execute(sql_text)
                truncated = False
                if cur.description is not None:
                    columns = [d.name for d in cur.description]
                    rows = cur.fetchmany(MAX_RETURNED_ROWS + 1)
                    if len(rows) > MAX_RETURNED_ROWS:
                        rows = rows[:MAX_RETURNED_ROWS]
                        truncated = True
                    rows = [_jsonable_row(row) for row in rows]
                else:
                    columns, rows = [], []
            conn.commit()
            return ExecutionResult(success=True, columns=columns, rows=rows, truncated=truncated)
    except psycopg.Error as e:
        return ExecutionResult(
            success=False,
            error_code=e.sqlstate or "UNKNOWN",
            error_message=str(e).strip(),
        )
