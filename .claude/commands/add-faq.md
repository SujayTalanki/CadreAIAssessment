---
description: Add or amend a FAQ entry in backend/app/data/faqs.json from a source URL or a topic, with human confirmation before applying and a real load-check after
argument-hint: [URL or topic/question]
allowed-tools: Read, Edit, Bash(python3:*), Agent
---

Add or amend an entry in `backend/app/data/faqs.json` for: $ARGUMENTS

Steps:
1. Delegate to the `faq-writer` subagent (via the Agent tool) with $ARGUMENTS as input, whether it's a URL or a freeform topic - it checks the existing corpus for overlap and drafts the entry (or an amendment) in one pass. Don't duplicate its overlap-check or drafting logic here.
2. Show the proposed JSON entry (or diff, if amending) to the user and wait for confirmation before editing `faqs.json`.
3. After editing, verify it actually worked, not just that it was written:
   - Structural: valid JSON, unique `id`s, non-empty `category`/`question`/`answer` fields - same checks as `/validate-faqs`.
   - Functional: from `backend/`, reload the knowledge block fresh (e.g. `python3 -c "from app.services.llm_client import _load_knowledge_block; b = _load_knowledge_block(); print('present:', 'THE NEW QUESTION TEXT' in b)"`) and confirm the new entry's question text actually appears in it - this is what the model sees on the very next request, so confirm it's really there, not just that the JSON parses.
4. Report both results to the user.

Never commit or push as part of this command.
