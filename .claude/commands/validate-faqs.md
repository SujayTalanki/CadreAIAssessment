---
description: Validate backend/app/data/faqs.json — JSON validity, duplicate ids, non-empty fields
allowed-tools: Read, Bash(python3:*), Grep
---

Validate the FAQ corpus at `backend/app/data/faqs.json`:

1. Confirm the file is valid JSON (e.g. `python3 -c "import json; json.load(open('backend/app/data/faqs.json'))"` from the repo root).
2. Check every entry has a unique `id` — flag any duplicates by name.
3. Check every entry has non-empty `category`, `question`, and `answer` fields.

Report findings as a short pass/fail checklist. Do not edit any files — if something's wrong, report it and stop; let the user decide the fix. Do not run the full pytest suite or call the OpenRouter API — this check must stay free and local.
