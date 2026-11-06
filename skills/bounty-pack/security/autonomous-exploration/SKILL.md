---
name: autonomous-exploration
description: "Dual-graph exploration tracking, dependency-gated step ledger, cross-worker trace exchange, and on-demand traffic recording for audits. ARTEX-inspired, clean-room. ADDITIVE sidecar - safe alongside the existing 0A-0F pipeline."
category: security
metadata:
  hermes:
    tags: [security, audit, exploration, dual-graph, dependency-plan, trace, traffic, sidecar]
---

# Autonomous Exploration (sidecar)

Four ADDITIVE tools that give an audit target a *memory structure*. They are inspired by the
mechanisms in ARTEX (github.com/jiwoochris/artex-ko, AGPL-3.0) but are **clean-room
re-implementations** in our own idiom — no ARTEX code, no ARTEX runtime, no Postgres.

> **Contract — never violate:** these tools only CREATE files under `<target_dir>/_graph`,
> `/_plan`, `/_traces`, `/_traffic`. They never modify existing pipeline scripts, and no
> existing pipeline script depends on them. If they are absent, the 0A-0F pipeline runs exactly
> as before. Breaking that contract is the one unacceptable failure.

## When to load

- Auditing a target where you want **coverage you can actually query** ("which endpoints did I test?")
- A multi-step chain where step 3 depends on step 2's output (unauth -> creds -> lateral -> impact)
- You suspect a previous step already saw something useful but it never became a finding
- You need an automatic, faithful PoC transcript (request/response) instead of hand-copying
- Any mention of: dual graph, asset graph, exploration graph, anchor, chain plan, dependency gate,
  trace exchange, worker trace, traffic capture, PoC transcript, coverage query

## The four tools (all in `$LOCALAPPDATA/hermes/scripts/`)

| tool | role | state file |
|---|---|---|
| `dualgraph.py` | asset graph + exploration graph + anchors (SQLite) | `<target>/_graph/graph.db` |
| `chainplan.py` | dependency-gated step ledger (the "what next" gate) | `<target>/_plan/chain.json` |
| `tracestore.py` | append-only process-trace exchange | `<target>/_traces/traces.jsonl` |
| `trafficrec.py` | mitmproxy addon + query CLI (on-demand) | `<target>/_traffic/traffic.db` |

Every script self-tests: `python <script> <dir> verify` (or `<script> verify`) prints PASS x/y.

## Trigger -> reference (read the file before working that part)

| when | read |
|---|---|
| creating/querying the graph, coverage, lineage, anchors | `references/01-dual-graph.md` |
| building or gating a multi-step chain | `references/02-dependency-plan.md` |
| preserving/reusing observations across steps or subagents | `references/03-trace-exchange.md` |
| capturing PoC traffic automatically | `references/04-traffic-recorder.md` |
| blue-team material (Sigma/Suricata/ATT&CK/MISP) — license-gated | `references/05-blue-team-detections.md` |
| porting ARTEX's api-recon / playwright-cli / scopesentry skills | `references/06-skill-ports.md` |
| what already existed vs what these add | `references/00-gap-analysis.md` |

## The 60-second loop

```bash
S="$LOCALAPPDATA/hermes/scripts"
T="D:/data hermes/bug-bounty/_progress/<target>_v1"

# 0) one-time
python "$S/dualgraph.py"  "$T" init
python "$S/chainplan.py"  "$T" init --target <target>

# 1) recon lands assets (0B)
python "$S/dualgraph.py" "$T" asset add --type endpoint --value "https://h/api/x" --status 200 --tech "nginx,php"

# 2) plan the chain as dependency steps (0A/0B)
python "$S/chainplan.py" "$T" add --id s1 --desc "confirm injection point" --phase 0C
python "$S/chainplan.py" "$T" add --id s2 --desc "pivot via creds" --phase 0C --prereq s1

# 3) ask the gate what may run now (ONLY one step at a time)
python "$S/chainplan.py" "$T" next

# 4) run it; write the graph as you go; dump the raw trace too
python "$S/dualgraph.py" "$T" node add --kind intent --title "test IDOR /api/x" --asset 1
python "$S/tracestore.py" "$T" add --step s1 --tool ffuf --cmd "ffuf ..." --output-file out.txt
python "$S/dualgraph.py" "$T" node add --kind fact --title "IDOR confirmed" \
       --evidence "GET /api/x?id=2 -> 200 other-user data" --confidence observed --asset 1
python "$S/chainplan.py" "$T" done --id s1 --fact <fact_node_id>     # opens the next step

# 5) before dispatching anything, mine earlier traces
python "$S/tracestore.py" "$T" search --q "token" --exclude-step s1
```

## Non-negotiable rules (learned from ARTEX's own design)

1. **Separate the two graphs.** A *thing* (endpoint/host/param/credential) goes to the ASSET graph;
   a *conclusion* goes to the EXPLORATION graph as a `fact`. Never mix them.
2. **One fact per step, default.** Merge observations into one fact; splitting inflates the graph.
   Only split when conclusions are truly independent.
3. **Negative observations are observations, not verdicts.** Record them as `fact` with
   `--confidence inferred` (or `observed`) — do not treat "looks blocked" as a closed door.
4. **Findings need a real, reproduced PoC.** `--kind finding` only when you actually triggered it
   this run and hold the request/response. Match-on-version is a `fact`, not a finding.
5. **The gate is the gate.** Do not dispatch step N+1 because "it'll probably work" — ask `next`.
6. **Depth over coverage.** Coverage is the floor/acceptance metric, not the goal. When a high-value
   entry appears, push THAT path deep before widening.

## Pitfalls on this host

- **`/tmp` is ambiguous.** MSYS bash and native Windows Python disagree on `/tmp`. Always pass an
  explicit Windows path (`D:/data hermes/...`) to these scripts; a leading `/tmp` silently lands in
  two different places (`C:\tmp\...` vs the MSYS tmp) and your reads will not see your writes.
- **mitmproxy has its OWN python (3.11).** `trafficrec.py` under `mitmdump` uses `~/.local/bin`
  (3.11); running it as a CLI uses the system python (3.14). That is why the mitmproxy import is
  guarded. Do not "fix" it by forcing one interpreter.
- **SQLite WAL.** Data stays in `traffic.db-wal` until checkpoint. Always point the query CLI at the
  SAME db path the recorder used, or you will read an empty db.
- **Never bind :8080 / :6666** on this host — MiniTool ShadowMaker owns them. Use e.g. :8081.
- These scripts are additive; if you ever feel the urge to edit `audit-pipeline-orchestrator.py`
  or `audit-checkpoint.py` to wire them in, stop — wire via the skill instead.
