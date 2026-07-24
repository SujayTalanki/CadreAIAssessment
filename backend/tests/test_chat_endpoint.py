import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.services import llm_client


class FakeChatMessage:
    def __init__(self, content: str):
        self.content = content


class FakeChoice:
    def __init__(self, content: str):
        self.message = FakeChatMessage(content)


class FakeChatCompletion:
    def __init__(self, content: str):
        self.choices = [FakeChoice(content)]


def _post_chat(client: TestClient, message: str):
    return client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": message}]},
    )


def test_chat_happy_path_no_escalation(monkeypatch):
    monkeypatch.setattr(
        llm_client._client.chat.completions,
        "create",
        lambda **kwargs: FakeChatCompletion(
            "You can book a call at https://cal.com/cadre-ai/strategy-call."
        ),
    )

    with TestClient(app) as client:
        response = _post_chat(client, "How do I book a call?")

    assert response.status_code == 200
    body = response.json()
    assert body["escalate"] is False
    assert "cal.com" in body["reply"]


def test_chat_escalation_marker_is_parsed(monkeypatch):
    monkeypatch.setattr(
        llm_client._client.chat.completions,
        "create",
        lambda **kwargs: FakeChatCompletion(
            "I don't have that information.\n[[ESCALATE]]"
        ),
    )

    with TestClient(app) as client:
        response = _post_chat(client, "Can you sign a custom SLA with 24/7 uptime guarantees?")

    body = response.json()
    assert body["escalate"] is True
    assert "[[ESCALATE]]" not in body["reply"]


def test_chat_rate_limit_error_degrades_gracefully(monkeypatch):
    def raise_rate_limit(**kwargs):
        request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
        response = httpx.Response(status_code=429, request=request)
        raise llm_client.openai.RateLimitError(
            "rate limited", response=response, body=None
        )

    monkeypatch.setattr(llm_client._client.chat.completions, "create", raise_rate_limit)

    with TestClient(app) as client:
        response = _post_chat(client, "What is Cadre AI?")

    assert response.status_code == 200
    body = response.json()
    assert body["escalate"] is True
    assert body["reply"] == llm_client.RATE_LIMIT_MESSAGE


def test_chat_connection_error_degrades_gracefully(monkeypatch):
    def raise_connection_error(**kwargs):
        request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
        raise llm_client.openai.APIConnectionError(request=request)

    monkeypatch.setattr(llm_client._client.chat.completions, "create", raise_connection_error)

    with TestClient(app) as client:
        response = _post_chat(client, "What is Cadre AI?")

    assert response.status_code == 200
    body = response.json()
    assert body["escalate"] is True
    assert body["reply"] == llm_client.CONNECTION_ERROR_MESSAGE


def test_chat_authentication_error_degrades_gracefully(monkeypatch):
    def raise_auth_error(**kwargs):
        request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
        response = httpx.Response(status_code=401, request=request)
        raise llm_client.openai.AuthenticationError(
            "invalid key", response=response, body=None
        )

    monkeypatch.setattr(llm_client._client.chat.completions, "create", raise_auth_error)

    with TestClient(app) as client:
        response = _post_chat(client, "What is Cadre AI?")

    assert response.status_code == 200
    body = response.json()
    assert body["escalate"] is True
    assert body["reply"] == llm_client.GENERIC_ERROR_MESSAGE


def test_chat_unexpected_exception_degrades_gracefully(monkeypatch):
    def raise_unexpected(**kwargs):
        raise ValueError("something unrelated to the LLM broke")

    monkeypatch.setattr(llm_client._client.chat.completions, "create", raise_unexpected)

    with TestClient(app) as client:
        response = _post_chat(client, "What is Cadre AI?")

    assert response.status_code == 200
    body = response.json()
    assert body["escalate"] is True
    assert body["reply"] == llm_client.GENERIC_ERROR_MESSAGE


class FakeEmptyChoicesCompletion:
    def __init__(self):
        self.choices = []


def test_chat_empty_choices_degrades_gracefully_instead_of_500(monkeypatch):
    # A provider can return HTTP 200 with an empty choices list (e.g. on a
    # moderation refusal). generate_reply must not let that raise an
    # unhandled IndexError past the always-200 contract.
    monkeypatch.setattr(
        llm_client._client.chat.completions,
        "create",
        lambda **kwargs: FakeEmptyChoicesCompletion(),
    )

    with TestClient(app) as client:
        response = _post_chat(client, "What is Cadre AI?")

    assert response.status_code == 200
    body = response.json()
    assert body["escalate"] is True
    assert body["reply"] == llm_client.GENERIC_ERROR_MESSAGE


def test_chat_sends_system_prompt_and_full_history_to_the_model(monkeypatch):
    captured = {}

    def capture_and_respond(**kwargs):
        captured.update(kwargs)
        return FakeChatCompletion("Sure, here's the answer.")

    monkeypatch.setattr(llm_client._client.chat.completions, "create", capture_and_respond)

    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={
                "messages": [
                    {"role": "user", "content": "What does Cadre AI do?"},
                    {"role": "assistant", "content": "We help with AI strategy."},
                    {"role": "user", "content": "How do I book a call?"},
                ]
            },
        )

    assert response.status_code == 200
    sent_messages = captured["messages"]
    assert sent_messages[0]["role"] == "system"
    assert "Cadre AI support assistant" in sent_messages[0]["content"]
    assert "Relevant knowledge for this question" in sent_messages[0]["content"]
    # The full conversation history follows the system message, in order,
    # unmodified.
    assert [m["role"] for m in sent_messages[1:]] == ["user", "assistant", "user"]
    assert sent_messages[-1]["content"] == "How do I book a call?"


def test_chat_rejects_empty_messages():
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"messages": []})

    assert response.status_code == 422
