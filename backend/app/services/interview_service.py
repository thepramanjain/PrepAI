"""
app/services/interview_service.py

Business logic for Interview Management and the Text Interview Engine.
"""

from fastapi import HTTPException, status
from bson import ObjectId
from typing import List, Dict, Any, Optional
from pymongo.errors import DuplicateKeyError

from app.models.interview import interviews_collection
from app.models.question import questions_collection
from app.models.response import responses_collection
from app.schemas.interview import InterviewCreate, InterviewUpdate, Status
from app.schemas.question import QuestionCreate
from app.schemas.response import ResponseCreate
from app.services import follow_up_service
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
    
    if not interview or str(interview["user_id"]) != user_id_str:
        # Prevent information leakage
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
        
    return interview


def _question_to_engine_dict(q: dict) -> dict:
    """Convert a MongoDB question document into a clean engine response dict."""
    return {
        "id": str(q["_id"]),
        "question_number": q["question_number"],
        "question": q["question"],
        "category": q.get("category", "General"),
        "difficulty": q.get("difficulty", "Medium"),
        "question_type": q.get("question_type", "primary"),
    }


# ==========================================
# INTERVIEW CRUD (Phase 3 — unchanged)
# ==========================================

def create_interview(data: InterviewCreate, user_id: str) -> Dict[str, Any]:
    doc = data.model_dump()
    doc["user_id"] = ObjectId(user_id)
    if doc.get("resume_id"):
        try:
            doc["resume_id"] = ObjectId(doc["resume_id"])
        except Exception:
            doc["resume_id"] = None
    else:
        doc["resume_id"] = None
    doc["status"] = Status.draft
    doc["question_count"] = 0
    now = utc_now()
    doc["created_at"] = now
    doc["updated_at"] = now
    doc["started_at"] = None
    doc["completed_at"] = None
    doc["current_question_id"] = None
    doc["current_question_number"] = None
    
    result = interviews_collection.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


def get_interviews(user_id: str, page: int = 1, limit: int = 10) -> Dict[str, Any]:
    skip = (page - 1) * limit
    cursor = interviews_collection.find({"user_id": ObjectId(user_id)}).sort("created_at", -1).skip(skip).limit(limit)
    items = list(cursor)
    total = interviews_collection.count_documents({"user_id": ObjectId(user_id)})
    
    return {
        "items": items,
        "page": page,
        "limit": limit,
        "total": total
    }


def get_interview(interview_id: str, user_id: str) -> Dict[str, Any]:
    return _get_interview_and_verify_ownership(interview_id, user_id)


def update_interview(interview_id: str, data: InterviewUpdate, user_id: str) -> Dict[str, Any]:
    interview = _get_interview_and_verify_ownership(interview_id, user_id)
    
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        return interview
        
    update_data["updated_at"] = utc_now()
    
    interviews_collection.update_one(
        {"_id": interview["_id"]},
        {"$set": update_data}
    )
    
    return interviews_collection.find_one({"_id": interview["_id"]})


def delete_interview(interview_id: str, user_id: str):
    interview = _get_interview_and_verify_ownership(interview_id, user_id)
    obj_id = interview["_id"]
    
    # Delete questions and responses associated with the interview
    questions_collection.delete_many({"interview_id": obj_id})
    responses_collection.delete_many({"interview_id": obj_id})
    
    # Delete the interview itself
    interviews_collection.delete_one({"_id": obj_id})


# ==========================================
# QUESTION CRUD (Phase 3 — unchanged)
# ==========================================

def add_question(interview_id: str, data: QuestionCreate, user_id: str) -> Dict[str, Any]:
    interview = _get_interview_and_verify_ownership(interview_id, user_id)
    obj_id = interview["_id"]
    
    # Get current question count to determine the new number
    current_count = interview.get("question_count", 0)
    new_number = current_count + 1
    
    doc = data.model_dump()
    doc["interview_id"] = obj_id
    doc["question_number"] = new_number
    doc["source"] = "manual"
    doc["question_type"] = "primary"
    doc["parent_question_id"] = None
    doc["created_at"] = utc_now()
    
    result = questions_collection.insert_one(doc)
    doc["_id"] = result.inserted_id
    
    # Update interview's question count
    interviews_collection.update_one(
        {"_id": obj_id},
        {
            "$inc": {"question_count": 1},
            "$set": {"updated_at": utc_now()}
        }
    )
    
    return doc


def get_questions(interview_id: str, user_id: str) -> List[Dict[str, Any]]:
    interview = _get_interview_and_verify_ownership(interview_id, user_id)
    cursor = questions_collection.find({"interview_id": interview["_id"]}).sort("question_number", 1)
    return list(cursor)


