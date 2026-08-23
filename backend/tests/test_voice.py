"""
tests/test_voice.py

Integration tests for Phase 9 — Voice Interview Engine.

All LiveKit token generation is mocked — no real LiveKit server or
microphone hardware is required to run this suite.

Isolation:
  - Unique TEST_EMAIL per file avoids cross-file contamination.
  - clean_db deletes only documents belonging to the test user.
  - Patches livekit.api at import time so the backend can work even
    if livekit-api is not installed in the test environment.
"""

import pytest
from unittest.mock import MagicMock, patch
from bson import ObjectId
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import users_collection
from app.models.interview import interviews_collection
from app.models.question import questions_collection
from app.models.voice_session import voice_sessions_collection
from app.models.response import responses_collection

client = TestClient(app)

TEST_EMAIL = "voice_test@example.com"
TEST_PASSWORD = "voicepassword123"

FAKE_TOKEN = "eyJhbGciOiJIUzI1NiJ9.fake.token"
FAKE_LIVEKIT_URL = "wss://test.livekit.cloud"


# ---------------------------------------------------------------------------
# DB isolation helpers
# ---------------------------------------------------------------------------

def _delete_user_data(email: str) -> None:
    user = users_collection.find_one({"email": email})
    if user:
        uid = user["_id"]
        responses_collection.delete_many({"user_id": uid})
        questions_collection.delete_many({"interview_id": {"$in": [
            i["_id"] for i in interviews_collection.find({"user_id": uid}, {"_id": 1})
        ]}})
        voice_sessions_collection.delete_many({"user_id": uid})
        interviews_collection.delete_many({"user_id": uid})
    users_collection.delete_many({"email": email})


