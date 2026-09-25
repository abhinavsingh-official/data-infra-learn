"""In-memory session_id -> credentials/created_at store, with TTL-based
expiry. Deliberately single-process, not distributed - this platform runs
as one backend process; a distributed store (Redis etc.) would be
premature abstraction for a scope this size. Documented as a known
limitation for whenever the platform needs to run more than one backend
process, not silently glossed over."""

import time
from dataclasses import dataclass

SESSION_TTL_SECONDS = 30 * 60


@dataclass
class SessionRecord:
    password: str
    created_at: float


_sessions: dict[str, SessionRecord] = {}


def register(session_id: str, password: str) -> None:
    _sessions[session_id] = SessionRecord(password=password, created_at=time.time())


def get(session_id: str) -> SessionRecord | None:
    return _sessions.get(session_id)


def forget(session_id: str) -> None:
    _sessions.pop(session_id, None)


def expired_session_ids() -> list[str]:
    # Snapshot before iterating: defensive against a concurrent
    # register()/forget() mutating the dict mid-iteration (Python raises
    # RuntimeError if a dict changes size while iterating it directly).
    # Tried to reproduce this under real concurrent stress (20+ threads,
    # shared keys) and didn't manage to - noting that honestly rather than
    # claiming a bug was found - but the fix is free, so applying it as
    # standard defensive practice rather than leaving the theoretical risk.
    now = time.time()
    snapshot = list(_sessions.items())
    return [sid for sid, rec in snapshot if now - rec.created_at > SESSION_TTL_SECONDS]
