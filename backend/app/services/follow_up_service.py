"""
app/services/follow_up_service.py

Orchestrates follow-up question generation:
- Builds context from the interview
- Calls the follow-up generator
- Validates the response
- Saves the follow-up question to MongoDB
"""

from typing import Optional, Dict, Any
from bson import ObjectId

from app.ai.follow_up_generator import generate_follow_up, FollowUpDecision
from app.models.question import questions_collection
from app.models.resume import resumes_collection
from app.utils.helpers import utc_now


def _get_resume_text(interview: dict, user_id: str) -> str:
    """Safely fetch resume text if the interview has a linked resume."""
    resume_id = interview.get("resume_id")
    if not resume_id:
        return ""
    resume = resumes_collection.find_one({"_id": resume_id})
    if not resume or str(resume.get("user_id")) != user_id:
        return ""
    return (resume.get("extracted_text") or "")[:5000]


def has_follow_up_for_question(parent_question_id: ObjectId) -> bool:
    """Check if a follow-up already exists for the given primary question."""
    return questions_collection.count_documents({
        "parent_question_id": parent_question_id,
        "question_type": "follow_up",
    }) > 0


def generate_follow_up_if_needed(
    interview: dict,
    current_question: dict,
    candidate_answer: str,
    user_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Determines whether to generate a follow-up and, if so, creates and stores it.

    Returns the new follow-up question document if created, or None.
    """
    # Rule: Only primary questions get follow-ups
    if current_question.get("question_type", "primary") != "primary":
        return None

    # Rule: Max 1 follow-up per primary question
    if has_follow_up_for_question(current_question["_id"]):
        return None

    # Build context
    resume_text = _get_resume_text(interview, user_id)

    # Call Gemini — any exception gracefully falls back to no follow-up
    try:
        decision: Optional[FollowUpDecision] = generate_follow_up(
            role=interview.get("role", ""),
            experience_level=interview.get("experience_level", ""),
            skills=interview.get("skills", []),
            interview_type=interview.get("interview_type", ""),
            difficulty=interview.get("difficulty", ""),
            current_question=current_question.get("question", ""),
            candidate_answer=candidate_answer,
            job_description=(interview.get("job_description") or "")[:5000],
            resume_text=resume_text,
        )
    except Exception:
        # AI failure is non-fatal; the interview continues without a follow-up
        return None

    # If Gemini failed or decided no follow-up, return None
    if not decision or not decision.should_follow_up or not decision.question:
        return None

    # Determine question_number: place it right after the current question
    # We'll find the max question_number in this interview and add 1
    max_q = questions_collection.find_one(
        {"interview_id": interview["_id"]},
        sort=[("question_number", -1)],
    )
    next_number = (max_q["question_number"] + 1) if max_q else 1

    now = utc_now()
    follow_up_doc = {
        "interview_id": interview["_id"],
        "question_number": next_number,
        "question": decision.question,
        "category": decision.category or current_question.get("category", "General"),
        "difficulty": decision.difficulty or current_question.get("difficulty", "Medium"),
        "source": "gemini",
        "question_type": "follow_up",
        "parent_question_id": current_question["_id"],
        "created_at": now,
    }

    result = questions_collection.insert_one(follow_up_doc)
    follow_up_doc["_id"] = result.inserted_id

    return follow_up_doc
