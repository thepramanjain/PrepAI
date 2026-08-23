"""
app/agents/evaluation_agent.py

Evaluation Agent — handles interview evaluation workflows.

Delegates all evaluation to Phase 7 Gemini evaluator via evaluation_tools.
GPT-4o does NOT perform evaluation — only interprets the result.
"""

from app.graph.state import AgentState
from app.ai.tool_calling import execute_tool, ToolError


def run_evaluation_agent(state: AgentState) -> dict:
    """
    Execute the evaluation workflow.

    Prefers existing feedback (get_feedback) to avoid re-evaluating unnecessarily.
    Falls back to triggering evaluation (evaluate_interview) if no feedback exists.

    Args:
        state: Current AgentState.

    Returns:
        Partial state update with feedback and final_response.
    """
    user_id: str = state["user_id"]
    interview_id: str | None = state.get("interview_id")
    tool_results: dict = state.get("tool_results") or {}

    # Reuse orchestrator results if available
    for key in ("evaluate_interview", "get_feedback"):
        if key in tool_results:
            result = tool_results[key]
            return {
                "feedback": result,
                "final_response": _format_feedback_response(result),
                "tool_results": tool_results,
            }

    if not interview_id:
        return {
            "error": "No interview_id provided for evaluation.",
            "final_response": "Please provide an interview ID to evaluate.",
        }

    # Try to get existing feedback first (no-op if already evaluated)
    try:
        result = execute_tool(
            tool_name="get_feedback",
            tool_args={"interview_id": interview_id},
            user_id=user_id,
        )
        tool_results["get_feedback"] = result
        return {
            "feedback": result,
            "final_response": _format_feedback_response(result),
            "tool_results": tool_results,
        }
    except ToolError:
        pass  # No existing feedback — trigger evaluation

    # Trigger new evaluation via Gemini
    try:
        result = execute_tool(
            tool_name="evaluate_interview",
            tool_args={"interview_id": interview_id},
            user_id=user_id,
        )
        tool_results["evaluate_interview"] = result
        return {
            "feedback": result,
            "final_response": _format_feedback_response(result),
            "tool_results": tool_results,
        }
    except ToolError as e:
        return {
            "error": str(e),
            "final_response": f"Could not evaluate the interview: {e}",
        }


def _format_feedback_response(feedback: dict) -> str:
    """Format feedback into a human-readable summary."""
    score = feedback.get("overall_score")
    summary = feedback.get("summary", "")
    strengths = feedback.get("strengths", [])
    weaknesses = feedback.get("weaknesses", [])
    cat = feedback.get("category_scores", {})

    lines = []
    if score is not None:
        lines.append(f"**Overall Score: {score}/100**")
    if summary:
        lines.append(f"\n{summary}")
    if cat:
        lines.append("\n**Category Scores:**")
        for k, v in cat.items():
            if v is not None:
                lines.append(f"  - {k.replace('_', ' ').title()}: {v}")
    if strengths:
        lines.append("\n**Strengths:** " + ", ".join(strengths[:3]))
    if weaknesses:
        lines.append("**Areas to Improve:** " + ", ".join(weaknesses[:3]))

    return "\n".join(lines) if lines else "Evaluation complete."
