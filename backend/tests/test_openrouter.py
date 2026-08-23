"""
tests/test_openrouter.py

Tests for the OpenRouter client (Phase 10).

All tests use mocks — no real API calls are made.
"""

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# 1. Client Initialization
# ---------------------------------------------------------------------------

class TestOpenRouterClientInit:
    def test_client_initializes_when_api_key_set(self):
        """Client should initialize when a valid API key is configured."""
        with patch("app.ai.openrouter_client.settings") as mock_settings:
            mock_settings.OPENROUTER_API_KEY = "sk-test-key"
            mock_settings.OPENROUTER_MODEL = "openai/gpt-4o"
            mock_settings.OPENROUTER_SITE_URL = ""
            mock_settings.OPENROUTER_APP_NAME = ""

            with patch("app.ai.openrouter_client.OpenAI") as mock_openai:
                mock_openai.return_value = MagicMock()

                from importlib import reload
                import app.ai.openrouter_client as module
                reload(module)

                # Re-create a fresh instance inline
                from app.ai.openrouter_client import OpenRouterClient
                client = OpenRouterClient.__new__(OpenRouterClient)
                client.api_key = "sk-test-key"
                client.model = "openai/gpt-4o"
                client.site_url = ""
                client.app_name = ""
                client._client = mock_openai.return_value

                assert client.is_configured() is True

    def test_client_not_configured_when_key_empty(self):
        """Client should not configure itself when API key is empty."""
        from app.ai.openrouter_client import OpenRouterClient
        client = OpenRouterClient.__new__(OpenRouterClient)
        client.api_key = ""
        client._client = None

        assert client.is_configured() is False

    def test_get_client_raises_when_not_configured(self):
        """get_client() should raise ValueError when client is not initialized."""
        from app.ai.openrouter_client import OpenRouterClient
        client = OpenRouterClient.__new__(OpenRouterClient)
        client._client = None

        with pytest.raises(ValueError, match="not configured"):
            client.get_client()


# ---------------------------------------------------------------------------
# 2. Model Configuration
# ---------------------------------------------------------------------------

class TestModelConfiguration:
    def test_default_model(self):
        """Default model should be openai/gpt-4o."""
        from app.config.settings import Settings
        s = Settings(OPENROUTER_API_KEY="", OPENROUTER_MODEL="openai/gpt-4o")
        assert s.OPENROUTER_MODEL == "openai/gpt-4o"

    def test_custom_model_configurable(self):
        """Model should be overridable via settings."""
        from app.config.settings import Settings
        s = Settings(OPENROUTER_API_KEY="sk-x", OPENROUTER_MODEL="openai/gpt-4o-mini")
        assert s.OPENROUTER_MODEL == "openai/gpt-4o-mini"

    def test_site_url_and_app_name_optional(self):
        """OPENROUTER_SITE_URL and OPENROUTER_APP_NAME should be optional."""
        from app.config.settings import Settings
        s = Settings(OPENROUTER_API_KEY="sk-x")
        assert s.OPENROUTER_SITE_URL == ""
        assert s.OPENROUTER_APP_NAME == ""


# ---------------------------------------------------------------------------
# 3. Successful Mocked Response
# ---------------------------------------------------------------------------

class TestChatCompletion:
    def _make_mock_client(self, content="Hello!", tool_calls=None):
        mock_message = MagicMock()
        mock_message.content = content
        mock_message.tool_calls = tool_calls or []

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = mock_response

        from app.ai.openrouter_client import OpenRouterClient
        client = OpenRouterClient.__new__(OpenRouterClient)
        client.api_key = "sk-test"
        client.model = "openai/gpt-4o"
        client._client = mock_openai
        return client, mock_response

    def test_successful_chat_completion(self):
        """Should return the mock response successfully."""
        client, mock_response = self._make_mock_client("Test response")
        messages = [{"role": "user", "content": "Hello"}]
        result = client.chat_completion(messages=messages)
        assert result is mock_response

    def test_chat_completion_with_tools(self):
        """Should pass tools to the underlying API call."""
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = MagicMock()

        from app.ai.openrouter_client import OpenRouterClient
        client = OpenRouterClient.__new__(OpenRouterClient)
        client.model = "openai/gpt-4o"
        client._client = mock_openai

        tools = [{"type": "function", "function": {"name": "test_tool"}}]
        client.chat_completion(messages=[{"role": "user", "content": "Hi"}], tools=tools)

        call_kwargs = mock_openai.chat.completions.create.call_args.kwargs
        assert "tools" in call_kwargs
        assert call_kwargs["tools"] == tools


# ---------------------------------------------------------------------------
# 4. API Failure Handling
# ---------------------------------------------------------------------------

class TestAPIFailureHandling:
    def test_rate_limit_error_propagates(self):
        """RateLimitError should propagate from chat_completion."""
        from openai import RateLimitError
        from app.ai.openrouter_client import OpenRouterClient

        mock_openai = MagicMock()
        mock_openai.chat.completions.create.side_effect = RateLimitError(
            message="Rate limit", response=MagicMock(status_code=429), body={}
        )

        client = OpenRouterClient.__new__(OpenRouterClient)
        client.model = "openai/gpt-4o"
        client._client = mock_openai

        with pytest.raises(RateLimitError):
            client.chat_completion(messages=[{"role": "user", "content": "Hi"}])

    def test_api_error_propagates(self):
        """Generic APIError should propagate."""
        from openai import APIError
        from app.ai.openrouter_client import OpenRouterClient

        mock_openai = MagicMock()
        mock_openai.chat.completions.create.side_effect = APIError(
            message="API error", request=MagicMock(), body={}
        )

        client = OpenRouterClient.__new__(OpenRouterClient)
        client.model = "openai/gpt-4o"
        client._client = mock_openai

        with pytest.raises(APIError):
            client.chat_completion(messages=[{"role": "user", "content": "Hi"}])
