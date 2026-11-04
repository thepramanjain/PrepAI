"""
app/services/ai_question_service.py

Business logic for AI Question Generation.
Supports primary Google Gemini model with bounded exponential retries
(handling 503 UNAVAILABLE, 429 RESOURCE_EXHAUSTED, 504 DEADLINE_EXCEEDED)
and automatic fallback to OpenRouter (GPT-4o / GPT-4o-mini).
"""

import json
import logging
import re
import time
from typing import List

from bson import ObjectId
from fastapi import HTTPException, status
from google.genai import types

from app.ai.gemini_client import gemini_wrapper
from app.ai.prompts import INTERVIEW_QUESTION_SYSTEM_PROMPT
from app.models.interview import interviews_collection
from app.models.question import questions_collection
from app.models.resume import resumes_collection
from app.schemas.ai_question import GeneratedQuestion, GeneratedQuestionList
from app.schemas.interview import Difficulty
from app.utils.helpers import utc_now

logger = logging.getLogger(__name__)

# Bounded retries configuration for Gemini transient errors
MAX_GEMINI_RETRIES = 3
INITIAL_BACKOFF = 0.5  # seconds (exponential: 0.5s, 1.0s)


def _get_openrouter_client():
    """
    Dynamically retrieve the OpenRouter client singleton.
    Preserves static module isolation while enabling seamless fallback.
    """
    try:
        import importlib
        mod = importlib.import_module("app.ai.openrouter_client")
        return getattr(mod, "openrouter_client", None)
    except Exception:
        return None


def _verify_object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid ID format",
        )


def _get_interview_and_verify_ownership(interview_id_str: str, user_id_str: str):
    obj_id = _verify_object_id(interview_id_str)
    interview = interviews_collection.find_one({"_id": obj_id})

    if not interview or str(interview.get("user_id")) != user_id_str:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found",
        )

    return interview


def _is_gemini_retryable_error(exc: Exception) -> bool:
    """
    Return True if the exception represents a transient failure
    (503 UNAVAILABLE, 429 RESOURCE_EXHAUSTED, 504 DEADLINE_EXCEEDED, network/timeout errors).
    """
    code = getattr(exc, "code", None)
    if code in {429, 500, 502, 503, 504}:
        return True

    msg = str(exc).lower()
    retryable_patterns = [
        "503", "429", "504", "502", "500",
        "unavailable", "high demand", "resource_exhausted",
        "deadline_exceeded", "quota", "rate limit",
        "timed out", "timeout", "connecterror", "remoteprotocolerror",
        "connection reset", "broken pipe", "overloaded",
    ]
    return any(pattern in msg for pattern in retryable_patterns)


def _parse_and_validate_questions(raw_text: str) -> List[GeneratedQuestion]:
    """
    Parse and validate raw JSON text from Gemini or OpenRouter into
    a list of GeneratedQuestion objects matching the system schema.
    Returns empty list if invalid or empty.
    """
    if not raw_text or not raw_text.strip():
        return []

    cleaned = raw_text.strip()
    # Strip markdown code blocks if present (```json ... ``` or ``` ... ```)
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except Exception:
        return []

    if isinstance(data, list):
        data = {"questions": data}

    if not isinstance(data, dict) or "questions" not in data:
        return []

    raw_list = data.get("questions")
    if not isinstance(raw_list, list) or len(raw_list) == 0:
        return []

    difficulty_map = {
        "easy": Difficulty.easy,
        "medium": Difficulty.medium,
        "hard": Difficulty.hard,
        "expert": Difficulty.expert,
    }

    validated: List[GeneratedQuestion] = []
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        q_text = str(item.get("question") or "").strip()
        if not q_text:
            continue
        cat = str(item.get("category") or "").strip() or "General"
        raw_diff = str(item.get("difficulty") or "").strip().lower()
        diff = difficulty_map.get(raw_diff, Difficulty.medium)

        validated.append(
            GeneratedQuestion(
                question=q_text,
                category=cat,
                difficulty=diff,
            )
        )

    return validated


