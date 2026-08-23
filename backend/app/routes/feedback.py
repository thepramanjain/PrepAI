"""
app/routes/feedback.py

Phase 7 — AI Evaluation & Feedback API routes.

Endpoints:
  POST /api/interviews/{interview_id}/evaluate  — Trigger AI evaluation
  GET  /api/interviews/{interview_id}/feedback  — Retrieve stored feedback
"""

from fastapi import APIRouter, Depends, status

from app.schemas.feedback import FeedbackResponse
from app.auth.dependencies import get_current_user
from app.services import feedback_service

router = APIRouter(prefix="/api/interviews", tags=["Feedback"])


@router.post(
    "/{interview_id}/evaluate",
    response_model=FeedbackResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate a completed interview with AI",
)
def evaluate_interview(interview_id: str, current_user: dict = Depends(get_current_user)):
    """
    Trigger AI evaluation for a completed interview.

    - Interview must be in `completed` status.
    - Sends all questions and answers to Gemini for structured evaluation.
    - Returns overall score, category scores, per-question feedback, strengths,
      weaknesses, recommendations, topic analysis, and summary.
    - If called again, re-evaluates and replaces the existing feedback.
    """
    doc = feedback_service.create_or_update_feedback(
        interview_id=interview_id,
        user_id=str(current_user["_id"]),
    )
    return FeedbackResponse(**doc)


@router.get(
    "/{interview_id}/feedback",
    response_model=FeedbackResponse,
    summary="Retrieve AI feedback for an interview",
)
def get_feedback(interview_id: str, current_user: dict = Depends(get_current_user)):
    """
    Retrieve stored AI feedback for a completed interview.

    - Returns 404 if the interview has not been evaluated yet.
    - Users can only access their own interview feedback.
    """
    doc = feedback_service.get_feedback(
        interview_id=interview_id,
        user_id=str(current_user["_id"]),
    )
    return FeedbackResponse(**doc)
