"""
app/agents/interview_agent.py

Interview Agent — handles interview state and session queries.

Reuses Phase 3/6 interview service data via interview_tools.
"""

from app.graph.state import AgentState
from app.ai.tool_calling import execute_tool, ToolError


def run_interview_agent(state: AgentState) -> dict:
    """
    Execute the interview state workflow.

    Retrieves interview metadata or session state depending on what's available.

    Args:
        state: Current AgentState.

    Returns:
        Partial state update with interview data and final_response.
    """
    user_id: str = state["user_id"]
    interview_id: str | None = state.get("interview_id")
    tool_results: dict = state.get("tool_results") or {}

    # Reuse orchestrator results if available
    for key in ("get_interview_state", "get_interview", "get_recent_interview"):
        if key in tool_results:
            result = tool_results[key]
            interview = result.get("interview", result)
            return {
                "final_response": _format_interview_response(result),
                "tool_results": tool_results,
            }

    # Fetch interview state if we have an ID
    try:
        if interview_id:
            result = execute_tool(
                tool_name="get_interview_state",
                tool_args={"interview_id": interview_id},
                user_id=user_id,
            )
            tool_results["get_interview_state"] = result
        else:
            result = execute_tool(
                tool_name="get_recent_interview",
                tool_args={},
                user_id=user_id,
            )
            tool_results["get_recent_interview"] = result

        return {
            "final_response": _format_interview_response(result),
            "tool_results": tool_results,
        }
    except ToolError as e:
        return {
            "error": str(e),
            "final_response": f"Could not retrieve interview information: {e}",
        }


def _format_interview_response(data: dict) -> str:
    """Format interview state data into a human-readable summary."""
    if "message" in data and not data.get("interview"):
        return data["message"]

    interview = data.get("interview", data)
    status = data.get("status", interview.get("status", "unknown"))
    total = data.get("total_questions", interview.get("question_count", 0))
    answered = data.get("answered_questions", 0)

    lines = []
    if title := interview.get("title"):
        lines.append(f"**{title}**")
    if role := interview.get("role"):
        lines.append(f"Role: {role}")
    lines.append(f"Status: {status}")
    if total:
        lines.append(f"Progress: {answered}/{total} questions answered")

    return "\n".join(lines) if lines else "Interview information retrieved."
