import secrets

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.db import get_admin_connection, get_mongo_admin_client
from app.modules.nosql_phase import session_registry
from app.modules.nosql_phase.mongo_execution import execute_submission as execute_mongo_command
from app.modules.nosql_phase.report import grade_submission
from app.modules.nosql_phase.session_provisioning import (
    deprovision_mongo_session,
    deprovision_pg_readonly_session,
    mongo_db_name,
    pg_role_name,
    provision_mongo_session,
    provision_pg_readonly_session,
)
from app.modules.nosql_phase.task_content import NOSQL_PHASE_TASK
from app.modules.postgres_phase.sql_execution import execute_submission as execute_pg_sql

router = APIRouter(prefix="/nosql-phase", tags=["nosql-phase"])


class ExecuteRequest(BaseModel):
    command: dict


class QuerySourceRequest(BaseModel):
    sql: str


def _cleanup_expired_sessions() -> None:
    expired = session_registry.expired_session_ids()
    if not expired:
        return
    with get_admin_connection() as pg_conn, get_mongo_admin_client() as mongo_client:
        for session_id in expired:
            deprovision_pg_readonly_session(pg_conn, session_id)
            deprovision_mongo_session(mongo_client, session_id)
            session_registry.forget(session_id)


@router.get("/task")
def get_task() -> dict:
    return NOSQL_PHASE_TASK


@router.post("/sessions")
def create_session() -> dict:
    _cleanup_expired_sessions()
    session_id = secrets.token_hex(16)
    with get_admin_connection() as pg_conn:
        pg_password = provision_pg_readonly_session(pg_conn, session_id)
    with get_mongo_admin_client() as mongo_client:
        mongo_password = provision_mongo_session(mongo_client, session_id)
    session_registry.register(session_id, mongo_password=mongo_password, pg_password=pg_password)
    return {"session_id": session_id}


@router.post("/sessions/{session_id}/query-source")
def query_source(session_id: str, body: QuerySourceRequest) -> dict:
    record = session_registry.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    result = execute_pg_sql(pg_role_name(session_id), record.pg_password, body.sql)
    return {
        "success": result.success,
        "columns": result.columns,
        "rows": result.rows,
        "truncated": result.truncated,
        "error_code": result.error_code,
        "error_message": result.error_message,
    }


@router.post("/sessions/{session_id}/execute")
def execute(session_id: str, body: ExecuteRequest) -> dict:
    record = session_registry.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    result = execute_mongo_command(mongo_db_name(session_id), record.mongo_password, body.command)
    return {
        "success": result.success,
        "result": result.result,
        "truncated": result.truncated,
        "error_code": result.error_code,
        "error_message": result.error_message,
    }


@router.post("/sessions/{session_id}/grade")
def grade(session_id: str) -> dict:
    record = session_registry.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    with get_admin_connection() as pg_conn, get_mongo_admin_client() as mongo_client:
        report = grade_submission(pg_conn, mongo_client, session_id)
    return {
        "passed": report.passed,
        "total_profiles": report.total_profiles,
        "total_accounts": report.total_accounts,
        "findings": [vars(f) for f in report.findings],
    }


@router.delete("/sessions/{session_id}")
def end_session(session_id: str) -> dict:
    record = session_registry.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    with get_admin_connection() as pg_conn:
        deprovision_pg_readonly_session(pg_conn, session_id)
    with get_mongo_admin_client() as mongo_client:
        deprovision_mongo_session(mongo_client, session_id)
    session_registry.forget(session_id)
    return {"status": "deprovisioned"}
