"""
app/services/agent_service.py

Orchestration service for Phase 10 Agentic AI.

Responsibilities:
- Build the initial AgentState from the API request.
- Invoke the compiled LangGraph workflow.
- Serialize the final state into an AgentResponse.
- Handle all errors without exposing secrets or stack traces.
"""

from typing import Optional

from app.graph.state import AgentState
from app.schemas.agent import AgentResponse


def run_agent(
    message: str,
    user_id: str,
    interview_id: Optional[str] = None,
) -> AgentResponse:
    """
    Execute the full agent workflow for a user request.

    Args:
        message:      The user's natural-language message.
        user_id:      Authenticated user ID (from JWT — never from request body).
        interview_id: Optional interview context from the request.

    Returns:
        AgentResponse with success status, task, response text, and optional data.
    """
    # Lazy import to avoid circular dependencies at startup
    from app.graph.workflow import agent_workflow

    # --- Build initial state ---
    initial_state: AgentState = {
        "user_id": user_id,
        "task": None,
        "interview_id": interview_id,
        "messages": [{"role": "user", "content": message}],
        "tool_results": {},
        "next_action": None,
        "error": None,
        "final_response": None,
        # Remaining fields left as None/unset
    }

    try:
        final_state: AgentState = agent_workflow.invoke(initial_state)
    except Exception as e:
        # LangGraph or unexpected errors
        return AgentResponse(
            success=False,
            task=None,
            response="An unexpected error occurred while processing your request.",
            data={"error_type": type(e).__name__},
        )

    # --- Extract results from final state ---
    error = final_state.get("error")
    task = final_state.get("task") or final_state.get("next_action")
    final_response = final_state.get("final_response") or ""

    if not final_response and error:
        final_response = "I encountered an issue processing your request. Please try again."

    # Build data payload (exclude sensitive fields)
    data: dict = {}

    if coach_result := final_state.get("coach_result"):
        data["coaching"] = coach_result

    if feedback := final_state.get("feedback"):
        data["feedback"] = _safe_feedback(feedback)

    if questions := final_state.get("questions"):
        data["questions_count"] = len(questions)

    if analytics := final_state.get("analytics"):
        data["analytics_summary"] = _safe_analytics_summary(analytics)

    return AgentResponse(
        success=error is None,
        task=task,
        response=final_response,
        data=data,
    )


def _safe_feedback(feedback: dict) -> dict:
    """Return a trimmed, safe feedback summary for the API response."""
    return {
        "overall_score": feedback.get("overall_score"),
        "summary": feedback.get("summary", ""),
        "strengths": feedback.get("strengths", [])[:3],
        "weaknesses": feedback.get("weaknesses", [])[:3],
    }


def _safe_analytics_summary(analytics: dict) -> dict:
    """Return a trimmed analytics summary."""
    if not isinstance(analytics, dict):
        return {}

    # Handle full analytics payload
    if overview := analytics.get("overview"):
        return {
            "average_score": overview.get("average_score"),
            "evaluated_interviews": overview.get("evaluated_interviews"),
            "trend": analytics.get("improvement", {}).get("trend"),
        }

    # Handle improvement-only payload
    if "trend" in analytics:
        return {"trend": analytics.get("trend")}

    return {}
