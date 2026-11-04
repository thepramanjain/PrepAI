"""
app/graph/workflow.py

Native Python dispatcher for the PrepAI agent system.

Replaces the previous LangGraph StateGraph with a lightweight two-step pipeline
that preserves the identical .invoke() interface consumed by agent_service.

Architecture:
    orchestrator_node   <- GPT-4o determines intent, sets next_action
      | (route_from_orchestrator)
      v
    +-----------------------------------------------+
    | question_node  | interview_node               |
    | evaluation_node| analytics_node | coach_node  |
    +-----------------------------------------------+

No external orchestration framework is required.
"""

import logging

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

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Node registry — maps routing target names to their functions
# ---------------------------------------------------------------------------

_NODE_MAP: dict = {
    "question_node": question_node,
    "interview_node": interview_node,
    "evaluation_node": evaluation_node,
    "analytics_node": analytics_node,
    "coach_node": coach_node,
}


class _NativeWorkflow:
    """
    Lightweight two-step pipeline replacing LangGraph StateGraph.

    Preserves the .invoke() interface so agent_service.py requires no changes.

    Step 1: orchestrator_node  — determines intent, sets next_action
    Step 2: specialist node    — determined by route_from_orchestrator()
    """

    def invoke(self, initial_state: AgentState) -> AgentState:
        """
        Execute the two-step pipeline and return the final state.

        Args:
            initial_state: Initial AgentState dict (user_id, messages, etc.)

        Returns:
            Final AgentState dict with results merged in.
        """
        state: dict = dict(initial_state)

        # --- Step 1: Orchestrator determines intent ---
        try:
            orch_output = orchestrator_node(state)
            state.update(orch_output)
        except Exception as exc:
            logger.error("orchestrator_node raised an exception: %s", exc)
            state["error"] = str(exc)
            return state  # type: ignore[return-value]

        # --- Step 2: Route to the appropriate specialist node ---
        target = route_from_orchestrator(state)

        if target == "__end__":
            # Orchestrator decided no specialist is needed (or action was invalid)
            logger.debug("Workflow ended after orchestrator (target=__end__)")
            return state  # type: ignore[return-value]

        node_fn = _NODE_MAP.get(target)
        if node_fn is None:
            logger.warning("No node registered for routing target %r", target)
            state["error"] = f"Unknown routing target: {target}"
            return state  # type: ignore[return-value]

        try:
            specialist_output = node_fn(state)
            state.update(specialist_output)
        except Exception as exc:
            logger.error("Specialist node %r raised an exception: %s", target, exc)
            state["error"] = str(exc)

        return state  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Singleton workflow — shared across requests (identical interface to before)
# ---------------------------------------------------------------------------

agent_workflow = _NativeWorkflow()
