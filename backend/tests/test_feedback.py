"""
tests/test_feedback.py

Comprehensive Phase 7 test suite for AI Interview Evaluation & Feedback.
All Gemini calls are mocked — no live API key required.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from bson import ObjectId

from app.main import app
from app.models.user import users_collection
from app.models.interview import interviews_collection
from app.models.question import questions_collection
from app.models.response import responses_collection
from app.models.feedback import feedback_collection

client = TestClient(app)

TEST_EMAIL = "feedback_test_user@example.com"
TEST_PASSWORD = "feedbackpass123"

# ==========================================
# MOCK HELPERS
# ==========================================

def _make_mock_evaluation(question_ids: list) -> dict:
    """Build a valid mock Gemini evaluation payload for the given question IDs."""
    return {
        "overall_score": 82,
        "category_scores": {
            "technical": 85,
            "communication": 78,
            "problem_solving": 83,
            "relevance": 82,
        },
        "question_evaluations": [
            {
                "question_id": qid,
                "score": 80,
                "quality": "Good",
                "strengths": ["Clear explanation"],
                "improvements": ["Could add an example"],
                "feedback": "The answer demonstrates good understanding.",
            }
            for qid in question_ids
        ],
        "strengths": ["Good technical knowledge", "Clear communication"],
        "weaknesses": ["Lacks practical examples"],
        "recommendations": ["Practice explaining concepts with real-world examples"],
        "topic_analysis": [
            {"topic": "React", "score": 82, "assessment": "Good"}
        ],
        "summary": "The candidate demonstrated solid fundamentals with room for deeper practical examples.",
    }


# ==========================================
# FIXTURES & HELPERS
# ==========================================

def _register_and_login(email=TEST_EMAIL, password=TEST_PASSWORD, name="Feedback Tester"):
    users_collection.delete_many({"email": email})
    client.post("/api/auth/register", json={"name": name, "email": email, "password": password})
    resp = client.post("/api/auth/login", data={"username": email, "password": password})
    return resp.json()["access_token"]


def _create_interview(token: str) -> str:
    resp = client.post("/api/interviews", json={
        "title": "Feedback Test Interview",
        "role": "Frontend Developer",
        "experience_level": "1-3 years",
        "skills": ["React", "JavaScript"],
        "interview_type": "Technical",
        "difficulty": "Medium",
        "mode": "text",
    }, headers={"Authorization": f"Bearer {token}"})
    return resp.json()["id"]


def _add_question(token: str, iid: str) -> str:
    resp = client.post(f"/api/interviews/{iid}/questions", json={
        "question": "Explain the Virtual DOM.",
        "category": "React",
        "difficulty": "Medium",
    }, headers={"Authorization": f"Bearer {token}"})
    return resp.json()["id"]


def _run_full_interview(token: str, iid: str, q_id: str):
    """Start interview, answer question, and move to next (completing it)."""
    headers = {"Authorization": f"Bearer {token}"}
    with patch("app.services.follow_up_service.generate_follow_up", return_value=None):
        client.post(f"/api/interviews/{iid}/start", headers=headers)
        client.post(f"/api/interviews/{iid}/questions/{q_id}/response",
                    json={"answer": "The Virtual DOM is a lightweight in-memory representation of the real DOM."},
                    headers=headers)
        client.post(f"/api/interviews/{iid}/next", headers=headers)


@pytest.fixture(autouse=True)
def clean_db():
    """Clean all test data before and after each test."""
    _cleanup()
    yield
    _cleanup()


def _cleanup():
    users_collection.delete_many({"email": TEST_EMAIL})
    users_collection.delete_many({"email": "other_feedback_user@example.com"})
    interviews_collection.delete_many({})
    questions_collection.delete_many({})
    responses_collection.delete_many({})
    feedback_collection.delete_many({})


@pytest.fixture
def auth():
    token = _register_and_login()
    return token, {"Authorization": f"Bearer {token}"}


# ==========================================
# EVALUATE — SUCCESS
# ==========================================

class TestEvaluate:

    def test_evaluate_completed_interview(self, auth):
        """A completed interview can be evaluated successfully."""
        token, headers = auth
        iid = _create_interview(token)
        q_id = _add_question(token, iid)
        _run_full_interview(token, iid, q_id)

        mock_eval = _make_mock_evaluation([q_id])
        with patch("app.ai.evaluator.evaluate_interview") as mock_ev:
            from app.schemas.feedback import GeneratedEvaluation
            mock_ev.return_value = GeneratedEvaluation(**mock_eval)

            resp = client.post(f"/api/interviews/{iid}/evaluate", headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_score"] == 82
        assert data["category_scores"]["technical"] == 85
        assert len(data["question_evaluations"]) == 1
        assert len(data["strengths"]) > 0
        assert "summary" in data

    def test_evaluate_stores_feedback(self, auth):
        """Evaluation result is persisted in MongoDB."""
        token, headers = auth
        iid = _create_interview(token)
        q_id = _add_question(token, iid)
        _run_full_interview(token, iid, q_id)

        mock_eval = _make_mock_evaluation([q_id])
        with patch("app.ai.evaluator.evaluate_interview") as mock_ev:
            from app.schemas.feedback import GeneratedEvaluation
            mock_ev.return_value = GeneratedEvaluation(**mock_eval)
            client.post(f"/api/interviews/{iid}/evaluate", headers=headers)

        # Check MongoDB directly
        from app.models.interview import interviews_collection as ic
        from bson import ObjectId
        interview = ic.find_one({})
        stored = feedback_collection.find_one({"interview_id": interview["_id"]})
        assert stored is not None
        assert stored["overall_score"] == 82

    def test_re_evaluate_updates_not_duplicates(self, auth):
        """Calling evaluate twice updates the existing feedback, not creates a duplicate."""
        token, headers = auth
        iid = _create_interview(token)
        q_id = _add_question(token, iid)
        _run_full_interview(token, iid, q_id)

        mock_eval_1 = _make_mock_evaluation([q_id])
        mock_eval_2 = _make_mock_evaluation([q_id])
        mock_eval_2["overall_score"] = 90  # Different score for second call

        with patch("app.ai.evaluator.evaluate_interview") as mock_ev:
            from app.schemas.feedback import GeneratedEvaluation
            mock_ev.return_value = GeneratedEvaluation(**mock_eval_1)
            client.post(f"/api/interviews/{iid}/evaluate", headers=headers)

            mock_ev.return_value = GeneratedEvaluation(**mock_eval_2)
            resp2 = client.post(f"/api/interviews/{iid}/evaluate", headers=headers)

        # Only ONE document should exist
        count = feedback_collection.count_documents({})
        assert count == 1
        assert resp2.json()["overall_score"] == 90


# ==========================================
# EVALUATE — VALIDATION FAILURES
# ==========================================

class TestEvaluateValidation:

    def test_evaluate_draft_interview_rejected(self, auth):
        """Draft interviews cannot be evaluated."""
        token, headers = auth
        iid = _create_interview(token)
        _add_question(token, iid)

        resp = client.post(f"/api/interviews/{iid}/evaluate", headers=headers)
        assert resp.status_code == 400
        assert "completed" in resp.json()["detail"].lower()

    def test_evaluate_in_progress_interview_rejected(self, auth):
        """In-progress interviews cannot be evaluated."""
        token, headers = auth
        iid = _create_interview(token)
        q_id = _add_question(token, iid)
        client.post(f"/api/interviews/{iid}/start", headers=headers)

        resp = client.post(f"/api/interviews/{iid}/evaluate", headers=headers)
        assert resp.status_code == 400

    def test_evaluate_unauthenticated_rejected(self):
        """Unauthenticated evaluation requests are rejected."""
        resp = client.post(f"/api/interviews/{str(ObjectId())}/evaluate")
        assert resp.status_code == 401

    def test_evaluate_other_users_interview_rejected(self, auth):
        """User cannot evaluate another user's interview."""
        token, headers = auth
        iid = _create_interview(token)
        q_id = _add_question(token, iid)
        _run_full_interview(token, iid, q_id)

        # Create another user
        other_token = _register_and_login("other_feedback_user@example.com", "otherpass123", "Other User")
        other_headers = {"Authorization": f"Bearer {other_token}"}

        resp = client.post(f"/api/interviews/{iid}/evaluate", headers=other_headers)
        assert resp.status_code == 404

    def test_invalid_question_id_from_gemini_rejected(self, auth):
        """If Gemini returns a non-existent question_id, the evaluation is rejected."""
        token, headers = auth
        iid = _create_interview(token)
        q_id = _add_question(token, iid)
        _run_full_interview(token, iid, q_id)

        # Gemini returns a fake question_id
        fake_q_id = str(ObjectId())
        mock_eval = _make_mock_evaluation([fake_q_id])

        with patch("app.ai.evaluator.evaluate_interview") as mock_ev:
            from app.schemas.feedback import GeneratedEvaluation
            mock_ev.return_value = GeneratedEvaluation(**mock_eval)
            resp = client.post(f"/api/interviews/{iid}/evaluate", headers=headers)

        assert resp.status_code == 422
        assert "unknown question_id" in resp.json()["detail"].lower()

    def test_invalid_score_from_gemini_rejected(self, auth):
        """If Gemini returns an out-of-range score, Pydantic validation rejects it."""
        token, headers = auth
        iid = _create_interview(token)
        q_id = _add_question(token, iid)
        _run_full_interview(token, iid, q_id)

        bad_eval = _make_mock_evaluation([q_id])
        bad_eval["overall_score"] = 150  # Invalid score

        with patch("app.ai.evaluator.evaluate_interview") as mock_ev:
            # Simulate Pydantic validation failing inside the evaluator
            mock_ev.side_effect = RuntimeError("AI response failed schema validation: overall_score must be <= 100")
            resp = client.post(f"/api/interviews/{iid}/evaluate", headers=headers)

        assert resp.status_code == 500

    def test_gemini_api_failure_is_handled(self, auth):
        """Gemini API failure returns a 500 without corrupting any data."""
        token, headers = auth
        iid = _create_interview(token)
        q_id = _add_question(token, iid)
        _run_full_interview(token, iid, q_id)

        with patch("app.ai.evaluator.evaluate_interview") as mock_ev:
            mock_ev.side_effect = RuntimeError("Failed to communicate with AI Service.")
            resp = client.post(f"/api/interviews/{iid}/evaluate", headers=headers)

        assert resp.status_code == 500
        # No feedback should have been stored
        assert feedback_collection.count_documents({}) == 0

    def test_gemini_rate_limit_returns_429(self, auth):
        """Gemini rate limit error returns HTTP 429."""
        token, headers = auth
        iid = _create_interview(token)
        q_id = _add_question(token, iid)
        _run_full_interview(token, iid, q_id)

        with patch("app.ai.evaluator.evaluate_interview") as mock_ev:
            mock_ev.side_effect = RuntimeError("AI Service rate limit exceeded. Please try again later.")
            resp = client.post(f"/api/interviews/{iid}/evaluate", headers=headers)

        assert resp.status_code == 429


