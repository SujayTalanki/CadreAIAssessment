from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.chat import router as chat_router
from app.services.retrieval import ingest_faqs

app = FastAPI(title="Cadre AI Support Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.on_event("startup")
async def startup():
    app.state.faq_collection = ingest_faqs()


@app.get("/api/health")
async def health():
    return {"status": "ok"}


app.include_router(chat_router)
