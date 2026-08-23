"""
tests/test_graph.py

Tests for the LangGraph workflow (Phase 10).

All OpenRouter/Gemini calls and DB operations are mocked.
Tests verify graph routing, state propagation, and edge behaviour.
"""

import json
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_response(content="", tool_calls=None):
    mock_message = MagicMock()
    mock_message.content = content
    mock_message.tool_calls = tool_calls or []
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


def _build_state(message="test", interview_id=None, tool_results=None):
    return {
        "user_id": "user_abc123",
        "task": None,
        "interview_id": interview_id,
        "messages": [{"role": "user", "content": message}],
        "tool_results": tool_results or {},
        "next_action": None,
        "error": None,
        "final_response": None,
    }


# ---------------------------------------------------------------------------
# 1. Routing Logic (edges.py)
# ---------------------------------------------------------------------------

class TestRouting:
    def test_generate_questions_routes_to_question_node(self):
        from app.graph.edges import route_from_orchestrator
        state = {"next_action": "generate_questions"}
        assert route_from_orchestrator(state) == "question_node"

    def test_conduct_interview_routes_to_interview_node(self):
        from app.graph.edges import route_from_orchestrator
        state = {"next_action": "conduct_interview"}
        assert route_from_orchestrator(state) == "interview_node"

    def test_evaluate_interview_routes_to_evaluation_node(self):
        from app.graph.edges import route_from_orchestrator
        state = {"next_action": "evaluate_interview"}
        assert route_from_orchestrator(state) == "evaluation_node"

    def test_analyze_performance_routes_to_analytics_node(self):
        from app.graph.edges import route_from_orchestrator
        state = {"next_action": "analyze_performance"}
        assert route_from_orchestrator(state) == "analytics_node"

    def test_get_coaching_routes_to_coach_node(self):
        from app.graph.edges import route_from_orchestrator
        state = {"next_action": "get_coaching"}
        assert route_from_orchestrator(state) == "coach_node"

    def test_invalid_action_routes_to_end(self):
        from app.graph.edges import route_from_orchestrator
        state = {"next_action": "hack_system"}
        assert route_from_orchestrator(state) == "__end__"

    def test_empty_action_routes_to_end(self):
        from app.graph.edges import route_from_orchestrator
        state = {"next_action": None}
        assert route_from_orchestrator(state) == "__end__"

    def test_missing_action_routes_to_end(self):
        from app.graph.edges import route_from_orchestrator
        state = {}
        assert route_from_orchestrator(state) == "__end__"


# ---------------------------------------------------------------------------
# 2. State Schema
# ---------------------------------------------------------------------------

class TestAgentState:
    def test_state_accepts_all_fields(self):
        """AgentState TypedDict should accept all documented fields."""
        from app.graph.state import AgentState
        state: AgentState = {
            "user_id": "user123",
            "task": "get_coaching",
            "interview_id": "interview_abc",
            "messages": [],
            "tool_results": {},
            "next_action": "get_coaching",
            "error": None,
            "final_response": "Done.",
        }
        assert state["user_id"] == "user123"
        assert state["task"] == "get_coaching"

    def test_partial_state_is_valid(self):
        """AgentState should work with partial fields (total=False)."""
        from app.graph.state import AgentState
        state: AgentState = {"user_id": "user123"}
        assert state["user_id"] == "user123"


# ---------------------------------------------------------------------------
# 3. Analytics Workflow
# ---------------------------------------------------------------------------

class TestAnalyticsWorkflow:
    def test_analytics_workflow_end_to_end(self):
        """Full analytics workflow: orchestrator → analytics_node."""
        orchestrator_response = _make_mock_response(
            content="Let me check your performance.\nACTION: analyze_performance"
        )
        analytics_data = {
            "overview": {"average_score": 72.0, "evaluated_interviews": 3},
            "improvement": {"trend": "improving", "score_difference": 5.0},
            "category_performance": {"technical": 70.0, "communication": 75.0},
            "top_topics": [],
            "top_strengths": [],
            "top_weaknesses": [],
        }
        improvement_data = {"trend": "improving", "score_difference": 5.0}

        with patch("app.agents.orchestrator.openrouter_client") as mock_client:
            mock_client.is_configured.return_value = True
            mock_client.chat_completion.return_value = orchestrator_response

            with patch("app.tools.analytics_tools.get_full_analytics", return_value=analytics_data):
                with patch("app.tools.analytics_tools.get_improvement", return_value=improvement_data):
                    from app.graph.workflow import agent_workflow
                    result = agent_workflow.invoke(_build_state("Am I improving?"))

        assert result.get("task") == "analyze_performance"
        assert result.get("analytics") is not None


# ---------------------------------------------------------------------------
# 4. Coaching Workflow
# ---------------------------------------------------------------------------

class TestCoachingWorkflow:
    def test_coaching_workflow_end_to_end(self):
        """Full coaching workflow: orchestrator → coach_node."""
        orchestrator_response = _make_mock_response(
            content="I'll provide coaching advice.\nACTION: get_coaching"
        )
        coaching_context = {
            "overview": {"evaluated_interviews": 2, "average_score": 68.0},
            "top_weaknesses": ["System design"],
            "top_strengths": ["Communication"],
            "category_performance": {"technical": 60.0, "communication": 80.0},
            "top_topics": [],
            "improvement": {"trend": "stable"},
        }
        coach_json = json.dumps({
            "summary": "Focus on system design.",
            "strengths": ["Communication"],
            "priority_weaknesses": ["System design"],
            "focus_topics": ["Distributed systems"],
            "action_plan": [
                {"task": "Study system design", "reason": "Low score", "priority": "high"}
            ],
        })
        coach_response = _make_mock_response(content=coach_json)

        with patch("app.agents.orchestrator.openrouter_client") as mock_orch_client:
            mock_orch_client.is_configured.return_value = True
            mock_orch_client.chat_completion.return_value = orchestrator_response

            with patch("app.agents.coach_agent.openrouter_client") as mock_coach_client:
                mock_coach_client.is_configured.return_value = True
                mock_coach_client.chat_completion.return_value = coach_response

                with patch("app.tools.coaching_tools.get_overview", return_value=coaching_context["overview"]):
                    with patch("app.tools.coaching_tools.get_category_performance", return_value={}):
                        with patch("app.tools.coaching_tools.get_topic_performance", return_value=[]):
                            with patch("app.tools.coaching_tools.get_strengths", return_value=[]):
                                with patch("app.tools.coaching_tools.get_weaknesses", return_value=[]):
                                    with patch("app.tools.coaching_tools.get_improvement", return_value={}):
                                        from app.graph.workflow import agent_workflow
                                        result = agent_workflow.invoke(
                                            _build_state("What should I improve?")
                                        )

        assert result.get("task") == "get_coaching"


# ---------------------------------------------------------------------------
# 5. Evaluation Workflow
# ---------------------------------------------------------------------------

class TestEvaluationWorkflow:
    def test_evaluation_workflow_reuses_feedback(self):
        """Evaluation workflow should reuse pre-fetched feedback."""
        feedback_data = {
            "overall_score": 82,
            "summary": "Strong technical answers.",
            "strengths": ["Algorithm knowledge"],
            "weaknesses": ["Communication clarity"],
            "category_scores": {"technical": 85, "communication": 78, "problem_solving": 80, "relevance": 82},
        }

        orchestrator_response = _make_mock_response(
            content="I'll evaluate your interview.\nACTION: evaluate_interview"
        )

        with patch("app.agents.orchestrator.openrouter_client") as mock_client:
            mock_client.is_configured.return_value = True
            mock_client.chat_completion.return_value = orchestrator_response

            from app.graph.workflow import agent_workflow
            result = agent_workflow.invoke(
                _build_state(
                    "Evaluate my interview",
                    interview_id="int_123",
                    tool_results={"get_feedback": feedback_data},
                )
            )

        assert result.get("task") == "evaluate_interview"
        assert result.get("feedback", {}).get("overall_score") == 82


# ---------------------------------------------------------------------------
# 6. Invalid Route
# ---------------------------------------------------------------------------

class TestInvalidRoute:
    def test_unknown_action_does_not_crash(self):
        """Unknown action from orchestrator should end gracefully."""
        orchestrator_response = _make_mock_response(
            content="I don't know. ACTION: hack_system"
        )

        with patch("app.agents.orchestrator.openrouter_client") as mock_client:
            mock_client.is_configured.return_value = True
            mock_client.chat_completion.return_value = orchestrator_response

            from app.graph.workflow import agent_workflow
            result = agent_workflow.invoke(_build_state("Do something dangerous"))

        # Workflow should end without exception
        assert result.get("next_action") is None or result.get("next_action") not in {
            "generate_questions", "conduct_interview", "evaluate_interview",
            "analyze_performance", "get_coaching",
        }
