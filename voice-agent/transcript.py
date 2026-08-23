"""
voice-agent/transcript.py

Transcript management for the PrepAI voice agent.

The TranscriptManager maintains a structured in-memory conversation log
and syncs entries to the PrepAI backend via HTTP after each turn.

Structure:
  [
    {"speaker": "interviewer", "text": "...", "timestamp": "..."},
    {"speaker": "candidate",   "text": "...", "timestamp": "..."},
  ]

Design decisions:
  - Raw audio is NOT stored permanently.
  - Text transcript only (from STT or Gemini Live transcription).
  - Each entry is posted to the backend immediately so partial transcripts
    survive a voice agent crash.
  - interview_id and jwt_token are stored at construction — the backend
    enforces ownership independently via JWT.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class TranscriptEntry:
    """One turn in the voice conversation."""
    speaker: str        # "interviewer" or "candidate"
    text: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict:
        return {
            "speaker": self.speaker,
            "text": self.text,
            "timestamp": self.timestamp.isoformat(),
        }


class TranscriptManager:
    """
    Manages the voice interview transcript.
    Thread-safe for asyncio use (single-threaded event loop).
    """

    def __init__(
        self,
        interview_id: str,
        backend_url: str,
        jwt_token: str,
    ) -> None:
        self.interview_id = interview_id
        self.backend_url = backend_url
        self.jwt_token = jwt_token
        self._entries: List[TranscriptEntry] = []

    def add_entry(self, speaker: str, text: str) -> TranscriptEntry:
        """Add an entry to the in-memory transcript."""
        entry = TranscriptEntry(speaker=speaker, text=text.strip())
        self._entries.append(entry)
        return entry

    async def add_and_sync(self, speaker: str, text: str) -> None:
        """Add an entry and immediately sync it to the backend."""
        entry = self.add_entry(speaker, text)
        await self._post_entry(entry)

    async def _post_entry(self, entry: TranscriptEntry) -> None:
        """
        POST a single transcript entry to the backend.
        Uses the candidate's JWT token — the backend enforces ownership.
        Failures are logged but do not crash the agent.
        """
        url = f"{self.backend_url}/api/interviews/{self.interview_id}/voice/transcript/append"
        headers = {"Authorization": f"Bearer {self.jwt_token}"}
        payload = {
            "speaker": entry.speaker,
            "text": entry.text,
            "timestamp": entry.timestamp.isoformat(),
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as http:
                resp = await http.post(url, json=payload, headers=headers)
                if resp.status_code not in (200, 204):
                    logger.warning(
                        "Transcript sync failed [%s]: %s",
                        resp.status_code,
                        resp.text[:200],
                    )
        except Exception as exc:
            logger.warning("Transcript sync error (non-fatal): %s", exc)

    @property
    def entries(self) -> List[TranscriptEntry]:
        return list(self._entries)

    @property
    def full_text(self) -> str:
        """Return the full transcript as a readable string."""
        lines = []
        for e in self._entries:
            lines.append(f"[{e.speaker.upper()}] {e.text}")
        return "\n".join(lines)

    def interviewer_texts(self) -> List[str]:
        return [e.text for e in self._entries if e.speaker == "interviewer"]

    def candidate_texts(self) -> List[str]:
        return [e.text for e in self._entries if e.speaker == "candidate"]
