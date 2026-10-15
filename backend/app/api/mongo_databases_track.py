from fastapi import APIRouter

from app.modules.mongo_databases_track.skill_tree import MONGO_DATABASES_SKILL_TREE

router = APIRouter(prefix="/mongo-databases-track", tags=["mongo-databases-track"])


@router.get("/skill-tree")
def get_skill_tree() -> dict:
    return MONGO_DATABASES_SKILL_TREE
