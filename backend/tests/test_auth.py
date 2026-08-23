"""
tests/test_auth.py

Integration tests for authentication flows.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import users_collection

client = TestClient(app)

# Use a test email to easily clean up after tests
TEST_EMAIL = "testuser_auth@example.com"
TEST_PASSWORD = "supersecurepassword123"


@pytest.fixture(autouse=True)
def clean_db():
    """Fixture to run before each test to clean up the test user."""
    users_collection.delete_many({"email": TEST_EMAIL})
    yield
    users_collection.delete_many({"email": TEST_EMAIL})


def test_successful_registration():
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Test User",
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test User"
    assert data["email"] == TEST_EMAIL
    assert "password" not in data
    assert "password_hash" not in data
    assert "id" in data


def test_duplicate_email_registration():
    # Register once
    client.post(
        "/api/auth/register",
        json={"name": "Test", "email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    
    # Try registering again
    response = client.post(
        "/api/auth/register",
        json={"name": "Test 2", "email": TEST_EMAIL, "password": "otherpassword"}
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_successful_login():
    # Register
    client.post(
        "/api/auth/register",
        json={"name": "Test", "email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    
    # Login
    response = client.post(
        "/api/auth/login",
        data={"username": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_wrong_password_login():
    client.post(
        "/api/auth/register",
        json={"name": "Test", "email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    
    response = client.post(
        "/api/auth/login",
        data={"username": TEST_EMAIL, "password": "wrongpassword"}
    )
    assert response.status_code == 401


def test_unknown_email_login():
    response = client.post(
        "/api/auth/login",
        data={"username": "unknown@example.com", "password": TEST_PASSWORD}
    )
    assert response.status_code == 401


def test_get_me_with_valid_token():
    client.post(
        "/api/auth/register",
        json={"name": "Test", "email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    
    login_response = client.post(
        "/api/auth/login",
        data={"username": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    token = login_response.json()["access_token"]
    
    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == TEST_EMAIL


def test_get_me_without_token():
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_get_me_with_invalid_token():
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"}
    )
    assert response.status_code == 401
