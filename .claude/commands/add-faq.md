---
description: Scaffold a new FAQ entry in backend/app/data/faqs.json following this repo's schema and conventions
argument-hint: [topic or question, optionally a source URL]
allowed-tools: Read, Edit, Grep, WebFetch, Agent
---

Add a new entry to `backend/app/data/faqs.json` for: $ARGUMENTS

Steps:
1. Read `backend/app/data/faqs.json` first and check whether this topic is already covered, even partially, by an existing entry — if so, say so and propose amending that entry instead of creating a near-duplicate.
2. If a source URL was given, delegate drafting to the `faq-writer` subagent (via the Agent tool) so it can research the source and cross-check against the existing corpus in one pass. If no source was given, draft the entry directly from what's provided in this conversation.
3. Follow the existing schema exactly: `id` (kebab-case, derived from the question), `category` (reuse an existing category where it fits — `company`, `services`, `process`, `pricing`, `product`, `technical`, `agent-library` — only introduce a new one if nothing existing fits), `question`, `answer`.
4. Match the corpus's existing tone: concise, professional-but-warm, no fabricated facts — only include claims actually backed by what was provided or found in the source.
5. Show the proposed JSON entry to the user and wait for confirmation before editing `faqs.json`.
6. After the entry is added, remind the user: (a) the dev server needs a manual restart to pick it up (`uvicorn --reload` doesn't watch JSON, per `CLAUDE.md`), and (b) the corpus-count assertion in `backend/tests/test_retrieval.py::test_ingest_loads_all_faqs` needs bumping by one.

Never commit or push as part of this command.
