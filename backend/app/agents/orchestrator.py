"""
app/agents/orchestrator.py

GPT-4o Orchestrator — determines user intent and routes to the correct node.

Implements the full tool-calling loop:
    1. Send user message + tool definitions to GPT-4o.
    2. GPT-4o returns tool_calls.
    3. Parse tool name and arguments.
    4. Execute predefined Python tool (user_id injected from context).
    5. Append tool result to conversation.
    6. Send updated conversation back to GPT-4o.
    7. GPT-4o sets next_action in its final text response.

GPT-4o does NOT execute code — only names which tool to call.
"""

import json
from typing import Any

from openai import RateLimitError, APIConnectionError, APIError

from app.ai.openrouter_client import openrouter_client
from app.ai.openrouter_prompts import ORCHESTRATOR_SYSTEM_PROMPT, build_orchestrator_user_message
from app.ai.tool_calling import (
    TOOL_DEFINITIONS,
    execute_tool,
    parse_tool_calls,
    tool_result_message,
    UnknownToolError,
    ToolError,
)
from app.graph.state import AgentState

# Valid action strings GPT-4o may select
_VALID_ACTIONS = {
    "generate_questions",
    "conduct_interview",
    "evaluate_interview",
    "analyze_performance",
    "get_coaching",
}

_MAX_TOOL_ROUNDS = 5  # Safety: prevent infinite tool-calling loops


def _build_system_message() -> dict:
    return {"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT}


def _action_selection_suffix(interview_id: str | None) -> str:
    """Append routing instruction to every orchestrator turn."""
    ctx = f" The user's current interview ID context is: {interview_id}." if interview_id else ""
    return (
        f"\n\nAfter gathering any necessary information, end your response with exactly one line:\n"
        f"ACTION: <action>\n"
        f"where <action> is one of: generate_questions, conduct_interview, "
        f"evaluate_interview, analyze_performance, get_coaching.{ctx}"
    )


def _parse_action_from_text(text: str) -> str | None:
    """Extract the ACTION: line from GPT-4o's final response."""
    for line in reversed(text.strip().splitlines()):
        line = line.strip()
        if line.startswith("ACTION:"):
            action = line.split("ACTION:", 1)[1].strip().lower()
            if action in _VALID_ACTIONS:
                return action
    return None


def run_orchestrator(state: AgentState) -> dict:
    """
    Orchestrator node implementation.

    Args:
        state: Current AgentState with user_id and messages.

    Returns:
        Partial state update with next_action, final_response, messages, and task.
    """
    user_id: str = state["user_id"]
    interview_id: str | None = state.get("interview_id")
    messages: list[dict] = state.get("messages", [])

    if not openrouter_client.is_configured():
        return {
            "error": "OpenRouter is not configured. Please set OPENROUTER_API_KEY.",
            "next_action": None,
            "final_response": "The AI orchestrator is currently unavailable.",
        }

    # Build the conversation with the action selection suffix
    if not messages:
        return {"error": "No messages in state.", "next_action": None}

    # Append routing instruction to the last user message
    routing_messages = list(messages)
    if routing_messages and routing_messages[-1]["role"] == "user":
        last = routing_messages[-1]
        routing_messages[-1] = {
            "role": "user",
            "content": last["content"] + _action_selection_suffix(interview_id),
        }

    conversation: list[dict] = [_build_system_message()] + routing_messages
    tool_results_collected: dict[str, Any] = state.get("tool_results") or {}

    try:
        # --- Tool-calling loop ---
        for _round in range(_MAX_TOOL_ROUNDS):
            response = openrouter_client.chat_completion(
                messages=conversation,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                temperature=0.2,
            )

            response_message = response.choices[0].message
            tool_calls = parse_tool_calls(response_message)

            if not tool_calls:
                # Final answer — no more tools needed
                final_text = response_message.content or ""
                action = _parse_action_from_text(final_text)

                # Strip the ACTION line from the user-facing response
                visible_lines = [
                    l for l in final_text.splitlines()
                    if not l.strip().startswith("ACTION:")
                ]
                visible_response = "\n".join(visible_lines).strip()

                return {
                    "next_action": action,
                    "task": action,
                    "final_response": visible_response,
                    "messages": conversation,
                    "tool_results": tool_results_collected,
                    "error": None if action else "Could not determine a valid action from the user's request.",
                }

            # Append assistant message with tool calls
            conversation.append({
                "role": "assistant",
                "content": response_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in response_message.tool_calls
                ],
            })

            # Execute each requested tool securely
            for tc in tool_calls:
                try:
                    result = execute_tool(
                        tool_name=tc["name"],
                        tool_args=tc["args"],
                        user_id=user_id,
                    )
                    tool_results_collected[tc["name"]] = result
                    conversation.append(
                        tool_result_message(tc["id"], tc["name"], result)
                    )
                except UnknownToolError as e:
                    conversation.append(
                        tool_result_message(tc["id"], tc["name"], {"error": str(e)})
                    )
                except ToolError as e:
                    conversation.append(
                        tool_result_message(tc["id"], tc["name"], {"error": str(e)})
                    )

        # Exceeded max rounds — return what we have
        return {
            "next_action": None,
            "task": None,
            "final_response": "The agent could not complete the request after multiple attempts.",
            "messages": conversation,
            "tool_results": tool_results_collected,
            "error": "Exceeded maximum tool-calling rounds.",
        }

    except RateLimitError:
        return {
            "error": "OpenRouter rate limit exceeded. Please try again later.",
            "next_action": None,
            "final_response": "The AI service is currently rate-limited. Please try again shortly.",
        }
    except APIConnectionError:
        return {
            "error": "Could not connect to OpenRouter.",
            "next_action": None,
            "final_response": "Unable to reach the AI service. Please check your connection.",
        }
    except APIError as e:
        return {
            "error": f"OpenRouter API error: {type(e).__name__}",
            "next_action": None,
            "final_response": "The AI service returned an error. Please try again.",
        }
    except Exception as e:
        return {
            "error": f"Unexpected orchestrator error: {type(e).__name__}",
            "next_action": None,
            "final_response": "An unexpected error occurred. Please try again.",
        }
