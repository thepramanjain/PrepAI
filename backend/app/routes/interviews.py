"""
app/routes/interviews.py

API routes for Interview Management and the Text Interview Engine.
"""

from fastapi import APIRouter, Depends, status, Query
from typing import List

from app.schemas.interview import (
    InterviewCreate, InterviewUpdate, InterviewResponse, InterviewListResponse,
    StartInterviewResponse, CurrentQuestionResponse,
    SubmitAnswerRequest, SubmitAnswerResponse, NextQuestionResponse,
)
from app.schemas.question import QuestionCreate, QuestionResponse, QuestionListResponse
from app.schemas.response import ResponseCreate, ResponseResponse, ResponseListResponse
from app.auth.dependencies import get_current_user
from app.services import interview_service

router = APIRouter(prefix="/api/interviews", tags=["Interviews"])

# --- INTERVIEWS ---

@router.post(
    "",
    response_model=InterviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new interview"
)
def create_interview(data: InterviewCreate, current_user: dict = Depends(get_current_user)):
    doc = interview_service.create_interview(data, str(current_user["_id"]))
    return InterviewResponse(**doc)


@router.get(
    "",
    response_model=InterviewListResponse,
    summary="List current user's interviews"
)
def get_interviews(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user)
):
    result = interview_service.get_interviews(str(current_user["_id"]), page, limit)
    # Ensure items are parsed through the InterviewResponse schema
    result["items"] = [InterviewResponse(**item) for item in result["items"]]
    return result


@router.get(
    "/{interview_id}",
    response_model=InterviewResponse,
    summary="Get a specific interview"
)
def get_interview(interview_id: str, current_user: dict = Depends(get_current_user)):
    doc = interview_service.get_interview(interview_id, str(current_user["_id"]))
    return InterviewResponse(**doc)


@router.patch(
    "/{interview_id}",
    response_model=InterviewResponse,
    summary="Update an interview"
)
def update_interview(interview_id: str, data: InterviewUpdate, current_user: dict = Depends(get_current_user)):
    doc = interview_service.update_interview(interview_id, data, str(current_user["_id"]))
    return InterviewResponse(**doc)


@router.delete(
    "/{interview_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an interview"
)
def delete_interview(interview_id: str, current_user: dict = Depends(get_current_user)):
    interview_service.delete_interview(interview_id, str(current_user["_id"]))
    return


# --- LIFECYCLE (Phase 3 backward compat) ---

@router.post(
    "/{interview_id}/complete",
    response_model=InterviewResponse,
    summary="Complete an interview (manual)"
)
def complete_interview(interview_id: str, current_user: dict = Depends(get_current_user)):
    doc = interview_service.complete_interview_simple(interview_id, str(current_user["_id"]))
    return InterviewResponse(**doc)


# --- QUESTIONS ---

@router.post(
    "/{interview_id}/questions",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a question to an interview manually"
)
def add_question(interview_id: str, data: QuestionCreate, current_user: dict = Depends(get_current_user)):
    doc = interview_service.add_question(interview_id, data, str(current_user["_id"]))
    return QuestionResponse(**doc)


@router.get(
    "/{interview_id}/questions",
    response_model=QuestionListResponse,
    summary="List questions for an interview"
)
def get_questions(interview_id: str, current_user: dict = Depends(get_current_user)):
    items = interview_service.get_questions(interview_id, str(current_user["_id"]))
    return {"items": [QuestionResponse(**item) for item in items]}


@router.get(
    "/{interview_id}/questions/{question_id}",
    response_model=QuestionResponse,
    summary="Get a specific question"
)
def get_question(interview_id: str, question_id: str, current_user: dict = Depends(get_current_user)):
    doc = interview_service.get_question(interview_id, question_id, str(current_user["_id"]))
    return QuestionResponse(**doc)


@router.delete(
    "/{interview_id}/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a question"
)
def delete_question(interview_id: str, question_id: str, current_user: dict = Depends(get_current_user)):
    interview_service.delete_question(interview_id, question_id, str(current_user["_id"]))
    return


# --- RESPONSES (Phase 3 compat) ---

@router.get(
    "/{interview_id}/responses",
    response_model=ResponseListResponse,
    summary="List all responses for an interview"
)
def get_responses(interview_id: str, current_user: dict = Depends(get_current_user)):
    items = interview_service.get_responses(interview_id, str(current_user["_id"]))
    return {"items": [ResponseResponse(**item) for item in items]}


# ==========================================
# TEXT INTERVIEW ENGINE (Phase 6)
# ==========================================

@router.post(
    "/{interview_id}/start",
    response_model=StartInterviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Start an interview (engine)",
    tags=["Interview Engine"],
)
def engine_start_interview(interview_id: str, current_user: dict = Depends(get_current_user)):
    """Start the interview and receive the first question."""
    return interview_service.engine_start_interview(interview_id, str(current_user["_id"]))


@router.get(
    "/{interview_id}/current-question",
    response_model=CurrentQuestionResponse,
    summary="Get the current question",
    tags=["Interview Engine"],
)
def engine_get_current_question(interview_id: str, current_user: dict = Depends(get_current_user)):
    """Retrieve the current active question for an in-progress interview."""
    return interview_service.engine_get_current_question(interview_id, str(current_user["_id"]))


@router.post(
    "/{interview_id}/questions/{question_id}/response",
    response_model=SubmitAnswerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit an answer to the current question",
    tags=["Interview Engine"],
)
def engine_submit_answer(
    interview_id: str,
    question_id: str,
    data: SubmitAnswerRequest,
    current_user: dict = Depends(get_current_user),
):
    """Submit an answer to the current question. Must be the active question."""
    return interview_service.engine_submit_answer(
        interview_id=interview_id,
        question_id=question_id,
        answer=data.answer,
        user_id=str(current_user["_id"]),
        duration_seconds=data.duration_seconds,
    )


@router.post(
    "/{interview_id}/next",
    response_model=NextQuestionResponse,
    summary="Move to the next question",
    tags=["Interview Engine"],
)
def engine_next_question(interview_id: str, current_user: dict = Depends(get_current_user)):
    """
    Advance the interview to the next question.
    May generate an AI follow-up or move to the next primary question.
    If no questions remain, completes the interview.
    """
    return interview_service.engine_next_question(interview_id, str(current_user["_id"]))
