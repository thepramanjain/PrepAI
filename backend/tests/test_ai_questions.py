"""
tests/test_ai_questions.py

Tests for AI Question Generation logic.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import users_collection
from app.models.interview import interviews_collection
from app.models.question import questions_collection
from app.models.resume import resumes_collection

client = TestClient(app)

TEST_EMAIL = "testuser_ai_questions@example.com"
TEST_PASSWORD = "supersecurepassword123"

# Fake Gemini JSON Response
MOCK_GEMINI_RESPONSE_JSON = """
{
    "questions": [
        {
            "question": "Mock Question 1",
            "category": "React",
            "difficulty": "Medium"
        },
        {
            "question": "Mock Question 2",
            "category": "Python",
            "difficulty": "Hard"
        }
    ]
}
"""

def setup_user_and_get_token():
    # Register
    client.post(
        "/api/auth/register",
        json={"name": "Test User", "email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    # Login
    resp = client.post(
        "/api/auth/login",
        data={"username": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    return resp.json()["access_token"]


@pytest.fixture(autouse=True)
def clean_db():
    users_collection.delete_many({"email": TEST_EMAIL})
    interviews_collection.delete_many({})
    questions_collection.delete_many({})
    resumes_collection.delete_many({})
    yield
    users_collection.delete_many({"email": TEST_EMAIL})
    interviews_collection.delete_many({})
    questions_collection.delete_many({})
    resumes_collection.delete_many({})


@pytest.fixture
def token():
    return setup_user_and_get_token()


@pytest.fixture
def test_interview_id(token):
    resp = client.post("/api/interviews", json={
        "title": "Frontend Interview",
        "role": "Frontend Developer",
        "experience_level": "Fresher",
        "skills": ["React"],
        "interview_type": "Technical",
        "difficulty": "Medium",
        "mode": "text"
    }, headers={"Authorization": f"Bearer {token}"})
    return resp.json()["id"]


@patch("app.services.ai_question_service.gemini_wrapper.get_client")
def test_generate_questions_success(mock_get_client, token, test_interview_id):
    # Setup mock
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = MOCK_GEMINI_RESPONSE_JSON
    mock_client.models.generate_content.return_value = mock_response
    mock_get_client.return_value = mock_client
    
    # Also we need to ensure the wrapper has a model_name set for the test context
    with patch("app.services.ai_question_service.gemini_wrapper.model_name", "test-model"):
        response = client.post(
            f"/api/ai/interviews/{test_interview_id}/generate-questions",
            json={"question_count": 2},
            headers={"Authorization": f"Bearer {token}"}
        )
        
    assert response.status_code == 201
    data = response.json()
    assert data["count"] == 2
    assert len(data["questions"]) == 2
    
    q1 = data["questions"][0]
    assert q1["question"] == "Mock Question 1"
    assert q1["source"] == "gemini"


@patch("app.services.ai_question_service.gemini_wrapper.get_client")
def test_generate_questions_invalid_json(mock_get_client, token, test_interview_id):
    # Setup mock returning invalid JSON
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "this is not json"
    mock_client.models.generate_content.return_value = mock_response
    mock_get_client.return_value = mock_client
    
    with patch("app.services.ai_question_service.gemini_wrapper.model_name", "test-model"):
        response = client.post(
            f"/api/ai/interviews/{test_interview_id}/generate-questions",
            json={"question_count": 2},
            headers={"Authorization": f"Bearer {token}"}
        )
        
    # Should handle parsing error
    assert response.status_code == 500
    assert "validate structured AI response" in response.json()["detail"]


@patch("app.services.ai_question_service.gemini_wrapper.get_client")
def test_generate_questions_rate_limit(mock_get_client, token, test_interview_id):
    # Setup mock raising an exception mimicking rate limit
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("429 Resource exhausted")
    mock_get_client.return_value = mock_client
    
    with patch("app.services.ai_question_service.gemini_wrapper.model_name", "test-model"):
        response = client.post(
            f"/api/ai/interviews/{test_interview_id}/generate-questions",
            json={"question_count": 2},
            headers={"Authorization": f"Bearer {token}"}
        )
        
    assert response.status_code == 429
    assert "rate limit" in response.json()["detail"]


def test_generate_questions_unauthorized(test_interview_id):
    response = client.post(
        f"/api/ai/interviews/{test_interview_id}/generate-questions",
        json={"question_count": 2},
        # Missing auth header
    )
    assert response.status_code == 401


def test_generate_questions_invalid_count(token, test_interview_id):
    response = client.post(
        f"/api/ai/interviews/{test_interview_id}/generate-questions",
        json={"question_count": 50}, # over limit
        headers={"Authorization": f"Bearer {token}"}
    )
    # Pydantic validation handles this
    assert response.status_code == 422
