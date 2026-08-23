"""
voice-agent/tools.py

LiveKit Agents function tools for the PrepAI voice interviewer.

Tools are called by the Gemini LLM during the agent session to:
  - Signal that the current question has been fully answered
  - Store the candidate's response to the backend
  - Move to the next question
  - End the interview

These tools bridge the voice agent with the PrepAI backend API.
All backend calls use the candidate's JWT token — ownership is
enforced by the backend, not by the tool itself.

Usage in agent.py:
  session = AgentSession(
      llm=google.realtime.RealtimeModel(..., tools=[...]),
      ...
  )
"""

from __future__ import annotations

import logging
from typing import Annotated, Optional

import httpx
from livekit.agents import function_tool  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


def make_tools(
    interview_id: str,
    backend_url: str,
    jwt_token: str,
) -> list:
    """
    Factory that creates all voice agent tools bound to the current session.
    Returns a list of tool functions ready to pass to RealtimeModel.
    """

    @function_tool
    async def store_response(
        question_id: Annotated[str, "The question ID being answered"],
        answer_text: Annotated[str, "The candidate's spoken answer, transcribed to text"],
    ) -> str:
        """
        Store the candidate's answer to the current question in the PrepAI backend.
        Call this after the candidate has finished answering a question.
        """
        url = f"{backend_url}/api/interviews/{interview_id}/questions/{question_id}/response"
        headers = {"Authorization": f"Bearer {jwt_token}"}
        payload = {
            "answer": answer_text,
            "source": "voice",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as http:
                resp = await http.post(url, json=payload, headers=headers)
                if resp.status_code in (200, 201):
                    logger.info("Response stored for question %s", question_id)
                    return "Response stored successfully."
                else:
                    logger.warning(
                        "Failed to store response [%s]: %s",
                        resp.status_code,
                        resp.text[:200],
                    )
                    return f"Storage warning: {resp.status_code}"
        except Exception as exc:
            logger.error("Error storing response: %s", exc)
            return f"Storage error: {exc}"

    @function_tool
    async def advance_to_next_question() -> str:
        """
        Signal the PrepAI backend to advance to the next question.
        Call this after storing the response and (optionally) asking a follow-up.
        """
        url = f"{backend_url}/api/interviews/{interview_id}/next"
        headers = {"Authorization": f"Bearer {jwt_token}"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as http:
                resp = await http.post(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status", "unknown")
                    if status == "completed":
                        return "INTERVIEW_COMPLETE"
                    return f"Advanced to question {data.get('current_question_number', '?')}"
                else:
                    logger.warning(
                        "Failed to advance question [%s]: %s",
                        resp.status_code,
                        resp.text[:200],
                    )
                    return f"Advance warning: {resp.status_code}"
        except Exception as exc:
            logger.error("Error advancing question: %s", exc)
            return f"Advance error: {exc}"

    @function_tool
    async def end_interview() -> str:
        """
        Signal the PrepAI backend to end the voice interview session.
        Call this only after all questions have been covered and the candidate
        has been thanked and dismissed.
        """
        url = f"{backend_url}/api/interviews/{interview_id}/voice/end"
        headers = {"Authorization": f"Bearer {jwt_token}"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as http:
                resp = await http.post(url, headers=headers)
                if resp.status_code == 200:
                    logger.info("Interview %s ended via tool", interview_id)
                    return "Interview session ended successfully."
                else:
                    logger.warning(
                        "Failed to end interview [%s]: %s",
                        resp.status_code,
                        resp.text[:200],
                    )
                    return f"End interview warning: {resp.status_code}"
        except Exception as exc:
            logger.error("Error ending interview: %s", exc)
            return f"End interview error: {exc}"

    return [store_response, advance_to_next_question, end_interview]
