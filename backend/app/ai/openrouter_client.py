"""
app/ai/openrouter_client.py

OpenRouter-compatible client for GPT-4o agentic workflows with automatic
GPT-4o-mini fallback for retryable errors.

Architecture:
    OpenAI Python SDK
        |
    base_url = https://openrouter.ai/api/v1
        |
    primary model  = openai/gpt-4o   (OPENROUTER_MODEL)
    fallback model = openai/gpt-4o-mini (OPENROUTER_FALLBACK_MODEL)

Fallback policy
---------------
The fallback model is attempted once when the primary model raises a
*retryable* error:
    - openai.RateLimitError          (HTTP 429)
    - openai.APIConnectionError      (network failure)
    - openai.APITimeoutError         (read timeout)
    - openai.APIStatusError with 5xx (server-side error)

Fallback is NOT triggered for permanent errors:
    - openai.AuthenticationError     (401) — wrong API key
    - openai.PermissionDeniedError   (403) — account restriction
    - openai.BadRequestError         (400) — malformed request
    - openai.NotFoundError           (404) — model not found
    - Any other non-retryable status code

This client is used exclusively for:
- Agent orchestration
- Tool calling
- Career coaching
- Agentic workflows

It does NOT replace Gemini, which remains responsible for:
- Interview question generation
- Text interview follow-ups
- AI evaluation
- Voice interview intelligence
"""

import logging

from openai import (
    OpenAI,
    APIError,
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)

from app.config.settings import settings

logger = logging.getLogger(__name__)

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# HTTP status codes that should trigger a fallback attempt.
_RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({500, 502, 503, 504})

# Error types that are permanent — never fall back on these.
_PERMANENT_ERROR_TYPES = (
    AuthenticationError,    # 401
    PermissionDeniedError,  # 403
    BadRequestError,        # 400
    NotFoundError,          # 404
)


def _is_retryable(exc: Exception) -> bool:
    """
    Return True when *exc* represents a transient failure that may resolve
    if we retry with a different (or same) model.

    Permanent errors (auth, bad request, model not found) return False so
    the caller can surface a meaningful error immediately.
    """
    if isinstance(exc, _PERMANENT_ERROR_TYPES):
        return False
    if isinstance(exc, RateLimitError):
        return True
    if isinstance(exc, (APIConnectionError, APITimeoutError)):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code in _RETRYABLE_STATUS_CODES
    return False


