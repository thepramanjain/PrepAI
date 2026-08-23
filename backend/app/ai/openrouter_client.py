"""
app/ai/openrouter_client.py

OpenRouter-compatible client for GPT-4o agentic workflows.

Architecture:
    OpenAI Python SDK
        ↓
    base_url = https://openrouter.ai/api/v1
        ↓
    model = openai/gpt-4o (configurable via OPENROUTER_MODEL)

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

from openai import OpenAI, APIError, APIConnectionError, RateLimitError, APITimeoutError
from app.config.settings import settings

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterClient:
    """
    Wrapper for the OpenRouter API using the OpenAI-compatible SDK.
    Initialized once and shared as a singleton across the application.
    """

    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.OPENROUTER_MODEL
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
            except Exception as e:
                # Log without exposing the key
                print(f"[OpenRouter] Failed to initialize client: {type(e).__name__}")

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

    def chat_completion(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str = "auto",
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> object:
        """
        Send a chat completion request to OpenRouter / GPT-4o.

        Args:
            messages:     Conversation history in OpenAI message format.
            tools:        Optional list of tool definitions (JSON schema).
            tool_choice:  "auto" | "none" | "required" — default "auto".
            temperature:  Sampling temperature (default 0.3 for reliable routing).
            max_tokens:   Maximum tokens in the response.

        Returns:
            The raw ChatCompletion response object.

        Raises:
            RateLimitError:      OpenRouter rate-limit hit.
            APIConnectionError:  Network failure reaching OpenRouter.
            APIError:            Any other OpenRouter / OpenAI API error.
            ValueError:          Client not configured.
        """
        client = self.get_client()

        kwargs: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice

        try:
            return client.chat.completions.create(**kwargs)
        except RateLimitError:
            raise
        except APIConnectionError:
            raise
        except APITimeoutError:
            raise
        except APIError:
            raise


# Singleton — shared across the application
openrouter_client = OpenRouterClient()