@pytest.fixture(autouse=True)
def clean_db():
    _delete_user_data(TEST_EMAIL)
    yield
    _delete_user_data(TEST_EMAIL)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _register_and_login() -> str:
    reg = client.post(
        "/api/auth/register",
        json={"name": "Voice User", "email": TEST_EMAIL, "password": TEST_PASSWORD},
    )
    assert reg.status_code == 201, f"Register failed: {reg.text}"
    login = client.post(
        "/api/auth/login",
        data={"username": TEST_EMAIL, "password": TEST_PASSWORD},
    )
    assert login.status_code == 200, f"Login failed: {login.text}"
    return login.json()["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_interview(token: str) -> str:
    resp = client.post(
        "/api/interviews",
        json={
            "title": "Voice Interview",
            "role": "Backend Developer",
            "experience_level": "1-3 years",
            "skills": ["Python"],
            "interview_type": "Technical",
            "difficulty": "Medium",
            "mode": "voice",
        },
        headers=_headers(token),
    )
    assert resp.status_code == 201, f"Create interview failed: {resp.text}"
    return resp.json()["id"]


def _add_question(interview_id: str, user_id: str) -> str:
    """Insert a question directly into MongoDB (bypass Gemini)."""
    from datetime import datetime, timezone
    doc = {
        "interview_id": ObjectId(interview_id),
        "user_id": ObjectId(user_id),
        "text": "What is a REST API?",
        "type": "technical",
        "difficulty": "medium",
        "topic": "APIs",
        "source": "gemini",
        "created_at": datetime.now(timezone.utc),
    }
    result = questions_collection.insert_one(doc)
    return str(result.inserted_id)


def _get_user_id(token: str) -> str:
    resp = client.get("/api/auth/me", headers=_headers(token))
    assert resp.status_code == 200
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Mock LiveKit settings helper
# ---------------------------------------------------------------------------

def _livekit_env():
    """Patch settings to have LiveKit configured."""
    return patch.multiple(
        "app.services.voice_service.settings",
        LIVEKIT_URL=FAKE_LIVEKIT_URL,
        LIVEKIT_API_KEY="APItest123",
        LIVEKIT_API_SECRET="secret123",
    )


def _mock_livekit_token():
    """
    Patch the token-generation function inside voice_service directly.
    This avoids the MagicMock-chain issue where to_jwt() returns a MagicMock
    rather than a real string, which causes FastAPI response validation to fail.
    """
    return patch(
        "app.services.voice_service._generate_livekit_token",
        return_value=FAKE_TOKEN,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCreateVoiceSession:
    def test_unauthenticated_rejected(self):
        """Unauthenticated requests must return 401."""
        # Use a valid-looking ObjectId to bypass path validation
        fake_id = str(ObjectId())
        resp = client.post(f"/api/interviews/{fake_id}/voice/session")
        assert resp.status_code == 401

    def test_invalid_interview_id_returns_404(self):
        token = _register_and_login()
        resp = client.post(
            "/api/interviews/not-an-objectid/voice/session",
            headers=_headers(token),
        )
        assert resp.status_code == 404

    def test_livekit_not_configured_returns_503(self):
        """Without LiveKit env vars, returns 503 Service Unavailable."""
        token = _register_and_login()
        interview_id = _create_interview(token)
        resp = client.post(
            f"/api/interviews/{interview_id}/voice/session",
            headers=_headers(token),
        )
        assert resp.status_code == 503
        assert "not configured" in resp.json()["detail"].lower()

    def test_interview_not_found_returns_404(self):
        token = _register_and_login()
        fake_id = str(ObjectId())
        with _livekit_env():
            resp = client.post(
                f"/api/interviews/{fake_id}/voice/session",
                headers=_headers(token),
            )
        assert resp.status_code == 404

    def test_cannot_create_session_for_another_users_interview(self):
        """User A cannot create a voice session for User B's interview."""
        token = _register_and_login()
        interview_id = _create_interview(token)

        # Register User B with a different email
        from app.models.user import users_collection as uc
        other_email = "voice_other@example.com"
        try:
            client.post(
                "/api/auth/register",
                json={"name": "Other", "email": other_email, "password": "pass12345"},
            )
            login2 = client.post(
                "/api/auth/login",
                data={"username": other_email, "password": "pass12345"},
            )
            token2 = login2.json()["access_token"]
            with _livekit_env(), _mock_livekit_token():
                resp = client.post(
                    f"/api/interviews/{interview_id}/voice/session",
                    headers=_headers(token2),
                )
            assert resp.status_code == 403
        finally:
            uc.delete_many({"email": other_email})

    def test_no_questions_returns_400(self):
        """Cannot create a voice session if the interview has no questions."""
        token = _register_and_login()
        interview_id = _create_interview(token)
        with _livekit_env(), _mock_livekit_token():
            resp = client.post(
                f"/api/interviews/{interview_id}/voice/session",
                headers=_headers(token),
            )
        assert resp.status_code == 400
        assert "questions" in resp.json()["detail"].lower()

    def test_creates_session_successfully(self):
        """Creates a session and returns token + room_name."""
        token = _register_and_login()
        interview_id = _create_interview(token)
        user_id = _get_user_id(token)
        _add_question(interview_id, user_id)

        with _livekit_env(), _mock_livekit_token():
            resp = client.post(
                f"/api/interviews/{interview_id}/voice/session",
                headers=_headers(token),
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "created"
        assert data["token"] == FAKE_TOKEN
        assert data["livekit_url"] == FAKE_LIVEKIT_URL
        assert data["room_name"].startswith("prepai-")
        assert "session_id" in data
        assert "interview_id" in data

    def test_room_name_unique_format(self):
        """Room name follows prepai-{iid_short}-{rand} format."""
        token = _register_and_login()
        interview_id = _create_interview(token)
        user_id = _get_user_id(token)
        _add_question(interview_id, user_id)

        with _livekit_env(), _mock_livekit_token():
            resp = client.post(
                f"/api/interviews/{interview_id}/voice/session",
                headers=_headers(token),
            )
        room_name = resp.json()["room_name"]
        parts = room_name.split("-")
        # Format: prepai-{8 chars}-{8 chars}
        assert parts[0] == "prepai"
        assert len(parts) == 3


class TestDuplicateSessionProtection:
    def test_duplicate_active_session_returns_409(self):
        """Creating a second active session returns 409 Conflict."""
        token = _register_and_login()
        interview_id = _create_interview(token)
        user_id = _get_user_id(token)
        _add_question(interview_id, user_id)

        with _livekit_env(), _mock_livekit_token():
            # Create first session
            resp1 = client.post(
                f"/api/interviews/{interview_id}/voice/session",
                headers=_headers(token),
            )
            assert resp1.status_code == 201

            # Start it (make it active)
            client.post(
                f"/api/interviews/{interview_id}/voice/start",
                headers=_headers(token),
            )

            # Try to create another — should conflict
            resp2 = client.post(
                f"/api/interviews/{interview_id}/voice/session",
                headers=_headers(token),
            )
        assert resp2.status_code == 409

    def test_created_session_is_reused(self):
        """A 'created' (not yet started) session is reused, not duplicated."""
        token = _register_and_login()
        interview_id = _create_interview(token)
        user_id = _get_user_id(token)
        _add_question(interview_id, user_id)

        with _livekit_env(), _mock_livekit_token():
            resp1 = client.post(
                f"/api/interviews/{interview_id}/voice/session",
                headers=_headers(token),
            )
            session_id_1 = resp1.json()["session_id"]

            resp2 = client.post(
                f"/api/interviews/{interview_id}/voice/session",
                headers=_headers(token),
            )
            session_id_2 = resp2.json()["session_id"]

        # Same session should be returned
        assert session_id_1 == session_id_2


class TestGetVoiceSession:
    def test_get_session_unauthenticated(self):
        fake_id = str(ObjectId())
        resp = client.get(f"/api/interviews/{fake_id}/voice/session")
        assert resp.status_code == 401

    def test_get_session_no_session_returns_404(self):
        token = _register_and_login()
        interview_id = _create_interview(token)
        resp = client.get(
            f"/api/interviews/{interview_id}/voice/session",
            headers=_headers(token),
        )
        assert resp.status_code == 404

    def test_get_session_returns_status(self):
        token = _register_and_login()
        interview_id = _create_interview(token)
        user_id = _get_user_id(token)
        _add_question(interview_id, user_id)

        with _livekit_env(), _mock_livekit_token():
            client.post(
                f"/api/interviews/{interview_id}/voice/session",
                headers=_headers(token),
            )
            resp = client.get(
                f"/api/interviews/{interview_id}/voice/session",
                headers=_headers(token),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "created"
        assert "room_name" in data
        assert "token" not in data  # Token must NOT appear in status response


class TestStartVoiceSession:
    def test_start_unauthenticated(self):
        fake_id = str(ObjectId())
        resp = client.post(f"/api/interviews/{fake_id}/voice/start")
        assert resp.status_code == 401

    def test_start_no_session_returns_404(self):
        token = _register_and_login()
        interview_id = _create_interview(token)
        user_id = _get_user_id(token)
        _add_question(interview_id, user_id)
        resp = client.post(
            f"/api/interviews/{interview_id}/voice/start",
            headers=_headers(token),
        )
        assert resp.status_code == 404

    def test_start_session_success(self):
        token = _register_and_login()
        interview_id = _create_interview(token)
        user_id = _get_user_id(token)
        _add_question(interview_id, user_id)

        with _livekit_env(), _mock_livekit_token():
            client.post(
                f"/api/interviews/{interview_id}/voice/session",
                headers=_headers(token),
            )
            resp = client.post(
                f"/api/interviews/{interview_id}/voice/start",
                headers=_headers(token),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "active"
        assert data["started_at"] is not None


class TestEndVoiceSession:
    def test_end_unauthenticated(self):
        fake_id = str(ObjectId())
        resp = client.post(f"/api/interviews/{fake_id}/voice/end")
        assert resp.status_code == 401

    def test_end_session_success(self):
        token = _register_and_login()
        interview_id = _create_interview(token)
        user_id = _get_user_id(token)
        _add_question(interview_id, user_id)

        with _livekit_env(), _mock_livekit_token():
            client.post(
                f"/api/interviews/{interview_id}/voice/session",
                headers=_headers(token),
            )
            client.post(
                f"/api/interviews/{interview_id}/voice/start",
                headers=_headers(token),
            )
            resp = client.post(
                f"/api/interviews/{interview_id}/voice/end",
                headers=_headers(token),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["ended_at"] is not None

    def test_end_session_status_becomes_completed(self):
        token = _register_and_login()
        interview_id = _create_interview(token)
        user_id = _get_user_id(token)
        _add_question(interview_id, user_id)

        with _livekit_env(), _mock_livekit_token():
            client.post(f"/api/interviews/{interview_id}/voice/session", headers=_headers(token))
            client.post(f"/api/interviews/{interview_id}/voice/start", headers=_headers(token))
            client.post(f"/api/interviews/{interview_id}/voice/end", headers=_headers(token))

            status_resp = client.get(
                f"/api/interviews/{interview_id}/voice/session",
                headers=_headers(token),
            )

        assert status_resp.json()["status"] == "completed"


class TestVoiceTranscript:
    def test_transcript_unauthenticated(self):
        fake_id = str(ObjectId())
        resp = client.get(f"/api/interviews/{fake_id}/voice/transcript")
        assert resp.status_code == 401

    def test_transcript_no_session_returns_404(self):
        token = _register_and_login()
        interview_id = _create_interview(token)
        resp = client.get(
            f"/api/interviews/{interview_id}/voice/transcript",
            headers=_headers(token),
        )
        assert resp.status_code == 404

    def test_transcript_empty_for_new_session(self):
        token = _register_and_login()
        interview_id = _create_interview(token)
        user_id = _get_user_id(token)
        _add_question(interview_id, user_id)

        with _livekit_env(), _mock_livekit_token():
            client.post(
                f"/api/interviews/{interview_id}/voice/session",
                headers=_headers(token),
            )
            resp = client.get(
                f"/api/interviews/{interview_id}/voice/transcript",
                headers=_headers(token),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["entries"] == []
        assert data["total_entries"] == 0

    def test_transcript_append_and_retrieve(self):
        token = _register_and_login()
        interview_id = _create_interview(token)
        user_id = _get_user_id(token)
        _add_question(interview_id, user_id)

        with _livekit_env(), _mock_livekit_token():
            client.post(
                f"/api/interviews/{interview_id}/voice/session",
                headers=_headers(token),
            )
            client.post(
                f"/api/interviews/{interview_id}/voice/start",
                headers=_headers(token),
            )

            # Append entries (simulates voice agent posting transcript)
            client.post(
                f"/api/interviews/{interview_id}/voice/transcript/append",
                json={"speaker": "interviewer", "text": "Tell me about yourself."},
                headers=_headers(token),
            )
            client.post(
                f"/api/interviews/{interview_id}/voice/transcript/append",
                json={"speaker": "candidate", "text": "I am a backend developer..."},
                headers=_headers(token),
            )

            resp = client.get(
                f"/api/interviews/{interview_id}/voice/transcript",
                headers=_headers(token),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_entries"] == 2
        assert data["entries"][0]["speaker"] == "interviewer"
        assert data["entries"][1]["speaker"] == "candidate"

    def test_transcript_enforces_ownership(self):
        """User B cannot read User A's transcript."""
        token = _register_and_login()
        interview_id = _create_interview(token)
        user_id = _get_user_id(token)
        _add_question(interview_id, user_id)

        other_email = "voice_other2@example.com"
        try:
            client.post(
                "/api/auth/register",
                json={"name": "Other2", "email": other_email, "password": "pass12345"},
            )
            login2 = client.post(
                "/api/auth/login",
                data={"username": other_email, "password": "pass12345"},
            )
            token2 = login2.json()["access_token"]

            with _livekit_env(), _mock_livekit_token():
                client.post(
                    f"/api/interviews/{interview_id}/voice/session",
                    headers=_headers(token),
                )
                resp = client.get(
                    f"/api/interviews/{interview_id}/voice/transcript",
                    headers=_headers(token2),
                )
            # Either 403 (ownership) or 404 (no session for this user)
            assert resp.status_code in (403, 404)
        finally:
            from app.models.user import users_collection as uc
            uc.delete_many({"email": other_email})
