"""
voice-agent/config.py

Configuration for the PrepAI voice agent process.
Loads all settings from the .env file in the voice-agent directory.

Security:
  - LIVEKIT_API_SECRET and GEMINI_API_KEY are only accessible here,
    inside the isolated voice-agent process. They are never sent
    to the frontend or included in any API response.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class VoiceAgentConfig:
    """Immutable configuration for the voice agent process."""

    # LiveKit
    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str

    # Gemini (via livekit-plugins-google)
    gemini_api_key: str
    gemini_model: str

    # PrepAI backend (for fetching interview context)
    backend_url: str


def load_config() -> VoiceAgentConfig:
    """
    Load and validate configuration from environment variables.
    Raises RuntimeError if any required variable is missing.
    """
    required = {
        "LIVEKIT_URL": os.getenv("LIVEKIT_URL", ""),
        "LIVEKIT_API_KEY": os.getenv("LIVEKIT_API_KEY", ""),
        "LIVEKIT_API_SECRET": os.getenv("LIVEKIT_API_SECRET", ""),
        "GEMINI_API_KEY": os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY", ""),
    }

    missing = [k for k, v in required.items() if not v]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Copy voice-agent/.env.example to voice-agent/.env and fill in the values."
        )

    return VoiceAgentConfig(
        livekit_url=required["LIVEKIT_URL"],
        livekit_api_key=required["LIVEKIT_API_KEY"],
        livekit_api_secret=required["LIVEKIT_API_SECRET"],
        gemini_api_key=required["GEMINI_API_KEY"],
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-native-audio-preview"),
        backend_url=os.getenv("PREPAI_BACKEND_URL", "http://localhost:8000"),
    )


# Shared config instance (loaded once at import time)
config = load_config()
