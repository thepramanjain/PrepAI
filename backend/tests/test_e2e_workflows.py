"""
tests/test_e2e_workflows.py

End-to-End Workflow Verification for PrepAI:
- Part B: Core workflow validation & unified evaluation pipeline
- Part C: Full 9-dimension evaluation report generation, MongoDB persistence, duplicate prevention, and zero-AI retrieval
- Part D: Complete end-to-end user flows (TEXT & VOICE) from login to history/results.
"""

import json
from unittest.mock import patch, MagicMock
from bson import ObjectId
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import users_collection
from app.models.interview import interviews_collection
from app.models.question import questions_collection
from app.models.response import responses_collection
from app.models.feedback import feedback_collection
from app.models.voice_session import voice_sessions_collection
from app.ai.follow_up_generator import FollowUpDecision

client = TestClient(app)

E2E_EMAIL = "e2e_user@example.com"
E2E_PASSWORD = "e2epassword123"
E2E_OTHER_EMAIL = "e2e_other@example.com"
FAKE_LIVEKIT_TOKEN = "eyJhbGciOiJIUzI1NiJ9.fake.voice.token"


# ---------------------------------------------------------------------------
# Mock Data Generators
# ---------------------------------------------------------------------------

def _mock_generated_questions_payload(count: int = 2):
    return {
        "questions": [
            {
                "question": f"Sample technical question {i+1} on Python and architecture?",
                "category": "Technical",
                "difficulty": "Medium",
            }
            for i in range(count)
        ]
    }


def _mock_evaluation_payload(question_ids: list):
    """Produces all 9 required report dimensions matching GeneratedEvaluation schema."""
    return {
        "overall_score": 88,
        "category_scores": {
            "technical": 90,
            "communication": 85,
            "problem_solving": 87,
            "relevance": 89,
        },
        "question_evaluations": [
            {
                "question_id": qid,
                "score": 88,
                "quality": "Strong",
                "strengths": ["Clear explanation of time complexity", "Accurate data structure choices"],
                "improvements": ["Could mention edge case handling"],
                "feedback": "Comprehensive and well-structured answer.",
            }
            for qid in question_ids
        ],
        "strengths": [
            "Demonstrated in-depth knowledge of backend architecture",
            "Clear and articulate communication of trade-offs",
        ],
        "weaknesses": [
            "Could elaborate more on distributed caching failure modes",
        ],
        "recommendations": [
            "Review Redis cluster failover mechanisms",
            "Practice structuring system design explanations using top-down approach",
        ],
        "topic_analysis": [
            {"topic": "Backend Systems", "score": 90, "assessment": "Excellent"},
            {"topic": "System Design", "score": 85, "assessment": "Good"},
        ],
        "summary": "Overall an impressive technical interview with strong problem solving and clear communication.",
    }


# ---------------------------------------------------------------------------
# DB Cleanup Fixture
# ---------------------------------------------------------------------------

def _cleanup_test_data():
    for email in [E2E_EMAIL, E2E_OTHER_EMAIL]:
        user = users_collection.find_one({"email": email})
        if user:
            uid = user["_id"]
            interviews = list(interviews_collection.find({"user_id": uid}))
            iids = [i["_id"] for i in interviews]
            feedback_collection.delete_many({"user_id": uid})
            responses_collection.delete_many({"user_id": uid})
            questions_collection.delete_many({"interview_id": {"$in": iids}})
            voice_sessions_collection.delete_many({"user_id": uid})
            interviews_collection.delete_many({"user_id": uid})
            users_collection.delete_one({"_id": uid})


@pytest.fixture(autouse=True)
def clean_db():
    _cleanup_test_data()
    yield
    _cleanup_test_data()


# ---------------------------------------------------------------------------
# Helper: Register & Login
# ---------------------------------------------------------------------------

def _get_auth_token(email: str = E2E_EMAIL, password: str = E2E_PASSWORD, name: str = "E2E Tester") -> str:
    client.post("/api/auth/register", json={"name": name, "email": email, "password": password})
    res = client.post("/api/auth/login", data={"username": email, "password": password})
    assert res.status_code == 200, f"Login failed: {res.text}"
    return res.json()["access_token"]


# ===========================================================================
# 1. Complete Text Interview Workflow End-to-End
# ===========================================================================

