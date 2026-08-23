"""
tests/test_agents.py

Tests for agent implementations (Phase 10).

All OpenRouter and Gemini calls are mocked.
No real API calls are made.
"""

import json
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_response(content="", tool_calls=None):
    """Create a mocked OpenAI chat completion response."""
    mock_message = MagicMock()
    mock_message.content = content
    mock_message.tool_calls = tool_calls or []

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


def _make_tool_call(name, args_dict, call_id="call_001"):
    tc = MagicMock()
    tc.id = call_id
    tc.function.name = name
    tc.function.arguments = json.dumps(args_dict)
    return tc


# ---------------------------------------------------------------------------
# 1. Orchestrator Intent Detection
# ---------------------------------------------------------------------------

class TestOrchestratorIntent:
    def _run_orchestrator(self, response_content):
        """Helper to run the orchestrator with a mocked GPT-4o response."""
        mock_response = _make_mock_response(content=response_content)

        with patch("app.agents.orchestrator.openrouter_client") as mock_client:
            mock_client.is_configured.return_value = True
            mock_client.chat_completion.return_value = mock_response

            from app.agents.orchestrator import run_orchestrator
            state = {
                "user_id": "user123",
                "interview_id": None,
                "messages": [{"role": "user", "content": "test message"}],
                "tool_results": {},
            }
            return run_orchestrator(state)

    def test_coaching_intent(self):
        """Orchestrator should detect get_coaching intent."""
        result = self._run_orchestrator(
            "I'll gather your performance data.\nACTION: get_coaching"
        )
        assert result.get("next_action") == "get_coaching"

    def test_analytics_intent(self):
        """Orchestrator should detect analyze_performance intent."""
        result = self._run_orchestrator(
            "Let me check your scores.\nACTION: analyze_performance"
        )
        assert result.get("next_action") == "analyze_performance"

    def test_generate_questions_intent(self):
        """Orchestrator should detect generate_questions intent."""
        result = self._run_orchestrator(
            "Generating interview questions.\nACTION: generate_questions"
        )
        assert result.get("next_action") == "generate_questions"

    def test_evaluate_interview_intent(self):
        """Orchestrator should detect evaluate_interview intent."""
        result = self._run_orchestrator(
            "I'll evaluate your interview.\nACTION: evaluate_interview"
        )
        assert result.get("next_action") == "evaluate_interview"

    def test_invalid_action_returns_none(self):
        """Orchestrator should return None for unrecognized actions."""
        result = self._run_orchestrator("I'm not sure what to do. ACTION: hack_system")
        assert result.get("next_action") is None

    def test_no_api_key_returns_error(self):
        """Orchestrator should handle missing API key gracefully."""
        with patch("app.agents.orchestrator.openrouter_client") as mock_client:
            mock_client.is_configured.return_value = False

            from app.agents.orchestrator import run_orchestrator
            result = run_orchestrator({
                "user_id": "user123",
                "messages": [{"role": "user", "content": "test"}],
                "tool_results": {},
            })
            assert result.get("error") is not None
            assert result.get("next_action") is None


# ---------------------------------------------------------------------------
# 2. Question Agent
# ---------------------------------------------------------------------------

class TestQuestionAgent:
    def test_reuses_orchestrator_result(self):
        """Question agent should reuse tool results from orchestrator."""
        from app.agents.question_agent import run_question_agent

        state = {
            "user_id": "user123",
            "interview_id": "interview_abc",
            "tool_results": {
                "generate_questions": {
                    "count": 5,
                    "questions": [{"question": "Q1"}, {"question": "Q2"}],
                }
            },
        }
        result = run_question_agent(state)
        assert result.get("questions") is not None
        assert len(result["questions"]) == 2

    def test_error_without_interview_id(self):
        """Question agent should return error if no interview_id."""
        from app.agents.question_agent import run_question_agent

        state = {
            "user_id": "user123",
            "interview_id": None,
            "tool_results": {},
        }
        result = run_question_agent(state)
        assert "error" in result or "final_response" in result


# ---------------------------------------------------------------------------
# 3. Evaluation Agent
# ---------------------------------------------------------------------------

class TestEvaluationAgent:
    def test_reuses_orchestrator_feedback(self):
        """Evaluation agent should reuse feedback from orchestrator."""
        from app.agents.evaluation_agent import run_evaluation_agent

        state = {
            "user_id": "user123",
            "interview_id": "interview_abc",
            "tool_results": {
                "get_feedback": {
                    "overall_score": 78,
                    "summary": "Good performance.",
                    "strengths": ["Clear communication"],
                    "weaknesses": ["System design depth"],
                    "category_scores": {
                        "technical": 75,
                        "communication": 85,
                        "problem_solving": 70,
                        "relevance": 80,
                    },
                }
            },
        }
        result = run_evaluation_agent(state)
        assert result.get("feedback", {}).get("overall_score") == 78

    def test_no_interview_id_returns_error(self):
        """Evaluation agent should gracefully handle missing interview_id."""
        from app.agents.evaluation_agent import run_evaluation_agent

        state = {
            "user_id": "user123",
            "interview_id": None,
            "tool_results": {},
        }
        result = run_evaluation_agent(state)
        assert "error" in result or "final_response" in result


