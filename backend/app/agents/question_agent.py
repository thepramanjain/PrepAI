"""
app/agents/question_agent.py

Question Agent — handles generate_questions and get_questions workflows.

Delegates all question generation to Phase 5 Gemini service via question_tools.
"""

from app.graph.state import AgentState
from app.ai.tool_calling import execute_tool, ToolError


def run_question_agent(state: AgentState) -> dict:
    """
    Execute the question workflow.

    Attempts to generate questions if an interview_id is available,
    otherwise retrieves existing questions.

    Args:
        state: Current AgentState.

    Returns:
        Partial state update with questions and final_response.
    """
    user_id: str = state["user_id"]
    interview_id: str | None = state.get("interview_id")
    tool_results: dict = state.get("tool_results") or {}

    # If the orchestrator already ran generate_questions as a tool, reuse result
    if "generate_questions" in tool_results:
        result = tool_results["generate_questions"]
        return {
            "questions": result.get("questions", []),
            "final_response": (
                f"Generated {result.get('count', 0)} interview questions successfully."
            ),
            "tool_results": tool_results,
        }

    if "get_questions" in tool_results:
        result = tool_results["get_questions"]
        return {
            "questions": result.get("questions", []),
            "final_response": (
                f"Retrieved {result.get('count', 0)} existing questions."
            ),
            "tool_results": tool_results,
        }

    # No prior tool result — execute now
    if not interview_id:
        return {
            "error": "No interview_id provided. Please specify which interview to use.",
            "final_response": "I need an interview ID to generate or retrieve questions. Please provide one.",
        }

    try:
        result = execute_tool(
            tool_name="generate_questions",
            tool_args={"interview_id": interview_id, "question_count": 10},
            user_id=user_id,
        )
        tool_results["generate_questions"] = result
        return {
            "questions": result.get("questions", []),
            "final_response": (
                f"Successfully generated {result.get('count', 0)} interview questions "
                f"for interview {interview_id}."
            ),
            "tool_results": tool_results,
        }
    except ToolError as e:
        return {
            "error": str(e),
            "final_response": f"Could not generate questions: {e}",
        }
