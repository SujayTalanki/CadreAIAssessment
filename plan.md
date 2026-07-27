# Build Plan — Cadre AI Support Chatbot

## Scope

A customer support chatbot for Cadre AI that handles the scenarios called out in the challenge brief: what Cadre AI does and industry fit, booking a call with a strategist, accessing the Cadre portal, what the AI Maturity Index is, Cadre's approach to LLM selection and data security, and graceful escalation for anything out of scope.

## Key decisions

- **Stack:** Python FastAPI backend + React (Vite/TS/Tailwind) frontend, deployed as two separate services (backend → Render, frontend → Vercel).
- **Model:** Claude Sonnet 5 (`anthropic/claude-sonnet-5`), thinking/reasoning explicitly disabled. This is a grounded-QA + escalation-calibration task — answer from a fixed knowledge base, know when to refuse — not a hard-reasoning task, so Sonnet's instruction-following is the right tier; Opus is unnecessary cost/latency for a support widget.
- **Model access: OpenRouter, not the native Anthropic API.** Only an OpenRouter key (`sk-or-...`) was provided for this exercise, not a native Anthropic key — so the backend calls Claude through OpenRouter's OpenAI-compatible `chat/completions` endpoint (via the `openai` SDK pointed at `https://openrouter.ai/api/v1`) rather than the native `anthropic` SDK. This also happens to match Cadre AI's own stated approach in the brief ("OpenRouter for model access"). Extended thinking is disabled via `extra_body={"reasoning": {"enabled": False}}`, OpenRouter's equivalent of the native `thinking` param.
- **Knowledge base: Cache-Augmented Generation (CAG), no vector store.** FAQs live in `backend/app/data/faqs.json`, read fresh from disk on every call in `llm_client.py` (in the file's own order) and sent in full - cheap enough not to cache in memory, so edits take effect immediately with no restart. Fixed top-k values (3 → 5 → 6 → 10) were tried first as the corpus grew and each got outpaced; at this corpus size there's nothing to meaningfully select, so a vector store/embedding step would just be complexity with nothing to select from - the FAQ set is small enough to send in full instead. The whole system prompt is identical on every call, which is exactly what makes it cacheable: Anthropic `cache_control` (1h TTL) via OpenRouter, one full-price write per hour of activity (~$0.03), ~90% cheaper reads after. If the corpus outgrows this: reintroduce a vector store and real top-k retrieval, pick chunk size empirically (test a few sizes against real questions, don't guess one), choose `k` via precision@k/recall@k against a labeled query set, and add a reranking step on top of initial retrieval if embedding-similarity alone isn't precise enough. The FAQ set stays extensible today regardless (add a JSON entry, redeploy - no prompt surgery).
- **Escalation:** the system prompt instructs the model to decide, per-turn, whether the retrieved knowledge actually answers the question. If not, it appends a literal `[[ESCALATE]]` marker; the backend strips it into a boolean `escalate` field, and the frontend renders a single "Talk With Our Team" CTA linking to the real Cadre AI contact page (`https://www.cadreai.com/contact`) — the same link used in the persistent header, so there's one consistent destination for "talk to a human" everywhere in the app. The model makes the escalation judgment call itself, not a similarity-score cutoff — embedding distance alone is a weak signal for "should a human take over."
- **Stateless conversations:** no database, no auth, no server-side session. The browser holds the full message history in React state and sends it on every request. This is a deliberate scope cut, not an oversight — see below.
- **Non-streaming responses:** `max_tokens` is small (~1024), well under where streaming becomes necessary. This keeps escalation-marker parsing and error handling trivial (the full response is available before returning) at the cost of a typing-indicator standing in for token-by-token output.

## Phases

| Phase | Work | Commit |
|---|---|---|
| 0 | Scaffold repo structure, `.gitignore`, `README.md`, `CLAUDE.md`, `plan.md` | `chore: scaffold repo structure and planning docs` |
| 1 | FastAPI skeleton: `main.py`, `config.py`, CORS, `/api/health` | `feat(backend): scaffold FastAPI app with health check` |
| 2 | `data/faqs.json` + `services/retrieval.py` (Chroma ingest/query) + `system_prompt.py` | `feat(backend): add FAQ corpus and Chroma-based retrieval` |
| 3 | `models.py`, `services/anthropic_client.py`, `routes/chat.py` — RAG-grounded `/api/chat`, error handling, escalation parsing | `feat(backend): implement /api/chat with RAG-grounded Claude Sonnet 5 integration` |
| 4 | `tests/` — pytest with mocked LLM client + Chroma collection | `test(backend): add pytest suite for retrieval, chat endpoint, and escalation logic` |
| 5 | Frontend scaffold: Vite + React + TS + Tailwind | `feat(frontend): scaffold chat app shell` |
| 6 | Chat UI components, wire local state | `feat(frontend): build chat UI components and message flow` |
| 7 | Integration: discovered only an OpenRouter key was available (not native Anthropic) — pivoted `anthropic_client.py` → `llm_client.py` to call Claude through OpenRouter's OpenAI-compatible API, updated env vars/docs/tests accordingly; then ran a real end-to-end pass against the live model across all 6 required scenarios and tuned retrieval `k` (see above) | `refactor(backend): switch LLM access from native Anthropic SDK to OpenRouter` + `feat: wire frontend to backend, polish UX and error states` |
| 8 | Deploy: Render (backend) + Vercel (frontend), smoke test live URLs | `chore: add deployment configs and update README with live URL` |
| 9 | Self code-review pass, fix findings, finalize docs | `docs: finalize docs; address review findings` |

Phases 1+2 and 4+6 are independent enough to run as parallel Claude Code subagents once the `/api/chat` request/response contract is fixed.

## Explicit scope cuts

- **No database or persisted conversation history.** State is browser-only; escalation "lead capture" is a link to Cadre AI's real contact page, nothing is stored server-side.
- **No authentication.** This is a public support widget with nothing to gate.
- **No admin dashboard or analytics** — nothing is stored to analyze.
- **No rate limiting beyond the OpenAI SDK's own retry/backoff** — acceptable for a low-traffic demo; documented rather than silently absent.
- **No streaming** — traded for a typing indicator.
- **No vector store, embeddings, chunking, or reranking at all** — the FAQ corpus loads directly into a static prompt constant; see the Knowledge base decision above for what triggers adding these back and how (precision@k/recall@k, not guesswork).
- **No CI/CD pipeline** — native git-push deploys via Vercel/Render.
- **No i18n, voice input, or native mobile app.**
- **Automated tests are the one place scope is *not* cut** — a small pytest suite covers the health check, escalation-marker parsing, and both the happy and error paths of `/api/chat`.

## Known limitations

- Render's free tier spins down after ~15 minutes idle, causing a 30-50 second cold start on the first request after. Mitigated with a scheduled GitHub Actions job (`.github/workflows/keep-alive.yml`) that pings `/api/health` every 10 minutes so the service never idles long enough to spin down — chosen over paying for Render's Starter plan (removes the issue but costs money) or switching to Cloud Run (faster cold starts if it does happen, but requires containerizing the app instead of Render's zero-config Python buildpack, more setup for no real gain here).
- The knowledge base content (booking link, portal URL, AI Maturity Index specifics) is fabricated for this exercise, since Cadre AI has no real backend systems to integrate with.