def get_question(interview_id: str, question_id: str, user_id: str) -> Dict[str, Any]:
    interview = _get_interview_and_verify_ownership(interview_id, user_id)
    q_obj_id = _verify_object_id(question_id)
    
    question = questions_collection.find_one({
        "_id": q_obj_id,
        "interview_id": interview["_id"]
    })
    
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        
    return question


def delete_question(interview_id: str, question_id: str, user_id: str):
    interview = _get_interview_and_verify_ownership(interview_id, user_id)
    q_obj_id = _verify_object_id(question_id)
    
    result = questions_collection.delete_one({
        "_id": q_obj_id,
        "interview_id": interview["_id"]
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        
    interviews_collection.update_one(
        {"_id": interview["_id"]},
        {
            "$inc": {"question_count": -1},
            "$set": {"updated_at": utc_now()}
        }
    )


# ==========================================
# RESPONSE CRUD (Phase 3 — unchanged)
# ==========================================

def submit_response(interview_id: str, question_id: str, data: ResponseCreate, user_id: str) -> Dict[str, Any]:
    interview = _get_interview_and_verify_ownership(interview_id, user_id)
    q_obj_id = _verify_object_id(question_id)
    
    question = questions_collection.find_one({
        "_id": q_obj_id,
        "interview_id": interview["_id"]
    })
    
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        
    doc = data.model_dump()
    doc["interview_id"] = interview["_id"]
    doc["question_id"] = q_obj_id
    doc["user_id"] = ObjectId(user_id)
    doc["answered_at"] = utc_now()
    
    result = responses_collection.insert_one(doc)
    doc["_id"] = result.inserted_id
    
    return doc


def get_responses(interview_id: str, user_id: str) -> List[Dict[str, Any]]:
    interview = _get_interview_and_verify_ownership(interview_id, user_id)
    cursor = responses_collection.find({"interview_id": interview["_id"]}).sort("answered_at", 1)
    return list(cursor)


# ==========================================
# LIFECYCLE (Phase 3 — kept for backward compat)
# ==========================================

def complete_interview_simple(interview_id: str, user_id: str) -> Dict[str, Any]:
    """Phase 3 backward-compatible complete endpoint."""
    interview = _get_interview_and_verify_ownership(interview_id, user_id)
    
    if interview["status"] != Status.in_progress:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot complete interview in {interview['status']} status"
        )
        
    now = utc_now()
    interviews_collection.update_one(
        {"_id": interview["_id"]},
        {"$set": {
            "status": Status.completed,
            "completed_at": now,
            "updated_at": now,
            "current_question_id": None,
            "current_question_number": None,
        }}
    )
    
    return interviews_collection.find_one({"_id": interview["_id"]})


# ==========================================
# TEXT INTERVIEW ENGINE (Phase 6)
# ==========================================

def engine_start_interview(interview_id: str, user_id: str) -> dict:
    """
    Start an interview:
    - Must be in 'draft' status.
    - Must have at least one question.
    - Sets status to 'in_progress', assigns first question.
    """
    interview = _get_interview_and_verify_ownership(interview_id, user_id)

    if interview["status"] != Status.draft:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot start interview in '{interview['status']}' status"
        )

    # Check that questions exist
    first_question = questions_collection.find_one(
        {"interview_id": interview["_id"]},
        sort=[("question_number", 1)],
    )

    if not first_question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview has no questions."
        )

    now = utc_now()
    interviews_collection.update_one(
        {"_id": interview["_id"]},
        {"$set": {
            "status": Status.in_progress,
            "started_at": now,
            "updated_at": now,
            "current_question_id": first_question["_id"],
            "current_question_number": first_question["question_number"],
        }}
    )

    return {
        "interview_id": str(interview["_id"]),
        "status": "in_progress",
        "current_question": _question_to_engine_dict(first_question),
    }


def engine_get_current_question(interview_id: str, user_id: str) -> dict:
    """Retrieve the current question for an in-progress interview."""
    interview = _get_interview_and_verify_ownership(interview_id, user_id)

    if interview["status"] != Status.in_progress:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Interview is not in progress (status: '{interview['status']}')"
        )

    current_q_id = interview.get("current_question_id")
    if not current_q_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No current question set for this interview."
        )

    question = questions_collection.find_one({"_id": current_q_id})
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Current question not found in database."
        )

    return {
        "interview_id": str(interview["_id"]),
        "question": _question_to_engine_dict(question),
    }


