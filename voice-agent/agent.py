"""
PrepAI Voice Interview Agent
LiveKit Agents 1.8.10 + Gemini Live API (Native Speech-to-Speech)

Architecture:
    Candidate audio
        -> LiveKit Room
        -> AgentSession
        -> Google Gemini Live API (gemini-3.8-live)
        -> AI audio response
        -> LiveKit Room
        -> Candidate

Interview context is received through LiveKit room metadata:
    - interview_id
    - jwt_token

Run:
    python agent.py dev     # connect to LiveKit Cloud dev room
    python agent.py start   # production worker mode

Environment:
    LIVEKIT_URL
    LIVEKIT_API_KEY
    LIVEKIT_API_SECRET
    GOOGLE_API_KEY (or GEMINI_API_KEY)
    GEMINI_LIVE_MODEL (default: gemini-3.8-live)
    GEMINI_VOICE (default: Puck)
    PREPAI_BACKEND_URL (default: http://localhost:8000)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------
# Environment configuration
# ---------------------------------------------------------

ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Support either GOOGLE_API_KEY or GEMINI_API_KEY.
# livekit-plugins-google expects GOOGLE_API_KEY in the environment.
GOOGLE_API_KEY = (
    os.getenv("GOOGLE_API_KEY")
    or os.getenv("GEMINI_API_KEY")
    or ""
)

if GOOGLE_API_KEY:
    os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

BACKEND_URL = os.getenv(
    "PREPAI_BACKEND_URL",
    "http://localhost:8000",
).rstrip("/")

# Default to gemini-3.8-live, keeping voice model separate from backend text model.
GEMINI_LIVE_MODEL = (
    os.getenv("GEMINI_LIVE_MODEL")
    or os.getenv("GEMINI_MODEL")
    or "gemini-3.8-live"
)

GEMINI_VOICE = os.getenv("GEMINI_VOICE", "Puck")

# ---------------------------------------------------------
# LiveKit imports
# ---------------------------------------------------------

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    room_io,
)
from livekit.plugins import google

# ---------------------------------------------------------
# PrepAI internal modules
# ---------------------------------------------------------

from interview_context import InterviewContext
from prompts import (
    build_greeting_instruction,
    build_system_prompt,
)
from tools import make_tools
from transcript import TranscriptManager

logger = logging.getLogger("prepai.voice-agent")


# ---------------------------------------------------------
# Room metadata parser
# ---------------------------------------------------------

def _parse_room_metadata(metadata: str) -> dict:
    """
    Parse room metadata provided by PrepAI backend.

    Expected JSON:
    {
        "interview_id": "...",
        "jwt_token": "..."
    }
    """
    if not metadata:
        return {}

    try:
        parsed = json.loads(metadata)
        if isinstance(parsed, dict):
            return parsed
        logger.warning("Room metadata must be a JSON object, got: %s", type(parsed).__name__)
        return {}
    except json.JSONDecodeError:
        logger.warning("Could not parse room metadata as JSON.")
        return {}


# ---------------------------------------------------------
# Transcript synchronization helper
# ---------------------------------------------------------

def _schedule_transcript_sync(
    transcript: TranscriptManager,
    speaker: str,
    text: str,
) -> None:
    """
    Sync a finalized conversation message with PrepAI backend.
    Runs asynchronously so transcript syncing does not block
    the voice conversation.
    """
    if not text.strip():
        return

    task = asyncio.create_task(
        transcript.add_and_sync(speaker, text)
    )

    def on_sync_complete(completed_task: asyncio.Task) -> None:
        try:
            completed_task.result()
        except asyncio.CancelledError:
            logger.warning("Transcript sync task was cancelled.")
        except Exception:
            logger.exception("Failed to sync %s transcript with backend.", speaker)

    task.add_done_callback(on_sync_complete)


# ---------------------------------------------------------
# Graceful session termination
# ---------------------------------------------------------

async def _graceful_close(session: AgentSession, room) -> None:
    """Cleanly shut down AgentSession and disconnect from LiveKit room."""
    try:
        await session.aclose()
    except Exception as exc:
        logger.debug("Error closing AgentSession: %s", exc)

    try:
        await room.disconnect()
    except Exception as exc:
        logger.debug("Error disconnecting room: %s", exc)


# ---------------------------------------------------------
# Agent entrypoint
# ---------------------------------------------------------

async def entrypoint(ctx: JobContext) -> None:
    """
    Main LiveKit worker entrypoint.
    One agent session is created for each interview room.
    """
    logger.info("Starting PrepAI voice agent for room: %s", ctx.room.name)

    # -----------------------------------------------------
    # 1. Validate environment
    # -----------------------------------------------------
    required_variables = [
        "LIVEKIT_URL",
        "LIVEKIT_API_KEY",
        "LIVEKIT_API_SECRET",
    ]

    missing_variables = [
        key for key in required_variables
        if not os.getenv(key)
    ]

    if missing_variables:
        logger.error(
            "Missing required LiveKit environment variables: %s",
            ", ".join(missing_variables),
        )
        return

    if not GOOGLE_API_KEY:
        logger.error(
            "Missing Gemini API key: set GOOGLE_API_KEY or GEMINI_API_KEY in voice-agent/.env"
        )
        return

    # -----------------------------------------------------
    # 2. Connect to LiveKit room
    # -----------------------------------------------------
    try:
        await ctx.connect()
    except Exception as exc:
        logger.error("Failed to connect to LiveKit room %s: %s", ctx.room.name, exc)
        return

    logger.info("Connected to LiveKit room: %s", ctx.room.name)

    # -----------------------------------------------------
    # 3. Read interview metadata
    # -----------------------------------------------------
    metadata = _parse_room_metadata(ctx.room.metadata or "")
    interview_id = metadata.get("interview_id")
    jwt_token = metadata.get("jwt_token")

    if not interview_id or not jwt_token:
        logger.error(
            "Missing interview_id or jwt_token in room metadata. "
            "Ensure the PrepAI backend creates the session with room metadata."
        )
        await ctx.room.disconnect()
        return

    logger.info("Interview context received for interview ID: %s", interview_id)

    # -----------------------------------------------------
    # 4. Load interview context from PrepAI backend
    # -----------------------------------------------------
    try:
        context = await InterviewContext.load_from_backend(
            backend_url=BACKEND_URL,
            interview_id=interview_id,
            jwt_token=jwt_token,
        )
    except Exception as exc:
        logger.error(
            "Failed to load interview context from backend (%s): %s",
            BACKEND_URL,
            exc,
        )
        await ctx.room.disconnect()
        return

    if not context.questions:
        logger.error("Interview %s has no questions configured.", interview_id)
        await ctx.room.disconnect()
        return

    first_question = context.current_question
    if not first_question:
        logger.error("No current question available for interview %s.", interview_id)
        await ctx.room.disconnect()
        return

    # -----------------------------------------------------
    # 5. Initialize transcript manager
    # -----------------------------------------------------
    transcript = TranscriptManager(
        interview_id=interview_id,
        backend_url=BACKEND_URL,
        jwt_token=jwt_token,
    )

    # -----------------------------------------------------
    # 6. Initialize interview tools
    # -----------------------------------------------------
    tools = make_tools(
        interview_id=interview_id,
        backend_url=BACKEND_URL,
        jwt_token=jwt_token,
    )

    # -----------------------------------------------------
    # 7. Build Gemini system instructions
    # -----------------------------------------------------
    system_prompt = build_system_prompt(
        interview_context_str=context.to_system_prompt_context(),
        current_question=first_question.text,
    )

    # -----------------------------------------------------
    # 8. Configure Gemini Live model
    # -----------------------------------------------------
    logger.info(
        "Initializing Gemini Live model: %s (voice: %s)",
        GEMINI_LIVE_MODEL,
        GEMINI_VOICE,
    )

    try:
        realtime_model = google.realtime.RealtimeModel(
            model=GEMINI_LIVE_MODEL,
            voice=GEMINI_VOICE,
            instructions=system_prompt,
            api_key=GOOGLE_API_KEY,
        )
    except Exception as exc:
        logger.error("Failed to initialize Gemini RealtimeModel: %s", exc)
        await ctx.room.disconnect()
        return

    # -----------------------------------------------------
    # 9. Create AgentSession & Interview Agent
    # -----------------------------------------------------
    session = AgentSession(
        llm=realtime_model,
    )

    interview_agent = Agent(
        instructions=system_prompt,
        tools=tools,
    )

    # -----------------------------------------------------
    # 10. Event Handlers (Transcription, Errors, Close)
    # -----------------------------------------------------
    @session.on("conversation_item_added")
    def on_conversation_item_added(event) -> None:
        """
        Finalized conversation turn event in LiveKit Agents 1.8.10.
        Extracts speaker and text content, then syncs to backend.
        """
        item = getattr(event, "item", None)
        if item is None:
            return

        role = getattr(item, "role", "")
        if hasattr(role, "value"):
            role = role.value
        role = str(role).lower()

        if role == "user":
            speaker = "candidate"
        elif role == "assistant":
            speaker = "interviewer"
        else:
            return

        # Extract message text robustly
        message_text = getattr(item, "text_content", "") or ""
        if not message_text and hasattr(item, "content"):
            content = item.content
            if isinstance(content, list):
                message_text = " ".join(str(c) for c in content if isinstance(c, str))
            elif isinstance(content, str):
                message_text = content

        message_text = str(message_text).strip()
        if not message_text:
            return

        logger.info("%s: %s", speaker, message_text[:150])
        _schedule_transcript_sync(
            transcript=transcript,
            speaker=speaker,
            text=message_text,
        )

    @session.on("error")
    def on_session_error(event) -> None:
        """
        Handles and classifies Gemini Live & AgentSession errors.
        Prevents endless retry loops by ending the session on fatal errors.
        """
        raw_error = getattr(event, "error", event)
        error_msg = str(raw_error)
        err_lower = error_msg.lower()

        if "429" in err_lower or "quota" in err_lower or "rate limit" in err_lower:
            logger.error(
                "Gemini Live error: Rate limit or quota exhausted (HTTP 429). "
                "Ending voice session gracefully. Check Gemini quota at https://aistudio.google.com/."
            )
        elif "401" in err_lower or "403" in err_lower or "api_key" in err_lower or "unauthorized" in err_lower:
            logger.error(
                "Gemini Live error: Authentication failure (HTTP 401/403). "
                "Check that GOOGLE_API_KEY/GEMINI_API_KEY is valid."
            )
        elif "404" in err_lower or "not found" in err_lower or "unsupported" in err_lower:
            logger.error(
                "Gemini Live error: Model '%s' not found or unsupported (HTTP 404). "
                "Check GEMINI_LIVE_MODEL in voice-agent/.env.",
                GEMINI_LIVE_MODEL,
            )
        elif "500" in err_lower or "503" in err_lower or "unavailable" in err_lower or "internal" in err_lower:
            logger.error(
                "Gemini Live error: Service temporarily unavailable (HTTP 500/503). "
                "Google Gemini servers may be experiencing temporary degradation."
            )
        elif "timeout" in err_lower or "deadline" in err_lower:
            logger.error(
                "Gemini Live error: Connection timeout. Check your internet connection."
            )
        else:
            logger.error(
                "Gemini Live error: %s (source: %s)",
                error_msg[:300],
                getattr(event, "source", "unknown"),
            )

        # On unrecoverable model/transport errors, close gracefully
        if not getattr(raw_error, "recoverable", True):
            logger.warning("Unrecoverable error encountered; closing session.")
            asyncio.create_task(_graceful_close(session, ctx.room))

    @session.on("close")
    def on_session_close(event) -> None:
        reason = getattr(event, "reason", "unknown")
        logger.info("LiveKit voice session closed. Reason: %s", reason)

    # -----------------------------------------------------
    # 11. Start LiveKit session
    # -----------------------------------------------------
    try:
        await session.start(
            room=ctx.room,
            agent=interview_agent,
            room_options=room_io.RoomOptions(),
        )
        logger.info("LiveKit session started successfully.")
    except Exception as exc:
        logger.error("Failed to start LiveKit session: %s", exc)
        await _graceful_close(session, ctx.room)
        return

    # -----------------------------------------------------
    # 12. Generate interview greeting
    # -----------------------------------------------------
    greeting_instruction = build_greeting_instruction(
        total_questions=context.total_questions,
        first_question=first_question.text,
    )

    try:
        await session.generate_reply(
            instructions=greeting_instruction,
        )
    except Exception as exc:
        logger.error("Failed to generate initial interview greeting: %s", exc)

    logger.info(
        "PrepAI voice interview started successfully | "
        "Interview ID: %s | Questions: %d | Model: %s",
        interview_id,
        context.total_questions,
        GEMINI_LIVE_MODEL,
    )


# ---------------------------------------------------------
# Worker entrypoint
# ---------------------------------------------------------

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )
