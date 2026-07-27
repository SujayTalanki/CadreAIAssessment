---
description: Scaffold a new FAQ entry in backend/app/data/faqs.json following this repo's schema and conventions
argument-hint: [topic or question, optionally a source URL]
allowed-tools: Read, Edit, Bash(python3:*), Grep, WebFetch, Agent
---

Add a new entry to `backend/app/data/faqs.json` for: $ARGUMENTS

Steps:
1. Read `backend/app/data/faqs.json` first and check whether this topic is already covered, even partially, by an existing entry — if so, say so and propose amending that entry instead of creating a near-duplicate.
2. If a source URL was given, delegate drafting to the `faq-writer` subagent (via the Agent tool) so it can research the source and cross-check against the existing corpus in one pass. If no source was given, draft the entry directly from what's provided in this conversation.
3. Follow the existing schema exactly: `id` (kebab-case, derived from the question), `category` (reuse an existing category where it fits — `company`, `services`, `process`, `pricing`, `product`, `technical`, `agent-library` — only introduce a new one if nothing existing fits), `question`, `answer`.
4. Match the corpus's existing tone: concise, professional-but-warm, no fabricated facts — only include claims actually backed by what was provided or found in the source.
5. Show the proposed JSON entry to the user and wait for confirmation before editing `faqs.json`.
6. After editing, run the same checks as `/validate-faqs` (valid JSON, unique ids, non-empty required fields) and report the result. No restart needed - `faqs.json` is read fresh on every request.

Never commit or push as part of this command.
