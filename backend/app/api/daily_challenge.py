"""Module 21: Daily Challenge - one SQL problem + one Python problem
picked fresh per day. Mounted at /progress/daily so the frontend's
existing generic /api/progress/* proxy route (Module 17, forwards the
Auth.js session-token cookie as the X-Session-Token header) already
covers it with zero new frontend plumbing."""

from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.core.db import get_connection
from app.core.session_auth import resolve_user
from app.modules.daily_challenge import store
from app.modules.daily_challenge.content import PYTHON_CHALLENGE_POOL, SQL_CHALLENGE_POOL
from app.modules.daily_challenge.python_execution import run_python_submission
from app.modules.daily_challenge.selection import pick_python_problem, pick_sql_problem, tier_for_completions
from app.modules.progress.node_practice import check_practice_submission

router = APIRouter(prefix="/progress/daily", tags=["daily-challenge"])


class SqlCheckRequest(BaseModel):
    sql: str


class PythonCheckRequest(BaseModel):
    code: str


def _require_user_id(x_session_token: str | None) -> int:
    user = resolve_user(x_session_token)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in required")
    return user.id


def _today():
    return datetime.now(timezone.utc).date()


@router.get("/today")
def get_today(x_session_token: str | None = Header(default=None)) -> dict:
    user_id = _require_user_id(x_session_token)
    today = _today()

    with get_connection() as conn:
        sql_tier = tier_for_completions(store.completed_count(conn, user_id, store.SQL_PARADIGM))
        python_tier = tier_for_completions(store.completed_count(conn, user_id, store.PYTHON_PARADIGM))
        sql_problem = pick_sql_problem(SQL_CHALLENGE_POOL, sql_tier, today)
        python_problem = pick_python_problem(PYTHON_CHALLENGE_POOL, python_tier, today)
        sql_done = store.already_completed_today(conn, user_id, store.SQL_PARADIGM, sql_problem["id"], today)
        python_done = store.already_completed_today(conn, user_id, store.PYTHON_PARADIGM, python_problem["id"], today)

    return {
        "date": today.isoformat(),
        "sql": {
            "id": sql_problem["id"],
            "difficulty": sql_problem["difficulty"],
            "prompt": sql_problem["prompt"],
            "table_name": sql_problem.get("table_name"),
            "tables": sql_problem.get("tables"),
            "example_rows": sql_problem.get("example_rows"),
            "starter_sql": sql_problem.get("starter_sql"),
            "completed_today": sql_done,
        },
        "python": {
            "id": python_problem["id"],
            "difficulty": python_problem["difficulty"],
            "prompt": python_problem["prompt"],
            "function_name": python_problem["function_name"],
            "starter_code": python_problem["starter_code"],
            "completed_today": python_done,
        },
    }


@router.post("/sql/check")
def check_sql(body: SqlCheckRequest, x_session_token: str | None = Header(default=None)) -> dict:
    user_id = _require_user_id(x_session_token)
    today = _today()
    problem = pick_sql_problem(
        SQL_CHALLENGE_POOL,
        tier_for_completions(_completed_count(user_id, store.SQL_PARADIGM)),
        today,
    )

    result = check_practice_submission(problem, body.sql)
    if result["passed"]:
        with get_connection() as conn:
            result["progress"] = store.record_daily_completion(conn, user_id, store.SQL_PARADIGM, problem["id"], today)
    return result


@router.post("/python/check")
def check_python(body: PythonCheckRequest, x_session_token: str | None = Header(default=None)) -> dict:
    user_id = _require_user_id(x_session_token)
    today = _today()
    problem = pick_python_problem(
        PYTHON_CHALLENGE_POOL,
        tier_for_completions(_completed_count(user_id, store.PYTHON_PARADIGM)),
        today,
    )

    result = run_python_submission(body.code, problem["function_name"], problem["test_cases"])
    if result["passed"]:
        with get_connection() as conn:
            result["progress"] = store.record_daily_completion(
                conn, user_id, store.PYTHON_PARADIGM, problem["id"], today
            )
    return result


def _completed_count(user_id: int, paradigm: str) -> int:
    with get_connection() as conn:
        return store.completed_count(conn, user_id, paradigm)