# ==========================================
# GET FEEDBACK
# ==========================================

class TestGetFeedback:

    def test_get_feedback_success(self, auth):
        """User can retrieve stored feedback after evaluation."""
        token, headers = auth
        iid = _create_interview(token)
        q_id = _add_question(token, iid)
        _run_full_interview(token, iid, q_id)

        mock_eval = _make_mock_evaluation([q_id])
        with patch("app.ai.evaluator.evaluate_interview") as mock_ev:
            from app.schemas.feedback import GeneratedEvaluation
            mock_ev.return_value = GeneratedEvaluation(**mock_eval)
            client.post(f"/api/interviews/{iid}/evaluate", headers=headers)

        resp = client.get(f"/api/interviews/{iid}/feedback", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_score"] == 82
        assert "category_scores" in data
        assert "question_evaluations" in data
        assert "summary" in data

    def test_get_feedback_not_yet_evaluated(self, auth):
        """Retrieving feedback before evaluation returns 404."""
        token, headers = auth
        iid = _create_interview(token)
        _add_question(token, iid)

        resp = client.get(f"/api/interviews/{iid}/feedback", headers=headers)
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_get_feedback_unauthenticated_rejected(self):
        """Unauthenticated feedback retrieval is rejected."""
        resp = client.get(f"/api/interviews/{str(ObjectId())}/feedback")
        assert resp.status_code == 401

    def test_cannot_get_other_users_feedback(self, auth):
        """User cannot access another user's feedback."""
        token, headers = auth
        iid = _create_interview(token)
        q_id = _add_question(token, iid)
        _run_full_interview(token, iid, q_id)

        mock_eval = _make_mock_evaluation([q_id])
        with patch("app.ai.evaluator.evaluate_interview") as mock_ev:
            from app.schemas.feedback import GeneratedEvaluation
            mock_ev.return_value = GeneratedEvaluation(**mock_eval)
            client.post(f"/api/interviews/{iid}/evaluate", headers=headers)

        # Second user tries to read
        other_token = _register_and_login("other_feedback_user@example.com", "otherpass123", "Other User")
        other_headers = {"Authorization": f"Bearer {other_token}"}

        resp = client.get(f"/api/interviews/{iid}/feedback", headers=other_headers)
        assert resp.status_code == 404
