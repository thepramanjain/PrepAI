"""
tests/test_analytics.py

Integration tests for Phase 8 — Analytics & Performance Tracking.

Isolation contract:
  - clean_db deletes ONLY documents belonging to TEST_EMAIL / TEST_EMAIL_2.
  - It never calls delete_many({}) on shared collections, which would corrupt
    other test files when running the full suite.
  - seeded has its own yield teardown as a safety net.
  - Data is inserted directly into MongoDB (no Gemini API calls).
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Optional
from bson import ObjectId
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import users_collection
from app.models.interview import interviews_collection
from app.models.feedback import feedback_collection

client = TestClient(app)

TEST_EMAIL = "analytics_test@example.com"
TEST_EMAIL_2 = "analytics_other@example.com"
TEST_PASSWORD = "analyticspassword123"

# ---------------------------------------------------------------------------
# Known test data values
# ---------------------------------------------------------------------------
# Interview 1: 60 days ago  — score 65  — Frontend Developer / Technical / Easy
# Interview 2: 20 days ago  — score 75  — Frontend Developer / Technical / Medium
# Interview 3:  3 days ago  — score 85  — Backend Developer  / Behavioral / Hard
#
# Derived expectations:
#   average_score   = (65+75+85) / 3 = 75.0
#   best_score      = 85
#   lowest_score    = 65
#   latest_score    = 85 (most recent)
#   category avg    = technical: (60+75+88)/3=74.33, comm: (70+72+82)/3=74.67,
#                     ps: (65+78+86)/3=76.33, rel: (65+75+84)/3=74.67
#   improvement     = earlier=[65], recent=[75,85]→80.0
#                     diff=15.0, trend="improving"
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Low-level DB helpers (safe — user-scoped, never delete all)
# ---------------------------------------------------------------------------

def _delete_user_data(email: str) -> None:
    """Delete the user and ALL their interviews + feedback from the DB."""
    user = users_collection.find_one({"email": email})
    if user:
        uid = user["_id"]
        feedback_collection.delete_many({"user_id": uid})
        interviews_collection.delete_many({"user_id": uid})
    users_collection.delete_many({"email": email})


def _register_and_login(email: str = TEST_EMAIL) -> str:
    """Register a fresh user (must not already exist) and return an access token."""
    reg = client.post(
        "/api/auth/register",
        json={"name": "Analytics User", "email": email, "password": TEST_PASSWORD},
    )
    assert reg.status_code == 201, f"Registration failed: {reg.text}"
    login = client.post(
        "/api/auth/login", data={"username": email, "password": TEST_PASSWORD}
    )
    assert login.status_code == 200, f"Login failed: {login.text}"
    return login.json()["access_token"]


def _get_user_id(token: str) -> str:
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, f"/api/auth/me failed: {resp.text}"
    data = resp.json()
    assert "id" in data, f"/api/auth/me response has no 'id' field: {data}"
    return data["id"]


def _build_interview(user_obj_id: ObjectId, days_ago: int, **overrides) -> dict:
    """Build a completed interview document."""
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    doc = {
        "user_id": user_obj_id,
        "title": "Test Interview",
        "role": "Frontend Developer",
        "experience_level": "1-3 years",
        "skills": ["React"],
        "interview_type": "Technical",
        "difficulty": "Medium",
        "mode": "text",
        "status": "completed",
        "question_count": 3,
        "resume_id": None,
        "job_description": None,
        "current_question_id": None,
        "current_question_number": None,
        "created_at": ts,
        "updated_at": ts,
        "started_at": ts,
        "completed_at": ts,
    }
    doc.update(overrides)
    return doc


def _build_feedback(
    user_obj_id: ObjectId,
    interview_id: ObjectId,
    days_ago: int,
    overall_score: int,
    **overrides,
) -> dict:
    """Build an evaluated feedback document."""
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    doc = {
        "interview_id": interview_id,
        "user_id": user_obj_id,
        "overall_score": overall_score,
        "category_scores": {
            "technical": overall_score,
            "communication": overall_score,
            "problem_solving": overall_score,
            "relevance": overall_score,
        },
        "question_evaluations": [],
        "strengths": ["Good structure"],
        "weaknesses": ["Lacks examples"],
        "recommendations": ["Practice more"],
        "topic_analysis": [{"topic": "React", "score": overall_score, "assessment": "Good"}],
        "summary": "Test summary.",
        "created_at": ts,
        "updated_at": ts,
    }
    doc.update(overrides)
    return doc


def _seed_test_data(user_id_str: str) -> list:
    """
    Insert 3 controlled interviews + feedback directly into MongoDB.
    Returns list of interview_id strings.
    """
    uid = ObjectId(user_id_str)

    entries = [
        {
            "interview": _build_interview(
                uid, days_ago=60,
                title="Frontend Interview 1",
                role="Frontend Developer",
                interview_type="Technical",
                difficulty="Easy",
            ),
            "feedback_overrides": {
                "overall_score": 65,
                "category_scores": {
                    "technical": 60,
                    "communication": 70,
                    "problem_solving": 65,
                    "relevance": 65,
                },
                "strengths": ["Clear communication", "Good problem structure"],
                "weaknesses": ["Lacks practical examples", "Needs more depth"],
                "topic_analysis": [
                    {"topic": "React", "score": 65, "assessment": "Average"},
                    {"topic": "JavaScript", "score": 60, "assessment": "Average"},
                ],
            },
        },
        {
            "interview": _build_interview(
                uid, days_ago=20,
                title="Frontend Interview 2",
                role="Frontend Developer",
                interview_type="Technical",
                difficulty="Medium",
            ),
            "feedback_overrides": {
                "overall_score": 75,
                "category_scores": {
                    "technical": 75,
                    "communication": 72,
                    "problem_solving": 78,
                    "relevance": 75,
                },
                "strengths": ["Clear communication", "Structured thinking"],
                "weaknesses": ["Lacks practical examples"],
                "topic_analysis": [
                    {"topic": "React", "score": 78, "assessment": "Good"},
                    {"topic": "CSS", "score": 72, "assessment": "Good"},
                ],
            },
        },
        {
            "interview": _build_interview(
                uid, days_ago=3,
                title="Backend Interview",
                role="Backend Developer",
                interview_type="Behavioral",
                difficulty="Hard",
            ),
            "feedback_overrides": {
                "overall_score": 85,
                "category_scores": {
                    "technical": 88,
                    "communication": 82,
                    "problem_solving": 86,
                    "relevance": 84,
                },
                "strengths": ["Strong technical knowledge", "Good structure"],
                "weaknesses": ["Could improve on speed"],
                "topic_analysis": [
                    {"topic": "Python", "score": 88, "assessment": "Strong"},
                    {"topic": "FastAPI", "score": 82, "assessment": "Good"},
                ],
            },
        },
    ]

    interview_ids = []
    for item in entries:
        r = interviews_collection.insert_one(item["interview"])
        iid = r.inserted_id
        completed_at = item["interview"]["completed_at"]
        fb = _build_feedback(uid, iid, days_ago=0, overall_score=0)
        fb.update(item["feedback_overrides"])
        fb["created_at"] = completed_at
        fb["updated_at"] = completed_at
        feedback_collection.insert_one(fb)
        interview_ids.append(str(iid))

    return interview_ids


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_db():
    """
    Safe isolation: delete ONLY the test users and their owned documents.

    IMPORTANT: Never calls delete_many({}) on shared collections.
    That would corrupt data created by other test files when running
    the full suite with `pytest tests/`.
    """
    _delete_user_data(TEST_EMAIL)
    _delete_user_data(TEST_EMAIL_2)
    yield
    _delete_user_data(TEST_EMAIL)
    _delete_user_data(TEST_EMAIL_2)


@pytest.fixture
def auth():
    """
    Create a fresh TEST_EMAIL user (clean_db already deleted any prior one)
    and return (token, user_id_str, auth_headers).
    """
    token = _register_and_login(TEST_EMAIL)
    user_id = _get_user_id(token)
    headers = {"Authorization": f"Bearer {token}"}
    return token, user_id, headers


@pytest.fixture
def seeded(auth):
    """
    Seed 3 controlled interviews + feedback for the primary test user.
    Returns (token, user_id, headers, interview_ids).
    Also has its own yield teardown as an extra safety net.
    """
    token, user_id, headers = auth
    iids = _seed_test_data(user_id)
    yield token, user_id, headers, iids
    # Safety-net teardown: delete only THIS user's seeded data
    uid = ObjectId(user_id)
    feedback_collection.delete_many({"user_id": uid})
    interviews_collection.delete_many({"user_id": uid})


# ---------------------------------------------------------------------------
# 1. Authentication
# ---------------------------------------------------------------------------

class TestAuthentication:
    ALL_ENDPOINTS = [
        "/api/analytics",
        "/api/analytics/overview",
        "/api/analytics/score-trend",
        "/api/analytics/categories",
        "/api/analytics/topics",
        "/api/analytics/strengths",
        "/api/analytics/weaknesses",
        "/api/analytics/history",
        "/api/analytics/interview-types",
        "/api/analytics/difficulty",
        "/api/analytics/roles",
        "/api/analytics/improvement",
    ]

    def test_unauthenticated_rejected(self):
        """Every analytics endpoint must reject unauthenticated requests."""
        for endpoint in self.ALL_ENDPOINTS:
            resp = client.get(endpoint)
            assert resp.status_code == 401, f"{endpoint} should require auth"

    def test_authenticated_can_access(self, auth):
        _, _, headers = auth
        resp = client.get("/api/analytics/overview", headers=headers)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 2. User Isolation
# ---------------------------------------------------------------------------

class TestUserIsolation:
    def test_other_user_sees_empty_data(self, seeded):
        """A second user sees their own (empty) analytics, not user 1's data."""
        token2 = _register_and_login(TEST_EMAIL_2)
        headers2 = {"Authorization": f"Bearer {token2}"}

        resp = client.get("/api/analytics/overview", headers=headers2)
        assert resp.status_code == 200
        data = resp.json()
        assert data["evaluated_interviews"] == 0
        assert data["average_score"] is None
        assert data["best_score"] is None


