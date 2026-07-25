from typing import Literal
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in a chat conversation, from either the user or the assistant."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    """Request body for POST /api/chat: the full conversation history so far."""

    messages: list[ChatMessage] = Field(min_length=1, max_length=50)


class ChatResponse(BaseModel):
    """Response body for POST /api/chat: the assistant's reply and whether to escalate."""

    reply: str
    escalate: bool
