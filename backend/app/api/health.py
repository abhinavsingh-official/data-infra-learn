from fastapi import APIRouter, Response
from psycopg import OperationalError

from app.core.db import get_connection

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health_check(response: Response) -> dict[str, str]:
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1")
    except OperationalError:
        response.status_code = 503
        return {"status": "error", "database": "unreachable"}
    return {"status": "ok", "database": "reachable"}
