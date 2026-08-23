"""
app/graph/edges.py

Conditional routing logic for the PrepAI LangGraph workflow.

SECURITY: Only the predefined action allowlist is accepted.
Unknown or unsupported actions route to the terminal "end" node with an error.
"""

from app.graph.state import AgentState

# ---------------------------------------------------------------------------
# Allowlist of valid routing targets
# ---------------------------------------------------------------------------
VALID_ACTIONS = frozenset({
    "generate_questions",
    "conduct_interview",
    "evaluate_interview",
    "analyze_performance",
    "get_coaching",
})

# Map action → node name (must match graph.add_node() names)
ACTION_TO_NODE: dict[str, str] = {
    "generate_questions": "question_node",
    "conduct_interview": "interview_node",
    "evaluate_interview": "evaluation_node",
    "analyze_performance": "analytics_node",
    "get_coaching": "coach_node",
}


def route_from_orchestrator(state: AgentState) -> str:
    """
    Conditional edge function: determines which node to execute next.

    Called by LangGraph after the orchestrator_node completes.

    Args:
        state: Current AgentState with "next_action" set by orchestrator.

    Returns:
        The node name to route to, or "__end__" if routing is invalid.
    """
    next_action = state.get("next_action", "")

    if not next_action:
        return "__end__"

    if next_action not in VALID_ACTIONS:
        # Do not raise — allow the graph to end gracefully with an error state
        return "__end__"

    return ACTION_TO_NODE[next_action]
