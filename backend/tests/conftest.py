import os

os.environ.setdefault("OPENROUTER_API_KEY", "test-key-for-pytest")
os.environ.setdefault("FRONTEND_ORIGIN", "http://localhost:5173")
os.environ.setdefault("MODEL_NAME", "anthropic/claude-sonnet-5")

import httpx
import pytest


def make_httpx_response(status_code: int) -> httpx.Response:
    request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    return httpx.Response(status_code=status_code, request=request)


@pytest.fixture
def httpx_request() -> httpx.Request:
    return httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
