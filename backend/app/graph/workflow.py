"""
app/graph/workflow.py

LangGraph workflow assembly for the PrepAI agent system.

Architecture:
    START
      ↓
    orchestrator_node   ← GPT-4o determines intent, sets next_action
      ↓ (conditional)
    ┌─────────────────────────────────────────────┐
    │ question_node  │ interview_node             │
    │ evaluation_node│ analytics_node│ coach_node │
    └─────────────────────────────────────────────┘
      ↓
    END

The compiled workflow is a singleton used by agent_service.
"""

from langgraph.graph import StateGraph, END

from app.graph.state import AgentState
from app.graph.nodes import (
    orchestrator_node,
    question_node,
    interview_node,
    evaluation_node,
    analytics_node,
    coach_node,
)
from app.graph.edges import route_from_orchestrator, ACTION_TO_NODE


def build_workflow():
    """
    Construct and compile the LangGraph StateGraph.

    Returns:
        A compiled LangGraph workflow ready for .invoke() calls.
    """
    builder = StateGraph(AgentState)

    # --- Register nodes ---
    builder.add_node("orchestrator_node", orchestrator_node)
    builder.add_node("question_node", question_node)
    builder.add_node("interview_node", interview_node)
    builder.add_node("evaluation_node", evaluation_node)
    builder.add_node("analytics_node", analytics_node)
    builder.add_node("coach_node", coach_node)

    # --- Entry point ---
    builder.set_entry_point("orchestrator_node")

    # --- Conditional routing from orchestrator ---
    # Maps each possible return value of route_from_orchestrator() to a node
    conditional_map = {node_name: node_name for node_name in ACTION_TO_NODE.values()}
    conditional_map["__end__"] = END

    builder.add_conditional_edges(
        "orchestrator_node",
        route_from_orchestrator,
        conditional_map,
    )

    # --- All specialist nodes terminate after completing their work ---
    for node_name in ACTION_TO_NODE.values():
        builder.add_edge(node_name, END)

    return builder.compile()


# Singleton compiled workflow — shared across requests
agent_workflow = build_workflow()
