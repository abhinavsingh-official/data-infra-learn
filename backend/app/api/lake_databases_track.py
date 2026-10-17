from fastapi import APIRouter

from app.modules.lake_databases_track.skill_tree import LAKE_DATABASES_SKILL_TREE

router = APIRouter(prefix="/lake-databases-track", tags=["lake-databases-track"])


@router.get("/skill-tree")
def get_skill_tree() -> dict:
    return LAKE_DATABASES_SKILL_TREE
