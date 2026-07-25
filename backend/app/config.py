import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application configuration, loaded from environment variables at import time."""

    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    MODEL_NAME = os.getenv("MODEL_NAME", "anthropic/claude-sonnet-5")


settings = Settings()

# Fail fast: Ask for the API key if it's missing
if not settings.OPENROUTER_API_KEY:
    raise RuntimeError(
        "OPENROUTER_API_KEY is missing or empty. Set it in backend/.env "
        "(see backend/.env.example)."
    )
