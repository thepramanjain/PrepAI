"""
app/services/voice_service.py

Phase 9 — Voice Interview Engine service layer.

Responsibilities:
  - Create voice sessions
  - Generate LiveKit participant tokens (server-side only)
  - Enforce duplicate session protection
  - Manage session state (created → active → completed / failed)
  - Retrieve and store transcript entries
  - Enforce user ownership on every operation

Security invariants:
  - LIVEKIT_API_SECRET is used only inside this module, never returned to client
  - GEMINI_API_KEY is not used here (voice agent only)
  - user_id is always derived from the JWT token (passed as parameter, never from request)
  - Token grants only the minimum required permissions
"""

import secrets
import string
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import HTTPException

from app.config.settings import settings
from app.models.interview import interviews_collection
from app.models.question import questions_collection
from app.models.voice_session import voice_sessions_collection


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _require_livekit_config() -> None:
    """Raise HTTP 503 if LiveKit is not configured."""
    if not settings.LIVEKIT_URL or not settings.LIVEKIT_API_KEY or not settings.LIVEKIT_API_SECRET:
        raise HTTPException(
            status_code=503,
            detail=(
                "Voice interviews are not configured. "
                "Please set LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET "
                "in the backend .env file."
            ),
        )


def _generate_room_name(interview_id: str) -> str:
    """
    Generate a unique LiveKit room name.
    Format: prepai-{interview_id_short}-{random_suffix}

    The random suffix ensures uniqueness even if the same interview
    creates multiple sessions. Room names are NOT the authorization
    mechanism — that is handled by LiveKit participant tokens.
    """
    suffix = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
    # Use last 8 chars of interview_id to keep name short but traceable
    iid_short = interview_id[-8:]
    return f"prepai-{iid_short}-{suffix}"


def _generate_livekit_token(room_name: str, participant_identity: str) -> str:
    """
    Generate a signed LiveKit participant JWT for the candidate.

    Grants:
      - room_join: True
      - can_publish: True   (microphone audio)
      - can_subscribe: True  (hear the AI interviewer)

    Uses the current livekit-api SDK (AccessToken + VideoGrants).
    LIVEKIT_API_SECRET is used only here and never returned to the client.

    Raises HTTPException(503) if the livekit-api package is not installed,
    or HTTPException(500) if token signing fails.
    """
    try:
        from livekit import api  # type: ignore[import-untyped]
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail=(
                "livekit-api package is not installed. "
                "Run: pip install livekit-api"
            ),
        )

    try:
        grant = api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
        )
        token = (
            api.AccessToken(
                api_key=settings.LIVEKIT_API_KEY,
                api_secret=settings.LIVEKIT_API_SECRET,
            )
            .with_identity(participant_identity)
            .with_name(f"Candidate {participant_identity}")
            .with_grants(grant)
            .with_ttl(3600)  # Token valid for 1 hour
        )
        return token.to_jwt()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate LiveKit token: {exc}",
        )


def _get_interview_for_user(interview_id_str: str, user_id_str: str) -> Dict[str, Any]:
    """
    Fetch the interview and verify ownership.
    Raises 404 if not found, 403 if wrong user.
    """
    try:
        interview_obj_id = ObjectId(interview_id_str)
    except Exception:
        raise HTTPException(status_code=404, detail="Interview not found.")

    interview = interviews_collection.find_one({"_id": interview_obj_id})
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found.")

    if str(interview["user_id"]) != user_id_str:
        raise HTTPException(status_code=403, detail="Access denied.")

    return interview


def _require_questions(interview_id_str: str) -> int:
    """Raise 400 if the interview has no questions. Returns question count."""
    count = questions_collection.count_documents(
        {"interview_id": ObjectId(interview_id_str)}
    )
    if count == 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "This interview has no questions. "
                "Generate questions first via POST /api/interviews/{id}/generate-questions."
            ),
        )
    return count


def _get_active_session(
    interview_id_str: str, user_id_str: str
) -> Optional[Dict[str, Any]]:
    """Return an existing active or created session, or None."""
    return voice_sessions_collection.find_one(
        {
            "interview_id": ObjectId(interview_id_str),
            "user_id": ObjectId(user_id_str),
            "status": {"$in": ["created", "active"]},
        }
    )


def _get_session_for_user(
    interview_id_str: str, user_id_str: str
) -> Dict[str, Any]:
    """Get the most recent voice session for this user+interview. Raises 404 if none."""
    session = voice_sessions_collection.find_one(
        {
            "interview_id": ObjectId(interview_id_str),
            "user_id": ObjectId(user_id_str),
        },
        sort=[("created_at", -1)],
    )
    if not session:
        raise HTTPException(
            status_code=404,
            detail="No voice session found for this interview.",
        )
    return session


