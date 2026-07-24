from fastapi import APIRouter, Request

from app.models import ChatRequest, ChatResponse
from app.services.llm_client import generate_reply

router = APIRouter()


@router.post("/api/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
    return generate_reply(body.messages, request.app.state.faq_collection)
