"""
tests/test_openrouter_fallback.py

Tests for the OpenRouter primary → fallback model chain.

All tests are fully mocked — no real API calls are made.

Coverage:
    1. GPT-4o succeeds → no fallback attempted.
    2. GPT-4o RateLimitError → GPT-4o-mini called and succeeds.
    3. GPT-4o APIConnectionError → GPT-4o-mini called and succeeds.
    4. GPT-4o 503 APIStatusError → GPT-4o-mini called and succeeds.
    5. Both models fail → last error raised.
    6. AuthenticationError → raised immediately, mini never called.
    7. BadRequestError → raised immediately, mini never called.
    8. NotFoundError → raised immediately, mini never called.
    9. PermissionDeniedError → raised immediately, mini never called.
   10. Tool definitions and tool_choice are forwarded to fallback model.
   11. Fallback disabled (empty string) → primary error re-raised.
   12. Gemini question generation does NOT use OpenRouter (isolation check).
"""

import pytest
from unittest.mock import MagicMock, patch, call

from openai import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(content: str = "ok") -> MagicMock:
    """Build a minimal mock ChatCompletion response."""
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = []

    choice = MagicMock()
    choice.message = msg

    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _make_client(primary_model: str = "openai/gpt-4o",
                 fallback_model: str = "openai/gpt-4o-mini") -> "OpenRouterClient":
    """
    Return a configured OpenRouterClient instance whose _client is a fresh
    MagicMock (no real HTTP connection is made).
    """
    from app.ai.openrouter_client import OpenRouterClient

    client = OpenRouterClient.__new__(OpenRouterClient)
    client.api_key = "sk-test"
    client.model = primary_model
    client.fallback_model = fallback_model
    client.site_url = ""
    client.app_name = ""
    client._client = MagicMock()
    return client


def _rate_limit_error() -> RateLimitError:
    return RateLimitError(
        message="Rate limit exceeded",
        response=MagicMock(status_code=429),
        body={},
    )


def _connection_error() -> APIConnectionError:
    return APIConnectionError(request=MagicMock())


def _server_error(status_code: int = 503) -> APIStatusError:
    return APIStatusError(
        message=f"Server error {status_code}",
        response=MagicMock(status_code=status_code),
        body={},
    )


def _payment_required_error() -> APIStatusError:
    return APIStatusError(
        message="Payment required: max_tokens exceeds the affordable token limit of 3907",
        response=MagicMock(status_code=402),
        body={},
    )


def _auth_error() -> AuthenticationError:
    return AuthenticationError(
        message="Invalid API key",
        response=MagicMock(status_code=401),
        body={},
    )


def _permission_error() -> PermissionDeniedError:
    return PermissionDeniedError(
        message="Forbidden",
        response=MagicMock(status_code=403),
        body={},
    )


def _bad_request_error() -> BadRequestError:
    return BadRequestError(
        message="Bad request",
        response=MagicMock(status_code=400),
        body={},
    )


def _not_found_error() -> NotFoundError:
    return NotFoundError(
        message="Model not found",
        response=MagicMock(status_code=404),
        body={},
    )


# ---------------------------------------------------------------------------
# Test suite
# ---------------------------------------------------------------------------

class TestPrimarySucceeds:
    """Primary model works — fallback should never be called."""

    def test_primary_success_returns_response(self):
        client = _make_client()
        expected = _make_response("primary answer")
        client._client.chat.completions.create.return_value = expected

        result = client.chat_completion(messages=[{"role": "user", "content": "Hello"}])

        assert result is expected
        assert client._client.chat.completions.create.call_count == 1

    def test_primary_uses_configured_model(self):
        client = _make_client(primary_model="openai/gpt-4o")
        client._client.chat.completions.create.return_value = _make_response()

        client.chat_completion(messages=[{"role": "user", "content": "Hi"}])

        kwargs = client._client.chat.completions.create.call_args.kwargs
        assert kwargs["model"] == "openai/gpt-4o"

    def test_primary_no_tools_success(self):
        client = _make_client()
        client._client.chat.completions.create.return_value = _make_response("done")

        result = client.chat_completion(
            messages=[{"role": "user", "content": "coach me"}],
            tools=None,
            temperature=0.5,
            max_tokens=1500,
        )
        assert result.choices[0].message.content == "done"


class TestRateLimitFallback:
    """Primary returns 429 → fallback model is used."""

    def test_rate_limit_triggers_fallback(self):
        client = _make_client()
        fallback_response = _make_response("mini answer")

        client._client.chat.completions.create.side_effect = [
            _rate_limit_error(),   # primary raises
            fallback_response,     # fallback succeeds
        ]

        result = client.chat_completion(messages=[{"role": "user", "content": "Hi"}])

        assert result is fallback_response
        assert client._client.chat.completions.create.call_count == 2

    def test_rate_limit_fallback_uses_mini_model(self):
        client = _make_client(primary_model="openai/gpt-4o",
                              fallback_model="openai/gpt-4o-mini")
        client._client.chat.completions.create.side_effect = [
            _rate_limit_error(),
            _make_response(),
        ]

        client.chat_completion(messages=[{"role": "user", "content": "Hi"}])

        calls = client._client.chat.completions.create.call_args_list
        assert calls[0].kwargs["model"] == "openai/gpt-4o"
        assert calls[1].kwargs["model"] == "openai/gpt-4o-mini"


