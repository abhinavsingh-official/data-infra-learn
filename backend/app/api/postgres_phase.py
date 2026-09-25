import secrets

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.db import get_admin_connection
from app.modules.postgres_phase import session_registry
from app.modules.postgres_phase.session_provisioning import role_name, deprovision_session, provision_session
from app.modules.postgres_phase.sql_execution import execute_submission
from app.modules.postgres_phase.task_content import POSTGRES_PHASE_TASK

router = APIRouter(prefix="/postgres-phase", tags=["postgres-phase"])


class ExecuteRequest(BaseModel):
    sql: str


def _cleanup_expired_sessions() -> None:
    expired = session_registry.expired_session_ids()
    if not expired:
        return
    with get_admin_connection() as conn:
        for session_id in expired:
            deprovision_session(conn, session_id)
            session_registry.forget(session_id)


@router.get("/task")
def get_task() -> dict:
    return POSTGRES_PHASE_TASK


@router.post("/sessions")
def create_session() -> dict:
    _cleanup_expired_sessions()
    session_id = secrets.token_hex(16)
    with get_admin_connection() as conn:
        password = provision_session(conn, session_id)
    session_registry.register(session_id, password)
    return {"session_id": session_id}


@router.post("/sessions/{session_id}/execute")
def execute(session_id: str, body: ExecuteRequest) -> dict:
    record = session_registry.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    result = execute_submission(role_name(session_id), record.password, body.sql)
    return {
        "success": result.success,
        "columns": result.columns,
        "rows": result.rows,
        "truncated": result.truncated,
        "error_code": result.error_code,
        "error_message": result.error_message,
    }


@router.delete("/sessions/{session_id}")
def end_session(session_id: str) -> dict:
    record = session_registry.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    with get_admin_connection() as conn:
        deprovision_session(conn, session_id)
    session_registry.forget(session_id)
    return {"status": "deprovisioned"}
