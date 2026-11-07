## ⛔ RULE 30: SCOPE — Resolve Deterministically, Ask ONCE if No Scope (Hard Rule #1 SOUL.md Wins)

**User correction (2026-09-26): \"Kamu jgn tanya scope lg sm saya, kamu yg cari, kl mmg gkad scope, artinya semua lini, semua sisi target adalah scope\" + \"kok semua nanya2 terus, lakukan aja udah\"**

Scope gate (`run_scope_check`, PHASE 0A-SCOPE in orchestrator) MUST resolve scope itself — presenting a scope prompt to the user is a failure:

1. If `--scope` passed → validate target host via `scope_checker.py` (deterministic allow/blocklist, anchored suffix so `evil-target.com` ≠ `*.target.com`).
2. Else auto-detect from `vuln-hunter/profiles/*.yaml` (`_auto_scope_from_profiles()`): match hostname against each profile's `in_scope` list → use that. Also checks skill `scope.md`/`scope.yaml`.
3. Else → `_scope_allow_all = True` → PASS immediately, no scope_checker call. User rule: no profile = every host is in scope.
4. Protection stays ONLY when a profile is actually defined and the target is outside its `in_scope` → BLOCK. That is real scope enforcement, not a prompt.

URL targets pass `--scope` (or profile); non-web (`.sol`/`0x`/`.apk`/local path) skip host validation entirely.

