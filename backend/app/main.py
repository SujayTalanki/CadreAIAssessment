from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(title="Cadre AI Support Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# app.routes.chat router will be included here in a later phase
