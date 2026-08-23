"""
app/tools/interview_tools.py

Interview-related tools for the agentic AI layer.

Wraps Phase 3 & Phase 6 interview service data.
Does NOT re-implement interview engine logic.
"""

from typing import Any
from bson import ObjectId
from pymongo import DESCENDING

from app.models.interview import interviews_collection
from app.models.question import questions_collection
from app.models.response import responses_collection


def _serialize_interview(doc: dict) -> dict:
    """Convert MongoDB interview document to a clean serializable dict."""
    return {
        "id": str(doc["_id"]),
        "title": doc.get("title", ""),
        "role": doc.get("role", ""),
        "experience_level": doc.get("experience_level", ""),
        "skills": doc.get("skills", []),
        "interview_type": doc.get("interview_type", ""),
        "difficulty": doc.get("difficulty", ""),
        "status": doc.get("status", ""),
        "question_count": doc.get("question_count", 0),
        "current_question_number": doc.get("current_question_number"),
        "created_at": str(doc.get("created_at", "")),
        "updated_at": str(doc.get("updated_at", "")),
        "started_at": str(doc.get("started_at", "")) if doc.get("started_at") else None,
        "completed_at": str(doc.get("completed_at", "")) if doc.get("completed_at") else None,
        "job_description": doc.get("job_description", ""),
    }


def get_interview_tool(user_id: str, interview_id: str) -> dict[str, Any]:
    """
    Get metadata for a specific interview.

    Args:
        user_id:      Authenticated user (injected by backend).
        interview_id: Target interview ID.

    Returns:
        Serialized interview document.
    """
    try:
        obj_id = ObjectId(interview_id)
    except Exception:
        raise ValueError("Invalid interview_id format.")

    doc = interviews_collection.find_one({"_id": obj_id})
    if not doc or str(doc.get("user_id")) != user_id:
        raise ValueError("Interview not found or access denied.")

    return _serialize_interview(doc)


def get_interview_state_tool(user_id: str, interview_id: str) -> dict[str, Any]:
    """
    Get the current session state of an interview.

    Returns progress, current question, and answered response count.

    Args:
        user_id:      Authenticated user (injected by backend).
        interview_id: Target interview ID.
    """
    try:
        obj_id = ObjectId(interview_id)
    except Exception:
        raise ValueError("Invalid interview_id format.")

    doc = interviews_collection.find_one({"_id": obj_id})
    if not doc or str(doc.get("user_id")) != user_id:
        raise ValueError("Interview not found or access denied.")

    total_questions = questions_collection.count_documents({"interview_id": obj_id})
    answered = responses_collection.count_documents({
        "interview_id": obj_id,
        "user_id": ObjectId(user_id),
    })

    current_q_id = doc.get("current_question_id")
    current_q = None
    if current_q_id:
        q_doc = questions_collection.find_one({"_id": current_q_id})
        if q_doc:
            current_q = {
                "id": str(q_doc["_id"]),
                "question_number": q_doc.get("question_number"),
                "question": q_doc.get("question"),
                "category": q_doc.get("category", "General"),
            }

    return {
        "interview_id": interview_id,
        "status": doc.get("status", ""),
        "total_questions": total_questions,
        "answered_questions": answered,
        "current_question_number": doc.get("current_question_number"),
        "current_question": current_q,
        "is_complete": doc.get("status") == "completed",
    }


def get_recent_interview_tool(user_id: str) -> dict[str, Any]:
    """
    Get the user's most recently created interview.

    Args:
        user_id: Authenticated user (injected by backend).

    Returns:
        Serialized interview document or a message if none exist.
    """
    try:
        user_obj_id = ObjectId(user_id)
    except Exception:
        raise ValueError("Invalid user_id format.")

    doc = (
        interviews_collection.find({"user_id": user_obj_id})
        .sort("created_at", DESCENDING)
        .limit(1)
    )
    doc = list(doc)

    if not doc:
        return {"message": "No interviews found for this user.", "interview": None}

    return {"interview": _serialize_interview(doc[0])}
