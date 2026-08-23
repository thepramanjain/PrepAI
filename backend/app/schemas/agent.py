"""
app/schemas/agent.py

Pydantic schemas for Phase 10 Agentic AI API.

Covers:
- Request / response shapes for POST /api/agent/run
- Structured output schema for the Career Coach
"""

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# API Request
# ---------------------------------------------------------------------------

class AgentRequest(BaseModel):
    """
    Request body for the agent run endpoint.

    The user speaks naturally — GPT-4o determines intent.
    No 'task' field required.
    """
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The user's natural-language request.",
        examples=["What are my biggest weaknesses?"],
    )
    interview_id: Optional[str] = Field(
        default=None,
        description="Optional interview ID to scope the request.",
    )


# ---------------------------------------------------------------------------
# Career Coach Output
# ---------------------------------------------------------------------------

class ActionItem(BaseModel):
    """A single coaching action item."""
    task: str = Field(..., description="What the candidate should do.")
    reason: str = Field(..., description="Why this task is important.")
    priority: Literal["low", "medium", "high"] = Field(
        ..., description="Priority level of this action."
    )


class CoachingResult(BaseModel):
    """
    Structured output from the GPT-4o Career Coach.

    Validated by Pydantic after receiving the model response.
    If validation fails, the agent returns a controlled error.
    """
    summary: str = Field(..., description="2–3 sentence overall assessment.")
    strengths: list[str] = Field(default_factory=list, description="Identified strengths.")
    priority_weaknesses: list[str] = Field(
        default_factory=list, description="Most critical weaknesses to address."
    )
    focus_topics: list[str] = Field(
        default_factory=list, description="Topics to prioritize in practice."
    )
    action_plan: list[ActionItem] = Field(
        default_factory=list, description="Ordered list of actionable steps."
    )


# ---------------------------------------------------------------------------
# API Response
# ---------------------------------------------------------------------------

class AgentResponse(BaseModel):
    """
    Standard response from POST /api/agent/run.

    Internal tool calls and raw OpenRouter responses are NOT exposed.
    """
    success: bool = Field(..., description="Whether the agent completed successfully.")
    task: Optional[str] = Field(
        default=None,
        description="The action the orchestrator identified.",
    )
    response: str = Field(..., description="Human-readable response from the agent.")
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional structured data returned by the agent.",
    )
