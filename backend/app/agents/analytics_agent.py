"""
app/agents/analytics_agent.py

Analytics Agent — handles performance analysis and trend queries.

All statistics are computed by Python/MongoDB (Phase 8).
GPT-4o receives results and provides natural-language interpretation
only when the orchestrator routes here for analysis tasks.
"""

from app.graph.state import AgentState
from app.ai.tool_calling import execute_tool, ToolError


def run_analytics_agent(state: AgentState) -> dict:
    """
    Execute the analytics workflow.

    Reuses tool results already gathered by the orchestrator when available.
    Otherwise fetches the full analytics payload.

    Args:
        state: Current AgentState.

    Returns:
        Partial state update with analytics data and final_response.
    """
    user_id: str = state["user_id"]
    tool_results: dict = state.get("tool_results") or {}

    # Reuse any analytics already gathered by the orchestrator
    analytics_keys = (
        "get_analytics",
        "get_score_trend",
        "get_category_performance",
        "get_topic_performance",
        "get_strengths",
        "get_weaknesses",
        "get_improvement",
    )
    collected = {k: tool_results[k] for k in analytics_keys if k in tool_results}

    if collected:
        # Summarize what we have
        return {
            "analytics": collected,
            "final_response": _format_analytics_response(collected),
            "tool_results": tool_results,
        }

    # Fetch full analytics payload
    try:
        result = execute_tool(
            tool_name="get_analytics",
            tool_args={},
            user_id=user_id,
        )
        tool_results["get_analytics"] = result

        # Also fetch improvement trend
        improvement = execute_tool(
            tool_name="get_improvement",
            tool_args={},
            user_id=user_id,
        )
        tool_results["get_improvement"] = improvement
        result["improvement"] = improvement

        return {
            "analytics": result,
            "final_response": _format_analytics_response({"get_analytics": result}),
            "tool_results": tool_results,
        }
    except ToolError as e:
        return {
            "error": str(e),
            "final_response": f"Could not retrieve analytics: {e}",
        }


def _format_analytics_response(collected: dict) -> str:
    """Format analytics data into a human-readable summary."""
    lines = []

    # Full analytics
    if full := collected.get("get_analytics"):
        overview = full.get("overview", {})
        avg = overview.get("average_score")
        latest = overview.get("latest_score")
        total = overview.get("evaluated_interviews", 0)

        if total == 0:
            return "No evaluated interviews found yet. Complete and evaluate an interview to see your analytics."

        lines.append(f"**Performance Summary** ({total} evaluated interview(s))")
        if avg is not None:
            lines.append(f"  Average Score: {avg}/100")
        if latest is not None:
            lines.append(f"  Latest Score: {latest}/100")

        # Category performance
        cat = full.get("category_performance", {})
        if any(v is not None for v in cat.values()):
            lines.append("\n**Category Scores:**")
            for k, v in cat.items():
                if v is not None:
                    lines.append(f"  - {k.replace('_', ' ').title()}: {v}")

        # Improvement
        imp = full.get("improvement", {})
        trend = imp.get("trend")
        if trend and trend != "insufficient_data":
            diff = imp.get("score_difference", 0)
            sign = "+" if diff and diff > 0 else ""
            lines.append(f"\n**Trend:** {trend.title()} ({sign}{diff} points)")

    # Improvement only
    elif imp := collected.get("get_improvement"):
        trend = imp.get("trend")
        if trend == "insufficient_data":
            lines.append("Not enough data to determine improvement trend yet.")
        else:
            diff = imp.get("score_difference", 0)
            sign = "+" if diff and diff > 0 else ""
            lines.append(f"Performance trend: **{trend}** ({sign}{diff} points difference)")

    return "\n".join(lines) if lines else "Analytics data retrieved."