class TestTextInterviewWorkflow:
    def test_complete_text_interview_e2e_flow(self):
        """
        TEXT FLOW:
        1. Login
        2. Create Interview
        3. Generate Questions (via Gemini)
        4. Start Session
        5. Answer Questions + Follow-up trigger
        6. Complete Interview
        7. Evaluate Interview (Part C: 9 dimensions)
        8. Save Report in MongoDB & prevent duplicates
        9. View Results (ensure 0 AI calls made)
        10. Verify Analytics History
        """
        token = _get_auth_token()
        headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Create Interview
        create_res = client.post("/api/interviews", json={
            "title": "Senior Backend Engineer Mock",
            "role": "Senior Backend Engineer",
            "experience_level": "5+ years",
            "skills": ["Python", "FastAPI", "MongoDB", "System Design"],
            "interview_type": "Technical",
            "difficulty": "Hard",
            "mode": "text",
        }, headers=headers)
        assert create_res.status_code == 201
        interview_id = create_res.json()["id"]

        # Step 3: Generate Questions using Gemini
        mock_ai_questions = _mock_generated_questions_payload(count=2)
        mock_response = MagicMock()
        mock_response.text = json.dumps(mock_ai_questions)

        with patch("app.ai.gemini_client.gemini_wrapper.get_client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_factory.return_value = mock_client

            gen_res = client.post(
                f"/api/ai/interviews/{interview_id}/generate-questions",
                json={"question_count": 2},
                headers=headers,
            )
            assert gen_res.status_code == 201
            assert gen_res.json()["count"] == 2
            q_list = gen_res.json()["questions"]
            q1_id = q_list[0]["id"]
            q2_id = q_list[1]["id"]

        # Step 4: Start Interview
        start_res = client.post(f"/api/interviews/{interview_id}/start", headers=headers)
        assert start_res.status_code == 200
        assert start_res.json()["status"] == "in_progress"
        assert start_res.json()["current_question"]["id"] == q1_id

        # Step 5: Answer Question 1 (with contextual follow-up triggered via mocked follow-up generator)
        mock_decision = FollowUpDecision(
            should_follow_up=True,
            question="How would you handle cache invalidation in that scenario?",
            category="System Design",
            difficulty="Hard",
        )

        with patch("app.services.follow_up_service.generate_follow_up", return_value=mock_decision):
            ans1_res = client.post(
                f"/api/interviews/{interview_id}/questions/{q1_id}/response",
                json={"answer": "I use Redis write-through caching with connection pooling."},
                headers=headers,
            )
            assert ans1_res.status_code == 201

            # Advance to next question (should present follow-up)
            next1_res = client.post(f"/api/interviews/{interview_id}/next", headers=headers)
            assert next1_res.status_code == 200
            follow_up_q = next1_res.json()["question"]
            assert follow_up_q["question"] == "How would you handle cache invalidation in that scenario?"
            follow_up_id = follow_up_q["id"]

        # Answer the follow-up question (follow-ups do not trigger subsequent follow-ups)
        with patch("app.services.follow_up_service.generate_follow_up", return_value=None):
            ans_fu_res = client.post(
                f"/api/interviews/{interview_id}/questions/{follow_up_id}/response",
                json={"answer": "I use TTL expiry combined with event-driven pub/sub invalidation."},
                headers=headers,
            )
            assert ans_fu_res.status_code == 201

            # Advance to Q2
            next2_res = client.post(f"/api/interviews/{interview_id}/next", headers=headers)
            assert next2_res.status_code == 200
            assert next2_res.json()["question"]["id"] == q2_id

            # Answer Q2
            ans2_res = client.post(
                f"/api/interviews/{interview_id}/questions/{q2_id}/response",
                json={"answer": "MongoDB sharding distributes chunks using a hashed shard key."},
                headers=headers,
            )
            assert ans2_res.status_code == 201

            # Advance beyond last question -> completes interview
            complete_res = client.post(f"/api/interviews/{interview_id}/next", headers=headers)
            assert complete_res.status_code == 200
            assert complete_res.json()["status"] == "completed"

        # Step 7: Evaluate Interview (Part C: Full 9 dimensions)
        all_q_ids = [q1_id, follow_up_id, q2_id]
        mock_eval = _mock_evaluation_payload(all_q_ids)
        mock_eval_response = MagicMock()
        mock_eval_response.text = json.dumps(mock_eval)

        with patch("app.ai.gemini_client.gemini_wrapper.get_client") as mock_gemini_client:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_eval_response
            mock_gemini_client.return_value = mock_client

            eval_res = client.post(f"/api/interviews/{interview_id}/evaluate", headers=headers)
            assert eval_res.status_code == 200
            report = eval_res.json()

            # Verify all 9 required report dimensions
            assert report["overall_score"] == 88                                    # 1. Overall score
            assert len(report["question_evaluations"]) == 3                         # 2. Question-wise scores
            assert report["category_scores"]["technical"] == 90                     # 3. Technical accuracy
            assert report["category_scores"]["relevance"] == 89                     # 4. Answer relevance
            assert report["category_scores"]["communication"] == 85                 # 5. Communication assessment
            assert len(report["strengths"]) >= 1                                    # 6. Strengths
            assert len(report["weaknesses"]) >= 1                                   # 7. Weaknesses
            assert len(report["recommendations"]) >= 1                              # 8. Improvement recommendations
            assert "impressive technical interview" in report["summary"]            # 9. Final summary

        # Step 8: Verify persistence in MongoDB and duplicate prevention
        db_reports = list(feedback_collection.find({"interview_id": ObjectId(interview_id)}))
        assert len(db_reports) == 1, "Exactly one evaluation report must be persisted in MongoDB"

        # Calling evaluate again re-evaluates and replaces (upserts) the record
        with patch("app.ai.gemini_client.gemini_wrapper.get_client") as mock_gemini_client:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_eval_response
            mock_gemini_client.return_value = mock_client

            eval_res_2 = client.post(f"/api/interviews/{interview_id}/evaluate", headers=headers)
            assert eval_res_2.status_code == 200

        # Assert no duplicate created
        db_reports_after = list(feedback_collection.find({"interview_id": ObjectId(interview_id)}))
        assert len(db_reports_after) == 1, "Duplicate evaluation records must be prevented"

        # Step 9: View Results (must load stored report without calling Gemini)
        with patch("app.ai.gemini_client.gemini_wrapper.get_client") as mock_never_called:
            view_res = client.get(f"/api/interviews/{interview_id}/feedback", headers=headers)
            assert view_res.status_code == 200
            view_data = view_res.json()
            assert view_data["overall_score"] == 88
            assert view_data["category_scores"]["technical"] == 90
            assert mock_never_called.call_count == 0, "Viewing results must load saved report without calling Gemini"

        # Step 10: Verify Analytics History shows the completed interview
        history_res = client.get("/api/analytics/history", headers=headers)
        assert history_res.status_code == 200
        history_items = history_res.json()["items"]
        assert len(history_items) >= 1
        found = any(item["interview_id"] == interview_id and item["score"] == 88 for item in history_items)
        assert found, "Completed interview and evaluation score must be reflected in analytics history"


# ===========================================================================
# 2. Complete Voice Interview Workflow End-to-End
# ===========================================================================

class TestVoiceInterviewWorkflow:
    def test_complete_voice_interview_e2e_flow(self):
        """
        VOICE FLOW:
        1. Login
        2. Create Voice Interview
        3. Add questions
        4. Request LiveKit Token
        5. Start Voice Session
        6. Append Transcripts & Record Responses
        7. End Voice Session & Complete Interview
        8. Evaluate Voice Interview via unified pipeline
        9. Save Report & View Results (zero-AI retrieval)
        """
        token = _get_auth_token()
        headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Create Voice Interview
        create_res = client.post("/api/interviews", json={
            "title": "Voice System Design Interview",
            "role": "Distributed Systems Engineer",
            "experience_level": "3-5 years",
            "skills": ["Distributed Systems", "Raft", "gRPC"],
            "interview_type": "Technical",
            "difficulty": "Hard",
            "mode": "voice",
        }, headers=headers)
        assert create_res.status_code == 201
        interview_id = create_res.json()["id"]

        # Step 3: Add a Question
        q_res = client.post(f"/api/interviews/{interview_id}/questions", json={
            "question": "Explain the Raft consensus algorithm leader election.",
            "category": "Distributed Systems",
            "difficulty": "Hard",
        }, headers=headers)
        assert q_res.status_code == 201
        q_id = q_res.json()["id"]

        # Step 4: Create LiveKit Session & Token
        with patch("app.services.voice_service._generate_livekit_token", return_value=FAKE_LIVEKIT_TOKEN):
            token_res = client.post(f"/api/interviews/{interview_id}/voice/session", headers=headers)
            assert token_res.status_code == 201
            voice_data = token_res.json()
            assert voice_data["token"] == FAKE_LIVEKIT_TOKEN
            assert "room_name" in voice_data

        # Step 5: Start Voice Session
        start_res = client.post(f"/api/interviews/{interview_id}/voice/start", headers=headers)
        assert start_res.status_code == 200
        assert start_res.json()["status"] == "active"

        # Step 6: Transcripts appended & Candidate answer recorded
        append_res = client.post(f"/api/interviews/{interview_id}/voice/transcript/append", json={
            "speaker": "candidate",
            "text": "Raft uses randomized election timers to avoid split votes. When a follower times out, it requests votes.",
        }, headers=headers)
        assert append_res.status_code == 204

        # Submit response to the question (voice agent records candidate answer)
        ans_res = client.post(
            f"/api/interviews/{interview_id}/questions/{q_id}/response",
            json={"answer": "Raft uses randomized election timers to avoid split votes. When a follower times out, it requests votes."},
            headers=headers,
        )
        assert ans_res.status_code == 201

        # Verify transcript retrieval
        transcript_res = client.get(f"/api/interviews/{interview_id}/voice/transcript", headers=headers)
        assert transcript_res.status_code == 200
        assert len(transcript_res.json()["entries"]) == 1

        # Step 7: End Voice Session
        end_res = client.post(f"/api/interviews/{interview_id}/voice/end", headers=headers)
        assert end_res.status_code == 200
        assert end_res.json()["status"] == "completed"
        assert end_res.json()["interview_completed"] is True

        # Verify interview state in DB is completed
        db_int = interviews_collection.find_one({"_id": ObjectId(interview_id)})
        assert db_int["status"] == "completed"

        # Step 8: Evaluate Voice Interview via shared evaluation pipeline
        mock_eval = _mock_evaluation_payload([q_id])
        mock_eval_response = MagicMock()
        mock_eval_response.text = json.dumps(mock_eval)

        with patch("app.ai.gemini_client.gemini_wrapper.get_client") as mock_gemini_client:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_eval_response
            mock_gemini_client.return_value = mock_client

            eval_res = client.post(f"/api/interviews/{interview_id}/evaluate", headers=headers)
            assert eval_res.status_code == 200
            voice_report = eval_res.json()
            assert voice_report["overall_score"] == 88
            assert voice_report["category_scores"]["technical"] == 90
            assert voice_report["category_scores"]["communication"] == 85
            assert len(voice_report["strengths"]) >= 1

        # Step 9: View Results (reads saved document, no Gemini call)
        with patch("app.ai.gemini_client.gemini_wrapper.get_client") as mock_never_called:
            view_res = client.get(f"/api/interviews/{interview_id}/feedback", headers=headers)
            assert view_res.status_code == 200
            assert view_res.json()["overall_score"] == 88
            assert mock_never_called.call_count == 0


# ===========================================================================
# 3. Evaluation Report Persistence & Protection Invariants
# ===========================================================================

class TestEvaluationInvariants:
    def test_cannot_evaluate_uncompleted_interview(self):
        """Evaluation must reject draft or in-progress interviews with 400."""
        token = _get_auth_token()
        headers = {"Authorization": f"Bearer {token}"}

        # Create draft interview
        create_res = client.post("/api/interviews", json={
            "title": "Draft Interview",
            "role": "QA Engineer",
            "experience_level": "Fresher",
            "skills": ["Pytest"],
            "interview_type": "Technical",
            "difficulty": "Easy",
            "mode": "text",
        }, headers=headers)
        assert create_res.status_code == 201
        iid = create_res.json()["id"]

        eval_res = client.post(f"/api/interviews/{iid}/evaluate", headers=headers)
        assert eval_res.status_code == 400
        assert "must be completed" in eval_res.json()["detail"].lower()

    def test_feedback_user_isolation(self):
        """User B cannot view or evaluate User A's interview."""
        token_a = _get_auth_token(email=E2E_EMAIL)
        token_b = _get_auth_token(email=E2E_OTHER_EMAIL, name="User B")

        # User A creates interview
        res_a = client.post("/api/interviews", json={
            "title": "Private Interview",
            "role": "Security Engineer",
            "experience_level": "5+ years",
            "skills": ["AppSec"],
            "interview_type": "Technical",
            "difficulty": "Hard",
            "mode": "text",
        }, headers={"Authorization": f"Bearer {token_a}"})
        assert res_a.status_code == 201
        iid = res_a.json()["id"]

        # User B tries to view feedback
        view_res = client.get(
            f"/api/interviews/{iid}/feedback",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert view_res.status_code == 404
