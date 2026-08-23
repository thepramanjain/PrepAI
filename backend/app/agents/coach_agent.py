"""
app/agents/coach_agent.py

Career Coach Agent — uses GPT-4o for personalized career coaching.

Flow:
    1. Gather coaching context (analytics, weaknesses, topics) via coaching_tools.
    2. Send context to GPT-4o with the career coach system prompt.
    3. GPT-4o returns structured JSON matching CoachingResult schema.
    4. Validate with Pydantic.
    5. Return structured coaching result.

GPT-4o only interprets data — Python calculates all analytics.
"""

import json

from openai import RateLimitError, APIConnectionError, APIError

from app.ai.openrouter_client import openrouter_client
from app.ai.openrouter_prompts import CAREER_COACH_SYSTEM_PROMPT, build_coaching_user_prompt
from app.ai.tool_calling import execute_tool, ToolError
from app.schemas.agent import CoachingResult
from app.graph.state import AgentState


def run_coach_agent(state: AgentState) -> dict:
    """
    Execute the career coaching workflow.

    Args:
        state: Current AgentState with user_id.

    Returns:
        Partial state update with coach_result, analytics, and final_response.
    """
    user_id: str = state["user_id"]
    tool_results: dict = state.get("tool_results") or {}

    if not openrouter_client.is_configured():
        return {
            "error": "OpenRouter is not configured.",
            "final_response": "Career coaching is currently unavailable. Please configure the AI service.",
        }

    # --- Step 1: Gather coaching context ---
    if "get_coaching_context" in tool_results:
        coaching_data = tool_results["get_coaching_context"]
    else:
        try:
            coaching_data = execute_tool(
                tool_name="get_coaching_context",
                tool_args={},
                user_id=user_id,
            )
            tool_results["get_coaching_context"] = coaching_data
        except ToolError as e:
            return {
                "error": str(e),
                "final_response": f"Could not gather performance data for coaching: {e}",
            }

    # Check if there's enough data to coach
    overview = coaching_data.get("overview", {})
    if overview.get("evaluated_interviews", 0) == 0:
        return {
            "analytics": coaching_data,
            "tool_results": tool_results,
            "final_response": (
                "You haven't completed and evaluated any interviews yet. "
                "Complete at least one interview and evaluate it to receive personalized coaching."
            ),
        }

    # --- Step 2: Call GPT-4o Career Coach ---
    messages = [
        {"role": "system", "content": CAREER_COACH_SYSTEM_PROMPT},
        {"role": "user", "content": build_coaching_user_prompt(coaching_data)},
    ]

    try:
        response = openrouter_client.chat_completion(
            messages=messages,
            tools=None,  # No tool calling for coach — pure generation
            temperature=0.5,
            max_tokens=1500,
        )

        raw_text = response.choices[0].message.content or ""

        # --- Step 3: Parse and validate structured output ---
        try:
            # Strip any accidental markdown fences
            clean_text = raw_text.strip()
            if clean_text.startswith("```"):
                lines = clean_text.splitlines()
                clean_text = "\n".join(lines[1:-1]).strip()

            parsed = json.loads(clean_text)
            coach_result = CoachingResult(**parsed)
        except (json.JSONDecodeError, Exception) as parse_err:
            # Fallback: return raw response without structured validation
            return {
                "analytics": coaching_data,
                "tool_results": tool_results,
                "final_response": raw_text,
                "error": f"Could not parse structured coaching output: {type(parse_err).__name__}",
            }

        return {
            "analytics": coaching_data,
            "coach_result": coach_result.model_dump(),
            "tool_results": tool_results,
            "final_response": coach_result.summary,
        }

    except RateLimitError:
        return {
            "error": "OpenRouter rate limit exceeded.",
            "final_response": "Career coaching is temporarily unavailable due to rate limits. Please try again.",
        }
    except APIConnectionError:
        return {
            "error": "Could not connect to OpenRouter.",
            "final_response": "Unable to reach the coaching service. Please check your connection.",
        }
    except APIError as e:
        return {
            "error": f"OpenRouter API error: {type(e).__name__}",
            "final_response": "The coaching service returned an error. Please try again.",
        }
