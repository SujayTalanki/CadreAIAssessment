from fastapi import APIRouter, Request

from app.models import ChatRequest, ChatResponse
from app.services.llm_client import generate_reply

router = APIRouter()


@router.post("/api/chat", response_model=ChatResponse)
def chat(request: Request, body: ChatRequest) -> ChatResponse:
    # Plain `def`, not `async def`: generate_reply does blocking work (a
    # synchronous Chroma embedding query, then a synchronous HTTP call to
    # OpenRouter). FastAPI runs sync route handlers in a thread pool, so this
    # keeps one slow chat request from stalling the event loop - and with it,
    # every other concurrent request, including the /api/health keep-alive
    # ping that prevents Render's free tier from spinning down.
    return generate_reply(body.messages, request.app.state.faq_collection)
