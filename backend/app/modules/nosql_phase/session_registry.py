"""In-memory session_id -> credentials/created_at store for the NoSQL
phase - a separate registry from postgres_phase's, since a session_id
here refers to a Mongo database, not a Postgres schema, and a user could
plausibly have one of each open at once. Same single-process, TTL-based
design as postgres_phase.session_registry - see that module's docstring
for the documented distributed-store limitation, which applies equally
here and isn't repeated per module (CODE_STANDARDS.md: three similar
modules are fine as three similar modules)."""

import time
from dataclasses import dataclass

SESSION_TTL_SECONDS = 30 * 60


@dataclass
class SessionRecord:
    mongo_password: str
    pg_password: str
    created_at: float


_sessions: dict[str, SessionRecord] = {}


def register(session_id: str, mongo_password: str, pg_password: str) -> None:
    _sessions[session_id] = SessionRecord(
        mongo_password=mongo_password, pg_password=pg_password, created_at=time.time()
    )


def get(session_id: str) -> SessionRecord | None:
    return _sessions.get(session_id)


def forget(session_id: str) -> None:
    _sessions.pop(session_id, None)


def expired_session_ids() -> list[str]:
    now = time.time()
    snapshot = list(_sessions.items())
    return [sid for sid, rec in snapshot if now - rec.created_at > SESSION_TTL_SECONDS]
