import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-for-pytest")
os.environ.setdefault("FRONTEND_ORIGIN", "http://localhost:5173")
os.environ.setdefault("MODEL_NAME", "claude-sonnet-5")

import httpx
import pytest


def make_httpx_response(status_code: int) -> httpx.Response:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return httpx.Response(status_code=status_code, request=request)


@pytest.fixture
def httpx_request() -> httpx.Request:
    return httpx.Request("POST", "https://api.anthropic.com/v1/messages")