# ---------------------------------------------------------------------------
# 1. Create Voice Session
# ---------------------------------------------------------------------------

def create_voice_session(
    interview_id_str: str, user_id_str: str
) -> Dict[str, Any]:
    """
    Create a new voice session for the interview.

    Steps:
      1. Validate LiveKit configuration
      2. Verify interview ownership
      3. Verify interview has questions
      4. Check for existing active session (conflict protection)
      5. Generate unique room name
      6. Generate LiveKit participant token
      7. Store session in MongoDB
      8. Return session + token

    Returns a dict matching VoiceSessionCreateResponse.
    """
    _require_livekit_config()
    interview = _get_interview_for_user(interview_id_str, user_id_str)
    _require_questions(interview_id_str)

    # Duplicate active session protection
    existing = _get_active_session(interview_id_str, user_id_str)
    if existing and existing["status"] == "active":
        raise HTTPException(
            status_code=409,
            detail={
                "error": "An active voice session already exists for this interview.",
                "session_id": str(existing["_id"]),
                "room_name": existing["room_name"],
                "status": existing["status"],
            },
        )

    # If there's a "created" (not yet started) session, reuse it
    if existing and existing["status"] == "created":
        # Generate a fresh token for the same room
        participant_identity = f"candidate-{user_id_str}"
        token = _generate_livekit_token(existing["room_name"], participant_identity)
        return {
            "session_id": str(existing["_id"]),
            "interview_id": interview_id_str,
            "room_name": existing["room_name"],
            "status": existing["status"],
            "token": token,
            "livekit_url": settings.LIVEKIT_URL,
        }

    # Create a new session
    room_name = _generate_room_name(interview_id_str)
    participant_identity = f"candidate-{user_id_str}"
    token = _generate_livekit_token(room_name, participant_identity)

    now = _now()
    session_doc = {
        "interview_id": ObjectId(interview_id_str),
        "user_id": ObjectId(user_id_str),
        "room_name": room_name,
        "status": "created",
        "started_at": None,
        "ended_at": None,
        "transcript": [],       # Populated by the voice agent via PATCH/internal calls
        "created_at": now,
        "updated_at": now,
    }
    result = voice_sessions_collection.insert_one(session_doc)

    return {
        "session_id": str(result.inserted_id),
        "interview_id": interview_id_str,
        "room_name": room_name,
        "status": "created",
        "token": token,
        "livekit_url": settings.LIVEKIT_URL,
    }


# ---------------------------------------------------------------------------
# 2. Get Voice Session (status)
# ---------------------------------------------------------------------------

def get_voice_session(
    interview_id_str: str, user_id_str: str
) -> Dict[str, Any]:
    """Return the most recent voice session for this interview (no token)."""
    _get_interview_for_user(interview_id_str, user_id_str)  # ownership check
    session = _get_session_for_user(interview_id_str, user_id_str)
    return _format_session(session, interview_id_str)


def _format_session(session: Dict[str, Any], interview_id_str: str) -> Dict[str, Any]:
    return {
        "session_id": str(session["_id"]),
        "interview_id": interview_id_str,
        "room_name": session["room_name"],
        "status": session["status"],
        "started_at": session.get("started_at"),
        "ended_at": session.get("ended_at"),
        "created_at": session["created_at"],
        "updated_at": session["updated_at"],
    }


# ---------------------------------------------------------------------------
# 3. Start Voice Session
# ---------------------------------------------------------------------------

def start_voice_session(
    interview_id_str: str, user_id_str: str
) -> Dict[str, Any]:
    """
    Start the voice session:
      1. Verify ownership
      2. Find the created/active session
      3. Mark interview as in_progress (reuses Phase 6 logic via direct update)
      4. Mark session as active
      5. Set started_at
      6. Initialize current_question_id on the interview
    """
    interview = _get_interview_for_user(interview_id_str, user_id_str)

    session = _get_active_session(interview_id_str, user_id_str)
    if not session:
        raise HTTPException(
            status_code=404,
            detail="No voice session found. Create a session first via POST /voice/session.",
        )
    if session["status"] == "active":
        return _format_session(session, interview_id_str)

    # Verify interview has questions
    _require_questions(interview_id_str)

    # Transition interview to in_progress if it's still draft
    interview_status = interview.get("status", "draft")
    now = _now()

    if interview_status == "draft":
        # Find the first question to set as current
        first_question = questions_collection.find_one(
            {"interview_id": ObjectId(interview_id_str)},
            sort=[("created_at", 1)],
        )
        current_question_id = first_question["_id"] if first_question else None

        interviews_collection.update_one(
            {"_id": ObjectId(interview_id_str)},
            {
                "$set": {
                    "status": "in_progress",
                    "started_at": now,
                    "current_question_id": current_question_id,
                    "current_question_number": 1,
                    "updated_at": now,
                }
            },
        )
    elif interview_status == "completed":
        raise HTTPException(
            status_code=400,
            detail="This interview is already completed.",
        )
    # If already in_progress (e.g. reconnection), allow continuing

    # Mark session active
    voice_sessions_collection.update_one(
        {"_id": session["_id"]},
        {
            "$set": {
                "status": "active",
                "started_at": now,
                "updated_at": now,
            }
        },
    )

    session["status"] = "active"
    session["started_at"] = now
    session["updated_at"] = now
    return _format_session(session, interview_id_str)