def generate_questions(
    interview_id: str,
    user_id: str,
    question_count: int = 10,
    retry_sleep: bool = True,
) -> dict:
    """
    Generate questions using Google Gemini with bounded retries and
    exponential backoff, automatically falling back to OpenRouter if Gemini fails.

    Validates all questions before persisting to database, ensuring clean
    regeneration without orphan or duplicate questions.
    """
    if question_count < 1 or question_count > 20:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="question_count must be between 1 and 20",
        )

    # 1. Fetch Interview Context
    interview = _get_interview_and_verify_ownership(interview_id, user_id)

    # 2. Fetch Resume Context (if linked)
    resume_text = ""
    resume_id = interview.get("resume_id")
    if resume_id:
        resume = resumes_collection.find_one({"_id": resume_id})
        if resume and str(resume.get("user_id")) == user_id:
            extracted_text = resume.get("extracted_text", "")
            resume_text = extracted_text[:15000]

    # 3. Build Prompt
    system_prompt = INTERVIEW_QUESTION_SYSTEM_PROMPT.format(question_count=question_count)

    job_description = interview.get("job_description", "")
    if job_description:
        job_description = job_description[:5000]

    user_prompt = f"""
Please generate {question_count} interview questions.

--- CANDIDATE & INTERVIEW DETAILS ---
Role: {interview.get('role')}
Experience Level: {interview.get('experience_level')}
Skills: {', '.join(interview.get('skills', []))}
Interview Type: {interview.get('interview_type')}
Difficulty: {interview.get('difficulty')}
"""

    if job_description:
        user_prompt += f"\n--- JOB DESCRIPTION ---\n{job_description}\n"

    if resume_text:
        user_prompt += f"\n--- CANDIDATE RESUME TEXT ---\n{resume_text}\n"

    generated_questions: List[GeneratedQuestion] = []
    provider_source: str = ""
    last_gemini_error: str = ""
    last_openrouter_error: str = ""

    # 4. Attempt Primary Provider: Google Gemini
    gemini_client = None
    model_name = getattr(gemini_wrapper, "model_name", "gemini-3.8-flash")
    try:
        gemini_client = gemini_wrapper.get_client()
    except Exception as exc:
        last_gemini_error = f"Gemini client unavailable: {exc}"
        logger.warning("[AI Questions] %s", last_gemini_error)

    if gemini_client:
        for attempt in range(MAX_GEMINI_RETRIES):
            try:
                logger.info(
                    "[AI Questions] Calling Gemini model=%s (attempt %d/%d)...",
                    model_name,
                    attempt + 1,
                    MAX_GEMINI_RETRIES,
                )
                response = gemini_client.models.generate_content(
                    model=model_name,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type="application/json",
                        response_schema=GeneratedQuestionList,
                        temperature=0.7,
                    ),
                )
                raw_text = getattr(response, "text", "") or ""
                parsed = _parse_and_validate_questions(raw_text)
                if parsed:
                    generated_questions = parsed
                    provider_source = "gemini"
                    logger.info(
                        "[AI Questions] Gemini generated %d questions successfully.",
                        len(generated_questions),
                    )
                    break
                else:
                    last_gemini_error = "Gemini returned empty or invalid question JSON."
                    logger.warning(
                        "[AI Questions] Gemini attempt %d: empty or unparseable response.",
                        attempt + 1,
                    )
            except Exception as e:
                last_gemini_error = str(e)
                logger.warning(
                    "[AI Questions] Gemini attempt %d failed: %s",
                    attempt + 1,
                    last_gemini_error,
                )
                if attempt < MAX_GEMINI_RETRIES - 1 and _is_gemini_retryable_error(e):
                    backoff_delay = INITIAL_BACKOFF * (2 ** attempt)
                    logger.info(
                        "[AI Questions] Retrying Gemini in %.2fs (exponential backoff)...",
                        backoff_delay,
                    )
                    if retry_sleep:
                        time.sleep(backoff_delay)
                    continue
                # Non-retryable error or retries exhausted
                break

    # 5. Attempt Fallback Provider: OpenRouter (if Gemini failed)
    if not generated_questions:
        logger.info(
            "[AI Questions] Gemini unavailable or exhausted retries. Checking OpenRouter fallback..."
        )
        openrouter_client = _get_openrouter_client()
        if openrouter_client and openrouter_client.is_configured():
            try:
                openrouter_system_prompt = (
                    "You are an expert technical interviewer and career coach.\n"
                    f"Your task is to generate {question_count} personalized interview questions for a candidate.\n"
                    "You must return ONLY a JSON object that satisfies this exact schema:\n"
                    "{\n"
                    '  "questions": [\n'
                    '    {"question": "<question text>", "category": "<topic>", "difficulty": "Easy"|"Medium"|"Hard"|"Expert"}\n'
                    "  ]\n"
                    "}\n"
                    "Do NOT include markdown formatting or conversational text. Return valid JSON only."
                )
                messages = [
                    {"role": "system", "content": openrouter_system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
                or_resp = openrouter_client.chat_completion(
                    messages=messages,
                    temperature=0.7,
                    max_tokens=3500,
                    response_format={"type": "json_object"},
                )
                choices = getattr(or_resp, "choices", None)
                first_choice = choices[0] if choices else None
                content = (
                    first_choice.message.content
                    if first_choice and hasattr(first_choice, "message")
                    else ""
                )
                parsed = _parse_and_validate_questions(content)
                if parsed:
                    generated_questions = parsed
                    provider_source = "openrouter"
                    logger.info(
                        "[AI Questions] OpenRouter fallback succeeded with %d questions.",
                        len(generated_questions),
                    )
                else:
                    last_openrouter_error = "OpenRouter returned empty or invalid question JSON."
            except Exception as or_exc:
                last_openrouter_error = str(or_exc)
                logger.error("[AI Questions] OpenRouter fallback failed: %s", or_exc)
        else:
            last_openrouter_error = "OpenRouter client is not configured (missing OPENROUTER_API_KEY)."
            logger.warning("[AI Questions] %s", last_openrouter_error)

    # 6. Verify and Validate Questions
    if not generated_questions:
        error_detail = (
            f"AI Question Generation service is currently unavailable. "
            f"Gemini failed: {last_gemini_error or 'no response'}. "
            f"OpenRouter fallback failed: {last_openrouter_error or 'unconfigured'}."
        )
        logger.error("[AI Questions] Both providers failed: %s", error_detail)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=error_detail,
        )

    # 7. Persist Validated Questions in Database (Clean Regeneration Strategy)
    # Delete previous AI questions for this interview to prevent duplicates
    questions_collection.delete_many({
        "interview_id": interview["_id"],
        "source": {"$in": ["gemini", "openrouter", "ai"]},
    })

    current_count = questions_collection.count_documents({"interview_id": interview["_id"]})
    now = utc_now()
    start_number = current_count + 1

    db_questions = []
    for idx, q in enumerate(generated_questions):
        diff_val = q.difficulty.value if hasattr(q.difficulty, "value") else str(q.difficulty)
        doc = {
            "interview_id": interview["_id"],
            "question_number": start_number + idx,
            "question": q.question,
            "category": q.category,
            "difficulty": diff_val,
            "source": provider_source,
            "created_at": now,
        }
        db_questions.append(doc)

    result = questions_collection.insert_many(db_questions)
    for i, doc in enumerate(db_questions):
        doc["_id"] = result.inserted_ids[i]

    # Update interview's question count
    new_total = questions_collection.count_documents({"interview_id": interview["_id"]})
    interviews_collection.update_one(
        {"_id": interview["_id"]},
        {"$set": {"question_count": new_total, "updated_at": now}},
    )

    # Prepare response items with string IDs
    response_items = []
    for doc in db_questions:
        doc["id"] = str(doc.pop("_id"))
        doc["interview_id"] = str(doc.pop("interview_id"))
        response_items.append(doc)

    return {
        "interview_id": str(interview["_id"]),
        "count": len(response_items),
        "questions": response_items,
    }
