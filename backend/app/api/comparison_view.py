from fastapi import APIRouter

from app.core.db import get_admin_connection
from app.modules.comparison_view.content import COMPARISON

router = APIRouter(prefix="/comparison-view", tags=["comparison-view"])


@router.get("/duplicate-delivery")
def get_comparison() -> dict:
    with get_admin_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM injected_fault_log WHERE fault_type = 'duplicate_delivery'")
            real_duplicate_count = cur.fetchone()[0]
    return {**COMPARISON, "real_duplicate_count": real_duplicate_count}
