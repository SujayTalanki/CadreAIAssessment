# CLAUDE.md

Onboarding doc for Claude Code sessions on this repo. Read this before making changes.

## What this is

A customer support chatbot for Cadre AI (a fictional-for-this-exercise AI strategy consultancy), built as a take-home challenge. It answers common inbound questions (what Cadre does, booking a strategist call, portal access, the AI Maturity Index, LLM selection/data security) and gracefully escalates to a human for anything it can't answer.

## Architecture

- **`backend/`** — FastAPI app. Retrieval-augmented generation over a static FAQ corpus:
  1. On startup, `app/data/faqs.json` is embedded into an in-memory Chroma collection (`app/services/retrieval.py`), using Chroma's bundled default embedding function (`all-MiniLM-L6-v2` via onnxruntime — no external embeddings API key needed).
  2. Each `POST /api/chat` call embeds the latest user message, retrieves the top-**5** most relevant FAQ chunks (bumped up from 3 — see the comment in `llm_client.py`; at 3, compound questions sometimes missed a relevant chunk in this 10-entry corpus), and appends them to the static system prompt (`app/system_prompt.py`) before calling Claude.
  3. The model call goes through **OpenRouter's OpenAI-compatible endpoint** (`app/services/llm_client.py`, using the `openai` SDK pointed at `https://openrouter.ai/api/v1`, model id `anthropic/claude-sonnet-5`), not the native Anthropic SDK — only an OpenRouter key was available for this exercise, not a native Anthropic key. This also matches Cadre AI's own stated approach in the brief ("OpenRouter for model access"). Extended thinking is disabled via `extra_body={"reasoning": {"enabled": False}}`, OpenRouter's equivalent of Anthropic's native `thinking` param.
  4. The model decides whether the retrieved knowledge actually answers the question. If not, it appends a literal `[[ESCALATE]]` marker to its reply, which the backend strips into a boolean `escalate` field in the response.
- **`frontend/`** — React + Vite + TypeScript + Tailwind. Plain `fetch()` chat UI; conversation state lives only in browser state (sent in full on every request) — there is no database and no server-side session.

## Hard conventions — don't casually change these

- **FAQ content only changes via `backend/app/data/faqs.json`.** Never hardcode facts into `system_prompt.py` — that file holds only behavioral instructions (scope, no-fabrication rule, escalation rule, tone), not content.
- **The Chroma index is rebuilt in-memory on every app startup.** There is no persistent volume and no external vector DB. Don't add one without updating this file and re-checking the Render deployment config — the corpus is small enough that in-memory rebuild is intentional, not a stopgap.
- **Non-streaming `/api/chat` by design.** Don't add SSE/streaming without updating this file first — the escalation-marker parsing and error-handling logic both assume the full response text is available before returning.
- **No database, no auth, no persisted conversation history.** This is a deliberate scope cut for a stateless MVP support widget, not an oversight. See `plan.md` for the full scope-cut list.
- **Backend tests never hit the real OpenRouter API** — `llm_client._client.chat.completions.create` is monkeypatched in `backend/tests/test_chat_endpoint.py`; retrieval tests run against a real (but ephemeral, in-memory) Chroma collection since that has no external cost.
- **Error handling in `llm_client.py` must always return HTTP 200** with a graceful user-facing message on failure (rate limit, connection error, auth error, etc.) — never leak a stack trace to the frontend.

## Run locally

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in OPENROUTER_API_KEY
uvicorn app.main:app --reload

# frontend
cd frontend
npm install
cp .env.example .env   # set VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

## Required env vars

- Backend: `OPENROUTER_API_KEY`, `FRONTEND_ORIGIN` (CORS allowlist), `MODEL_NAME` (defaults to `anthropic/claude-sonnet-5`)
- Frontend: `VITE_API_BASE_URL`

## Deployment

Backend → Render (via `render.yaml` blueprint), frontend → Vercel (root directory `frontend/`). Render's free tier spins down after ~15 min idle; `.github/workflows/keep-alive.yml` pings `/api/health` every 10 minutes to prevent that, driven by a repo variable `BACKEND_HEALTH_URL` (not a secret — it's just the public Render URL). Don't remove this workflow without either accepting the cold-start UX regression or setting up an equivalent mitigation.

## See also

`plan.md` at repo root for the full phased build plan and explicit scope-cut list.
