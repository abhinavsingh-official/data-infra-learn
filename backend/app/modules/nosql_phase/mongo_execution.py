"""Executes a user-submitted Mongo command as the session's own scoped
user. Same resilience contract as postgres_phase.sql_execution - any
failure comes back as a structured result, never an unhandled 500.

The submission format is a raw Mongo command document (`{"insert": ...,
"documents": [...]}`, `{"aggregate": ..., "pipeline": [...], "cursor":
{}}`, etc.) run via `db.command()` - Mongo's own native command
interface, not a hand-rolled subset. Safety comes from the connection
being authenticated as a user scoped to exactly one database (see
session_provisioning.py), the same way the Postgres phase trusts
Postgres's own restricted-role mechanism rather than sandboxing SQL
text itself."""

from dataclasses import dataclass, field
from typing import Any

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.core.config import get_settings

# A submitted command can set an explicit "batchSize"/"cursor.batchSize"
# well past Mongo's own default 101-document first batch - that default
# cap does NOT apply once a caller sets batchSize themselves, which is
# the same unbounded-result-set risk the Postgres phase guards against,
# just reachable through a different knob. Truncated here regardless of
# what the submitted command asked for, rather than trusting the
# command's own batchSize to stay reasonable.
MAX_RETURNED_DOCS = 1000


@dataclass
class MongoExecutionResult:
    success: bool
    result: dict[str, Any] = field(default_factory=dict)
    truncated: bool = False
    error_code: str | None = None
    error_message: str | None = None


def _session_uri(db_name: str, password: str) -> str:
    settings = get_settings()
    return f"mongodb://{db_name}:{password}@{settings.mongo_host}:{settings.mongo_port}/{db_name}?authSource={db_name}"


def _truncate_cursor_batches(result: dict[str, Any]) -> bool:
    """Mutates `result` in place, capping any embedded cursor batch
    (`find`/`aggregate` responses share this exact shape) to
    MAX_RETURNED_DOCS. Returns whether truncation happened."""
    cursor = result.get("cursor")
    if not isinstance(cursor, dict):
        return False
    truncated = False
    for batch_key in ("firstBatch", "nextBatch"):
        batch = cursor.get(batch_key)
        if isinstance(batch, list) and len(batch) > MAX_RETURNED_DOCS:
            cursor[batch_key] = batch[:MAX_RETURNED_DOCS]
            truncated = True
    return truncated


def execute_submission(db_name: str, password: str, command: dict[str, Any]) -> MongoExecutionResult:
    """Runs exactly one Mongo command as the session's own scoped user -
    never the admin connection. Any failure (bad command, permission
    violation, timeout) comes back as a structured MongoExecutionResult,
    not a raised exception."""
    client = MongoClient(_session_uri(db_name, password))
    try:
        result = client[db_name].command(command)
        result.pop("ok", None)  # always 1.0 on success - noise, not signal
        truncated = _truncate_cursor_batches(result)
        return MongoExecutionResult(success=True, result=result, truncated=truncated)
    except PyMongoError as e:
        code = getattr(e, "code", None)
        return MongoExecutionResult(
            success=False,
            error_code=str(code) if code is not None else "UNKNOWN",
            error_message=str(e).strip(),
        )
    finally:
        client.close()
