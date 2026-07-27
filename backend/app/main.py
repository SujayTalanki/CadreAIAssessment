from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes.chat import router as chat_router

app = FastAPI(title="Cadre AI Support Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(chat_router)


@app.get("/api/health")
async def health():
    """
    Health check endpoint used by Render's keep-alive workflow.

    Returns:
        dict: A static {"status": "ok"} payload.
    """
    return {"status": "ok"}
