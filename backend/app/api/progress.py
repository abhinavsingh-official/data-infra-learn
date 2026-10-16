"""Module 16: progress + XP API. Auth is a single forwarded header, not a
cookie read directly - FastAPI has no access to the Next.js cookie jar
across the process boundary, so the frontend is responsible for
forwarding its own Auth.js session-token cookie value as this header
(see core/session_auth.py for why that's a safe, simple lookup)."""

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.core.db import get_connection
from app.core.session_auth import resolve_user
from app.modules.progress import certificates, mongo_node_practice, node_practice, store
from app.modules.progress.xp_rules import all_badge_definitions

router = APIRouter(prefix="/progress", tags=["progress"])


class CheckRequest(BaseModel):
    sql: str


def _require_user_id(x_session_token: str | None) -> int:
    user = resolve_user(x_session_token)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in required")
    return user.id


@router.get("/me")
def get_my_progress(x_session_token: str | None = Header(default=None)) -> dict:
    user_id = _require_user_id(x_session_token)
    with get_connection() as conn:
        return store.get_progress(conn, user_id)


@router.get("/badges")
def get_badges(x_session_token: str | None = Header(default=None)) -> dict:
    user_id = _require_user_id(x_session_token)
    with get_connection() as conn:
        earned = set(store.get_progress(conn, user_id)["badges"])
    return {
        "badges": [
            {"badge_id": badge.badge_id, "label": badge.label, "earned": badge.badge_id in earned}
            for badge in all_badge_definitions()
        ]
    }


@router.get("/certificates")
def get_certificates(x_session_token: str | None = Header(default=None)) -> dict:
    user_id = _require_user_id(x_session_token)
    with get_connection() as conn:
        completed_nodes = store.get_progress(conn, user_id)["completed_nodes"]
    return {"certificates": certificates.certificate_status(completed_nodes)}


@router.post("/nodes/{paradigm}/{node_id}/check")
def check_node(
    paradigm: str, node_id: str, body: CheckRequest, x_session_token: str | None = Header(default=None)
) -> dict:
    user_id = _require_user_id(x_session_token)
    node = node_practice.find_skill_node(paradigm, node_id)
    if node is None or node.get("type") != "skill" or "practice" not in node:
        raise HTTPException(status_code=404, detail=f"No practice node '{node_id}' for paradigm '{paradigm}'")

    if paradigm in node_practice.MONGO_PARADIGMS:
        result = mongo_node_practice.check_mongo_node_submission(paradigm, node_id, body.sql)
    else:
        result = node_practice.check_node_submission(paradigm, node_id, body.sql)
    if result["passed"]:
        with get_connection() as conn:
            result["progress"] = store.record_node_completion(conn, user_id, paradigm, node_id, node["type"])
    return result
