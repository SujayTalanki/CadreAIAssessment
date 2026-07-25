from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes.chat import router as chat_router
from app.services.retrieval import ingest_faqs


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build the in-memory FAQ collection once at application startup.

    Args:
        app (FastAPI): The FastAPI application instance.

    Yields:
        None: Control returns to FastAPI until the app shuts down.
    """
    app.state.faq_collection = ingest_faqs()
    yield


app = FastAPI(title="Cadre AI Support Chatbot", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    """Health check endpoint used by Render's keep-alive workflow.

    Returns:
        dict: A static {"status": "ok"} payload.
    """
    return {"status": "ok"}


app.include_router(chat_router)