# ---------------------------------------------------------------------------
# 3. Overview
# ---------------------------------------------------------------------------

class TestOverview:
    def test_overview_with_data(self, seeded):
        _, _, headers, _ = seeded
        resp = client.get("/api/analytics/overview", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_interviews"] == 3
        assert data["completed_interviews"] == 3
        assert data["evaluated_interviews"] == 3
        assert data["average_score"] == 75.0        # (65+75+85)/3
        assert data["best_score"] == 85
        assert data["lowest_score"] == 65
        assert data["latest_score"] == 85

    def test_overview_empty(self, auth):
        _, _, headers = auth
        resp = client.get("/api/analytics/overview", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_interviews"] == 0
        assert data["evaluated_interviews"] == 0
        assert data["average_score"] is None
        assert data["best_score"] is None
        assert data["lowest_score"] is None
        assert data["latest_score"] is None

    def test_average_score_calculation(self, seeded):
        _, _, headers, _ = seeded
        resp = client.get("/api/analytics/overview", headers=headers)
        avg = resp.json()["average_score"]
        assert avg == round((65 + 75 + 85) / 3, 2)

    def test_best_score(self, seeded):
        _, _, headers, _ = seeded
        data = client.get("/api/analytics/overview", headers=headers).json()
        assert data["best_score"] == 85

    def test_lowest_score(self, seeded):
        _, _, headers, _ = seeded
        data = client.get("/api/analytics/overview", headers=headers).json()
        assert data["lowest_score"] == 65

    def test_latest_score(self, seeded):
        _, _, headers, _ = seeded
        data = client.get("/api/analytics/overview", headers=headers).json()
        assert data["latest_score"] == 85


# ---------------------------------------------------------------------------
# 4. Score Trend
# ---------------------------------------------------------------------------

class TestScoreTrend:
    def test_score_trend_order(self, seeded):
        """Scores must be sorted oldest → newest."""
        _, _, headers, _ = seeded
        resp = client.get("/api/analytics/score-trend", headers=headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 3
        scores = [item["score"] for item in data]
        assert scores == [65, 75, 85]  # chronological

    def test_score_trend_empty(self, auth):
        _, _, headers = auth
        resp = client.get("/api/analytics/score-trend", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_score_trend_has_required_fields(self, seeded):
        _, _, headers, _ = seeded
        item = client.get("/api/analytics/score-trend", headers=headers).json()["data"][0]
        assert "interview_id" in item
        assert "title" in item
        assert "date" in item
        assert "score" in item


# ---------------------------------------------------------------------------
# 5. Category Performance
# ---------------------------------------------------------------------------

class TestCategoryPerformance:
    def test_category_averages(self, seeded):
        _, _, headers, _ = seeded
        resp = client.get("/api/analytics/categories", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["technical"] == round((60 + 75 + 88) / 3, 2)
        assert data["communication"] == round((70 + 72 + 82) / 3, 2)
        assert data["problem_solving"] == round((65 + 78 + 86) / 3, 2)
        assert data["relevance"] == round((65 + 75 + 84) / 3, 2)

    def test_categories_empty(self, auth):
        _, _, headers = auth
        resp = client.get("/api/analytics/categories", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["technical"] is None
        assert data["communication"] is None


# ---------------------------------------------------------------------------
# 6. Topic Performance
# ---------------------------------------------------------------------------

class TestTopicPerformance:
    def test_topic_aggregation(self, seeded):
        _, _, headers, _ = seeded
        resp = client.get("/api/analytics/topics", headers=headers)
        assert resp.status_code == 200
        topics = resp.json()["topics"]
        assert len(topics) > 0
        topic_names = {t["topic"] for t in topics}
        assert "React" in topic_names

    def test_topic_sorted_by_score_desc(self, seeded):
        _, _, headers, _ = seeded
        topics = client.get("/api/analytics/topics", headers=headers).json()["topics"]
        scores = [t["average_score"] for t in topics]
        assert scores == sorted(scores, reverse=True)

    def test_topic_react_count(self, seeded):
        """React appears in 2 of 3 interviews."""
        _, _, headers, _ = seeded
        topics = client.get("/api/analytics/topics", headers=headers).json()["topics"]
        react = next(t for t in topics if t["topic"] == "React")
        assert react["interviews_count"] == 2

    def test_topic_limit(self, seeded):
        _, _, headers, _ = seeded
        resp = client.get("/api/analytics/topics?limit=2", headers=headers)
        topics = resp.json()["topics"]
        assert len(topics) <= 2

    def test_topic_empty(self, auth):
        _, _, headers = auth
        resp = client.get("/api/analytics/topics", headers=headers)
        assert resp.json()["topics"] == []


# ---------------------------------------------------------------------------
# 7. Strengths
# ---------------------------------------------------------------------------

class TestStrengths:
    def test_strengths_aggregated(self, seeded):
        _, _, headers, _ = seeded
        resp = client.get("/api/analytics/strengths", headers=headers)
        assert resp.status_code == 200
        strengths = resp.json()["strengths"]
        assert len(strengths) > 0

    def test_strength_count_accuracy(self, seeded):
        """'Clear communication' appears in interviews 1 and 2 → count=2."""
        _, _, headers, _ = seeded
        strengths = client.get("/api/analytics/strengths", headers=headers).json()["strengths"]
        clear_comm = next(
            (s for s in strengths if s["text"].lower() == "clear communication"), None
        )
        assert clear_comm is not None
        assert clear_comm["count"] == 2

    def test_strengths_sorted_by_count_desc(self, seeded):
        _, _, headers, _ = seeded
        strengths = client.get("/api/analytics/strengths", headers=headers).json()["strengths"]
        counts = [s["count"] for s in strengths]
        assert counts == sorted(counts, reverse=True)

    def test_strengths_empty(self, auth):
        _, _, headers = auth
        assert client.get("/api/analytics/strengths", headers=headers).json()["strengths"] == []


# ---------------------------------------------------------------------------
# 8. Weaknesses
# ---------------------------------------------------------------------------

class TestWeaknesses:
    def test_weaknesses_aggregated(self, seeded):
        _, _, headers, _ = seeded
        resp = client.get("/api/analytics/weaknesses", headers=headers)
        assert resp.status_code == 200
        weaknesses = resp.json()["weaknesses"]
        assert len(weaknesses) > 0

    def test_weakness_count_accuracy(self, seeded):
        """'Lacks practical examples' appears in interviews 1 and 2 → count=2."""
        _, _, headers, _ = seeded
        weaknesses = client.get("/api/analytics/weaknesses", headers=headers).json()["weaknesses"]
        repeated = next(
            (w for w in weaknesses if w["text"].lower() == "lacks practical examples"), None
        )
        assert repeated is not None
        assert repeated["count"] == 2

    def test_weaknesses_sorted_desc(self, seeded):
        _, _, headers, _ = seeded
        weaknesses = client.get("/api/analytics/weaknesses", headers=headers).json()["weaknesses"]
        counts = [w["count"] for w in weaknesses]
        assert counts == sorted(counts, reverse=True)

    def test_weaknesses_empty(self, auth):
        _, _, headers = auth
        assert client.get("/api/analytics/weaknesses", headers=headers).json()["weaknesses"] == []


# ---------------------------------------------------------------------------
# 9. Interview History
# ---------------------------------------------------------------------------

class TestInterviewHistory:
    def test_history_returns_completed_interviews(self, seeded):
        _, _, headers, _ = seeded
        resp = client.get("/api/analytics/history", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    def test_history_sorted_newest_first(self, seeded):
        _, _, headers, _ = seeded
        items = client.get("/api/analytics/history", headers=headers).json()["items"]
        scores = [i["score"] for i in items]
        assert scores[0] == 85
        assert scores[-1] == 65

    def test_history_has_required_fields(self, seeded):
        _, _, headers, _ = seeded
        item = client.get("/api/analytics/history", headers=headers).json()["items"][0]
        for field in ["interview_id", "title", "role", "interview_type", "difficulty", "score", "date"]:
            assert field in item

    def test_pagination(self, seeded):
        _, _, headers, _ = seeded
        page1 = client.get("/api/analytics/history?page=1&limit=2", headers=headers).json()
        assert len(page1["items"]) == 2
        assert page1["total"] == 3
        assert page1["page"] == 1
        assert page1["limit"] == 2

        page2 = client.get("/api/analytics/history?page=2&limit=2", headers=headers).json()
        assert len(page2["items"]) == 1

    def test_pagination_page_beyond_total(self, seeded):
        _, _, headers, _ = seeded
        data = client.get("/api/analytics/history?page=100&limit=10", headers=headers).json()
        assert data["items"] == []
        assert data["total"] == 3

    def test_history_empty(self, auth):
        _, _, headers = auth
        data = client.get("/api/analytics/history", headers=headers).json()
        assert data["total"] == 0
        assert data["items"] == []


# ---------------------------------------------------------------------------
# 10. Interview Type Performance
# ---------------------------------------------------------------------------

class TestInterviewTypePerformance:
    def test_type_performance(self, seeded):
        _, _, headers, _ = seeded
        resp = client.get("/api/analytics/interview-types", headers=headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 2  # Technical + Behavioral
        types = {d["type"] for d in data}
        assert "Technical" in types
        assert "Behavioral" in types

    def test_type_average_score(self, seeded):
        _, _, headers, _ = seeded
        data = client.get("/api/analytics/interview-types", headers=headers).json()["data"]
        technical = next(d for d in data if d["type"] == "Technical")
        assert technical["average_score"] == round((65 + 75) / 2, 2)
        assert technical["count"] == 2

    def test_type_empty(self, auth):
        _, _, headers = auth
        data = client.get("/api/analytics/interview-types", headers=headers).json()["data"]
        assert data == []


# ---------------------------------------------------------------------------
# 11. Difficulty Performance
# ---------------------------------------------------------------------------

class TestDifficultyPerformance:
    def test_difficulty_performance(self, seeded):
        _, _, headers, _ = seeded
        resp = client.get("/api/analytics/difficulty", headers=headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 3
        difficulties = {d["difficulty"] for d in data}
        assert {"Easy", "Medium", "Hard"} == difficulties

    def test_difficulty_only_returns_existing_levels(self, seeded):
        _, _, headers, _ = seeded
        data = client.get("/api/analytics/difficulty", headers=headers).json()["data"]
        assert all(d["difficulty"] != "Expert" for d in data)

    def test_difficulty_empty(self, auth):
        _, _, headers = auth
        data = client.get("/api/analytics/difficulty", headers=headers).json()["data"]
        assert data == []


# ---------------------------------------------------------------------------
# 12. Role Performance
# ---------------------------------------------------------------------------

class TestRolePerformance:
    def test_role_performance(self, seeded):
        _, _, headers, _ = seeded
        resp = client.get("/api/analytics/roles", headers=headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        roles = {d["role"] for d in data}
        assert "Frontend Developer" in roles
        assert "Backend Developer" in roles

    def test_role_average_score(self, seeded):
        _, _, headers, _ = seeded
        data = client.get("/api/analytics/roles", headers=headers).json()["data"]
        frontend = next(d for d in data if d["role"] == "Frontend Developer")
        assert frontend["average_score"] == round((65 + 75) / 2, 2)
        assert frontend["count"] == 2

    def test_role_empty(self, auth):
        _, _, headers = auth
        data = client.get("/api/analytics/roles", headers=headers).json()["data"]
        assert data == []


# ---------------------------------------------------------------------------
# 13. Improvement Analysis
# ---------------------------------------------------------------------------

class TestImprovementAnalysis:
    def test_improvement_with_3_interviews(self, seeded):
        """
        3 scores sorted: [65, 75, 85]
        mid=1 → earlier=[65], recent=[75, 85]→avg=80
        diff=15, pct=23.08, trend=improving
        """
        _, _, headers, _ = seeded
        resp = client.get("/api/analytics/improvement", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["previous_average"] == 65.0
        assert data["recent_average"] == 80.0
        assert data["score_difference"] == 15.0
        assert data["trend"] == "improving"
        assert data["improvement_percentage"] == round((15.0 / 65.0) * 100, 2)

    def test_improvement_insufficient_data_zero_interviews(self, auth):
        _, _, headers = auth
        data = client.get("/api/analytics/improvement", headers=headers).json()
        assert data["trend"] == "insufficient_data"
        assert data["previous_average"] is None
        assert data["recent_average"] is None

    def test_improvement_insufficient_data_one_interview(self, auth):
        _, user_id, headers = auth
        uid = ObjectId(user_id)
        r = interviews_collection.insert_one(
            _build_interview(uid, days_ago=10, title="Solo Interview")
        )
        feedback_collection.insert_one(
            _build_feedback(uid, r.inserted_id, days_ago=10, overall_score=72)
        )
        data = client.get("/api/analytics/improvement", headers=headers).json()
        assert data["trend"] == "insufficient_data"

    def test_declining_trend(self, auth):
        _, user_id, headers = auth
        uid = ObjectId(user_id)
        # Old interview: high score
        r1 = interviews_collection.insert_one(
            _build_interview(uid, days_ago=30, title="High Score Interview")
        )
        feedback_collection.insert_one(
            _build_feedback(uid, r1.inserted_id, days_ago=30, overall_score=90)
        )
        # Recent interview: low score
        r2 = interviews_collection.insert_one(
            _build_interview(uid, days_ago=5, title="Low Score Interview")
        )
        feedback_collection.insert_one(
            _build_feedback(uid, r2.inserted_id, days_ago=5, overall_score=60)
        )
        data = client.get("/api/analytics/improvement", headers=headers).json()
        # sorted=[90,60], mid=1, earlier=[90], recent=[60], diff=-30 → declining
        assert data["trend"] == "declining"

    def test_stable_trend(self, auth):
        _, user_id, headers = auth
        uid = ObjectId(user_id)
        # Two nearly identical scores → abs(diff) < 2 → stable
        r1 = interviews_collection.insert_one(
            _build_interview(uid, days_ago=20, title="Interview A")
        )
        feedback_collection.insert_one(
            _build_feedback(uid, r1.inserted_id, days_ago=20, overall_score=75)
        )
        r2 = interviews_collection.insert_one(
            _build_interview(uid, days_ago=5, title="Interview B")
        )
        feedback_collection.insert_one(
            _build_feedback(uid, r2.inserted_id, days_ago=5, overall_score=76)
        )
        data = client.get("/api/analytics/improvement", headers=headers).json()
        # sorted=[75,76], mid=1, earlier=[75], recent=[76], diff=1.0 → stable
        assert data["trend"] == "stable"


# ---------------------------------------------------------------------------
# 14. Date Filtering
# ---------------------------------------------------------------------------

class TestDateFiltering:
    def test_days_7_filters_correctly(self, seeded):
        """Only the interview 3 days ago (score=85) should appear."""
        _, _, headers, _ = seeded
        data = client.get("/api/analytics/score-trend?days=7", headers=headers).json()
        scores = [item["score"] for item in data["data"]]
        assert scores == [85]

    def test_days_30_filters_correctly(self, seeded):
        """Interviews 20 and 3 days ago (scores 75, 85) should appear."""
        _, _, headers, _ = seeded
        data = client.get("/api/analytics/score-trend?days=30", headers=headers).json()
        scores = [item["score"] for item in data["data"]]
        assert set(scores) == {75, 85}

    def test_days_90_returns_all(self, seeded):
        """All 3 interviews are within 90 days."""
        _, _, headers, _ = seeded
        data = client.get("/api/analytics/score-trend?days=90", headers=headers).json()
        assert len(data["data"]) == 3

    def test_invalid_days_returns_400(self, auth):
        _, _, headers = auth
        for invalid in [1, 15, 45, 100, 200]:
            resp = client.get(f"/api/analytics/overview?days={invalid}", headers=headers)
            assert resp.status_code == 400, f"days={invalid} should be rejected"

    def test_no_days_returns_all(self, seeded):
        _, _, headers, _ = seeded
        data = client.get("/api/analytics/score-trend", headers=headers).json()
        assert len(data["data"]) == 3


# ---------------------------------------------------------------------------
# 15. Invalid Parameters
# ---------------------------------------------------------------------------

class TestInvalidParameters:
    def test_history_limit_max_enforced(self, auth):
        _, _, headers = auth
        resp = client.get("/api/analytics/history?limit=51", headers=headers)
        assert resp.status_code == 422

    def test_history_page_min_enforced(self, auth):
        _, _, headers = auth
        resp = client.get("/api/analytics/history?page=0", headers=headers)
        assert resp.status_code == 422

    def test_topics_limit_max_enforced(self, auth):
        _, _, headers = auth
        resp = client.get("/api/analytics/topics?limit=21", headers=headers)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 16. Full Analytics Endpoint
# ---------------------------------------------------------------------------

class TestFullAnalytics:
    def test_full_analytics_structure(self, seeded):
        _, _, headers, _ = seeded
        resp = client.get("/api/analytics", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "overview" in data
        assert "score_trend" in data
        assert "category_performance" in data
        assert "top_topics" in data
        assert "top_strengths" in data
        assert "top_weaknesses" in data
        assert "improvement" in data

    def test_full_analytics_empty(self, auth):
        _, _, headers = auth
        resp = client.get("/api/analytics", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["overview"]["evaluated_interviews"] == 0
        assert data["score_trend"] == []
        assert data["improvement"]["trend"] == "insufficient_data"

    def test_full_analytics_with_days_filter(self, seeded):
        _, _, headers, _ = seeded
        resp = client.get("/api/analytics?days=7", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        # Only the most recent interview (3 days ago, score=85) in trend
        assert len(data["score_trend"]) == 1
        assert data["score_trend"][0]["score"] == 85
