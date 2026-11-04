"""
tests/test_ai_questions.py

Comprehensive tests for AI Question Generation logic:
- Gemini primary success
- Gemini 503 with retry recovery
- Gemini 503 exhausting retries with OpenRouter fallback
- OpenRouter structured output parsing and difficulty normalization
- Invalid or empty AI output handling
- Both providers failing (clean 503 error)
- Verification that retrying/regeneration never creates duplicate questions
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.interview import interviews_collection
from app.models.question import questions_collection
from app.models.resume import resumes_collection
from app.models.user import users_collection

client = TestClient(app)

TEST_EMAIL = "testuser_ai_questions@example.com"
TEST_PASSWORD = "supersecurepassword123"

# Mock Gemini JSON Response
MOCK_GEMINI_RESPONSE_JSON = """
{
    "questions": [
        {
            "question": "Explain the difference between React state and props.",
            "category": "React",
            "difficulty": "Medium"
        },
        {
            "question": "How does the Python GIL affect multithreaded performance?",
            "category": "Python",
            "difficulty": "Hard"
        }
    ]
}
"""

# Mock OpenRouter JSON Response (with markdown fences to test fence stripping)
MOCK_OPENROUTER_RESPONSE_JSON = """```json
{
    "questions": [
        {
            "question": "What is the event loop in Node.js?",
            "category": "Backend",
            "difficulty": "medium"
        },
        {
            "question": "Explain database indexing and B-trees.",
            "category": "Databases",
            "difficulty": "hard"
        }
    ]
}
```"""


def setup_user_and_get_token():
    client.post(
        "/api/auth/register",
        json={"name": "Test User", "email": TEST_EMAIL, "password": TEST_PASSWORD},
    )
    resp = client.post(
        "/api/auth/login",
        data={"username": TEST_EMAIL, "password": TEST_PASSWORD},
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
    resp = client.post(
        "/api/interviews",
        json={
            "title": "Frontend Interview",
            "role": "Frontend Developer",
            "experience_level": "Fresher",
            "skills": ["React"],
            "interview_type": "Technical",
            "difficulty": "Medium",
            "mode": "text",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# 1. Gemini primary success
# ---------------------------------------------------------------------------

@patch("app.services.ai_question_service.gemini_wrapper.get_client")
def test_generate_questions_gemini_success(mock_get_client, token, test_interview_id):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = MOCK_GEMINI_RESPONSE_JSON
    mock_client.models.generate_content.return_value = mock_response
    mock_get_client.return_value = mock_client

    with patch("app.services.ai_question_service.gemini_wrapper.model_name", "gemini-3.8-flash"):
        response = client.post(
            f"/api/ai/interviews/{test_interview_id}/generate-questions",
            json={"question_count": 2},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["count"] == 2
    assert len(data["questions"]) == 2

    q1 = data["questions"][0]
    assert q1["question"] == "Explain the difference between React state and props."
    assert q1["source"] == "gemini"
    assert q1["difficulty"] == "Medium"
    assert q1["question_number"] == 1


# ---------------------------------------------------------------------------
# 2. Gemini 503 with retry recovery
# ---------------------------------------------------------------------------

@patch("app.services.ai_question_service.gemini_wrapper.get_client")
def test_generate_questions_gemini_503_retry_success(mock_get_client, token, test_interview_id):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = MOCK_GEMINI_RESPONSE_JSON

    # Fail first with 503 UNAVAILABLE, then succeed on second attempt
    mock_client.models.generate_content.side_effect = [
        Exception("503 UNAVAILABLE: This model is currently experiencing high demand."),
        mock_response,
    ]
    mock_get_client.return_value = mock_client

    with patch("app.services.ai_question_service.gemini_wrapper.model_name", "gemini-3.8-flash"):
        response = client.post(
            f"/api/ai/interviews/{test_interview_id}/generate-questions",
            json={"question_count": 2},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["count"] == 2
    assert data["questions"][0]["source"] == "gemini"
    assert mock_client.models.generate_content.call_count == 2


# ---------------------------------------------------------------------------
# 3. Gemini 503 exhausts retries -> Fallback to OpenRouter
# ---------------------------------------------------------------------------

@patch("app.services.ai_question_service._get_openrouter_client")
@patch("app.services.ai_question_service.gemini_wrapper.get_client")
def test_generate_questions_gemini_503_fallback_to_openrouter(
    mock_get_client, mock_get_or_client, token, test_interview_id
):
    # Gemini consistently raises 503 across all 3 retries
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception(
        "503 UNAVAILABLE: This model is currently experiencing high demand."
    )
    mock_get_client.return_value = mock_client

    # OpenRouter mock
    mock_or_client = MagicMock()
    mock_or_client.is_configured.return_value = True
    mock_or_client.model = "openai/gpt-4o"
    mock_or_client.fallback_model = "openai/gpt-4o-mini"

    mock_chat_resp = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = MOCK_OPENROUTER_RESPONSE_JSON
    mock_chat_resp.choices = [mock_choice]
    mock_or_client.chat_completion.return_value = mock_chat_resp
    mock_get_or_client.return_value = mock_or_client

    response = client.post(
        f"/api/ai/interviews/{test_interview_id}/generate-questions",
        json={"question_count": 2},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["count"] == 2
    assert data["questions"][0]["source"] == "openrouter"
    assert data["questions"][0]["question"] == "What is the event loop in Node.js?"
    assert data["questions"][0]["difficulty"] == "Medium"  # Normalized from "medium"
    assert mock_or_client.chat_completion.called



# ---------------------------------------------------------------------------
# 3b. OpenRouter 402 on primary model -> Fallback to GPT-4o-mini
# ---------------------------------------------------------------------------

@patch("app.ai.openrouter_client.openrouter_client._call_once")
@patch("app.services.ai_question_service.gemini_wrapper.get_client")
def test_generate_questions_openrouter_402_fallback_to_mini(
    mock_gemini_client, mock_or_call_once, token, test_interview_id
):
    from openai import APIStatusError
    from unittest.mock import MagicMock
    from app.ai.openrouter_client import openrouter_client

    # 1. Gemini fails with 503
    mock_gemini = MagicMock()
    mock_gemini.models.generate_content.side_effect = Exception("503 UNAVAILABLE: high demand")
    mock_gemini_client.return_value = mock_gemini

    # 2. OpenRouter primary (GPT-4o) fails with 402 affordable limit
    payment_error = APIStatusError(
        message="402 Payment Required: max_tokens exceeds the affordable token limit of 3907",
        response=MagicMock(status_code=402),
        body={},
    )
    # 3. OpenRouter fallback (GPT-4o-mini) succeeds
    mini_response = MagicMock()
    mini_choice = MagicMock()
    mini_choice.message.content = MOCK_OPENROUTER_RESPONSE_JSON
    mini_response.choices = [mini_choice]

    mock_or_call_once.side_effect = [payment_error, mini_response]

    with patch.object(openrouter_client, "_client", MagicMock()):
        with patch.object(openrouter_client, "api_key", "sk-test"):
            response = client.post(
                f"/api/ai/interviews/{test_interview_id}/generate-questions",
                json={"question_count": 2},
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 201
    data = response.json()
    assert data["count"] == 2
    assert data["questions"][0]["source"] == "openrouter"
    assert mock_or_call_once.call_count == 2

# ---------------------------------------------------------------------------
# 4. OpenRouter structured output parsing and difficulty normalization
# ---------------------------------------------------------------------------

@patch("app.services.ai_question_service._get_openrouter_client")
@patch("app.services.ai_question_service.gemini_wrapper.get_client")
def test_generate_questions_openrouter_normalization(
    mock_get_client, mock_get_or_client, token, test_interview_id
):
    # Gemini unconfigured
    mock_get_client.side_effect = ValueError("Gemini key missing")

    mock_or_client = MagicMock()
    mock_or_client.is_configured.return_value = True
    raw_payload = json.dumps({
        "questions": [
            {"question": "Q1", "category": "General", "difficulty": "EASY"},
            {"question": "Q2", "category": "DevOps", "difficulty": "EXPERT"},
        ]
    })
    mock_chat_resp = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = raw_payload
    mock_chat_resp.choices = [mock_choice]
    mock_or_client.chat_completion.return_value = mock_chat_resp
    mock_get_or_client.return_value = mock_or_client

    response = client.post(
        f"/api/ai/interviews/{test_interview_id}/generate-questions",
        json={"question_count": 2},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["questions"][0]["difficulty"] == "Easy"
    assert data["questions"][1]["difficulty"] == "Expert"


# ---------------------------------------------------------------------------
# 5. Invalid / empty output handling
# ---------------------------------------------------------------------------

@patch("app.services.ai_question_service._get_openrouter_client")
@patch("app.services.ai_question_service.gemini_wrapper.get_client")
def test_generate_questions_invalid_output(
    mock_get_client, mock_get_or_client, token, test_interview_id
):
    # Gemini returns empty JSON questions
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = '{"questions": []}'
    mock_client.models.generate_content.return_value = mock_resp
    mock_get_client.return_value = mock_client

    # OpenRouter returns non-JSON garbage
    mock_or_client = MagicMock()
    mock_or_client.is_configured.return_value = True
    mock_chat_resp = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "I am an AI and cannot help with that."
    mock_chat_resp.choices = [mock_choice]
    mock_or_client.chat_completion.return_value = mock_chat_resp
    mock_get_or_client.return_value = mock_or_client

    response = client.post(
        f"/api/ai/interviews/{test_interview_id}/generate-questions",
        json={"question_count": 2},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 503
    assert "currently unavailable" in response.json()["detail"]


# ---------------------------------------------------------------------------
# 6. Both providers fail
# ---------------------------------------------------------------------------

@patch("app.services.ai_question_service._get_openrouter_client")
@patch("app.services.ai_question_service.gemini_wrapper.get_client")
def test_generate_questions_both_providers_fail(
    mock_get_client, mock_get_or_client, token, test_interview_id
):
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("503 UNAVAILABLE")
    mock_get_client.return_value = mock_client

    mock_or_client = MagicMock()
    mock_or_client.is_configured.return_value = True
    mock_or_client.chat_completion.side_effect = Exception("OpenRouter 429 RateLimit")
    mock_get_or_client.return_value = mock_or_client

    response = client.post(
        f"/api/ai/interviews/{test_interview_id}/generate-questions",
        json={"question_count": 2},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert "Gemini failed" in detail
    assert "OpenRouter fallback failed" in detail

    # Ensure no orphan questions were saved to DB
    saved_count = questions_collection.count_documents({})
    assert saved_count == 0


# ---------------------------------------------------------------------------
# 7. No duplicate questions on regeneration
# ---------------------------------------------------------------------------

@patch("app.services.ai_question_service.gemini_wrapper.get_client")
def test_generate_questions_no_duplicate_questions_on_regeneration(
    mock_get_client, token, test_interview_id
):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = MOCK_GEMINI_RESPONSE_JSON
    mock_client.models.generate_content.return_value = mock_response
    mock_get_client.return_value = mock_client

    # First generation
    resp1 = client.post(
        f"/api/ai/interviews/{test_interview_id}/generate-questions",
        json={"question_count": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp1.status_code == 201
    assert questions_collection.count_documents({}) == 2

    # Second generation (regeneration)
    resp2 = client.post(
        f"/api/ai/interviews/{test_interview_id}/generate-questions",
        json={"question_count": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.status_code == 201
    # Count must remain exactly 2, not 4
    assert questions_collection.count_documents({}) == 2


# ---------------------------------------------------------------------------
# 8. Validation and authorization checks
# ---------------------------------------------------------------------------

def test_generate_questions_unauthorized(test_interview_id):
    response = client.post(
        f"/api/ai/interviews/{test_interview_id}/generate-questions",
        json={"question_count": 2},
    )
    assert response.status_code == 401


def test_generate_questions_invalid_count(token, test_interview_id):
    response = client.post(
        f"/api/ai/interviews/{test_interview_id}/generate-questions",
        json={"question_count": 50},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
