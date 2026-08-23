"""
app/routes/ai.py

API routes for AI integration.
"""

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.services import ai_question_service

router = APIRouter(prefix="/api/ai", tags=["AI Integration"])

class GenerateQuestionsRequest(BaseModel):
    question_count: int = Field(10, ge=1, le=20)


@router.post(
    "/interviews/{interview_id}/generate-questions",
    status_code=status.HTTP_201_CREATED,
    summary="Generate AI interview questions"
)
def generate_questions(
    interview_id: str,
    request: GenerateQuestionsRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate interview questions using Google Gemini based on the interview's configured
    role, skills, experience level, job description, and linked resume.
    """
    return ai_question_service.generate_questions(
        interview_id=interview_id,
        user_id=str(current_user["_id"]),
        question_count=request.question_count
    )
