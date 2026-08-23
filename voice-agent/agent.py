"""
voice-agent/agent.py

PrepAI Voice Interview Agent — Phase 9

Architecture:
  LiveKit Agents 1.7 + Gemini Live API (speech-to-speech)

  Candidate audio → LiveKit Room → AgentSession
                                        ↓
                              google.realtime.RealtimeModel
                              (gemini-2.5-flash-native-audio-preview)
                                        ↓
                              AI audio → LiveKit Room → Candidate

Room metadata convention:
  The PrepAI backend encodes interview context in LiveKit room metadata
  when creating the participant token. The agent reads:
    - interview_id
    - jwt_token  (candidate's token for backend API calls)

Run locally:
  python agent.py dev               # connect to LiveKit Cloud dev room
  python agent.py start             # production mode

Environment (voice-agent/.env):
  LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET
  GOOGLE_API_KEY (or GEMINI_API_KEY)
  PREPAI_BACKEND_URL

Package versions (livekit-agents ~=1.7, livekit-plugins-google bundled):
  pip install "livekit-agents[google]>=1.7,<2.0"
"""

from __future__ import annotations

import asyncio
import json
import logging
import os

from dotenv import load_dotenv

load_dotenv()

# LiveKit Agents 1.7 imports
from livekit.agents import (  # type: ignore[import-untyped]
    Agent,
    AgentSession,
    JobContext,
    RoomInputOptions,
    WorkerOptions,
    cli,
)
from livekit.plugins import google  # type: ignore[import-untyped]

from interview_context import InterviewContext
from prompts import (
    build_greeting_instruction,
    build_next_question_instruction,
    build_system_prompt,
    CLOSING_PROMPT,
    FOLLOW_UP_PROMPT,
)
from tools import make_tools
from transcript import TranscriptManager

logger = logging.getLogger(__name__)

BACKEND_URL = os.getenv("PREPAI_BACKEND_URL", "http://localhost:8000")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-native-audio-preview")


# ---------------------------------------------------------------------------
# Room metadata parser
# ---------------------------------------------------------------------------

def _parse_room_metadata(metadata: str) -> dict:
    """
    Parse LiveKit room metadata injected by the PrepAI backend.
    Expected format: JSON string with interview_id and jwt_token.
    """
    if not metadata:
        return {}
    try:
        return json.loads(metadata)
    except json.JSONDecodeError:
        logger.warning("Could not parse room metadata: %r", metadata)
        return {}


# ---------------------------------------------------------------------------
# Agent entrypoint
# ---------------------------------------------------------------------------

async def entrypoint(ctx: JobContext) -> None:
    """
    Main agent lifecycle function.
    Called by LiveKit Workers when a new room job is assigned.
    """
    logger.info("PrepAI voice agent starting for room: %s", ctx.room.name)

    # --- Connect to the room ---
    await ctx.connect()

    # --- Parse room metadata for interview context ---
    metadata = _parse_room_metadata(ctx.room.metadata or "")
    interview_id = metadata.get("interview_id", "")
    jwt_token = metadata.get("jwt_token", "")

    if not interview_id or not jwt_token:
        logger.error(
            "Missing interview_id or jwt_token in room metadata. "
            "Ensure the PrepAI backend sets metadata when creating the room."
        )
        return

    # --- Load interview context from backend ---
    try:
        context = await InterviewContext.load_from_backend(
            backend_url=BACKEND_URL,
            interview_id=interview_id,
            jwt_token=jwt_token,
        )
    except Exception as exc:
        logger.error("Failed to load interview context: %s", exc)
        return

    if not context.questions:
        logger.error("Interview %s has no questions — cannot start voice interview.", interview_id)
        return

    first_question = context.current_question
    if not first_question:
        logger.error("No current question found for interview %s.", interview_id)
        return

    # --- Set up transcript manager ---
    transcript = TranscriptManager(
        interview_id=interview_id,
        backend_url=BACKEND_URL,
        jwt_token=jwt_token,
    )

    # --- Set up tools ---
    tools = make_tools(
        interview_id=interview_id,
        backend_url=BACKEND_URL,
        jwt_token=jwt_token,
    )

    # --- Build system prompt ---
    system_prompt = build_system_prompt(
        interview_context_str=context.to_system_prompt_context(),
        current_question=first_question.text,
    )

    # --- Create AgentSession with Gemini Live (speech-to-speech) ---
    # gemini-2.5-flash-native-audio-preview handles STT + LLM + TTS natively.
    # No separate Deepgram/Whisper or TTS service needed.
    session = AgentSession(
        llm=google.realtime.RealtimeModel(
            model=GEMINI_MODEL,
            voice="Puck",           # Natural, professional voice
            instructions=system_prompt,
            tools=tools,
        ),
    )

    # --- Register transcript event handler ---
    # livekit-agents 1.7 fires events on transcription availability
    @session.on("user_speech_committed")
    def on_candidate_speech(msg):
        """Called when candidate's speech is finalized."""
        if msg and hasattr(msg, "content") and msg.content:
            text = str(msg.content)
            asyncio.ensure_future(transcript.add_and_sync("candidate", text))
            logger.debug("Candidate: %s", text[:100])

    @session.on("agent_speech_committed")
    def on_agent_speech(msg):
        """Called when agent's speech is finalized."""
        if msg and hasattr(msg, "content") and msg.content:
            text = str(msg.content)
            asyncio.ensure_future(transcript.add_and_sync("interviewer", text))
            logger.debug("Interviewer: %s", text[:100])

    # --- Start the session ---
    await session.start(
        room=ctx.room,
        agent=Agent(instructions=system_prompt),
        room_input_options=RoomInputOptions(),
    )

    # --- Open greeting ---
    greeting_instruction = build_greeting_instruction(
        total_questions=context.total_questions,
        first_question=first_question.text,
    )
    await session.generate_reply(instructions=greeting_instruction)

    logger.info(
        "PrepAI voice interview started. Interview: %s | Questions: %d",
        interview_id,
        context.total_questions,
    )

    # The AgentSession runs until the room is disconnected or the agent
    # calls end_interview() via the function tool. LiveKit Agents manages
    # the lifecycle automatically.


# ---------------------------------------------------------------------------
# Worker entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            # agent_name can be used for targeted job dispatch if needed
        )
    )
