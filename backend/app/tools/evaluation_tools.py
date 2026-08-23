"""
app/tools/evaluation_tools.py

Evaluation-related tools for the agentic AI layer.

Delegates evaluation to the existing Phase 7 Gemini evaluator.
Does NOT move evaluation logic to GPT-4o.

Flow:
    Agent requests evaluate_interview
        ↓
    evaluate_interview_tool()
        ↓
    Phase 7 feedback_service.create_or_update_feedback()
        ↓
    Gemini evaluator
        ↓
    MongoDB feedback document
        ↓
    Serialized result back to GPT-4o
"""

from typing import Any
from bson import ObjectId
from fastapi import HTTPException

from app.services.feedback_service import (
    create_or_update_feedback,
    get_feedback as service_get_feedback,
)


def _serialize_feedback(doc: dict) -> dict:
    """Convert MongoDB feedback document to a clean serializable dict."""
    cat = doc.get("category_scores", {})
    return {
        "interview_id": str(doc.get("interview_id", "")),
        "overall_score": doc.get("overall_score"),
        "category_scores": {
            "technical": cat.get("technical"),
            "communication": cat.get("communication"),
            "problem_solving": cat.get("problem_solving"),
            "relevance": cat.get("relevance"),
        },
        "strengths": doc.get("strengths", []),
        "weaknesses": doc.get("weaknesses", []),
        "recommendations": doc.get("recommendations", []),
        "summary": doc.get("summary", ""),
        # Limit topic_analysis to avoid sending excessive tokens to GPT-4o
        "topic_analysis": doc.get("topic_analysis", [])[:10],
    }


def evaluate_interview_tool(user_id: str, interview_id: str) -> dict[str, Any]:
    """
    Trigger or re-trigger AI evaluation for a completed interview.

    Uses the Phase 7 Gemini evaluator — GPT-4o does NOT perform evaluation.

    Args:
        user_id:      Authenticated user (injected by backend).
        interview_id: Target completed interview ID.

    Returns:
        Serialized feedback document.
    """
    try:
        feedback_doc = create_or_update_feedback(
            interview_id=interview_id,
            user_id=user_id,
        )
    except HTTPException as e:
        raise ValueError(f"Evaluation failed: {e.detail}") from e

    return _serialize_feedback(feedback_doc)


def get_feedback_tool(user_id: str, interview_id: str) -> dict[str, Any]:
    """
    Retrieve stored evaluation feedback for an interview.

    Args:
        user_id:      Authenticated user (injected by backend).
        interview_id: Target interview ID.

    Returns:
        Serialized feedback document.
    """
    try:
        feedback_doc = service_get_feedback(
            interview_id=interview_id,
            user_id=user_id,
        )
    except HTTPException as e:
        raise ValueError(f"Feedback retrieval failed: {e.detail}") from e

    return _serialize_feedback(feedback_doc)
