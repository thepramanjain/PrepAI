"""
app/graph/nodes.py

LangGraph nodes for the PrepAI agent workflow.

Each node:
  1. Receives the current AgentState.
  2. Performs only its assigned responsibility.
  3. Returns a partial state update dict.

Nodes do NOT share mutable state directly — they return updates.
"""

from app.graph.state import AgentState


def orchestrator_node(state: AgentState) -> dict:
    """
    Entry node — uses GPT-4o to determine user intent and which action to take.

    Runs the tool-calling loop internally to gather any initial data needed
    for routing. Sets state["next_action"] for the conditional edge.
    """
    from app.agents.orchestrator import run_orchestrator
    return run_orchestrator(state)


def question_node(state: AgentState) -> dict:
    """
    Handles question generation and retrieval workflows.

    Delegates to Phase 5 Gemini via question_tools.
    """
    from app.agents.question_agent import run_question_agent
    return run_question_agent(state)


def interview_node(state: AgentState) -> dict:
    """
    Handles interview state and session queries.

    Wraps Phase 3/6 interview service data.
    """
    from app.agents.interview_agent import run_interview_agent
    return run_interview_agent(state)


def evaluation_node(state: AgentState) -> dict:
    """
    Handles interview evaluation workflows.

    Delegates to Phase 7 Gemini evaluator via evaluation_tools.
    """
    from app.agents.evaluation_agent import run_evaluation_agent
    return run_evaluation_agent(state)


def analytics_node(state: AgentState) -> dict:
    """
    Handles analytics and performance queries.

    Delegates to Phase 8 analytics service. GPT-4o interprets — does not calculate.
    """
    from app.agents.analytics_agent import run_analytics_agent
    return run_analytics_agent(state)


def coach_node(state: AgentState) -> dict:
    """
    Handles career coaching with GPT-4o.

    Aggregates analytics context, then uses GPT-4o to generate a
    structured CoachingResult.
    """
    from app.agents.coach_agent import run_coach_agent
    return run_coach_agent(state)