def engine_submit_answer(interview_id: str, question_id: str, answer: str, user_id: str, duration_seconds: Optional[int] = None) -> dict:
    """
    Submit an answer to the current question.
    Validates ownership, interview status, question correctness, and duplicate prevention.
    """
    interview = _get_interview_and_verify_ownership(interview_id, user_id)

    # Must be in_progress
    if interview["status"] != Status.in_progress:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot submit answers when interview is '{interview['status']}'"
        )

    q_obj_id = _verify_object_id(question_id)

    # Question must belong to this interview
    question = questions_collection.find_one({
        "_id": q_obj_id,
        "interview_id": interview["_id"],
    })
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found in this interview."
        )

    # Must be the current question
    current_q_id = interview.get("current_question_id")
    if not current_q_id or q_obj_id != current_q_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This is not the current question. Answer the current question first."
        )

    # Duplicate check
    existing = responses_collection.find_one({
        "interview_id": interview["_id"],
        "question_id": q_obj_id,
        "user_id": ObjectId(user_id),
    })
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already submitted a response for this question."
        )

    # Store response
    now = utc_now()
    doc = {
        "interview_id": interview["_id"],
        "question_id": q_obj_id,
        "user_id": ObjectId(user_id),
        "answer": answer,
        "answered_at": now,
        "duration_seconds": duration_seconds,
    }

    try:
        result = responses_collection.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already submitted a response for this question."
        )

    doc["_id"] = result.inserted_id

    return {
        "id": str(doc["_id"]),
        "interview_id": str(doc["interview_id"]),
        "question_id": str(doc["question_id"]),
        "answer": doc["answer"],
        "answered_at": doc["answered_at"],
        "duration_seconds": doc["duration_seconds"],
    }


def engine_next_question(interview_id: str, user_id: str) -> dict:
    """
    Advance to the next question after the current one has been answered.

    Logic:
    1. Verify current question has been answered.
    2. If current question is primary and has no follow-up yet → try generating one via Gemini.
    3. If a follow-up was generated → set it as current and return it.
    4. Otherwise → find the next primary question (by question_number) that hasn't been answered yet.
    5. If no questions remain → complete the interview.
    """
    interview = _get_interview_and_verify_ownership(interview_id, user_id)

    if interview["status"] != Status.in_progress:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Interview is not in progress (status: '{interview['status']}')"
        )

    current_q_id = interview.get("current_question_id")
    if not current_q_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No current question is set."
        )

    current_question = questions_collection.find_one({"_id": current_q_id})
    if not current_question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Current question not found."
        )

    # Ensure the current question has been answered
    answer_doc = responses_collection.find_one({
        "interview_id": interview["_id"],
        "question_id": current_q_id,
        "user_id": ObjectId(user_id),
    })
    if not answer_doc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must answer the current question before moving to the next."
        )

    # --- Follow-up logic ---
    # Only try follow-up if the current question is primary
    if current_question.get("question_type", "primary") == "primary":
        follow_up_doc = follow_up_service.generate_follow_up_if_needed(
            interview=interview,
            current_question=current_question,
            candidate_answer=answer_doc["answer"],
            user_id=user_id,
        )

        if follow_up_doc:
            # Set follow-up as the current question
            now = utc_now()
            interviews_collection.update_one(
                {"_id": interview["_id"]},
                {"$set": {
                    "current_question_id": follow_up_doc["_id"],
                    "current_question_number": follow_up_doc["question_number"],
                    "updated_at": now,
                }}
            )
            return {
                "interview_id": str(interview["_id"]),
                "status": "in_progress",
                "question": _question_to_engine_dict(follow_up_doc),
                "message": None,
            }

    # --- Next primary question logic ---
    # Get all questions for this interview that haven't been answered yet
    answered_q_ids = set()
    for resp in responses_collection.find({"interview_id": interview["_id"], "user_id": ObjectId(user_id)}):
        answered_q_ids.add(resp["question_id"])

    # Find the next unanswered question sorted by question_number
    all_questions = list(
        questions_collection.find({"interview_id": interview["_id"]}).sort("question_number", 1)
    )

    next_question = None
    for q in all_questions:
        if q["_id"] not in answered_q_ids:
            next_question = q
            break

    if next_question:
        now = utc_now()
        interviews_collection.update_one(
            {"_id": interview["_id"]},
            {"$set": {
                "current_question_id": next_question["_id"],
                "current_question_number": next_question["question_number"],
                "updated_at": now,
            }}
        )
        return {
            "interview_id": str(interview["_id"]),
            "status": "in_progress",
            "question": _question_to_engine_dict(next_question),
            "message": None,
        }

    # --- No more questions → complete the interview ---
    now = utc_now()
    interviews_collection.update_one(
        {"_id": interview["_id"]},
        {"$set": {
            "status": Status.completed,
            "completed_at": now,
            "updated_at": now,
            "current_question_id": None,
            "current_question_number": None,
        }}
    )

    return {
        "interview_id": str(interview["_id"]),
        "status": "completed",
        "question": None,
        "message": "Interview completed successfully",
    }
