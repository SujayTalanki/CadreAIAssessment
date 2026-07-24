import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    MODEL_NAME = os.getenv("MODEL_NAME", "anthropic/claude-sonnet-5")


settings = Settings()

# Fail fast: importing this module is the single choke point every entrypoint
# goes through, so a missing key surfaces immediately instead of the app
# starting up and only failing once a chat request hits the model provider.
if not settings.OPENROUTER_API_KEY:
    raise RuntimeError(
        "OPENROUTER_API_KEY is missing or empty. Set it in backend/.env "
        "(see backend/.env.example)."
    )
