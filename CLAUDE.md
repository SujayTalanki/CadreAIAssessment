# CLAUDE.md

Onboarding doc for Claude Code sessions on this repo. Read this before making changes.

## What this is

A customer support chatbot for Cadre AI (a fictional-for-this-exercise AI strategy consultancy), built as a take-home challenge. It answers common inbound questions (what Cadre does, booking a strategist call, portal access, the AI Maturity Index, LLM selection/data security) and gracefully escalates to a human for anything it can't answer.

## Architecture

- **`backend/`** — Cache-Augmented Generation (CAG), no vector store or retrieval step at all:
  1. `app/services/llm_client.py`'s `_load_knowledge_block()` reads the entire `app/data/faqs.json` corpus fresh from disk on every call, in the file's own order. There's no embedding model and no vector store (no `chromadb`) - at this corpus size there's nothing to select, so a real retrieval step would just be complexity with nothing to select from. It's a plain file read, cheap enough not to cache in memory - editing `faqs.json` takes effect on the very next request, no restart needed.
  2. The resulting system prompt (instructions + the knowledge block) is identical on every call, which is what makes it cacheable *on OpenRouter's side*: marked with Anthropic's `cache_control: {"ttl": "1h"}` (via OpenRouter's OpenAI-compatible endpoint), plus a fixed `session_id` for sticky provider routing. One full-price write per hour of activity, ~90% cheaper cached reads for every call after. This is a different cache from the file read above - one's about not re-reading a file, the other's about not re-billing an unchanged prompt.
  3. The model call goes through **OpenRouter's OpenAI-compatible endpoint** (`app/services/llm_client.py`, using the `openai` SDK pointed at `https://openrouter.ai/api/v1`, model id `anthropic/claude-sonnet-5`), not the native Anthropic SDK — only an OpenRouter key was available for this exercise, not a native Anthropic key. This also matches Cadre AI's own stated approach in the brief ("OpenRouter for model access"). Extended thinking is disabled via `extra_body={"reasoning": {"enabled": False}}`, OpenRouter's equivalent of Anthropic's native `thinking` param.
  4. The model decides whether the knowledge block actually answers the question. If not, it appends a literal `[[ESCALATE]]` marker to its reply, which the backend strips into a boolean `escalate` field in the response.
  5. **If the corpus outgrows CAG** (loading everything in full stops being cheap/fast enough): reintroduce a vector store (e.g. `chromadb`) and real top-k retrieval, drop the whole-corpus caching, pick a chunk size empirically (test a few sizes against real questions rather than guessing one), and add a reranking step on top of initial retrieval if the embedding-similarity results alone aren't precise enough - evaluate both chunk size and `k` via precision@k/recall@k against a labeled set of queries, not by eyeballing results.
- **`frontend/`** — React + Vite + TypeScript + Tailwind. Plain `fetch()` chat UI; conversation state lives only in browser state (sent in full on every request) — there is no database and no server-side session.

## Hard conventions — don't casually change these

- **FAQ content only changes via `backend/app/data/faqs.json`.** Never hardcode facts into `system_prompt.py` — that file holds only behavioral instructions (scope, no-fabrication rule, escalation rule, tone), not content.
- **No vector store, no embedding model.** `llm_client.py`'s `_load_knowledge_block()` reads `faqs.json` fresh on every call. Don't add `chromadb` (or similar) back without updating this file first - see the Architecture section above for when that'd actually be warranted.
- **Non-streaming `/api/chat` by design.** Don't add SSE/streaming without updating this file first — the escalation-marker parsing and error-handling logic both assume the full response text is available before returning.
- **No database, no auth, no persisted conversation history.** This is a deliberate scope cut for a stateless MVP support widget, not an oversight. See `plan.md` for the full scope-cut list.
- **Backend tests never hit the real OpenRouter API** — `llm_client._client.chat.completions.create` is monkeypatched in `backend/tests/test_chat_endpoint.py`.
- **Error handling in `llm_client.py` must always return HTTP 200** with a graceful user-facing message on failure (rate limit, connection error, auth error, empty response, or anything else) — never leak a stack trace to the frontend. This is why `generate_reply`'s try block wraps the API call and response parsing together, not just the API call alone.
- **`POST /api/chat` in `routes/chat.py` must stay a plain `def`, not `async def`.** `generate_reply` does a blocking HTTP call to OpenRouter; FastAPI runs sync route handlers in a thread pool, so this keeps one slow chat request from stalling the event loop for every other concurrent request — including the `/api/health` keep-alive ping.

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

## Required env vars

- Backend: `OPENROUTER_API_KEY`, `FRONTEND_ORIGIN` (CORS allowlist), `MODEL_NAME` (defaults to `anthropic/claude-sonnet-5`)
- Frontend: `VITE_API_BASE_URL`

## Deployment

Backend → Render (via `render.yaml` blueprint), frontend → Vercel (root directory `frontend/`). Render's free tier spins down after ~15 min idle; `.github/workflows/keep-alive.yml` pings `/api/health` every 10 minutes to prevent that, driven by a repo variable `BACKEND_HEALTH_URL` (not a secret — it's just the public Render URL). Don't remove this workflow without either accepting the cold-start UX regression or setting up an equivalent mitigation.

## Claude Code tooling

This repo has custom commands and subagents under `.claude/` — use them instead of re-deriving the same instructions by hand:

**Commands** (`.claude/commands/`):
- `/validate-faqs` — checks `faqs.json` is valid JSON, ids are unique, and required fields are non-empty. Free, local, no API calls. Standalone, since direct hand-edits to `faqs.json` don't go through `/add-faq` at all.
- `/add-faq` — scaffolds a new FAQ entry in the correct schema/tone, checks for overlap with existing entries first, asks for confirmation before editing `faqs.json`, then runs the same validation as `/validate-faqs` automatically. No restart needed after - `faqs.json` reloads fresh on the next request.
- `/commit` — stages, scans for anything secret-looking, and commits with a short auto-generated message. Local commit only, never pushes.

**Subagents** (`.claude/agents/`):
- `web-content-extractor` — verbatim extraction from external web pages (e.g. paginated listings); never summarizes or drops items, always reports exact counts.
- `faq-writer` — drafts FAQ content matching this repo's schema/tone/no-fabrication rules; read-only, so `/add-faq` applies its draft rather than letting it write directly.

## See also

`plan.md` at repo root for the full phased build plan and explicit scope-cut list.
