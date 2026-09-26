from fastapi import APIRouter

from app.modules.learn_page.content import build_learn_content

router = APIRouter(tags=["learn-page"])


@router.get("/learn-page")
def get_learn_page() -> dict:
    return build_learn_content()
