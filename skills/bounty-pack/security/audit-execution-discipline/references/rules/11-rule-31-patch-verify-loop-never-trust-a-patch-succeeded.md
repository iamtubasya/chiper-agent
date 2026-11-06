## ⛔ RULE 31: Patch-Verify Loop — Never Trust a Patch "Succeeded"

**User-visible bug (2026-09-26):** a patch to `execute-poc-variants.py` reported success but silently did NOT persist (file mtime stayed old, `grep -c tool_router` = 0) — caused by reusing a stale `p` variable across cells. Verification discipline:

- After any file edit, PROVE it landed: `stat -c %y` mtime changed + `grep -c <marker>` + `python -m py_compile`.
- After a multi-file upgrade, run a matrix check: every executor's marker count + mtime, plus `importlib` sanity for the shared module.
- If a patch "succeeded" but grep shows 0 → the write hit a different file/path or a stale variable. Re-apply with fresh, explicit paths.

