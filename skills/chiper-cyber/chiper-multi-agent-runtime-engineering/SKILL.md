---
name: chiper-multi-agent-runtime-engineering
description: "Use when Runtime engineering discipline for agent systems — structured JSON memory schemas, memory-driven convergence rules, shared-memory multi-agent coord"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, multi, agent, runtime, engineering]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-multi-agent-runtime-engineering/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-multi-agent-runtime-engineering/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-multi-agent-runtime-engineering/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-multi-agent-runtime-engineering/guides
---

# Multi Agent Runtime Engineering

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `jq` — `sudo apt install -y jq`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in jq; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v jq >/dev/null 2>&1 || sudo apt install -y jq
```

## When to Use

This skill is the **runtime engineering layer** for agent systems. It treats memory schemas, sync protocols, convergence rules, anti-pattern prevention, and topology selection as first-class engineering artifacts — the things that decide whether a multi-agent system actually converges on truth or spirals into hallucinated prose.

This skill **solidifies the engineering patterns of `validation/scenarios/SCEN-007.md` (Shared-Memory Multi-Agent Exploit Dev) and `validation/scenarios/SCEN-MEMORY-SCHEMA.md` (Structured Memory foundation) into a reusable knowledge base.** SCEN-007 is the live scenar

## Core Tools

### jq Patterns for Memory Operations

| Pattern | Use |
|---------|-----|
| `jq '.memory_lock.version' mem.json` | Read current version (for optimistic concurrency) |
| `jq --arg agent "$A" --arg path "$P" '.active_paths[$agent] = $path | ...' mem.json` | Path claim |
| `jq '.active_paths | (group_

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-multi-agent-runtime-engineering/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
