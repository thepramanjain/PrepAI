"""
app/graph/state.py

LangGraph state definition for the PrepAI agent workflow.

Uses TypedDict for strong typing compatible with LangGraph's StateGraph.
All fields are Optional so nodes can update only what they touch.
"""

from typing import Any, Optional
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    """
    Shared state object passed through every node in the LangGraph workflow.

    Fields:
        user_id         Authenticated user ID (set once, never modified by LLM).
        task            Identified action (e.g. "get_coaching", "generate_questions").
        interview_id    Optional interview context for the current request.

        role            Interview role (e.g. "Frontend Engineer").
        experience_level Candidate experience level.
        skills          List of candidate skills.
        interview_type  Type of interview (Technical, Behavioral, etc.).
        difficulty      Interview difficulty level.

        resume_context  Extracted resume text excerpt (if relevant).
        job_description Job description text (if relevant).

        questions       Questions retrieved or generated.
        current_question Current active question in an interview session.
        responses       User responses for an interview.
        feedback        Evaluation feedback document.
        analytics       Analytics data retrieved for the user.

        coach_result    Structured CoachingResult from the career coach.

        next_action     Routing decision from the orchestrator node.
        tool_results    Accumulated tool results from the current workflow.
        messages        OpenAI message history for multi-turn tool calling.
        error           Error message if any step fails.

        final_response  Human-readable final answer to return to the user.
    """

    # --- Core context ---
    user_id: str
    task: Optional[str]
    interview_id: Optional[str]

    # --- Interview metadata (populated as needed) ---
    role: Optional[str]
    experience_level: Optional[str]
    skills: Optional[list[str]]
    interview_type: Optional[str]
    difficulty: Optional[str]

    # --- Content context ---
    resume_context: Optional[str]
    job_description: Optional[str]

    # --- Agent working data ---
    questions: Optional[list[dict]]
    current_question: Optional[dict]
    responses: Optional[list[dict]]
    feedback: Optional[dict]
    analytics: Optional[dict]

    # --- Coach output ---
    coach_result: Optional[dict]

    # --- Routing & internal state ---
    next_action: Optional[str]
    tool_results: Optional[dict[str, Any]]
    messages: Optional[list[dict]]
    error: Optional[str]

    # --- Final output ---
    final_response: Optional[str]
