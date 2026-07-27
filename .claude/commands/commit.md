---
description: Stage all changes, scan for anything secret-looking, and commit with a short auto-generated summary message. Never pushes.
allowed-tools: Bash(git *)
---

Commit all current changes in this repo:

1. Run `git status` and `git diff` to see what's changed and what's currently untracked.
2. Stage everything with `git add .`, then run `git status` again to see exactly what got staged.
3. Before committing, scan the staged file list for anything that could contain secrets (`.env` files, credentials, keys) even if the filename looks innocuous. If anything suspicious is staged, unstage it, warn the user, and stop rather than committing it.
4. Write a short, concise commit message summarizing the actual staged changes - focus on why, not just what, matching this repo's existing commit message style (check `git log` for examples). One or two sentences unless the change genuinely needs more - don't ramble.
5. Create the commit with the message ending in:
   ```
   Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
   ```
6. Run `git status` after committing to confirm success, and report the resulting commit hash and message back to the user.

Never force-push, never amend an existing commit, never use `--no-verify`. This command commits locally only - it never pushes, regardless of how it's invoked.
