# CLAUDE.md

Onboarding doc for Claude Code sessions on this repo. Read this before making changes.

## What this is

A customer support chatbot for Cadre AI (a fictional-for-this-exercise AI strategy consultancy), built as a take-home challenge. It answers common inbound questions (what Cadre does, booking a strategist call, portal access, the AI Maturity Index, LLM selection/data security) and gracefully escalates to a human for anything it can't answer.

## Architecture

- **`backend/`** — FastAPI app. Retrieval-augmented generation over a static FAQ corpus:
  1. On startup, `app/data/faqs.json` is embedded into an in-memory Chroma collection (`app/services/retrieval.py`), using Chroma's bundled default embedding function (`all-MiniLM-L6-v2` via onnxruntime — no external embeddings API key needed).
  2. `retrieval.query()` implements simple, RAG-style top-k retrieval - it takes an explicit `k` and returns the k nearest FAQ entries by embedding similarity. Nothing about the retrieval code is hardcoded to "everything." What's tuned is the `k` value passed in at the call site: `llm_client.py` currently calls `retrieval.query(collection, latest_user_message, k=collection.count())`, i.e. it retrieves **the entire FAQ corpus** every turn rather than a fixed number, appending all of it to the static system prompt (`app/system_prompt.py`) before calling Claude. This isn't a bug, with the corpus still small (27 entries as of this writing), retrieving everything is simpler than tuning k further and permanently removes that failure mode, at negligible extra token cost per call. If the corpus grows large enough that whole-corpus retrieval becomes a real cost/latency concern, dropping back to a fixed `k` (paired with a real re-ranking strategy, since embedding similarity alone wasn't reliable enough at even 15 entries) is a one-line change at that call site - not a redesign.
  3. The model call goes through **OpenRouter's OpenAI-compatible endpoint** (`app/services/llm_client.py`, using the `openai` SDK pointed at `https://openrouter.ai/api/v1`, model id `anthropic/claude-sonnet-5`), not the native Anthropic SDK — only an OpenRouter key was available for this exercise, not a native Anthropic key. This also matches Cadre AI's own stated approach in the brief ("OpenRouter for model access"). Extended thinking is disabled via `extra_body={"reasoning": {"enabled": False}}`, OpenRouter's equivalent of Anthropic's native `thinking` param.
  4. The model decides whether the retrieved knowledge actually answers the question. If not, it appends a literal `[[ESCALATE]]` marker to its reply, which the backend strips into a boolean `escalate` field in the response.
- **`frontend/`** — React + Vite + TypeScript + Tailwind. Plain `fetch()` chat UI; conversation state lives only in browser state (sent in full on every request) — there is no database and no server-side session.

## Hard conventions — don't casually change these

- **FAQ content only changes via `backend/app/data/faqs.json`.** Never hardcode facts into `system_prompt.py` — that file holds only behavioral instructions (scope, no-fabrication rule, escalation rule, tone), not content.
- **The Chroma index is rebuilt in-memory on every app startup.** There is no persistent volume and no external vector DB. Don't add one without updating this file and re-checking the Render deployment config — the corpus is small enough that in-memory rebuild is intentional, not a stopgap.
- **Non-streaming `/api/chat` by design.** Don't add SSE/streaming without updating this file first — the escalation-marker parsing and error-handling logic both assume the full response text is available before returning.
- **No database, no auth, no persisted conversation history.** This is a deliberate scope cut for a stateless MVP support widget, not an oversight. See `plan.md` for the full scope-cut list.
- **Backend tests never hit the real OpenRouter API** — `llm_client._client.chat.completions.create` is monkeypatched in `backend/tests/test_chat_endpoint.py`; retrieval tests run against a real (but ephemeral, in-memory) Chroma collection since that has no external cost.
- **Error handling in `llm_client.py` must always return HTTP 200** with a graceful user-facing message on failure (rate limit, connection error, auth error, empty response, or anything else) — never leak a stack trace to the frontend. This is why `generate_reply`'s try block wraps retrieval + the API call + response parsing all together, not just the API call.
- **`POST /api/chat` in `routes/chat.py` must stay a plain `def`, not `async def`.** `generate_reply` does blocking work (a synchronous Chroma query, then a synchronous HTTP call to OpenRouter); FastAPI runs sync route handlers in a thread pool, so this keeps one slow chat request from stalling the event loop for every other concurrent request — including the `/api/health` keep-alive ping.

## Run locally

First-time setup (once per machine):

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in OPENROUTER_API_KEY

# frontend
cd frontend
npm install
cp .env.example .env   # set VITE_API_BASE_URL=http://localhost:8000
```

After that, start both servers together from the repo root:

```bash
./dev.sh          # starts backend (:8000) and frontend (:5173), logs to /tmp/cadre-*.log
./dev.sh stop     # stops both
```

**Gotcha:** `uvicorn --reload` only watches `.py` files by default, not `app/data/faqs.json`. After editing FAQ content, the running dev server won't pick it up until you manually restart it (`./dev.sh stop && ./dev.sh`, or touch a `.py` file) - the in-memory Chroma collection stays stale otherwise.

## Required env vars

- Backend: `OPENROUTER_API_KEY`, `FRONTEND_ORIGIN` (CORS allowlist), `MODEL_NAME` (defaults to `anthropic/claude-sonnet-5`)
- Frontend: `VITE_API_BASE_URL`

## Deployment

Backend → Render (via `render.yaml` blueprint), frontend → Vercel (root directory `frontend/`). Render's free tier spins down after ~15 min idle; `.github/workflows/keep-alive.yml` pings `/api/health` every 10 minutes to prevent that, driven by a repo variable `BACKEND_HEALTH_URL` (not a secret — it's just the public Render URL). Don't remove this workflow without either accepting the cold-start UX regression or setting up an equivalent mitigation.

## See also

`plan.md` at repo root for the full phased build plan and explicit scope-cut list.
