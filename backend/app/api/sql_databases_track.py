from fastapi import APIRouter

from app.modules.sql_databases_track.skill_tree import SQL_DATABASES_SKILL_TREE

router = APIRouter(prefix="/sql-databases-track", tags=["sql-databases-track"])


@router.get("/skill-tree")
def get_skill_tree() -> dict:
    return SQL_DATABASES_SKILL_TREE
