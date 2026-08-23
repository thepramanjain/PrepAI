"""
app/services/feedback_service.py

Phase 7 — Business logic for AI Interview Evaluation.

Responsibilities:
- Retrieve and validate the completed interview.
- Fetch all questions and user responses.
- Optionally fetch resume text.
- Delegate to the AI evaluator.
- Validate question IDs in the Gemini output.
- Upsert feedback into MongoDB (one document per interview).
- Retrieve existing feedback with ownership check.
"""

from fastapi import HTTPException, status
from bson import ObjectId
from typing import Dict, Any, Optional

from app.models.interview import interviews_collection
from app.models.question import questions_collection
from app.models.response import responses_collection
from app.models.feedback import feedback_collection
from app.models.resume import resumes_collection
from app.schemas.interview import Status
from app.schemas.feedback import GeneratedEvaluation
from app.ai import evaluator as ai_evaluator
from app.utils.helpers import utc_now


def _verify_object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found (invalid ID format)"
        )


def _get_interview_and_verify_ownership(interview_id_str: str, user_id_str: str) -> Dict[str, Any]:
    obj_id = _verify_object_id(interview_id_str)
    interview = interviews_collection.find_one({"_id": obj_id})
    if not interview or str(interview.get("user_id")) != user_id_str:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    return interview


def _get_resume_text(interview: Dict[str, Any], user_id: str) -> Optional[str]:
    """Safely fetch resume text if the interview has a linked resume."""
    resume_id = interview.get("resume_id")
    if not resume_id:
        return None
    resume = resumes_collection.find_one({"_id": resume_id})
    if not resume or str(resume.get("user_id")) != user_id:
        return None
    return (resume.get("extracted_text") or "").strip() or None


def create_or_update_feedback(interview_id: str, user_id: str) -> Dict[str, Any]:
    """
    Trigger AI evaluation for a completed interview.
    If feedback already exists for this interview, it is replaced (upsert).

    Raises:
        HTTPException 400: Interview is not completed.
        HTTPException 400: Interview has no questions or no responses.
        HTTPException 503: AI Service unavailable.
        HTTPException 422: AI returned invalid or unvalidatable output.
    """
    # 1. Retrieve and verify interview
    interview = _get_interview_and_verify_ownership(interview_id, user_id)

    if interview.get("status") != Status.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview must be completed before evaluation."
        )

    interview_obj_id = interview["_id"]
    user_obj_id = ObjectId(user_id)

    # 2. Fetch questions
    questions = list(
        questions_collection.find({"interview_id": interview_obj_id}).sort("question_number", 1)
    )
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview has no questions to evaluate."
        )

    # 3. Fetch responses
    responses = list(responses_collection.find({
        "interview_id": interview_obj_id,
        "user_id": user_obj_id,
    }))
    if not responses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview has no submitted responses to evaluate."
        )

    # 4. Optionally fetch resume text
    resume_text = _get_resume_text(interview, user_id)

    # 5. Call Gemini evaluator
    try:
        evaluation: GeneratedEvaluation = ai_evaluator.evaluate_interview(
            interview=interview,
            questions=questions,
            responses=responses,
            resume_text=resume_text,
        )
    except RuntimeError as e:
        error_msg = str(e)
        if "rate limit" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=error_msg)
        if "not configured" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=error_msg)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)

    # 6. Validate question IDs from Gemini against actual interview questions
    valid_q_ids = {str(q["_id"]) for q in questions}
    for q_eval in evaluation.question_evaluations:
        if q_eval.question_id not in valid_q_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"AI returned an unknown question_id: {q_eval.question_id}"
            )

    # 7. Build the document to store
    now = utc_now()

    # Serialize question_evaluations to plain dicts for MongoDB
    q_evals_docs = [qe.model_dump() for qe in evaluation.question_evaluations]
    category_scores_doc = evaluation.category_scores.model_dump()
    topic_analysis_docs = [ta.model_dump() for ta in evaluation.topic_analysis]

    # 8. Upsert — replace any existing feedback for this interview
    feedback_doc = {
        "interview_id": interview_obj_id,
        "user_id": user_obj_id,
        "overall_score": evaluation.overall_score,
        "category_scores": category_scores_doc,
        "question_evaluations": q_evals_docs,
        "strengths": evaluation.strengths,
        "weaknesses": evaluation.weaknesses,
        "recommendations": evaluation.recommendations,
        "topic_analysis": topic_analysis_docs,
        "summary": evaluation.summary,
        "updated_at": now,
    }

    existing = feedback_collection.find_one({"interview_id": interview_obj_id})
    if existing:
        feedback_collection.update_one(
            {"interview_id": interview_obj_id},
            {"$set": feedback_doc}
        )
        stored = feedback_collection.find_one({"interview_id": interview_obj_id})
    else:
        feedback_doc["created_at"] = now
        result = feedback_collection.insert_one(feedback_doc)
        stored = feedback_collection.find_one({"_id": result.inserted_id})

    return stored


def get_feedback(interview_id: str, user_id: str) -> Dict[str, Any]:
    """
    Retrieve stored feedback for a completed interview.

    Raises:
        HTTPException 404: Interview not found or doesn't belong to user.
        HTTPException 404: Feedback not yet generated.
    """
    # Verify interview ownership first (prevents data leakage)
    interview = _get_interview_and_verify_ownership(interview_id, user_id)

    feedback = feedback_collection.find_one({"interview_id": interview["_id"]})
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found. Please evaluate the interview first."
        )

    return feedback