class TestConnectionFailureFallback:
    """Primary raises APIConnectionError → fallback model is used."""

    def test_connection_error_triggers_fallback(self):
        client = _make_client()
        fallback_response = _make_response("mini ok")

        client._client.chat.completions.create.side_effect = [
            _connection_error(),
            fallback_response,
        ]

        result = client.chat_completion(messages=[{"role": "user", "content": "Hi"}])
        assert result is fallback_response
        assert client._client.chat.completions.create.call_count == 2


class TestServerErrorFallback:
    """Primary returns 5xx → fallback model is used."""

    @pytest.mark.parametrize("status_code", [500, 502, 503, 504])
    def test_5xx_triggers_fallback(self, status_code):
        client = _make_client()
        client._client.chat.completions.create.side_effect = [
            _server_error(status_code),
            _make_response("fallback ok"),
        ]

        result = client.chat_completion(messages=[{"role": "user", "content": "Hi"}])
        assert result.choices[0].message.content == "fallback ok"


class TestPaymentRequiredFallback:
    """Primary returns 402 / credit limit error → cheaper fallback model is used."""

    def test_402_triggers_fallback(self):
        client = _make_client()
        client._client.chat.completions.create.side_effect = [
            _payment_required_error(),
            _make_response("mini fallback ok"),
        ]

        result = client.chat_completion(messages=[{"role": "user", "content": "Hi"}])
        assert result.choices[0].message.content == "mini fallback ok"
        assert client._client.chat.completions.create.call_count == 2


class TestBothModelsFail:
    """When both primary and fallback fail the last error is raised."""

    def test_both_rate_limit_raises(self):
        client = _make_client()
        client._client.chat.completions.create.side_effect = [
            _rate_limit_error(),
            _rate_limit_error(),
        ]

        with pytest.raises(RateLimitError):
            client.chat_completion(messages=[{"role": "user", "content": "Hi"}])

        assert client._client.chat.completions.create.call_count == 2

    def test_primary_rate_limit_fallback_connection_error(self):
        client = _make_client()
        client._client.chat.completions.create.side_effect = [
            _rate_limit_error(),
            _connection_error(),
        ]

        with pytest.raises(APIConnectionError):
            client.chat_completion(messages=[{"role": "user", "content": "Hi"}])


class TestPermanentErrorsNoFallback:
    """Permanent errors must raise immediately without calling the fallback."""

    def test_auth_error_no_fallback(self):
        client = _make_client()
        client._client.chat.completions.create.side_effect = _auth_error()

        with pytest.raises(AuthenticationError):
            client.chat_completion(messages=[{"role": "user", "content": "Hi"}])

        # Only one call — fallback never attempted
        assert client._client.chat.completions.create.call_count == 1

    def test_permission_denied_no_fallback(self):
        client = _make_client()
        client._client.chat.completions.create.side_effect = _permission_error()

        with pytest.raises(PermissionDeniedError):
            client.chat_completion(messages=[{"role": "user", "content": "Hi"}])

        assert client._client.chat.completions.create.call_count == 1

    def test_bad_request_no_fallback(self):
        client = _make_client()
        client._client.chat.completions.create.side_effect = _bad_request_error()

        with pytest.raises(BadRequestError):
            client.chat_completion(messages=[{"role": "user", "content": "Hi"}])

        assert client._client.chat.completions.create.call_count == 1

    def test_not_found_no_fallback(self):
        client = _make_client()
        client._client.chat.completions.create.side_effect = _not_found_error()

        with pytest.raises(NotFoundError):
            client.chat_completion(messages=[{"role": "user", "content": "Hi"}])

        assert client._client.chat.completions.create.call_count == 1


