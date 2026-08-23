"""
app/ai/gemini_client.py

Reusable Gemini AI client wrapper using the official google-genai SDK.
Handles configuration and initialization.
"""

from google import genai
from app.config.settings import settings


class GeminiClientWrapper:
    """
    Wrapper for the Google GenAI SDK.
    Initialized once and shared across requests.
    """
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL
        self.client = None

        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                # Log the error safely without exposing the API key
                print(f"Failed to initialize Gemini Client: {str(e)}")

    def get_client(self) -> genai.Client:
        """
        Returns the configured client instance.
        Throws ValueError if not properly configured.
        """
        if not self.client:
            raise ValueError("Gemini client is not configured. Missing or invalid API key.")
        return self.client

# Singleton instance
gemini_wrapper = GeminiClientWrapper()
