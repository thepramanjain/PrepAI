"""
tests/test_interviews.py

Integration tests for interview management flows.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import users_collection
from app.models.interview import interviews_collection
from app.models.question import questions_collection
from app.models.response import responses_collection

client = TestClient(app)

TEST_EMAIL_1 = "testuser_interviews_1@example.com"
TEST_EMAIL_2 = "testuser_interviews_2@example.com"
TEST_PASSWORD = "supersecurepassword123"

def setup_user_and_get_token(email: str):
    # Register
    client.post(
        "/api/auth/register",
        json={"name": "Test User", "email": email, "password": TEST_PASSWORD}
    )
    # Login
    resp = client.post(
        "/api/auth/login",
        data={"username": email, "password": TEST_PASSWORD}
    )
    return resp.json()["access_token"]


@pytest.fixture(autouse=True)
def clean_db():
    users_collection.delete_many({"email": {"$in": [TEST_EMAIL_1, TEST_EMAIL_2]}})
    interviews_collection.delete_many({})
    questions_collection.delete_many({})
    responses_collection.delete_many({})
    yield
    users_collection.delete_many({"email": {"$in": [TEST_EMAIL_1, TEST_EMAIL_2]}})
    interviews_collection.delete_many({})
    questions_collection.delete_many({})
    responses_collection.delete_many({})


@pytest.fixture
def token_1():
    return setup_user_and_get_token(TEST_EMAIL_1)


@pytest.fixture
def token_2():
    return setup_user_and_get_token(TEST_EMAIL_2)


def test_unauthenticated_cannot_create_interview():
    response = client.post("/api/interviews", json={
        "title": "Test",
        "role": "Test",
        "experience_level": "Fresher",
        "skills": ["Test"],
        "interview_type": "Technical",
        "difficulty": "Easy",
        "mode": "text"
    })
    assert response.status_code == 401


def test_authenticated_can_create_interview(token_1):
    response = client.post("/api/interviews", json={
        "title": "Frontend Interview",
        "role": "Frontend Developer",
        "experience_level": "Fresher",
        "skills": ["React"],
        "interview_type": "Technical",
        "difficulty": "Easy",
        "mode": "text"
    }, headers={"Authorization": f"Bearer {token_1}"})
    
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "draft"


def test_user_cannot_access_another_users_interview(token_1, token_2):
    # User 1 creates interview
    resp1 = client.post("/api/interviews", json={
        "title": "Frontend Interview",
        "role": "Frontend",
        "experience_level": "Fresher",
        "skills": ["React"],
        "interview_type": "Technical",
        "difficulty": "Easy",
        "mode": "text"
    }, headers={"Authorization": f"Bearer {token_1}"})
    i_id = resp1.json()["id"]

    # User 2 tries to access it
    resp2 = client.get(f"/api/interviews/{i_id}", headers={"Authorization": f"Bearer {token_2}"})
    assert resp2.status_code == 404


def test_interview_lifecycle(token_1):
    # Create
    resp = client.post("/api/interviews", json={
        "title": "Frontend Interview",
        "role": "Frontend",
        "experience_level": "Fresher",
        "skills": ["React"],
        "interview_type": "Technical",
        "difficulty": "Easy",
        "mode": "text"
    }, headers={"Authorization": f"Bearer {token_1}"})
    i_id = resp.json()["id"]

    # Must add at least one question before starting (Phase 6 engine requirement)
    client.post(f"/api/interviews/{i_id}/questions", json={
        "question": "What is React?",
        "category": "React",
        "difficulty": "Easy"
    }, headers={"Authorization": f"Bearer {token_1}"})

    # Start
    start_resp = client.post(f"/api/interviews/{i_id}/start", headers={"Authorization": f"Bearer {token_1}"})
    assert start_resp.status_code == 200
    assert start_resp.json()["status"] == "in_progress"

    # Complete
    comp_resp = client.post(f"/api/interviews/{i_id}/complete", headers={"Authorization": f"Bearer {token_1}"})
    assert comp_resp.status_code == 200
    assert comp_resp.json()["status"] == "completed"

    # Invalid state transition (cannot start a completed interview)
    invalid_resp = client.post(f"/api/interviews/{i_id}/start", headers={"Authorization": f"Bearer {token_1}"})
    assert invalid_resp.status_code == 409


def test_questions_and_responses(token_1):
    """Test that questions can be added and responses submitted via the direct (Phase 3) route."""
    from unittest.mock import patch

    # Create interview
    resp = client.post("/api/interviews", json={
        "title": "Frontend Interview",
        "role": "Frontend",
        "experience_level": "Fresher",
        "skills": ["React"],
        "interview_type": "Technical",
        "difficulty": "Easy",
        "mode": "text"
    }, headers={"Authorization": f"Bearer {token_1}"})
    i_id = resp.json()["id"]

    # Add Question
    q_resp = client.post(f"/api/interviews/{i_id}/questions", json={
        "question": "What is React?",
        "category": "React",
        "difficulty": "Easy"
    }, headers={"Authorization": f"Bearer {token_1}"})
    assert q_resp.status_code == 201
    q_id = q_resp.json()["id"]

    # Start the interview so it's in_progress (required by Phase 6 engine)
    client.post(f"/api/interviews/{i_id}/start", headers={"Authorization": f"Bearer {token_1}"})

    # Submit Response via the engine endpoint (POST /questions/{q_id}/response)
    with patch("app.services.follow_up_service.generate_follow_up", return_value=None):
        r_resp = client.post(f"/api/interviews/{i_id}/questions/{q_id}/response", json={
            "answer": "It's a JS library"
        }, headers={"Authorization": f"Bearer {token_1}"})
    assert r_resp.status_code == 201
    assert r_resp.json()["answer"] == "It's a JS library"

    # Verify interview question_count updated
    get_resp = client.get(f"/api/interviews/{i_id}", headers={"Authorization": f"Bearer {token_1}"})
    assert get_resp.json()["question_count"] == 1


def test_delete_interview_cascades(token_1):
    resp = client.post("/api/interviews", json={
        "title": "Frontend Interview",
        "role": "Frontend",
        "experience_level": "Fresher",
        "skills": ["React"],
        "interview_type": "Technical",
        "difficulty": "Easy",
        "mode": "text"
    }, headers={"Authorization": f"Bearer {token_1}"})
    i_id = resp.json()["id"]

    q_resp = client.post(f"/api/interviews/{i_id}/questions", json={
        "question": "What is React?",
        "category": "React",
        "difficulty": "Easy"
    }, headers={"Authorization": f"Bearer {token_1}"})
    q_id = q_resp.json()["id"]

    client.post(f"/api/interviews/{i_id}/questions/{q_id}/response", json={
        "answer": "It's a JS library"
    }, headers={"Authorization": f"Bearer {token_1}"})

    # Delete interview
    del_resp = client.delete(f"/api/interviews/{i_id}", headers={"Authorization": f"Bearer {token_1}"})
    assert del_resp.status_code == 204

    # Verify everything is gone
    assert interviews_collection.count_documents({"_id": i_id}) == 0
    assert questions_collection.count_documents({"interview_id": i_id}) == 0
    assert responses_collection.count_documents({"interview_id": i_id}) == 0


def test_invalid_object_id_returns_404(token_1):
    resp = client.get("/api/interviews/not-a-valid-id", headers={"Authorization": f"Bearer {token_1}"})
    assert resp.status_code == 404
