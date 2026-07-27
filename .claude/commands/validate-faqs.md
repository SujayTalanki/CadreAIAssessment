---
description: Validate backend/app/data/faqs.json — JSON validity, duplicate ids, non-empty fields, and that every entry actually loads into the live knowledge block
allowed-tools: Read, Bash(python3:*), Grep
---

Validate the FAQ corpus at `backend/app/data/faqs.json`:

1. Confirm the file is valid JSON (e.g. `python3 -c "import json; json.load(open('backend/app/data/faqs.json'))"` from the repo root).
2. Check every entry has a unique `id` — flag any duplicates by name.
3. Check every entry has non-empty `category`, `question`, and `answer` fields.
4. Functional check: from `backend/`, run something like:
   ```
   python3 -c "
   import json
   from app.services.llm_client import _load_knowledge_block
   faqs = json.load(open('app/data/faqs.json'))
   block = _load_knowledge_block()
   missing = [f['question'] for f in faqs if f['question'] not in block]
   print('all entries present:', not missing)
   if missing: print('missing:', missing)
   "
   ```
   This confirms every entry actually appears in what the model would see on the next request - not just that the JSON parses, but that it really loads.

Report findings as a short pass/fail checklist. Do not edit any files — if something's wrong, report it and stop; let the user decide the fix. Do not run the full pytest suite or call the OpenRouter API — this check must stay free and local.
