"""
app/utils/helpers.py

General-purpose utility functions for the PrepAI backend.
Phase 1: Minimal — just a timestamp helper for now.
"""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc)
