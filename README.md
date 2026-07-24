# Cadre AI Support Chatbot

A customer support chatbot for Cadre AI — answers common inbound questions (what Cadre does, booking a strategist call, portal access, the AI Maturity Index, LLM selection & data security) and escalates gracefully when it can't help.

**Live demo:** TODO — add deployed Vercel URL here after Phase 8
**Backend API:** TODO — add deployed Render URL here after Phase 8

See [`plan.md`](./plan.md) for the full build plan, architecture decisions, and explicit scope cuts. See [`CLAUDE.md`](./CLAUDE.md) for repo conventions.

## Architecture

- `backend/` — FastAPI + Claude Sonnet 5 (`anthropic/claude-sonnet-5`) via OpenRouter's OpenAI-compatible API, with a retrieval-augmented knowledge base: FAQs in `backend/app/data/faqs.json` are embedded into an in-memory Chroma collection on startup, and the top-5 most relevant entries are retrieved per-turn and injected into the system prompt.
- `frontend/` — React + Vite + TypeScript + Tailwind chat UI. Conversation state lives only in the browser; there is no database.

## Running locally

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in OPENROUTER_API_KEY
uvicorn app.main:app --reload

# frontend (separate terminal)
cd frontend
npm install
cp .env.example .env   # set VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

## Known limitations

- Render's free tier spins down after ~15 minutes idle — the first request after idle can take 30-50 seconds to wake up.
- The knowledge base content (booking link, portal URL, etc.) is fabricated for this exercise, since Cadre AI has no real backend systems to integrate with.
- See `plan.md` for the full list of deliberate scope cuts (no DB, no auth, no streaming, etc.).
