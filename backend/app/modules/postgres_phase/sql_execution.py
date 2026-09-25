"""Module 4.3: executes user-submitted SQL as the session's restricted
role. Resilient by design, mirroring the health-check fix from Module 1 -
a bad submission (syntax error, timeout, permission violation) must come
back as a structured result, not an unhandled 500."""

from dataclasses import dataclass, field
from typing import Any

import psycopg

from app.core.config import get_settings


@dataclass
class ExecutionResult:
    success: bool
    columns: list[str] = field(default_factory=list)
    rows: list[tuple[Any, ...]] = field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None


def _session_dsn(role: str, password: str) -> str:
    settings = get_settings()
    return f"postgresql://{role}:{password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"


def execute_submission(role: str, password: str, sql_text: str) -> ExecutionResult:
    """Runs the full submitted script (may be multiple ;-separated
    statements) in one transaction as the session's own restricted role -
    never the admin connection. Any failure (syntax, timeout, permission)
    comes back as a structured ExecutionResult, not a raised exception."""
    try:
        with psycopg.connect(_session_dsn(role, password)) as conn:
            with conn.cursor() as cur:
                cur.execute(sql_text)
                if cur.description is not None:
                    columns = [d.name for d in cur.description]
                    rows = cur.fetchall()
                else:
                    columns, rows = [], []
            conn.commit()
            return ExecutionResult(success=True, columns=columns, rows=rows)
    except psycopg.Error as e:
        return ExecutionResult(
            success=False,
            error_code=e.sqlstate or "UNKNOWN",
            error_message=str(e).strip(),
        )
