"""In-memory session_id -> credentials/created_at store for the
lakehouse phase - same single-process, TTL-based design as the other
phases' registries. Also holds the session's own SparkSession object;
see warehouse_phase.session_registry for why that has to be the same
object reused across requests, not a fresh one each time."""

import time
from dataclasses import dataclass
from typing import Any

SESSION_TTL_SECONDS = 30 * 60


@dataclass
class SessionRecord:
    pg_password: str
    spark_session: Any
    created_at: float


_sessions: dict[str, SessionRecord] = {}


def register(session_id: str, pg_password: str, spark_session: Any) -> None:
    _sessions[session_id] = SessionRecord(pg_password=pg_password, spark_session=spark_session, created_at=time.time())


def get(session_id: str) -> SessionRecord | None:
    return _sessions.get(session_id)


def forget(session_id: str) -> None:
    _sessions.pop(session_id, None)


def expired_session_ids() -> list[str]:
    now = time.time()
    snapshot = list(_sessions.items())
    return [sid for sid, rec in snapshot if now - rec.created_at > SESSION_TTL_SECONDS]
