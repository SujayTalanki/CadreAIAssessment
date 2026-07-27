# CLAUDE.md

Onboarding doc for Claude Code sessions on this repo. Read this before making changes.

## What this is

A customer support chatbot for Cadre AI (a fictional-for-this-exercise AI strategy consultancy), built as a take-home challenge. It answers common inbound questions (what Cadre does, booking a strategist call, portal access, the AI Maturity Index, LLM selection/data security) and gracefully escalates to a human for anything it can't answer.

## Architecture

- **`backend/`** — Cache-Augmented Generation (CAG), no vector store or retrieval step at all:
  1. This is CAG (Cache-Augmented Generation) style pipeline - `app/services/llm_client.py`'s `_load_knowledge_block()` reads the entire `app/data/faqs.json` corpus fresh from disk on every call, in the file's own order. There's no embedding model and no vector store, at this corpus size there's nothing to select, so a real retrieval step would just be complexity with nothing to select from. It's a plain file read, cheap enough not to cache in memory - editing `faqs.json` takes effect on the very next request, no restart needed.
  2. The resulting system prompt (instructions + the knowledge block) is identical on every call, which is what makes it cacheable *on OpenRouter's side*: marked with Anthropic's `cache_control: {"ttl": "1h"}` (via OpenRouter's OpenAI-compatible endpoint), plus a fixed `session_id` for sticky provider routing. One full-price write per hour of activity, ~90% cheaper cached reads for every call after. This is a different cache from the file read above - one's about not re-reading a file, the other's about not re-billing an unchanged prompt. Conversation history is appended as separate `user`/`assistant` messages after this cached system message, not folded into the system prompt text itself - that's what keeps the cached portion byte-identical regardless of how long the conversation gets.
  3. The model call goes through **OpenRouter's OpenAI-compatible endpoint** (`app/services/llm_client.py`, using the `openai` SDK pointed at `https://openrouter.ai/api/v1`, model id `anthropic/claude-sonnet-5`), not the native Anthropic SDK — only an OpenRouter key was available for this exercise, not a native Anthropic key. This also matches Cadre AI's own stated approach in the brief ("OpenRouter for model access"). Extended thinking is disabled via `extra_body={"reasoning": {"enabled": False}}`, OpenRouter's equivalent of Anthropic's native `thinking` param.
  4. The model decides whether the knowledge block actually answers the question. If not, it appends a literal `[[ESCALATE]]` marker to its reply, which the backend strips into a boolean `escalate` field in the response.
- **`frontend/`** — React + Vite + TypeScript + Tailwind. Plain `fetch()` chat UI; conversation state lives only in browser state (sent in full on every request) — there is no database and no server-side session.

## Hard conventions — don't casually change these

- **FAQ content only changes via `backend/app/data/faqs.json`.** Never hardcode facts into `system_prompt.py` — that file holds only behavioral instructions (scope, no-fabrication rule, escalation rule, tone), not content.
- **No vector store, no embedding model.** `llm_client.py`'s `_load_knowledge_block()` reads `faqs.json` fresh on every call. Don't add `chromadb` (or similar) back without updating this file first - see the Architecture section above for when that'd actually be warranted.
- **Non-streaming `/api/chat` by design.** Don't add SSE/streaming without updating this file first — the escalation-marker parsing and error-handling logic both assume the full response text is available before returning.
- **No database, no auth, no persisted conversation history.** This is a deliberate scope cut for a stateless MVP support widget, not an oversight. See `plan.md` for the full scope-cut list.
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
- `/validate-faqs` — checks `faqs.json` is valid JSON, ids are unique, required fields are non-empty, *and* that every entry actually loads into the live knowledge block (not just that the JSON parses). Free, local, no API calls. Standalone, since direct hand-edits to `faqs.json` don't go through `/add-faq` at all.
- `/add-faq <url-or-topic>` — delegates to `faq-writer` for drafting (works from either a source URL or a freeform topic; overlap-checking against the existing corpus happens once, inside the agent, not duplicated here), shows the draft, asks for confirmation before editing `faqs.json`, then runs the same structural + functional checks as `/validate-faqs`. No restart needed after - `faqs.json` reloads fresh on the next request.
- `/commit` — stages, scans for anything secret-looking, and commits with a short auto-generated message. Local commit only, never pushes.

**Subagents** (`.claude/agents/`):
- `web-content-extractor` — verbatim extraction from external web pages (e.g. paginated listings); never summarizes or drops items, always reports exact counts.
- `faq-writer` — the single place that drafts FAQ content (from a URL or a topic) and checks it against the existing corpus for overlap; read-only, so `/add-faq` applies its draft after your confirmation rather than letting it write directly.

## System design choices & scaling path

### Why Claude Sonnet 5

This is a grounded-QA + escalation-calibration task (answer strictly from provided knowledge, know when to refuse) - not a hard-reasoning task, so the model choice trades off differently than a research-agent or coding-agent use case would:
- **Performance:** Sonnet's instruction-following is more than sufficient for staying grounded in a fixed knowledge block and making a binary escalate/don't-escalate call. Opus-tier reasoning would be paying for capability this task doesn't exercise.
- **Cost:** meaningfully cheaper per token than Opus-tier, which matters directly here since the entire FAQ corpus is resent on every call (this project's own CAG choice) - a more expensive model would multiply that cost on every single request, not just occasionally.
- **Latency:** Sonnet-tier is noticeably faster than Opus-tier for comparable input sizes, which matters more than usual given `/api/chat` is non-streaming - the whole reply has to land before the user sees anything, so model speed is directly perceived latency, not hidden behind token-by-token output.

### Why Vercel (frontend) + Render (backend)

Both were chosen for lowest friction at this project's actual scale (a take-home-sized, low-traffic app), not because they're what a large-scale production deployment would use:
- **Vercel:** zero-config deploys for a static Vite/React build, a generous free tier, and CDN-backed static asset delivery - a good fit for a purely client-side app with no server-side rendering to configure.
- **Render:** deploys a plain FastAPI service without needing to hand-roll a Dockerfile or manage Kubernetes, supports config-as-code (`render.yaml`), free tier available, and auto-deploys on push. The known trade-off (free-tier spin-down, mitigated by the keep-alive workflow) is an acceptable cost for this scale - at real production traffic, you'd size up to a paid plan (see the OOM investigation history in this repo for why "free tier" and "adequate resources" aren't the same thing once real load shows up).

### If the FAQ corpus outgrows CAG: reintroducing RAG

The current design (whole corpus, every call, cached) is deliberately simple because the corpus is small — see the Architecture section above. If it grows enough that this stops being cheap/fast, here's the concrete path back to real retrieval, not just "add a vector store":

- **Why `chromadb` specifically:** it was already used earlier in this project's history (removed once retrieval stopped adding value - see git history), embeds locally via a bundled model with no external embeddings API key needed, and its API (`add`/`query`) is simple enough for a single-server deployment at this scale. For larger scale or if the stack already includes Postgres, `pgvector` or a managed service (Pinecone, Weaviate) would be worth evaluating instead.
- **Choosing chunk size:** don't guess one number. Start from the content's natural structure (one FAQ entry was already one atomic chunk here; longer documents need a fixed token window, commonly 200-500 tokens with some overlap so context isn't lost at boundaries). Then test a few candidate sizes against a labeled set of real questions with known-correct source chunks, and pick based on measured retrieval quality (below) - not by eyeballing a few examples. Also respect the embedding model's own max sequence length (e.g. `all-MiniLM-L6-v2` truncates at 256 tokens) - a chunk size larger than that gets silently cut.
- **Choosing `k` via precision@k/recall@k:** build a small labeled eval set (representative questions + their correct chunk(s)). **Recall@k** = of all truly relevant chunks for a question, what fraction actually appear in the top k (misses here mean the model never sees the right fact at all). **Precision@k** = of the k retrieved chunks, what fraction are actually relevant (too low, and the model is wading through noise). Pick the smallest `k` that hits acceptable recall on the eval set - larger `k` isn't free, since every extra chunk is extra tokens and extra noise. Re-measure as the corpus grows: this project's own history is the cautionary tale - fixed `k` values (3 → 5 → 6 → 10) each got outpaced by corpus growth in turn, which is exactly the kind of regression a real eval set (not manual spot-checks) would catch early.
- **Adding a reranking step:** if embedding-similarity retrieval plateaus (queries keep missing the right chunk even after tuning chunk size and `k`), add a reranking stage: retrieve a larger, cheap candidate set via embeddings (e.g. top 20-50), then rerank that smaller set with a more accurate but more expensive model that scores the query and each candidate jointly (a cross-encoder, a hosted rerank API, or an LLM-based reranker) - too expensive to run over the whole corpus, cheap enough over a pre-filtered shortlist. This is the lever to pull once bigger `k` alone stops improving quality, not a replacement for tuning `k` first.

### If conversation volume grows: Redis for conversation history

Today the frontend holds the full conversation in browser state and resends it whole on every request (see Architecture above) - deliberately simple, but it means every turn re-sends every prior turn, and a page refresh loses the conversation entirely. If either of those becomes a real problem:
- Store conversation history server-side in Redis, keyed by a session id generated client-side on first load (e.g. a UUID in a cookie or local storage) - the client sends just `{session_id, new_message}` instead of the whole growing history, and the server looks up prior turns by key before calling the model.
- Redis specifically because it's a fast in-memory store well-suited to session data with a TTL - conversations can auto-expire (e.g. after 24-48h of inactivity) rather than needing the durability of a full relational database, and it's widely available as a managed add-on (including on Render).
- This also unlocks things the current stateless design can't: surviving a page refresh, per-session rate limiting, and passing conversation context along on an actual human handoff instead of just an escalation flag.

## See also

`plan.md` at repo root for the full phased build plan and explicit scope-cut list.
