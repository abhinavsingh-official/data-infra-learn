from fastapi import APIRouter

from app.modules.warehouse_databases_track.skill_tree import WAREHOUSE_DATABASES_SKILL_TREE

router = APIRouter(prefix="/warehouse-databases-track", tags=["warehouse-databases-track"])


@router.get("/skill-tree")
def get_skill_tree() -> dict:
    return WAREHOUSE_DATABASES_SKILL_TREE
