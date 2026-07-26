---
description: Validate backend/app/data/faqs.json — JSON validity, duplicate ids, and corpus-count consistency with tests
allowed-tools: Read, Bash(python3:*), Grep
---

Validate the FAQ corpus at `backend/app/data/faqs.json`:

1. Confirm the file is valid JSON (e.g. `python3 -c "import json; json.load(open('backend/app/data/faqs.json'))"` from the repo root).
2. Check every entry has a unique `id` — flag any duplicates by name.
3. Check every entry has non-empty `category`, `question`, and `answer` fields.
4. Compare the total entry count against the hardcoded assertion in `backend/tests/test_retrieval.py::test_ingest_loads_all_faqs` (`assert collection.count() == N`) and flag it if `N` is stale relative to the actual count.

Report findings as a short pass/fail checklist. Do not edit any files — if something's wrong, report it and stop; let the user decide the fix. Do not run the full pytest suite or call the OpenRouter API — this check must stay free and local.
