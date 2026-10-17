from fastapi import APIRouter

from app.modules.interview_questions.content import TOPICS

router = APIRouter(tags=["interview-questions"])


@router.get("/interview-questions")
def get_interview_questions() -> dict:
    return {"topics": TOPICS}
