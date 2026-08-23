"""
tests/test_tools.py

Tests for the tool registry and tool execution security (Phase 10).

Covers:
- Tool registration
- Valid tool calls
- Invalid / unknown tool calls
- Ownership enforcement
- Argument validation
"""

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# 1. Tool Definitions
# ---------------------------------------------------------------------------

class TestToolDefinitions:
    def test_all_tools_have_type_function(self):
        """Every tool definition must have type='function'."""
        from app.ai.tool_calling import TOOL_DEFINITIONS
        for tool in TOOL_DEFINITIONS:
            assert tool["type"] == "function"

    def test_all_tools_have_name(self):
        """Every tool definition must have a non-empty name."""
        from app.ai.tool_calling import TOOL_DEFINITIONS
        names = [t["function"]["name"] for t in TOOL_DEFINITIONS]
        assert all(n for n in names)

    def test_expected_tools_present(self):
        """Key tools must be present in the definitions."""
        from app.ai.tool_calling import TOOL_DEFINITIONS
        names = {t["function"]["name"] for t in TOOL_DEFINITIONS}
        expected = {
            "generate_questions", "get_questions",
            "get_interview", "get_interview_state", "get_recent_interview",
            "evaluate_interview", "get_feedback",
            "get_analytics", "get_score_trend", "get_category_performance",
            "get_topic_performance", "get_strengths", "get_weaknesses", "get_improvement",
            "get_resume", "get_coaching_context",
        }
        assert expected.issubset(names)

    def test_no_dangerous_tools_registered(self):
        """Dangerous tool names must never be in the registry."""
        from app.ai.tool_calling import TOOL_DEFINITIONS
        names = {t["function"]["name"] for t in TOOL_DEFINITIONS}
        forbidden = {"run_python", "execute_mongodb", "shell", "eval", "exec", "os_command"}
        assert names.isdisjoint(forbidden)


# ---------------------------------------------------------------------------
# 2. Unknown Tool Rejection
# ---------------------------------------------------------------------------

class TestUnknownToolRejection:
    def test_unknown_tool_raises_error(self):
        """execute_tool() must raise UnknownToolError for unregistered tools."""
        from app.ai.tool_calling import execute_tool, UnknownToolError

        with pytest.raises(UnknownToolError):
            execute_tool("run_arbitrary_python", {}, user_id="user123")

    def test_shell_tool_rejected(self):
        """'shell' must be rejected."""
        from app.ai.tool_calling import execute_tool, UnknownToolError
        with pytest.raises(UnknownToolError):
            execute_tool("shell", {"cmd": "ls"}, user_id="user123")

    def test_exec_tool_rejected(self):
        """'exec' must be rejected."""
        from app.ai.tool_calling import execute_tool, UnknownToolError
        with pytest.raises(UnknownToolError):
            execute_tool("exec", {"code": "import os"}, user_id="user123")

    def test_mongodb_query_tool_rejected(self):
        """'execute_mongodb' must be rejected."""
        from app.ai.tool_calling import execute_tool, UnknownToolError
        with pytest.raises(UnknownToolError):
            execute_tool("execute_mongodb", {"query": "{}"}, user_id="user123")


# ---------------------------------------------------------------------------
# 3. User ID Injection (Ownership Enforcement)
# ---------------------------------------------------------------------------

class TestOwnershipEnforcement:
    def test_user_id_from_llm_args_is_stripped(self):
        """user_id passed in tool_args must be removed before execution."""
        captured_kwargs = {}

        def mock_tool(user_id, **kwargs):
            captured_kwargs["user_id"] = user_id
            captured_kwargs["kwargs"] = kwargs
            return {"ok": True}

        from app.ai import tool_calling as tc
        # Temporarily register a mock tool
        registry = tc._get_registry()
        registry["__test_ownership__"] = mock_tool

        try:
            tc.execute_tool(
                "__test_ownership__",
                {"user_id": "attacker_id", "other": "value"},
                user_id="real_user_id",
            )
            assert captured_kwargs["user_id"] == "real_user_id"
            assert "user_id" not in captured_kwargs["kwargs"]
        finally:
            registry.pop("__test_ownership__", None)


# ---------------------------------------------------------------------------
# 4. Valid Tool Call (Analytics — mocked)
# ---------------------------------------------------------------------------

class TestValidToolCall:
    def test_get_analytics_tool_called_with_correct_user(self):
        """get_analytics tool should be called with the backend user_id."""
        from app.ai.tool_calling import execute_tool

        mock_result = {"overview": {"average_score": 75}}

        with patch("app.tools.analytics_tools.get_full_analytics", return_value=mock_result):
            result = execute_tool("get_analytics", {}, user_id="user123")

        assert result == mock_result

    def test_get_improvement_tool(self):
        """get_improvement tool should return improvement data."""
        from app.ai.tool_calling import execute_tool

        mock_result = {"trend": "improving", "score_difference": 5.0}

        with patch("app.tools.analytics_tools.get_improvement", return_value=mock_result):
            result = execute_tool("get_improvement", {}, user_id="user123")

        assert result["trend"] == "improving"


# ---------------------------------------------------------------------------
# 5. Tool Result Message Formatting
# ---------------------------------------------------------------------------

class TestToolResultMessage:
    def test_string_result(self):
        """String results should be returned as-is."""
        from app.ai.tool_calling import tool_result_message
        msg = tool_result_message("tc_123", "get_analytics", "some string")
        assert msg["content"] == "some string"
        assert msg["role"] == "tool"

    def test_dict_result_is_json_serialized(self):
        """Dict results should be JSON-serialized."""
        import json
        from app.ai.tool_calling import tool_result_message
        data = {"score": 75, "trend": "improving"}
        msg = tool_result_message("tc_456", "get_analytics", data)
        parsed = json.loads(msg["content"])
        assert parsed["score"] == 75


# ---------------------------------------------------------------------------
# 6. Parse Tool Calls
# ---------------------------------------------------------------------------

class TestParseToolCalls:
    def test_empty_tool_calls(self):
        """No tool_calls should return empty list."""
        from app.ai.tool_calling import parse_tool_calls
        msg = MagicMock()
        msg.tool_calls = None
        assert parse_tool_calls(msg) == []

    def test_single_tool_call_parsed(self):
        """A single tool call should be parsed correctly."""
        import json
        from app.ai.tool_calling import parse_tool_calls

        tc = MagicMock()
        tc.id = "call_abc"
        tc.function.name = "get_analytics"
        tc.function.arguments = json.dumps({})

        msg = MagicMock()
        msg.tool_calls = [tc]

        result = parse_tool_calls(msg)
        assert len(result) == 1
        assert result[0]["name"] == "get_analytics"
        assert result[0]["id"] == "call_abc"