class TestToolCallingWithFallback:
    """Tool definitions and tool_choice must be forwarded to the fallback model."""

    def _make_tool_call_response(self, tool_name: str) -> MagicMock:
        tc = MagicMock()
        tc.id = "call_abc123"
        tc.function.name = tool_name
        tc.function.arguments = '{"query": "test"}'

        msg = MagicMock()
        msg.content = None
        msg.tool_calls = [tc]

        choice = MagicMock()
        choice.message = msg

        resp = MagicMock()
        resp.choices = [choice]
        return resp

    def test_tools_forwarded_to_fallback(self):
        client = _make_client()
        tools = [{"type": "function", "function": {"name": "search"}}]

        client._client.chat.completions.create.side_effect = [
            _rate_limit_error(),
            self._make_tool_call_response("search"),
        ]

        result = client.chat_completion(
            messages=[{"role": "user", "content": "search for me"}],
            tools=tools,
            tool_choice="auto",
        )

        calls = client._client.chat.completions.create.call_args_list
        # Fallback call must have the same tools
        fallback_kwargs = calls[1].kwargs
        assert fallback_kwargs["tools"] == tools
        assert fallback_kwargs["tool_choice"] == "auto"
        assert fallback_kwargs["model"] == "openai/gpt-4o-mini"
        assert result.choices[0].message.tool_calls is not None

    def test_tool_choice_required_forwarded_to_fallback(self):
        client = _make_client()
        tools = [{"type": "function", "function": {"name": "get_data"}}]

        client._client.chat.completions.create.side_effect = [
            _connection_error(),
            _make_response("data fetched"),
        ]

        client.chat_completion(
            messages=[{"role": "user", "content": "get data"}],
            tools=tools,
            tool_choice="required",
            temperature=0.1,
            max_tokens=500,
        )

        fallback_kwargs = client._client.chat.completions.create.call_args_list[1].kwargs
        assert fallback_kwargs["tool_choice"] == "required"
        assert fallback_kwargs["temperature"] == 0.1
        assert fallback_kwargs["max_tokens"] == 500

    def test_no_tools_not_included_in_call(self):
        """When tools=None the underlying call must not include 'tools'."""
        client = _make_client()
        client._client.chat.completions.create.return_value = _make_response()

        client.chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            tools=None,
        )

        kwargs = client._client.chat.completions.create.call_args.kwargs
        assert "tools" not in kwargs
        assert "tool_choice" not in kwargs


class TestFallbackDisabled:
    """When fallback_model is empty the primary error is re-raised directly."""

    def test_empty_fallback_model_reraises_primary(self):
        client = _make_client(fallback_model="")
        client._client.chat.completions.create.side_effect = _rate_limit_error()

        with pytest.raises(RateLimitError):
            client.chat_completion(messages=[{"role": "user", "content": "Hi"}])

        # Only one attempt — no fallback
        assert client._client.chat.completions.create.call_count == 1


class TestClientConfiguration:
    """Settings-level tests for the new fallback field."""

    def test_default_fallback_model(self):
        from app.config.settings import Settings
        s = Settings(OPENROUTER_API_KEY="sk-x")
        assert s.OPENROUTER_FALLBACK_MODEL == "openai/gpt-4o-mini"

    def test_custom_fallback_model_configurable(self):
        from app.config.settings import Settings
        s = Settings(OPENROUTER_API_KEY="sk-x",
                     OPENROUTER_FALLBACK_MODEL="openai/gpt-3.5-turbo")
        assert s.OPENROUTER_FALLBACK_MODEL == "openai/gpt-3.5-turbo"

    def test_fallback_disabled_via_empty_string(self):
        from app.config.settings import Settings
        s = Settings(OPENROUTER_API_KEY="sk-x", OPENROUTER_FALLBACK_MODEL="")
        assert s.OPENROUTER_FALLBACK_MODEL == ""

    def test_client_reads_fallback_from_settings(self):
        """OpenRouterClient must pick up OPENROUTER_FALLBACK_MODEL from settings."""
        from app.ai.openrouter_client import OpenRouterClient

        with patch("app.ai.openrouter_client.settings") as mock_settings:
            mock_settings.OPENROUTER_API_KEY = ""
            mock_settings.OPENROUTER_MODEL = "openai/gpt-4o"
            mock_settings.OPENROUTER_FALLBACK_MODEL = "openai/gpt-4o-mini"
            mock_settings.OPENROUTER_SITE_URL = ""
            mock_settings.OPENROUTER_APP_NAME = ""

            client = OpenRouterClient()
            assert client.fallback_model == "openai/gpt-4o-mini"


class TestGeminiIsolation:
    """
    Verify that Gemini-based question generation does NOT use the OpenRouter
    client.  The two providers must remain completely isolated.
    """

    def test_question_service_does_not_import_openrouter_client(self):
        """
        The AI question service module must not reference openrouter_client
        directly.  If it does, the isolation guarantee is broken.
        """
        import ast
        import pathlib

        service_path = pathlib.Path(
            "C:/Users/HP/Desktop/PROGRAMMING/PrepAI/backend/app/services/ai_question_service.py"
        )
        if not service_path.exists():
            pytest.skip("ai_question_service.py not found — skipping isolation check")

        source = service_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        imported_names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imported_names.extend(n.name for n in node.names)
            elif isinstance(node, ast.Import):
                imported_names.extend(n.name for n in node.names)

        assert "openrouter_client" not in imported_names, (
            "ai_question_service.py must NOT import openrouter_client — "
            "Gemini and OpenRouter must remain isolated."
        )

    def test_evaluator_does_not_import_openrouter_client(self):
        import ast
        import pathlib

        evaluator_path = pathlib.Path(
            "C:/Users/HP/Desktop/PROGRAMMING/PrepAI/backend/app/ai/evaluator.py"
        )
        if not evaluator_path.exists():
            pytest.skip("evaluator.py not found")

        source = evaluator_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        imported_names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imported_names.extend(n.name for n in node.names)

        assert "openrouter_client" not in imported_names, (
            "evaluator.py must NOT import openrouter_client."
        )

