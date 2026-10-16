import secrets

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.db import get_admin_connection
from app.modules.lake_phase import session_registry
from app.modules.lake_phase.report import grade_submission
from app.modules.lake_phase.session_provisioning import (
    deprovision_session,
    execute,
    output_dir,
    provision_session,
)
from app.modules.lake_phase.skill_tree import LAKE_SKILL_TREE
from app.modules.lake_phase.task_content import LAKE_PHASE_TASK

router = APIRouter(prefix="/lake-phase", tags=["lake-phase"])


@router.get("/skill-tree")
def get_skill_tree() -> dict:
    return LAKE_SKILL_TREE


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
    return LAKE_PHASE_TASK


@router.post("/sessions")
def create_session() -> dict:
    _cleanup_expired_sessions()
    session_id = secrets.token_hex(16)
    with get_admin_connection() as conn:
        session_spark, pg_password = provision_session(conn, session_id)
    session_registry.register(session_id, pg_password, session_spark)
    return {"session_id": session_id, "output_dir": str(output_dir(session_id))}


@router.post("/sessions/{session_id}/execute")
def execute_endpoint(session_id: str, body: ExecuteRequest) -> dict:
    record = session_registry.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    result = execute(record.spark_session, session_id, body.sql)
    return {
        "success": result.success,
        "columns": result.columns,
        "rows": result.rows,
        "truncated": result.truncated,
        "error_code": result.error_code,
        "error_message": result.error_message,
    }


@router.post("/sessions/{session_id}/grade")
def grade(session_id: str) -> dict:
    record = session_registry.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    report = grade_submission(record.spark_session, session_id)
    return {
        "passed": report.passed,
        "total_clean_rows": report.total_clean_rows,
        "structural_findings": [vars(f) for f in report.structural_findings],
        "fault_findings": [vars(f) for f in report.fault_findings],
        "fault_type_summary": report.fault_type_summary,
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
