"""
tests/test_interview_engine.py

Comprehensive tests for the Phase 6 Text Interview Engine.
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

client = TestClient(app)

TEST_EMAIL = "engine_test_user@example.com"
TEST_PASSWORD = "enginepassword123"


def _register_and_login():
    """Helper: register a user and return the JWT token."""
    users_collection.delete_many({"email": TEST_EMAIL})
    client.post("/api/auth/register", json={
        "name": "Engine Tester",
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
    })
    resp = client.post("/api/auth/login", data={
        "username": TEST_EMAIL,
        "password": TEST_PASSWORD,
    })
    return resp.json()["access_token"]


def _create_interview(token: str) -> str:
    """Helper: create an interview and return its id."""
    resp = client.post("/api/interviews", json={
        "title": "Engine Test Interview",
        "role": "Frontend Developer",
        "experience_level": "Fresher",
        "skills": ["React", "JavaScript"],
        "interview_type": "Technical",
        "difficulty": "Medium",
        "mode": "text",
    }, headers={"Authorization": f"Bearer {token}"})
    return resp.json()["id"]


def _add_questions(token: str, interview_id: str, count: int = 3):
    """Helper: manually add N questions to an interview."""
    for i in range(count):
        client.post(f"/api/interviews/{interview_id}/questions", json={
            "question": f"Test question {i + 1}?",
            "category": "React",
            "difficulty": "Medium",
        }, headers={"Authorization": f"Bearer {token}"})


@pytest.fixture(autouse=True)
def clean_db():
    """Clean up all test data before and after each test."""
    users_collection.delete_many({"email": TEST_EMAIL})
    interviews_collection.delete_many({})
    questions_collection.delete_many({})
    responses_collection.delete_many({})
    yield
    users_collection.delete_many({"email": TEST_EMAIL})
    interviews_collection.delete_many({})
    questions_collection.delete_many({})
    responses_collection.delete_many({})


@pytest.fixture
def auth():
    """Fixture returning (token, headers)."""
    token = _register_and_login()
    return token, {"Authorization": f"Bearer {token}"}


# ==========================================
# START INTERVIEW
# ==========================================

class TestStartInterview:

    def test_start_interview_success(self, auth):
        token, headers = auth
        iid = _create_interview(token)
        _add_questions(token, iid, 2)

        resp = client.post(f"/api/interviews/{iid}/start", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "in_progress"
        assert data["current_question"]["question_number"] == 1
        assert data["current_question"]["question"] == "Test question 1?"

    def test_start_interview_no_questions(self, auth):
        token, headers = auth
        iid = _create_interview(token)

        resp = client.post(f"/api/interviews/{iid}/start", headers=headers)
        assert resp.status_code == 400
        assert "no questions" in resp.json()["detail"].lower()

    def test_start_interview_already_started(self, auth):
        token, headers = auth
        iid = _create_interview(token)
        _add_questions(token, iid, 1)

        client.post(f"/api/interviews/{iid}/start", headers=headers)
        resp = client.post(f"/api/interviews/{iid}/start", headers=headers)
        assert resp.status_code == 409


# ==========================================
# GET CURRENT QUESTION
# ==========================================

class TestGetCurrentQuestion:

    def test_get_current_question_success(self, auth):
        token, headers = auth
        iid = _create_interview(token)
        _add_questions(token, iid, 2)
        client.post(f"/api/interviews/{iid}/start", headers=headers)

        resp = client.get(f"/api/interviews/{iid}/current-question", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["question"]["question_number"] == 1
        assert data["question"]["question_type"] == "primary"

    def test_get_current_question_not_started(self, auth):
        token, headers = auth
        iid = _create_interview(token)
        _add_questions(token, iid, 1)

        resp = client.get(f"/api/interviews/{iid}/current-question", headers=headers)
        assert resp.status_code == 409


# ==========================================
# SUBMIT ANSWER
# ==========================================

class TestSubmitAnswer:

    def test_submit_answer_success(self, auth):
        token, headers = auth
        iid = _create_interview(token)
        _add_questions(token, iid, 2)
        start_resp = client.post(f"/api/interviews/{iid}/start", headers=headers)
        q_id = start_resp.json()["current_question"]["id"]

        resp = client.post(f"/api/interviews/{iid}/questions/{q_id}/response", json={
            "answer": "My answer to question 1.",
        }, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["answer"] == "My answer to question 1."
        assert data["question_id"] == q_id

    def test_submit_empty_answer(self, auth):
        token, headers = auth
        iid = _create_interview(token)
        _add_questions(token, iid, 1)
        start_resp = client.post(f"/api/interviews/{iid}/start", headers=headers)
        q_id = start_resp.json()["current_question"]["id"]

        resp = client.post(f"/api/interviews/{iid}/questions/{q_id}/response", json={
            "answer": "",
        }, headers=headers)
        assert resp.status_code == 422

    def test_submit_answer_wrong_question(self, auth):
        token, headers = auth
        iid = _create_interview(token)
        _add_questions(token, iid, 2)
        client.post(f"/api/interviews/{iid}/start", headers=headers)
        fake_q_id = str(ObjectId())

        resp = client.post(f"/api/interviews/{iid}/questions/{fake_q_id}/response", json={
            "answer": "Some answer",
        }, headers=headers)
        # Either 404 (question not found) or 400 (not current question)
        assert resp.status_code in [400, 404]

    def test_submit_duplicate_answer(self, auth):
        token, headers = auth
        iid = _create_interview(token)
        _add_questions(token, iid, 2)
        start_resp = client.post(f"/api/interviews/{iid}/start", headers=headers)
        q_id = start_resp.json()["current_question"]["id"]

        client.post(f"/api/interviews/{iid}/questions/{q_id}/response", json={
            "answer": "First answer",
        }, headers=headers)

        resp = client.post(f"/api/interviews/{iid}/questions/{q_id}/response", json={
            "answer": "Second answer",
        }, headers=headers)
        assert resp.status_code == 409

    def test_submit_answer_interview_not_started(self, auth):
        token, headers = auth
        iid = _create_interview(token)
        _add_questions(token, iid, 1)
        fake_q_id = str(ObjectId())

        resp = client.post(f"/api/interviews/{iid}/questions/{fake_q_id}/response", json={
            "answer": "Some answer",
        }, headers=headers)
        assert resp.status_code == 409


# ==========================================
# NEXT QUESTION
# ==========================================

class TestNextQuestion:

    @patch("app.services.follow_up_service.generate_follow_up")
    def test_next_question_no_follow_up(self, mock_gen, auth):
        """When Gemini says no follow-up, advance to the next primary question."""
        mock_gen.return_value = None  # No follow-up
        token, headers = auth
        iid = _create_interview(token)
        _add_questions(token, iid, 3)

        start_resp = client.post(f"/api/interviews/{iid}/start", headers=headers)
        q1_id = start_resp.json()["current_question"]["id"]

        # Answer Q1
        client.post(f"/api/interviews/{iid}/questions/{q1_id}/response", json={
            "answer": "Answer to Q1",
        }, headers=headers)

        # Next -> should give Q2
        resp = client.post(f"/api/interviews/{iid}/next", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "in_progress"
        assert data["question"]["question_number"] == 2

    @patch("app.services.follow_up_service.generate_follow_up")
    def test_next_question_with_follow_up(self, mock_gen, auth):
        """When Gemini generates a follow-up, the follow-up becomes the current question."""
        from app.ai.follow_up_generator import FollowUpDecision
        mock_gen.return_value = FollowUpDecision(
            should_follow_up=True,
            question="Can you explain how React reconciliation works?",
            category="React",
            difficulty="Medium",
        )
        token, headers = auth
        iid = _create_interview(token)
        _add_questions(token, iid, 2)

        start_resp = client.post(f"/api/interviews/{iid}/start", headers=headers)
        q1_id = start_resp.json()["current_question"]["id"]

        # Answer Q1
        client.post(f"/api/interviews/{iid}/questions/{q1_id}/response", json={
            "answer": "The Virtual DOM is a lightweight copy of the real DOM.",
        }, headers=headers)

        # Next -> should give the follow-up
        resp = client.post(f"/api/interviews/{iid}/next", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "in_progress"
        assert data["question"]["question_type"] == "follow_up"
        assert "reconciliation" in data["question"]["question"].lower()

    @patch("app.services.follow_up_service.generate_follow_up")
    def test_no_second_follow_up(self, mock_gen, auth):
        """After a follow-up is generated, answering it should NOT produce another follow-up."""
        from app.ai.follow_up_generator import FollowUpDecision

        # First call returns a follow-up; second call also returns one (but it should be ignored)
        mock_gen.side_effect = [
            FollowUpDecision(should_follow_up=True, question="Follow-up Q?", category="React", difficulty="Medium"),
            FollowUpDecision(should_follow_up=True, question="Should not appear", category="React", difficulty="Medium"),
        ]

        token, headers = auth
        iid = _create_interview(token)
        _add_questions(token, iid, 2)

        start_resp = client.post(f"/api/interviews/{iid}/start", headers=headers)
        q1_id = start_resp.json()["current_question"]["id"]

        # Answer Q1
        client.post(f"/api/interviews/{iid}/questions/{q1_id}/response", json={
            "answer": "Answer to Q1",
        }, headers=headers)

        # Next -> follow-up
        next1 = client.post(f"/api/interviews/{iid}/next", headers=headers)
        fu_id = next1.json()["question"]["id"]
        assert next1.json()["question"]["question_type"] == "follow_up"

        # Answer the follow-up
        client.post(f"/api/interviews/{iid}/questions/{fu_id}/response", json={
            "answer": "Answer to follow-up",
        }, headers=headers)

        # Next -> should go to Q2 (not another follow-up)
        next2 = client.post(f"/api/interviews/{iid}/next", headers=headers)
        assert next2.json()["status"] == "in_progress"
        assert next2.json()["question"]["question_type"] == "primary"

    @patch("app.services.follow_up_service.generate_follow_up")
    def test_gemini_failure_fallback(self, mock_gen, auth):
        """When Gemini throws an exception, fall back to the next primary question."""
        mock_gen.side_effect = Exception("Gemini is down")

        token, headers = auth
        iid = _create_interview(token)
        _add_questions(token, iid, 2)

        start_resp = client.post(f"/api/interviews/{iid}/start", headers=headers)
        q1_id = start_resp.json()["current_question"]["id"]

        # Answer Q1
        client.post(f"/api/interviews/{iid}/questions/{q1_id}/response", json={
            "answer": "Answer to Q1",
        }, headers=headers)

        # Next -> should gracefully fall back to Q2
        resp = client.post(f"/api/interviews/{iid}/next", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_progress"

    @patch("app.services.follow_up_service.generate_follow_up")
    def test_complete_after_all_questions(self, mock_gen, auth):
        """After all questions are answered, interview becomes completed."""
        mock_gen.return_value = None  # No follow-ups

        token, headers = auth
        iid = _create_interview(token)
        _add_questions(token, iid, 2)

        start_resp = client.post(f"/api/interviews/{iid}/start", headers=headers)
        q1_id = start_resp.json()["current_question"]["id"]

        # Answer Q1, next
        client.post(f"/api/interviews/{iid}/questions/{q1_id}/response", json={"answer": "A1"}, headers=headers)
        next1 = client.post(f"/api/interviews/{iid}/next", headers=headers)
        q2_id = next1.json()["question"]["id"]

        # Answer Q2, next
        client.post(f"/api/interviews/{iid}/questions/{q2_id}/response", json={"answer": "A2"}, headers=headers)
        next2 = client.post(f"/api/interviews/{iid}/next", headers=headers)

        assert next2.json()["status"] == "completed"
        assert next2.json()["message"] == "Interview completed successfully"
        assert next2.json()["question"] is None

    @patch("app.services.follow_up_service.generate_follow_up")
    def test_cannot_answer_after_completion(self, mock_gen, auth):
        """After interview is completed, submitting answers is rejected."""
        mock_gen.return_value = None

        token, headers = auth
        iid = _create_interview(token)
        _add_questions(token, iid, 1)

        start_resp = client.post(f"/api/interviews/{iid}/start", headers=headers)
        q1_id = start_resp.json()["current_question"]["id"]

        client.post(f"/api/interviews/{iid}/questions/{q1_id}/response", json={"answer": "A1"}, headers=headers)
        client.post(f"/api/interviews/{iid}/next", headers=headers)

        # Try answering again
        resp = client.post(f"/api/interviews/{iid}/questions/{q1_id}/response", json={"answer": "Late answer"}, headers=headers)
        assert resp.status_code == 409

    def test_must_answer_before_next(self, auth):
        token, headers = auth
        iid = _create_interview(token)
        _add_questions(token, iid, 2)
        client.post(f"/api/interviews/{iid}/start", headers=headers)

        resp = client.post(f"/api/interviews/{iid}/next", headers=headers)
        assert resp.status_code == 400
        assert "must answer" in resp.json()["detail"].lower()


# ==========================================
# OWNERSHIP / SECURITY
# ==========================================

class TestOwnership:

    def test_cannot_access_other_users_interview(self, auth):
        token, headers = auth
        iid = _create_interview(token)
        _add_questions(token, iid, 1)

        # Create a second user
        other_email = "other_engine_user@example.com"
        users_collection.delete_many({"email": other_email})
        client.post("/api/auth/register", json={
            "name": "Other User",
            "email": other_email,
            "password": "otherpassword123",
        })
        other_resp = client.post("/api/auth/login", data={
            "username": other_email,
            "password": "otherpassword123",
        })
        other_headers = {"Authorization": f"Bearer {other_resp.json()['access_token']}"}

        # Other user tries to start
        resp = client.post(f"/api/interviews/{iid}/start", headers=other_headers)
        assert resp.status_code == 404

        # Cleanup
        users_collection.delete_many({"email": other_email})
