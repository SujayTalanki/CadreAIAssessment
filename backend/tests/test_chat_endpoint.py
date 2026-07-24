import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.services import anthropic_client


class FakeTextBlock:
    def __init__(self, text: str):
        self.type = "text"
        self.text = text


class FakeMessage:
    def __init__(self, text: str):
        self.content = [FakeTextBlock(text)]


def _post_chat(client: TestClient, message: str):
    return client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": message}]},
    )


def test_chat_happy_path_no_escalation(monkeypatch):
    monkeypatch.setattr(
        anthropic_client._client.messages,
        "create",
        lambda **kwargs: FakeMessage("You can book a call at https://cal.com/cadre-ai/strategy-call."),
    )

    with TestClient(app) as client:
        response = _post_chat(client, "How do I book a call?")

    assert response.status_code == 200
    body = response.json()
    assert body["escalate"] is False
    assert "cal.com" in body["reply"]


def test_chat_escalation_marker_is_parsed(monkeypatch):
    monkeypatch.setattr(
        anthropic_client._client.messages,
        "create",
        lambda **kwargs: FakeMessage("I don't have that information.\n[[ESCALATE]]"),
    )

    with TestClient(app) as client:
        response = _post_chat(client, "Can you sign a custom SLA with 24/7 uptime guarantees?")

    body = response.json()
    assert body["escalate"] is True
    assert "[[ESCALATE]]" not in body["reply"]


def test_chat_rate_limit_error_degrades_gracefully(monkeypatch):
    def raise_rate_limit(**kwargs):
        request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        response = httpx.Response(status_code=429, request=request)
        raise anthropic_client.anthropic.RateLimitError(
            "rate limited", response=response, body=None
        )

    monkeypatch.setattr(anthropic_client._client.messages, "create", raise_rate_limit)

    with TestClient(app) as client:
        response = _post_chat(client, "What is Cadre AI?")

    assert response.status_code == 200
    body = response.json()
    assert body["escalate"] is True
    assert body["reply"] == anthropic_client.RATE_LIMIT_MESSAGE


def test_chat_connection_error_degrades_gracefully(monkeypatch):
    def raise_connection_error(**kwargs):
        request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        raise anthropic_client.anthropic.APIConnectionError(request=request)

    monkeypatch.setattr(anthropic_client._client.messages, "create", raise_connection_error)

    with TestClient(app) as client:
        response = _post_chat(client, "What is Cadre AI?")

    assert response.status_code == 200
    body = response.json()
    assert body["escalate"] is True
    assert body["reply"] == anthropic_client.CONNECTION_ERROR_MESSAGE


def test_chat_rejects_empty_messages():
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"messages": []})

    assert response.status_code == 422
