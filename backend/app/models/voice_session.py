"""
app/models/voice_session.py

MongoDB voice_sessions collection.

Document shape:
{
    "_id": ObjectId,
    "interview_id": ObjectId,   # The interview this session belongs to
    "user_id":      ObjectId,   # Owner — always set from JWT, never from client
    "room_name":    str,        # LiveKit room name  e.g. "prepai-<iid>-<rand>"
    "status":       str,        # "created" | "active" | "completed" | "failed"
    "started_at":   datetime | None,
    "ended_at":     datetime | None,
    "created_at":   datetime,
    "updated_at":   datetime,
}

Lifecycle:
  created  →  (POST /voice/start)  →  active
  active   →  (POST /voice/end)    →  completed
  active   →  (agent crash)        →  failed
"""

from pymongo import ASCENDING, DESCENDING, IndexModel

from app.config.database import db

voice_sessions_collection = db["voice_sessions"]

indexes = [
    # Find sessions by user
    IndexModel([("user_id", ASCENDING)], background=True),
    # Find sessions by interview
    IndexModel([("interview_id", ASCENDING)], background=True),
    # Find active sessions quickly
    IndexModel([("status", ASCENDING)], background=True),
    # Most recent session first
    IndexModel([("created_at", DESCENDING)], background=True),
    # Compound: enforce one active session per interview per user
    IndexModel(
        [
            ("interview_id", ASCENDING),
            ("user_id", ASCENDING),
            ("status", ASCENDING),
        ],
        background=True,
    ),
]
try:
    voice_sessions_collection.create_indexes(indexes)
except Exception:
    pass
