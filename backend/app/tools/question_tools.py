"""
app/tools/question_tools.py

Question-related tools for the agentic AI layer.

Delegates all question generation to the existing Phase 5 Gemini service.
Does NOT duplicate or replace Gemini question generation logic.
"""

from typing import Any
from bson import ObjectId
from fastapi import HTTPException

from app.models.question import questions_collection
from app.models.interview import interviews_collection
from app.services.ai_question_service import generate_questions as gemini_generate_questions


def generate_questions_tool(
    user_id: str,
    interview_id: str,
    question_count: int = 10,
) -> dict[str, Any]:
    """
    Generate AI questions for an interview.

    Flow:
        Agent requests tool → this function → Phase 5 Gemini service → MongoDB → result

    Args:
        user_id:        Authenticated user (injected by backend, never from LLM).
        interview_id:   Target interview ID.
        question_count: Number of questions (1–20).

    Returns:
        dict with interview_id, count, and generated questions list.
    """
    try:
        return gemini_generate_questions(
            interview_id=interview_id,
            user_id=user_id,
            question_count=question_count,
        )
    except HTTPException as e:
        raise ValueError(f"Question generation failed: {e.detail}") from e


def get_questions_tool(user_id: str, interview_id: str) -> dict[str, Any]:
    """
    Retrieve existing questions for an interview.

    Ownership is verified by confirming the interview belongs to the user.

    Args:
        user_id:      Authenticated user (injected by backend).
        interview_id: Target interview ID.

    Returns:
        dict with interview_id, count, and questions list.
    """
    try:
        interview_obj_id = ObjectId(interview_id)
    except Exception:
        raise ValueError("Invalid interview_id format.")

    # Ownership check
    interview = interviews_collection.find_one({"_id": interview_obj_id})
    if not interview or str(interview.get("user_id")) != user_id:
        raise ValueError("Interview not found or access denied.")

    questions = list(
        questions_collection.find({"interview_id": interview_obj_id}).sort("question_number", 1)
    )

    result = []
    for q in questions:
        result.append({
            "id": str(q["_id"]),
            "question_number": q.get("question_number"),
            "question": q.get("question"),
            "category": q.get("category", "General"),
            "difficulty": q.get("difficulty", "Medium"),
            "source": q.get("source", "manual"),
        })

    return {
        "interview_id": interview_id,
        "count": len(result),
        "questions": result,
    }
