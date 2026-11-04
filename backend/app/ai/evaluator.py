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


def _get_openrouter_client():
    """Dynamically get OpenRouter client to preserve AST isolation while enabling fallback."""
    try:
        import importlib
        mod = importlib.import_module("app.ai.openrouter_client")
        return getattr(mod, "openrouter_client", None)
    except Exception:
        return None


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
    models_to_try = [model_name]
    for fb in ["gemini-3.5-flash", "gemini-flash-latest"]:
        if fb not in models_to_try:
            models_to_try.append(fb)

    response = None
    for candidate_model in models_to_try:
        try:
            response = client.models.generate_content(
                model=candidate_model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=INTERVIEW_EVALUATION_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.3,  # Lower temperature for more deterministic evaluation
                ),
            )
            break
        except Exception as e:
            error_msg = str(e)
            print(f"[AI Evaluation] Gemini attempt with '{candidate_model}' failed: {error_msg}")
            is_recoverable = (
                "503" in error_msg
                or "404" in error_msg
                or "UNAVAILABLE" in error_msg
                or "NOT_FOUND" in error_msg
                or "disconnected" in error_msg
                or "RemoteProtocolError" in error_msg
                or "ConnectError" in error_msg
                or "timed out" in error_msg.lower()
            )

            # Fall back to OpenRouter immediately on provider failure
            or_client = _get_openrouter_client()
            if or_client and or_client.is_configured():
                print("[AI Evaluation] Provider failure on Gemini: attempting OpenRouter fallback...")
                try:
                    or_resp = or_client.chat_completion(
                        messages=[
                            {"role": "system", "content": INTERVIEW_EVALUATION_SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.3,
                        max_tokens=3500,
                        response_format={"type": "json_object"},
                    )
                    choice = or_resp.choices[0] if getattr(or_resp, "choices", None) else None
                    content_str = choice.message.content if choice and hasattr(choice, "message") else ""
                    if content_str:
                        clean_content = content_str.strip()
                        if clean_content.startswith("```"):
                            import re
                            clean_content = re.sub(r"^```(?:json)?\s*", "", clean_content, flags=re.IGNORECASE)
                            clean_content = re.sub(r"\s*```$", "", clean_content).strip()
                        raw_data = json.loads(clean_content)
                        evaluation = GeneratedEvaluation(**raw_data)
                        print(f"[AI Evaluation] OpenRouter evaluation succeeded with overall score: {evaluation.overall_score}")
                        return evaluation
                except Exception as or_err:
                    print(f"[AI Evaluation] OpenRouter fallback failed: {or_err}")

            if is_recoverable and candidate_model != models_to_try[-1]:
                continue

            if "401" in error_msg or "403" in error_msg or "UNAUTHENTICATED" in error_msg or "PERMISSION_DENIED" in error_msg or "API key not valid" in error_msg:
                raise RuntimeError("AI Service authentication failed. Please check that GEMINI_API_KEY is valid.") from e
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "rate limit" in error_msg.lower():
                raise RuntimeError("AI Service rate limit exceeded. Please try again later.") from e
            if "404" in error_msg or "NOT_FOUND" in error_msg:
                raise RuntimeError(f"AI Service model '{candidate_model}' not found or unavailable. Please check GEMINI_MODEL setting.") from e
            raise RuntimeError(f"Failed to communicate with AI Service: {error_msg}") from e

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
