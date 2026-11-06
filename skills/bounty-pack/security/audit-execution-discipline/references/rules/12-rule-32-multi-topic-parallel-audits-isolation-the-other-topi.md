## ⛔ RULE 32: Multi-Topic Parallel Audits — Isolation & the "Other Topic Silent" Trap

Parallel audits in separate Telegram topics are safe per-target: state files `trackers/audit-pipeline-<target>.json`, output dirs `poc-plans/orchestrator-<target>`, all executors receive `--target-dir`. Shared `poc-techniques-index.json` is built once then READ-only — no race. But:

- "Topik lain diam" is usually NOT a pipeline bug: sessions A processes while B waits on the SAME model-provider client (custom localhost:20128), or gateway Telegram polling reconnects (httpx.ReadError) disrupting all topics. Check gateway.log before blaming the pipeline.
- `max_concurrent_sessions: None` in config = no explicit cap; `_running_agents` is per-session, `_handle_message` uses per-message `create_task`. So concurrency is bounded by the model client + terminal backend, not a session lock.
- For true parallel CPU/network: separate Hermes profile per target (`hermes --profile <x>`), not parallel topics in one gateway.

> **References:** `references/poc-techniques-index-recipe.md`, `references/unified-pipeline-fixes-2026-09-26.md`

