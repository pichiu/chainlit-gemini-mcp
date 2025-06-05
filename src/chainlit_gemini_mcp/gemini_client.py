import os
import google.genai as genai


def get_client(api_key: str | None = None) -> genai.Client:
    """Create a Google Gemini client using the provided API key or
    the ``GOOGLE_API_KEY`` environment variable.
    """
    key = api_key or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set")
    return genai.Client(api_key=key)
