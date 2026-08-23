"""
app/ai/tool_calling.py

Central tool registry and secure tool execution engine.

Security model:
- GPT-4o may only REQUEST a tool by name.
- The backend EXECUTES the tool via this module.
- user_id is ALWAYS injected from the authenticated backend context.
- Unknown tools are rejected before any code runs.
- No eval(), exec(), shell commands, or arbitrary DB queries are permitted.

Tool flow:
    GPT-4o returns tool_calls
        ↓
    parse_tool_calls() extracts name + arguments
        ↓
    execute_tool(name, args, user_id) validates and runs the Python function
        ↓
    Result is appended to conversation and returned to GPT-4o
"""

import json
from typing import Any

# ---------------------------------------------------------------------------
# Tool JSON-Schema Definitions
# (sent to GPT-4o so it knows what tools are available)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict] = [
    # ---- Question Tools ----
    {
        "type": "function",
        "function": {
            "name": "generate_questions",
            "description": (
                "Generate AI interview questions for a specific interview. "
                "Uses the existing Gemini question generation pipeline."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "interview_id": {
                        "type": "string",
                        "description": "The MongoDB ObjectId string of the interview.",
                    },
                    "question_count": {
                        "type": "integer",
                        "description": "Number of questions to generate (1–20).",
                        "minimum": 1,
                        "maximum": 20,
                    },
                },
                "required": ["interview_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_questions",
            "description": "Retrieve existing questions for an interview.",
            "parameters": {
                "type": "object",
                "properties": {
                    "interview_id": {
                        "type": "string",
                        "description": "The MongoDB ObjectId string of the interview.",
                    },
                },
                "required": ["interview_id"],
            },
        },
    },
    # ---- Interview Tools ----
    {
        "type": "function",
        "function": {
            "name": "get_interview",
            "description": "Get metadata for a specific interview (title, role, status, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "interview_id": {
                        "type": "string",
                        "description": "The MongoDB ObjectId string of the interview.",
                    },
                },
                "required": ["interview_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_interview_state",
            "description": (
                "Get the current state of an interview session: "
                "current question number, total questions, and completion status."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "interview_id": {
                        "type": "string",
                        "description": "The MongoDB ObjectId string of the interview.",
                    },
                },
                "required": ["interview_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_interview",
            "description": "Get the user's most recently created or updated interview.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    # ---- Evaluation Tools ----
    {
        "type": "function",
        "function": {
            "name": "evaluate_interview",
            "description": (
                "Trigger AI evaluation of a completed interview using Gemini. "
                "Returns overall score, category scores, strengths, and weaknesses."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "interview_id": {
                        "type": "string",
                        "description": "The MongoDB ObjectId string of the completed interview.",
                    },
                },
                "required": ["interview_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_feedback",
            "description": "Retrieve stored evaluation feedback for an interview.",
            "parameters": {
                "type": "object",
                "properties": {
                    "interview_id": {
                        "type": "string",
                        "description": "The MongoDB ObjectId string of the interview.",
                    },
                },
                "required": ["interview_id"],
            },
        },
    },
    # ---- Analytics Tools ----
    {
        "type": "function",
        "function": {
            "name": "get_analytics",
            "description": (
                "Get the user's full analytics dashboard: overview, score trend, "
                "category performance, top topics, strengths, and weaknesses."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_score_trend",
            "description": "Get chronological score data across all evaluated interviews.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_category_performance",
            "description": (
                "Get average scores per evaluation category: "
                "technical, communication, problem_solving, relevance."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_topic_performance",
            "description": "Get average scores for each topic across all interviews.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_strengths",
            "description": "Get the user's most frequently identified interview strengths.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weaknesses",
            "description": "Get the user's most frequently identified interview weaknesses.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_improvement",
            "description": (
                "Analyze whether the user is improving, declining, or stable "
                "across their interview history."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    # ---- Resume Tools ----
    {
        "type": "function",
        "function": {
            "name": "get_resume",
            "description": "Retrieve the authenticated user's resume text and metadata.",
            "parameters": {
                "type": "object",
                "properties": {
                    "resume_id": {
                        "type": "string",
                        "description": "The MongoDB ObjectId string of the resume.",
                    },
                },
                "required": ["resume_id"],
            },
        },
    },
    # ---- Coaching Tools ----
    {
        "type": "function",
        "function": {
            "name": "get_coaching_context",
            "description": (
                "Aggregate analytics, weaknesses, and topic performance into a "
                "concise coaching payload for career advice generation."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]

# ---------------------------------------------------------------------------
# Tool Registry — name → Python callable
# Built lazily to avoid circular imports at module load time.
# ---------------------------------------------------------------------------

def _build_registry() -> dict[str, Any]:
    """Import and register all tool functions. Called once on first use."""
    from app.tools.question_tools import generate_questions_tool, get_questions_tool
    from app.tools.interview_tools import (
        get_interview_tool,
        get_interview_state_tool,
        get_recent_interview_tool,
    )
    from app.tools.evaluation_tools import evaluate_interview_tool, get_feedback_tool
    from app.tools.analytics_tools import (
        get_analytics_tool,
        get_score_trend_tool,
        get_category_performance_tool,
        get_topic_performance_tool,
        get_strengths_tool,
        get_weaknesses_tool,
        get_improvement_tool,
    )
    from app.tools.resume_tools import get_resume_tool
    from app.tools.coaching_tools import get_coaching_context_tool

    return {
        "generate_questions": generate_questions_tool,
        "get_questions": get_questions_tool,
        "get_interview": get_interview_tool,
        "get_interview_state": get_interview_state_tool,
        "get_recent_interview": get_recent_interview_tool,
        "evaluate_interview": evaluate_interview_tool,
        "get_feedback": get_feedback_tool,
        "get_analytics": get_analytics_tool,
        "get_score_trend": get_score_trend_tool,
        "get_category_performance": get_category_performance_tool,
        "get_topic_performance": get_topic_performance_tool,
        "get_strengths": get_strengths_tool,
        "get_weaknesses": get_weaknesses_tool,
        "get_improvement": get_improvement_tool,
        "get_resume": get_resume_tool,
        "get_coaching_context": get_coaching_context_tool,
    }


_REGISTRY: dict[str, Any] | None = None


def _get_registry() -> dict[str, Any]:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_registry()
    return _REGISTRY


# ---------------------------------------------------------------------------
# Tool Execution
# ---------------------------------------------------------------------------

class ToolError(Exception):
    """Raised when a tool call fails in a controlled way."""
    pass


class UnknownToolError(ToolError):
    """Raised when GPT-4o requests a tool that is not registered."""
    pass


def execute_tool(tool_name: str, tool_args: dict, user_id: str) -> Any:
    """
    Securely execute a registered tool.

    SECURITY RULES enforced here:
    - Only tools in the registry may be called.
    - user_id is ALWAYS injected from the backend context (never trusted from args).
    - No eval(), exec(), or shell access is possible through this interface.

    Args:
        tool_name:  The name of the tool GPT-4o requested.
        tool_args:  The arguments GPT-4o supplied (validated inside the tool).
        user_id:    The authenticated user's ID (from the backend session).

    Returns:
        The tool's return value (must be JSON-serializable).

    Raises:
        UnknownToolError: Tool name not in registry.
        ToolError:        Tool execution failed (wrapped for GPT-4o).
    """
    registry = _get_registry()

    if tool_name not in registry:
        raise UnknownToolError(
            f"Tool '{tool_name}' is not registered. "
            "Only approved tools may be called."
        )

    # Strip any user_id the LLM might have injected — always use backend value
    tool_args.pop("user_id", None)

    try:
        return registry[tool_name](user_id=user_id, **tool_args)
    except (TypeError, ValueError) as e:
        raise ToolError(f"Invalid arguments for tool '{tool_name}': {e}") from e
    except Exception as e:
        raise ToolError(f"Tool '{tool_name}' execution failed: {e}") from e


def parse_tool_calls(response_message) -> list[dict]:
    """
    Extract tool calls from a GPT-4o response message.

    Returns a list of dicts:
        [{"id": "...", "name": "...", "args": {...}}, ...]
    """
    if not response_message.tool_calls:
        return []

    result = []
    for tc in response_message.tool_calls:
        try:
            args = json.loads(tc.function.arguments)
        except json.JSONDecodeError:
            args = {}
        result.append({
            "id": tc.id,
            "name": tc.function.name,
            "args": args,
        })
    return result


def tool_result_message(tool_call_id: str, tool_name: str, result: Any) -> dict:
    """
    Format a tool result for insertion into the conversation messages list.
    Converts non-string results to JSON for the LLM.
    """
    if isinstance(result, str):
        content = result
    else:
        content = json.dumps(result, default=str)

    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "name": tool_name,
        "content": content,
    }
