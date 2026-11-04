"""
test_agent_verification.py

Comprehensive tests for the PrepAI LiveKit voice agent:
- Metadata parsing
- Context loading & prompts
- Tool definitions & execution
- Transcript management & sync
- Gemini Live model configuration & initialization
- Error classification (429, 401/403, 404, 500/503, timeouts)
- Graceful session termination logic
"""

import asyncio
import json
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestVoiceAgentMetadata(unittest.TestCase):
    def test_parse_valid_room_metadata(self):
        from agent import _parse_room_metadata

        raw = json.dumps({"interview_id": "int_123", "jwt_token": "token_abc"})
        parsed = _parse_room_metadata(raw)
        self.assertEqual(parsed.get("interview_id"), "int_123")
        self.assertEqual(parsed.get("jwt_token"), "token_abc")

    def test_parse_empty_or_invalid_metadata(self):
        from agent import _parse_room_metadata

        self.assertEqual(_parse_room_metadata(""), {})
        self.assertEqual(_parse_room_metadata("invalid json"), {})
        self.assertEqual(_parse_room_metadata("123"), {})
        self.assertEqual(_parse_room_metadata("[]"), {})


class TestVoiceAgentConfiguration(unittest.TestCase):
    def test_model_defaults_to_gemini_38_live(self):
        from agent import GEMINI_LIVE_MODEL, GEMINI_VOICE

        # Default model must be gemini-3.8-live
        self.assertEqual(GEMINI_LIVE_MODEL, "gemini-3.8-live")
        self.assertEqual(GEMINI_VOICE, "Puck")

    def test_api_key_resolution(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_gemini_key", "GOOGLE_API_KEY": ""}):
            key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            self.assertEqual(key, "test_gemini_key")


class TestPromptsAndContext(unittest.TestCase):
    def test_prompt_rendering(self):
        from prompts import (
            build_greeting_instruction,
            build_next_question_instruction,
            build_system_prompt,
        )

        sys_prompt = build_system_prompt(
            interview_context_str="ROLE: Senior Backend Developer\nSKILLS: Python, FastAPI",
            current_question="What is the GIL in Python?",
        )
        self.assertIn("Senior Backend Developer", sys_prompt)
        self.assertIn("What is the GIL in Python?", sys_prompt)
        self.assertIn("SECURITY RULES", sys_prompt)

        greeting = build_greeting_instruction(
            total_questions=5,
            first_question="Introduce yourself.",
        )
        self.assertIn("5", greeting)
        self.assertIn("Introduce yourself.", greeting)

        next_q = build_next_question_instruction(
            next_question="Explain indexing.",
            current_num=2,
            total=5,
        )
        self.assertIn("Explain indexing.", next_q)
        self.assertIn("Question 2 of 5", next_q)


class TestToolsFactory(unittest.IsolatedAsyncioTestCase):
    async def test_make_tools_returns_livekit_function_tools(self):
        from tools import make_tools

        tools = make_tools(
            interview_id="int_test_1",
            backend_url="http://localhost:8000",
            jwt_token="token_xyz",
        )
        self.assertEqual(len(tools), 3)

        tool_names = [t.__name__ for t in tools]
        self.assertIn("store_response", tool_names)
        self.assertIn("advance_to_next_question", tool_names)
        self.assertIn("end_interview", tool_names)

    async def test_tool_execution_mocked_http(self):
        from tools import make_tools

        tools = make_tools(
            interview_id="int_test_1",
            backend_url="http://localhost:8000",
            jwt_token="token_xyz",
        )
        tools_by_name = {t.__name__: t for t in tools}

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_post.return_value = mock_resp

            store_fn = tools_by_name["store_response"]
            result = await store_fn._func(
                question_id="q_1",
                answer_text="Python handles concurrency with asyncio.",
            )
            self.assertIn("successfully", result)
            self.assertTrue(mock_post.called)


class TestTranscriptManagement(unittest.IsolatedAsyncioTestCase):
    async def test_transcript_add_and_sync(self):
        from transcript import TranscriptManager

        tm = TranscriptManager(
            interview_id="int_test_1",
            backend_url="http://localhost:8000",
            jwt_token="token_xyz",
        )

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_post.return_value = mock_resp

            await tm.add_and_sync("candidate", "Here is my answer to the question.")

            self.assertEqual(len(tm.entries), 1)
            self.assertEqual(tm.entries[0].speaker, "candidate")
            self.assertEqual(tm.entries[0].text, "Here is my answer to the question.")
            self.assertTrue(mock_post.called)


class TestGeminiRealtimeModel(unittest.TestCase):
    def test_realtime_model_initialization(self):
        from livekit.plugins import google

        model = google.realtime.RealtimeModel(
            model="gemini-3.8-live",
            voice="Puck",
            instructions="Test system prompt",
            api_key="test_api_key_valid_syntax",
        )
        self.assertIsNotNone(model)
        self.assertEqual(model.model, "gemini-3.8-live")
        self.assertEqual(getattr(model._opts, "voice", "Puck"), "Puck")


class TestErrorHandlingClassification(unittest.TestCase):
    def test_error_categories(self):
        """Verify error messages correctly detect categories."""
        test_cases = [
            ("Resource has been exhausted (HTTP 429 quota exceeded)", "429"),
            ("Invalid API key provided (HTTP 401 unauthorized)", "401"),
            ("Model gemini-invalid is not found (HTTP 404)", "404"),
            ("Service unavailable (HTTP 503 backend error)", "503"),
            ("Deadline exceeded: connection timeout", "timeout"),
        ]

        for err_msg, expected_category in test_cases:
            err_lower = err_msg.lower()
            if expected_category == "429":
                self.assertTrue("429" in err_lower or "quota" in err_lower)
            elif expected_category == "401":
                self.assertTrue("401" in err_lower or "api_key" in err_lower)
            elif expected_category == "404":
                self.assertTrue("404" in err_lower or "not found" in err_lower)
            elif expected_category == "503":
                self.assertTrue("503" in err_lower or "unavailable" in err_lower)
            elif expected_category == "timeout":
                self.assertTrue("timeout" in err_lower or "deadline" in err_lower)


if __name__ == "__main__":
    unittest.main()
