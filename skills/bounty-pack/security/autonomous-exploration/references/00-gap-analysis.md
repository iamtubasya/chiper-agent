# 00 — Gap analysis (what existed vs what these add)

Checked on this host before building (2026-10-09). Result: **all four mechanisms were absent.**

| ARTEX mechanism | before | after |
|---|---|---|
| dual graph (asset + exploration) | absent | `dualgraph.py` (SQLite) |
| anchors (node <-> asset bridge) | absent | `anchors` table + `--asset` on node add |
| dependency todolist across wakes | absent (linear 0A->0F only) | `chainplan.py` |
| process-level trace exchange | absent | `tracestore.py` |
| recording traffic store | absent | `trafficrec.py` |
| PreToolUse approval gate | not ported (out of scope) | — |

Name-collision checks performed:
- `plan.json` is already produced by `poc-pipeline.py` (a test checklist) -> our ledger uses
  `_plan/chain.json`, a different file. No collision.
- No existing script/skill mentions dual-graph, anchors-as-graph, traces.jsonl, or a traffic store
  ("anchor" hits in audit scripts are web3 *blockchain* anchors — unrelated).
- Existing proxy infrastructure is all **LLM relay** proxies (Vercel/Python FastAPI). It is NOT a
  traffic recorder and shares nothing with `trafficrec.py`.

Where the existing pipeline keeps state (so you can stay consistent):
- per-target dir: `D:\data hermes\bug-bounty\_progress\<target>_v1\`
- phase log template: `<target>/PHASE_LOG.md`
- session state: `$LOCALAPPDATA/hermes/trackers/state-<target>.json`
- pipeline scripts: `$LOCALAPPDATA/hermes/scripts/` (audit-pipeline-orchestrator, audit-checkpoint, ...)
