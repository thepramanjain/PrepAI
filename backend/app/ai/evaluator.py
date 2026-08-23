"""
app/ai/evaluator.py

Phase 7 — AI Interview Evaluator.

Responsibilities:
- Build structured evaluation context from interview data.
- Call Gemini with the evaluation prompt.
- Parse and validate the structured JSON response.
- Raise on failure — do NOT return partial data.

Context truncation limits (documented):
- Resume text: max 3,000 characters
- Job description: max 1,000 characters
- Each individual answer: max 2,000 characters
"""

import json
from typing import List, Dict, Any, Optional
from google.genai import types

from app.ai.gemini_client import gemini_wrapper
from app.ai.prompts import INTERVIEW_EVALUATION_SYSTEM_PROMPT
from app.schemas.feedback import GeneratedEvaluation


# --- Truncation Constants ---
_RESUME_LIMIT = 3000
_JD_LIMIT = 1000
_ANSWER_LIMIT = 2000


def build_evaluation_context(
    interview: Dict[str, Any],
    questions: List[Dict[str, Any]],
    responses: List[Dict[str, Any]],
    resume_text: Optional[str] = None,
) -> str:
    """
    Build the user-turn prompt for Gemini containing the full interview transcript.
    Answers are matched to questions by question_id.
    Unanswered questions are explicitly marked as "Not Answered".
    All text fields are truncated to prevent token overflow.
    """
    # Build a lookup: question_id -> answer text
    response_map: Dict[str, str] = {}
    for resp in responses:
        q_id = str(resp.get("question_id", ""))
        answer = (resp.get("answer") or "").strip()
        if q_id and answer:
            response_map[q_id] = answer[:_ANSWER_LIMIT]

    # Build interview metadata section
    lines = [
        "=== INTERVIEW DETAILS ===",
        f"Role: {interview.get('role', 'N/A')}",
        f"Experience Level: {interview.get('experience_level', 'N/A')}",
        f"Interview Type: {interview.get('interview_type', 'N/A')}",
        f"Difficulty: {interview.get('difficulty', 'N/A')}",
        f"Skills: {', '.join(interview.get('skills', []))}",
    ]

    jd = (interview.get("job_description") or "").strip()
    if jd:
        lines.append(f"\n=== JOB DESCRIPTION ===\n{jd[:_JD_LIMIT]}")

    if resume_text:
        safe_resume = resume_text.strip()[:_RESUME_LIMIT]
        lines.append(f"\n=== CANDIDATE RESUME (context only) ===\n{safe_resume}")

    # Build the transcript
    lines.append("\n=== INTERVIEW TRANSCRIPT ===")
    for idx, q in enumerate(questions, start=1):
        q_id = str(q["_id"])
        question_text = q.get("question", "")
        category = q.get("category", "General")
        difficulty = q.get("difficulty", "Medium")
        answer = response_map.get(q_id, "Not Answered")

        lines.append(
            f"\n[Q{idx}] (ID: {q_id}) [{category}] [{difficulty}]\n"
            f"Question: {question_text}\n"
            f"Candidate Answer: {answer}"
        )

    lines.append(
        "\n=== INSTRUCTIONS ===\n"
        "Evaluate every question listed above. "
        "Use the exact question_id values provided in parentheses. "
        "Return ONLY valid JSON matching the required output format."
    )

    return "\n".join(lines)


def evaluate_interview(
    interview: Dict[str, Any],
    questions: List[Dict[str, Any]],
    responses: List[Dict[str, Any]],
    resume_text: Optional[str] = None,
) -> GeneratedEvaluation:
    """
    Call Gemini to evaluate the interview and return a validated GeneratedEvaluation.

    Raises:
        ValueError: If Gemini client is not configured.
        HTTPException-compatible RuntimeError: If Gemini API call fails or response is invalid.
    """
    # 1. Get Gemini client
    try:
        client = gemini_wrapper.get_client()
        model_name = gemini_wrapper.model_name
    except ValueError as e:
        raise RuntimeError("AI Service is not configured. Missing or invalid API key.") from e

    # 2. Build context
    user_prompt = build_evaluation_context(interview, questions, responses, resume_text)

    # 3. Call Gemini
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=INTERVIEW_EVALUATION_SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.3,  # Lower temperature for more deterministic evaluation
            ),
        )
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
            raise RuntimeError("AI Service rate limit exceeded. Please try again later.")
        raise RuntimeError(f"Failed to communicate with AI Service: {error_msg}")

    # 4. Validate the response is not empty
    if not response.text:
        raise RuntimeError("Received empty response from AI Service.")

    # 5. Parse JSON
    try:
        raw_data = json.loads(response.text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"AI Service returned invalid JSON: {e}")

    # 6. Validate with Pydantic
    try:
        validated = GeneratedEvaluation(**raw_data)
    except Exception as e:
        raise RuntimeError(f"AI response failed schema validation: {e}")

    return validated
