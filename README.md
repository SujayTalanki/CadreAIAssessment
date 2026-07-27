# Cadre AI Support Chatbot

A customer support chatbot for Cadre AI — answers common inbound questions (what Cadre does, booking a strategist call, portal access, the AI Maturity Index, LLM selection & data security) and escalates gracefully when it can't help.

**Live demo:** https://cadre-ai-assessment-iota.vercel.app
**Backend API:** https://cadre-ai-chatbot-backend.onrender.com

See [`plan.md`](./plan.md) for the full build plan, architecture decisions, and explicit scope cuts. See [`CLAUDE.md`](./CLAUDE.md) for repo conventions.

## Architecture

- `backend/` — FastAPI + Claude Sonnet 5 (`anthropic/claude-sonnet-5`) via OpenRouter's OpenAI-compatible API. FAQs in `backend/app/data/faqs.json` are read fresh into the prompt on every call (no vector store) and the resulting prompt gets cached (Cache-Augmented Generation, not RAG) — see `CLAUDE.md` for why, and for when we'd add real retrieval back.
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

- Render's free tier spins down after ~15 minutes idle, causing a 30-50 second cold start on the first request after. Mitigated by `.github/workflows/keep-alive.yml`, a scheduled GitHub Actions job that pings `/api/health` every 10 minutes so the service never idles long enough to spin down. **Setup required:** after deploying the backend, set a repo variable `BACKEND_HEALTH_URL` (Settings → Secrets and variables → Actions → Variables) to the Render URL, e.g. `https://cadre-ai-chatbot-backend.onrender.com`.
- The knowledge base content (booking link, portal URL, etc.) is fabricated for this exercise, since Cadre AI has no real backend systems to integrate with.
- See `plan.md` for the full list of deliberate scope cuts (no DB, no auth, no streaming, etc.).
