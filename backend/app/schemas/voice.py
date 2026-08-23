"""
app/schemas/voice.py

Pydantic schemas for Phase 9 — Voice Interview Engine.

Security rules enforced here:
  - No LIVEKIT_API_SECRET appears in any response schema.
  - No GEMINI_API_KEY appears in any response schema.
  - user_id is never accepted from request body.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class VoiceSessionCreateRequest(BaseModel):
    """
    No request body needed — interview_id comes from the URL path,
    user_id comes from the JWT token.
    This class exists as a placeholder in case future metadata is added.
    """
    pass


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class VoiceSessionCreateResponse(BaseModel):
    """
    Returned when a voice session is created (POST /voice/session).

    Contains the LiveKit participant token the client uses to join the room.
    The token is signed with LIVEKIT_API_SECRET (server-side) and grants:
      - room_join: True
      - can_publish: True  (microphone audio only)
      - can_subscribe: True  (hear the AI interviewer)
    """
    session_id: str
    interview_id: str
    room_name: str
    status: str
    token: str          # LiveKit participant JWT — expires in 1 hour
    livekit_url: str    # wss://... URL for the client to connect to


class VoiceSessionResponse(BaseModel):
    """
    Returned for GET /voice/session and POST /voice/start / /voice/end.
    Does NOT include the token (use POST /session to get a fresh one).
    """
    session_id: str
    interview_id: str
    room_name: str
    status: str
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class VoiceSessionEndResponse(BaseModel):
    """Returned when a voice session is ended."""
    session_id: str
    interview_id: str
    status: str             # "completed" or "failed"
    ended_at: Optional[datetime]
    interview_completed: bool   # Whether the interview was also marked complete


# ---------------------------------------------------------------------------
# Transcript schemas
# ---------------------------------------------------------------------------

class TranscriptEntry(BaseModel):
    """A single turn in the voice conversation."""
    speaker: str        # "interviewer" or "candidate"
    text: str
    timestamp: Optional[datetime]


class VoiceTranscriptResponse(BaseModel):
    """Full transcript for GET /voice/transcript."""
    interview_id: str
    session_id: str
    entries: List[TranscriptEntry]
    total_entries: int
