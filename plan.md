# Build Plan — Cadre AI Support Chatbot

## Scope

A customer support chatbot for Cadre AI that handles the scenarios called out in the challenge brief: what Cadre AI does and industry fit, booking a call with a strategist, accessing the Cadre portal, what the AI Maturity Index is, Cadre's approach to LLM selection and data security, and graceful escalation for anything out of scope.

## Key decisions

- **Stack:** Python FastAPI backend + React (Vite/TS/Tailwind) frontend, deployed as two separate services (backend → Render, frontend → Vercel).
- **Model:** Claude Sonnet 5 (`claude-sonnet-5`), thinking explicitly disabled. This is a grounded-QA + escalation-calibration task — answer from a fixed knowledge base, know when to refuse — not a hard-reasoning task, so Sonnet's instruction-following is the right tier; Opus is unnecessary cost/latency for a support widget.
- **Knowledge base: RAG, not a giant system prompt.** FAQs live in `backend/app/data/faqs.json` (static, human-editable) and are embedded into an in-memory Chroma collection on startup, using Chroma's bundled default embedding function — no external embeddings API key required. Each `/api/chat` call retrieves the top-k most relevant FAQ chunks and injects them into the system prompt for that turn. This means the FAQ set is extensible (add a JSON entry, redeploy — no prompt surgery) and gives the system a real retrieval/data-model story instead of one unbounded prompt.
- **Escalation:** the system prompt instructs the model to decide, per-turn, whether the retrieved knowledge actually answers the question. If not, it appends a literal `[[ESCALATE]]` marker; the backend strips it into a boolean `escalate` field, and the frontend renders a "book a call" / "email us" CTA. The model makes this judgment call, not a similarity-score cutoff — embedding distance alone is a weak signal for "should a human take over."
- **Stateless conversations:** no database, no auth, no server-side session. The browser holds the full message history in React state and sends it on every request. This is a deliberate scope cut, not an oversight — see below.
- **Non-streaming responses:** `max_tokens` is small (~1024), well under where streaming becomes necessary. This keeps escalation-marker parsing and error handling trivial (the full response is available before returning) at the cost of a typing-indicator standing in for token-by-token output.

## Phases

| Phase | Work | Commit |
|---|---|---|
| 0 | Scaffold repo structure, `.gitignore`, `README.md`, `CLAUDE.md`, `plan.md` | `chore: scaffold repo structure and planning docs` |
| 1 | FastAPI skeleton: `main.py`, `config.py`, CORS, `/api/health` | `feat(backend): scaffold FastAPI app with health check` |
| 2 | `data/faqs.json` + `services/retrieval.py` (Chroma ingest/query) + `system_prompt.py` | `feat(backend): add FAQ corpus and Chroma-based retrieval` |
| 3 | `models.py`, `services/anthropic_client.py`, `routes/chat.py` — RAG-grounded `/api/chat`, error handling, escalation parsing | `feat(backend): implement /api/chat with RAG-grounded Claude Sonnet 5 integration` |
| 4 | `tests/` — pytest with mocked Anthropic client + Chroma collection | `test(backend): add pytest suite for retrieval, chat endpoint, and escalation logic` |
| 5 | Frontend scaffold: Vite + React + TS + Tailwind | `feat(frontend): scaffold chat app shell` |
| 6 | Chat UI components, wire local state | `feat(frontend): build chat UI components and message flow` |
| 7 | Integration: env wiring, local end-to-end test, error banner, header CTA, polish | `feat: wire frontend to backend, polish UX and error states` |
| 8 | Deploy: Render (backend) + Vercel (frontend), smoke test live URLs | `chore: add deployment configs and update README with live URL` |
| 9 | Self code-review pass, fix findings, finalize docs | `docs: finalize docs; address review findings` |

Phases 1+2 and 4+6 are independent enough to run as parallel Claude Code subagents once the `/api/chat` request/response contract is fixed.

## Explicit scope cuts

- **No database or persisted conversation history.** State is browser-only; escalation "lead capture" is a `mailto:` link, nothing is stored server-side.
- **No authentication.** This is a public support widget with nothing to gate.
- **No admin dashboard or analytics** — nothing is stored to analyze.
- **No rate limiting beyond the Anthropic SDK's own retry/backoff** — acceptable for a low-traffic demo; documented rather than silently absent.
- **No streaming** — traded for a typing indicator.
- **No persistent vector store volume** — the Chroma index is rebuilt in-memory on every backend startup. The FAQ corpus is small enough that this costs a few hundred milliseconds, which avoids configuring a persistent disk on Render entirely.
- **No re-ranking, hybrid search, or similarity-threshold-based escalation logic** — top-k retrieval plus the model's own judgment is sufficient at this corpus size.
- **No CI/CD pipeline** — native git-push deploys via Vercel/Render.
- **No i18n, voice input, or native mobile app.**
- **Automated tests are the one place scope is *not* cut** — a small pytest suite covers the health check, retrieval, escalation-marker parsing, and both the happy and error paths of `/api/chat`.

## Known limitations

- Render's free tier spins down after ~15 minutes idle; the first request after idle can take 30-50 seconds while it wakes up. This is disclosed here and in the README rather than hidden.
- The knowledge base content (booking link, portal URL, AI Maturity Index specifics) is fabricated for this exercise, since Cadre AI has no real backend systems to integrate with.
