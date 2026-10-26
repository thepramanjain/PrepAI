"""
app/config/settings.py

Application settings loaded from environment variables using Pydantic Settings.
All configuration is centralized here so no hard-coded values leak into business logic.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings — loaded from .env file or environment variables."""

    # MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "prepai"

    # Application
    APP_NAME: str = "PrepAI Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # JWT Authentication
    JWT_SECRET: str = "change_this_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Generative AI (Gemini)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # LiveKit — server-side only. NEVER expose API secret to client.
    LIVEKIT_URL: str = ""
    LIVEKIT_API_KEY: str = ""
    LIVEKIT_API_SECRET: str = ""

    # OpenRouter — Agentic AI (Phase 10)
    # Used for GPT-4o orchestration, tool calling, and career coaching.
    # NEVER expose this key to the frontend.
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "openai/gpt-4o"
    OPENROUTER_SITE_URL: str = ""   # optional: sent as HTTP-Referer header
    OPENROUTER_APP_NAME: str = ""  # optional: sent as X-Title header

    # CORS — comma-separated list of allowed origins
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    model_config = {
        "env_file": [
            str(__import__("pathlib").Path(__file__).resolve().parent.parent.parent / ".env"),
            ".env",
        ],
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse the CORS_ORIGINS string into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


# Single shared settings instance used across the application
settings = Settings()
