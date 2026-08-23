"""
tests/test_health.py

Tests for the health check endpoints.
The basic health test does NOT require a live MongoDB instance.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root():
    """Root endpoint should return a welcome message."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data


def test_health_check():
    """GET /api/health should return status ok."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data
    assert "version" in data


def test_health_db_responds():
    """
    GET /api/health/db should return either:
    - 200 with database=connected (if MongoDB is running), or
    - 503 with database=disconnected (if MongoDB is not running).

    Either way, the endpoint should NOT crash the application.
    """
    response = client.get("/api/health/db")
    assert response.status_code in (200, 503)

    data = response.json()
    if response.status_code == 200:
        assert data["status"] == "ok"
        assert data["database"] == "connected"
    else:
        # 503 returns error detail
        assert data["detail"]["status"] == "error"
        assert data["detail"]["database"] == "disconnected"
