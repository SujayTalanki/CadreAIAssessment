from fastapi import APIRouter
from app.models import ChatRequest, ChatResponse
from app.services.llm_client import generate_reply

router = APIRouter()


@router.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest) -> ChatResponse:
    """
    Handle a chat request and return the assistant's reply.

    Deliberately a plain `def`, not `async def`: generate_reply does a
    blocking HTTP call to OpenRouter. FastAPI runs sync route handlers in a
    thread pool, so this keeps one slow chat request from stalling the
    event loop - and with it, every other concurrent request, including the
    /api/health keep-alive ping that prevents Render's free tier from
    spinning down.

    Args:
        body (ChatRequest): The parsed request body containing the full
            conversation history.

    Returns:
        ChatResponse: The assistant's reply and whether to escalate to a human.
    """
    return generate_reply(body.messages)
