"""
app/routes/voice.py

Phase 9 — Voice Interview Engine routes.

Endpoints:
  POST /api/interviews/{interview_id}/voice/session      — create session + get token
  GET  /api/interviews/{interview_id}/voice/session      — get session status
  POST /api/interviews/{interview_id}/voice/start        — start session
  POST /api/interviews/{interview_id}/voice/end          — end session
  GET  /api/interviews/{interview_id}/voice/transcript   — get transcript
  POST /api/interviews/{interview_id}/voice/transcript/append  — (internal, agent use)

Security:
  - All routes require JWT authentication (Depends(get_current_user))
  - user_id is ALWAYS derived from the JWT token, never from the request body
  - Ownership is enforced inside voice_service — routes remain thin
"""

from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.schemas.voice import (
    VoiceSessionCreateResponse,
    VoiceSessionEndResponse,
    VoiceSessionResponse,
    VoiceTranscriptResponse,
)
from app.services import voice_service

router = APIRouter(
    prefix="/api/interviews/{interview_id}/voice",
    tags=["Voice Interview"],
)


def _validate_interview_id(interview_id: str) -> str:
    """Validate the interview_id path parameter is a valid ObjectId."""
    try:
        ObjectId(interview_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found.",
        )
    return interview_id


# ---------------------------------------------------------------------------
# POST /voice/session — Create voice session
# ---------------------------------------------------------------------------

@router.post(
    "/session",
    response_model=VoiceSessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a voice interview session",
    description=(
        "Creates a LiveKit room and returns a signed participant token. "
        "The client uses the token to join the room via the LiveKit SDK. "
        "LIVEKIT_API_SECRET is never included in the response."
    ),
)
def create_voice_session(
    interview_id: str = Depends(_validate_interview_id),
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    result = voice_service.create_voice_session(interview_id, user_id)
    return result


# ---------------------------------------------------------------------------
# GET /voice/session — Get session status
# ---------------------------------------------------------------------------

@router.get(
    "/session",
    response_model=VoiceSessionResponse,
    summary="Get voice session status",
    description=(
        "Returns the current status of the voice session. "
        "Does not include the participant token — call POST /session for a fresh token."
    ),
)
def get_voice_session(
    interview_id: str = Depends(_validate_interview_id),
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    return voice_service.get_voice_session(interview_id, user_id)


# ---------------------------------------------------------------------------
# POST /voice/start — Start voice session
# ---------------------------------------------------------------------------

@router.post(
    "/start",
    response_model=VoiceSessionResponse,
    summary="Start the voice interview",
    description=(
        "Transitions session from 'created' to 'active', sets started_at, "
        "and initializes the interview state (mirrors Phase 6 start logic). "
        "Call after connecting to the LiveKit room."
    ),
)
def start_voice_session(
    interview_id: str = Depends(_validate_interview_id),
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    return voice_service.start_voice_session(interview_id, user_id)


# ---------------------------------------------------------------------------
# POST /voice/end — End voice session
# ---------------------------------------------------------------------------

@router.post(
    "/end",
    response_model=VoiceSessionEndResponse,
    summary="End the voice interview",
    description=(
        "Marks the session as completed and sets ended_at. "
        "If all questions have been answered, marks the interview as completed too. "
        "Phase 7 evaluation is NOT triggered automatically — call POST /evaluate separately."
    ),
)
def end_voice_session(
    interview_id: str = Depends(_validate_interview_id),
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    return voice_service.end_voice_session(interview_id, user_id)


# ---------------------------------------------------------------------------
# GET /voice/transcript — Get conversation transcript
# ---------------------------------------------------------------------------

@router.get(
    "/transcript",
    response_model=VoiceTranscriptResponse,
    summary="Get voice interview transcript",
    description=(
        "Returns the full chronological transcript for this interview's voice session. "
        "Only accessible by the interview owner."
    ),
)
def get_voice_transcript(
    interview_id: str = Depends(_validate_interview_id),
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    return voice_service.get_voice_transcript(interview_id, user_id)


# ---------------------------------------------------------------------------
# POST /voice/transcript/append — Internal: append transcript entry
# (Called by the voice agent. Still requires JWT to enforce ownership.)
# ---------------------------------------------------------------------------

class _AppendEntryBody(object):
    pass


from pydantic import BaseModel as _BaseModel


class _AppendEntryRequest(_BaseModel):
    speaker: str        # "interviewer" or "candidate"
    text: str
    timestamp: Optional[datetime] = None


@router.post(
    "/transcript/append",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Append a transcript entry (internal — used by voice agent)",
    description=(
        "Appends one transcript entry to the active voice session. "
        "Intended to be called by the voice agent process using a candidate JWT. "
        "Requires an active session to exist."
    ),
)
def append_transcript_entry(
    body: _AppendEntryRequest,
    interview_id: str = Depends(_validate_interview_id),
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    voice_service.append_transcript_entry(
        interview_id_str=interview_id,
        user_id_str=user_id,
        speaker=body.speaker,
        text=body.text,
        timestamp=body.timestamp,
    )