# ---------------------------------------------------------------------------
# 4. Analytics Agent
# ---------------------------------------------------------------------------

class TestAnalyticsAgent:
    def test_reuses_orchestrator_analytics(self):
        """Analytics agent should reuse analytics from orchestrator."""
        from app.agents.analytics_agent import run_analytics_agent

        analytics_data = {
            "overview": {
                "average_score": 72.5,
                "evaluated_interviews": 3,
                "latest_score": 80,
            },
            "improvement": {"trend": "improving"},
        }
        state = {
            "user_id": "user123",
            "tool_results": {"get_analytics": analytics_data},
        }
        result = run_analytics_agent(state)
        assert result.get("analytics") is not None

    def test_fetches_analytics_when_not_cached(self):
        """Analytics agent should fetch analytics when not in tool_results."""
        mock_analytics = {
            "overview": {"average_score": 65, "evaluated_interviews": 2},
            "improvement": {"trend": "stable"},
        }
        mock_improvement = {"trend": "stable", "score_difference": 1.0}

        with patch("app.tools.analytics_tools.get_full_analytics", return_value=mock_analytics):
            with patch("app.tools.analytics_tools.get_improvement", return_value=mock_improvement):
                from app.agents.analytics_agent import run_analytics_agent
                result = run_analytics_agent({
                    "user_id": "user123",
                    "tool_results": {},
                })

        assert result.get("analytics") is not None


# ---------------------------------------------------------------------------
# 5. Career Coach Agent
# ---------------------------------------------------------------------------

class TestCoachAgent:
    def _make_valid_coaching_json(self):
        return json.dumps({
            "summary": "Good overall performance with room to improve system design.",
            "strengths": ["Clear communication", "Problem decomposition"],
            "priority_weaknesses": ["System design", "Algorithm complexity"],
            "focus_topics": ["LRU Cache", "Graph algorithms"],
            "action_plan": [
                {"task": "Practice system design", "reason": "Weak area", "priority": "high"},
                {"task": "Solve 5 graph problems", "reason": "Low topic score", "priority": "medium"},
            ],
        })

    def test_successful_coaching_response(self):
        """Coach agent should return structured CoachingResult on success."""
        coaching_context = {
            "overview": {"evaluated_interviews": 3, "average_score": 70},
            "top_weaknesses": ["System design"],
            "top_strengths": ["Communication"],
        }

        mock_response = _make_mock_response(content=self._make_valid_coaching_json())

        with patch("app.agents.coach_agent.openrouter_client") as mock_client:
            mock_client.is_configured.return_value = True
            mock_client.chat_completion.return_value = mock_response

            from app.agents.coach_agent import run_coach_agent
            result = run_coach_agent({
                "user_id": "user123",
                "tool_results": {"get_coaching_context": coaching_context},
            })

        assert result.get("coach_result") is not None
        coach = result["coach_result"]
        assert "summary" in coach
        assert isinstance(coach["strengths"], list)
        assert isinstance(coach["action_plan"], list)

    def test_no_evaluated_interviews_skips_llm(self):
        """Coach agent should skip GPT-4o if no evaluated interviews exist."""
        coaching_context = {
            "overview": {"evaluated_interviews": 0, "average_score": None},
        }

        with patch("app.agents.coach_agent.openrouter_client") as mock_client:
            mock_client.is_configured.return_value = True

            from app.agents.coach_agent import run_coach_agent
            result = run_coach_agent({
                "user_id": "user123",
                "tool_results": {"get_coaching_context": coaching_context},
            })

        # Should not have called GPT-4o
        mock_client.chat_completion.assert_not_called()
        assert "final_response" in result

    def test_invalid_json_handled_gracefully(self):
        """Coach agent should handle invalid JSON output gracefully."""
        mock_response = _make_mock_response(content="This is not valid JSON at all.")

        with patch("app.agents.coach_agent.openrouter_client") as mock_client:
            mock_client.is_configured.return_value = True
            mock_client.chat_completion.return_value = mock_response

            from app.agents.coach_agent import run_coach_agent
            result = run_coach_agent({
                "user_id": "user123",
                "tool_results": {
                    "get_coaching_context": {
                        "overview": {"evaluated_interviews": 2, "average_score": 70}
                    }
                },
            })

        # Should return the raw text without crashing
        assert "final_response" in result
        assert result.get("coach_result") is None  # Not validated