# ---------------------------------------------------------------------------
# 4. End Voice Session
# ---------------------------------------------------------------------------

def end_voice_session(
    interview_id_str: str, user_id_str: str
) -> Dict[str, Any]:
    """
    End the voice session:
      1. Verify ownership
      2. Find active session
      3. Mark session completed
      4. Mark interview completed if all questions are answered
      5. Return result

    Phase 7 evaluation is NOT triggered here — it remains a separate operation.
    """
    interview = _get_interview_for_user(interview_id_str, user_id_str)

    session = _get_session_for_user(interview_id_str, user_id_str)
    if session["status"] == "completed":
        return {
            "session_id": str(session["_id"]),
            "interview_id": interview_id_str,
            "status": "completed",
            "ended_at": session.get("ended_at"),
            "interview_completed": interview.get("status") == "completed",
        }

    now = _now()

    # Check if interview should be marked completed
    # An interview is complete when all its questions have responses
    from app.models.response import responses_collection
    question_count = questions_collection.count_documents(
        {"interview_id": ObjectId(interview_id_str)}
    )
    response_count = responses_collection.count_documents(
        {"interview_id": ObjectId(interview_id_str)}
    )
    interview_completed = (question_count > 0 and response_count >= question_count)

    if interview_completed and interview.get("status") != "completed":
        interviews_collection.update_one(
            {"_id": ObjectId(interview_id_str)},
            {
                "$set": {
                    "status": "completed",
                    "completed_at": now,
                    "updated_at": now,
                }
            },
        )

    # Mark session completed
    voice_sessions_collection.update_one(
        {"_id": session["_id"]},
        {
            "$set": {
                "status": "completed",
                "ended_at": now,
                "updated_at": now,
            }
        },
    )

    return {
        "session_id": str(session["_id"]),
        "interview_id": interview_id_str,
        "status": "completed",
        "ended_at": now,
        "interview_completed": interview_completed,
    }


# ---------------------------------------------------------------------------
# 5. Store Transcript Entry (called by voice agent via internal API)
# ---------------------------------------------------------------------------

def append_transcript_entry(
    interview_id_str: str,
    user_id_str: str,
    speaker: str,
    text: str,
    timestamp: Optional[datetime] = None,
) -> None:
    """
    Append a single transcript entry to the voice session.
    Called by the voice agent (POST /voice/transcript/append).
    The timestamp defaults to now if not provided.
    """
    ts = timestamp or _now()
    entry = {"speaker": speaker, "text": text, "timestamp": ts}

    voice_sessions_collection.update_one(
        {
            "interview_id": ObjectId(interview_id_str),
            "user_id": ObjectId(user_id_str),
            "status": {"$in": ["active", "created"]},
        },
        {"$push": {"transcript": entry}, "$set": {"updated_at": _now()}},
    )


# ---------------------------------------------------------------------------
# 6. Get Transcript
# ---------------------------------------------------------------------------

def get_voice_transcript(
    interview_id_str: str, user_id_str: str
) -> Dict[str, Any]:
    """Return the full transcript for the most recent voice session."""
    _get_interview_for_user(interview_id_str, user_id_str)
    session = _get_session_for_user(interview_id_str, user_id_str)

    entries = session.get("transcript", [])
    return {
        "interview_id": interview_id_str,
        "session_id": str(session["_id"]),
        "entries": entries,
        "total_entries": len(entries),
    }


# ---------------------------------------------------------------------------
# 7. Mark Session Failed (called by voice agent on crash)
# ---------------------------------------------------------------------------

def mark_session_failed(
    interview_id_str: str, user_id_str: str
) -> None:
    """
    Mark the active session as failed. Called when the voice agent crashes.
    Does NOT modify interview data — preserves any stored responses.
    """
    now = _now()
    voice_sessions_collection.update_one(
        {
            "interview_id": ObjectId(interview_id_str),
            "user_id": ObjectId(user_id_str),
            "status": "active",
        },
        {"$set": {"status": "failed", "ended_at": now, "updated_at": now}},
    )
