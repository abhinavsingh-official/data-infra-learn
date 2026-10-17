from fastapi import APIRouter

from app.modules.lakehouse_databases_track.skill_tree import LAKEHOUSE_DATABASES_SKILL_TREE

router = APIRouter(prefix="/lakehouse-databases-track", tags=["lakehouse-databases-track"])


@router.get("/skill-tree")
def get_skill_tree() -> dict:
    return LAKEHOUSE_DATABASES_SKILL_TREE
