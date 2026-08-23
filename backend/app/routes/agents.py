"""
app/routes/agents.py

Phase 10 — Agentic AI API endpoint.

POST /api/agent/run

Accepts a natural-language message and returns the agent's response.
Authentication is required — user_id is taken from the JWT, never from the request.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.schemas.agent import AgentRequest, AgentResponse
from app.services.agent_service import run_agent

router = APIRouter(prefix="/api/agent", tags=["Agentic AI"])


@router.post(
    "/run",
    response_model=AgentResponse,
    summary="Run the AI Agent",
    description=(
        "Send a natural-language message to the PrepAI agent. "
        "The GPT-4o orchestrator determines intent, calls appropriate tools, "
        "and returns a structured response. "
        "Authentication required."
    ),
)
def run_agent_endpoint(
    request: AgentRequest,
    current_user: dict = Depends(get_current_user),
) -> AgentResponse:
    """
    Execute the agentic AI workflow.

    - Authenticates the user via JWT.
    - user_id is ALWAYS taken from the token (never from the request body).
    - Routes to the appropriate specialist agent via LangGraph.
    - Returns a structured response with task, response text, and optional data.

    Example requests:
        {"message": "What are my biggest weaknesses?"}
        {"message": "Generate 10 questions for my React interview.", "interview_id": "..."}
        {"message": "Analyze my recent interview performance."}
        {"message": "What should I practice for frontend interviews?"}
        {"message": "Evaluate my completed interview.", "interview_id": "..."}
    """
    # user_id comes from the JWT token — never trusted from the LLM or client body
    user_id: str = str(current_user["_id"])

    try:
        result = run_agent(
            message=request.message,
            user_id=user_id,
            interview_id=request.interview_id,
        )
        return result
    except Exception:
        # Catch-all — do not expose internal details
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent service encountered an unexpected error.",
        )