class OpenRouterClient:
    """
    Wrapper for the OpenRouter API using the OpenAI-compatible SDK.

    Implements a primary -> fallback model chain. When the primary model
    (OPENROUTER_MODEL, default openai/gpt-4o) raises a retryable error the
    request is replayed exactly once with the fallback model
    (OPENROUTER_FALLBACK_MODEL, default openai/gpt-4o-mini).

    Initialized once and shared as a singleton across the application.
    """

    fallback_model: str = "openai/gpt-4o-mini"

    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.OPENROUTER_MODEL
        self.fallback_model = settings.OPENROUTER_FALLBACK_MODEL
        self.site_url = settings.OPENROUTER_SITE_URL
        self.app_name = settings.OPENROUTER_APP_NAME
        self._client: OpenAI | None = None

        if self.api_key:
            try:
                # Build optional extra headers for OpenRouter attribution
                extra_headers: dict = {}
                if self.site_url:
                    extra_headers["HTTP-Referer"] = self.site_url
                if self.app_name:
                    extra_headers["X-Title"] = self.app_name

                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=_OPENROUTER_BASE_URL,
                    default_headers=extra_headers if extra_headers else None,
                )
                logger.info(
                    "[OpenRouter] Client initialized. primary=%s fallback=%s",
                    self.model,
                    self.fallback_model or "disabled",
                )
            except Exception as e:
                # Log without exposing the key
                logger.error("[OpenRouter] Failed to initialize client: %s", type(e).__name__)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def is_configured(self) -> bool:
        """Return True if the client has been successfully initialized."""
        return self._client is not None

    def get_client(self) -> OpenAI:
        """
        Return the configured OpenAI client pointed at OpenRouter.

        Raises:
            ValueError: If the client has not been configured (missing API key).
        """
        if self._client is None:
            raise ValueError(
                "OpenRouter client is not configured. "
                "Set OPENROUTER_API_KEY in your .env file."
            )
        return self._client

    # ------------------------------------------------------------------
    # Core method
    # ------------------------------------------------------------------

    def chat_completion(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str | dict = "auto",
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> object:
        """
        Send a chat completion request to OpenRouter.

        Attempts the primary model first. On a retryable error the same
        request is retried once with the fallback model. Permanent errors
        (auth, bad request, model not found) are re-raised immediately
        without attempting the fallback.

        Args:
            messages:     Conversation history in OpenAI message format.
            tools:        Optional list of tool definitions (JSON schema).
            tool_choice:  "auto" | "none" | "required" — default "auto".
            temperature:  Sampling temperature (default 0.3).
            max_tokens:   Maximum tokens in the response.

        Returns:
            The raw ChatCompletion response object from whichever model
            ultimately responded.

        Raises:
            RateLimitError:        Both models hit rate limits.
            APIConnectionError:    Network failure and fallback also failed.
            APIStatusError:        Permanent server error after exhausting
                                   retry budget.
            AuthenticationError:   Invalid API key — raised immediately.
            PermissionDeniedError: Account restriction — raised immediately.
            BadRequestError:       Malformed request — raised immediately.
            NotFoundError:         Model not found — raised immediately.
            ValueError:            Client not configured.
        """
        return self._call_with_fallback(
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_kwargs(
        self,
        model: str,
        messages: list[dict],
        tools: list[dict] | None,
        tool_choice: str | dict,
        temperature: float,
        max_tokens: int,
    ) -> dict:
        kwargs: dict = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice
        return kwargs

    def _call_once(self, kwargs: dict) -> object:
        """Execute a single completion call. kwargs must include 'model'."""
        client = self.get_client()
        return client.chat.completions.create(**kwargs)

    def _call_with_fallback(
        self,
        messages: list[dict],
        tools: list[dict] | None,
        tool_choice: str | dict,
        temperature: float,
        max_tokens: int,
    ) -> object:
        """
        Try the primary model; fall back to the fallback model on retryable
        errors. Raises the last error if both attempts fail.
        """
        fallback_model = getattr(self, "fallback_model", "")

        primary_kwargs = self._build_kwargs(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # --- Primary attempt ---
        try:
            response = self._call_once(primary_kwargs)
            logger.debug("[OpenRouter] Response received from primary model=%s", self.model)
            return response
        except _PERMANENT_ERROR_TYPES as permanent_exc:
            # Never fall back — surface the permanent error immediately.
            logger.error(
                "[OpenRouter] Permanent error from primary model=%s type=%s — not retrying.",
                self.model,
                type(permanent_exc).__name__,
            )
            raise
        except Exception as primary_exc:
            if not _is_retryable(primary_exc):
                # Unknown / non-retryable error — re-raise as-is.
                logger.error(
                    "[OpenRouter] Non-retryable error from primary model=%s type=%s",
                    self.model,
                    type(primary_exc).__name__,
                )
                raise

            # Retryable error — log and check fallback availability.
            logger.warning(
                "[OpenRouter] Retryable error from primary model=%s type=%s — "
                "attempting fallback model=%s",
                self.model,
                type(primary_exc).__name__,
                fallback_model or "none",
            )

            if not fallback_model:
                # Fallback disabled — re-raise the primary error.
                logger.error("[OpenRouter] Fallback disabled; raising primary error.")
                raise

        # --- Fallback attempt (one shot) ---
        fallback_kwargs = self._build_kwargs(
            model=fallback_model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        try:
            response = self._call_once(fallback_kwargs)
            logger.info(
                "[OpenRouter] Fallback model=%s responded successfully.",
                fallback_model,
            )
            return response
        except Exception as fallback_exc:
            logger.error(
                "[OpenRouter] Fallback model=%s also failed: type=%s — raising.",
                fallback_model,
                type(fallback_exc).__name__,
            )
            raise


# Singleton — shared across the application
openrouter_client = OpenRouterClient()
