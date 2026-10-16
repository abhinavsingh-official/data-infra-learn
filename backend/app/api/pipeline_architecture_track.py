from fastapi import APIRouter

from app.modules.pipeline_architecture_track.skill_tree import PIPELINE_ARCHITECTURE_SKILL_TREE

router = APIRouter(prefix="/pipeline-architecture-track", tags=["pipeline-architecture-track"])


@router.get("/skill-tree")
def get_skill_tree() -> dict:
    return PIPELINE_ARCHITECTURE_SKILL_TREE
