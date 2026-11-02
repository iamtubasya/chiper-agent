---
name: chiper-llm-red-team
description: "Use when LLM and generative AI red team testing covering prompt injection, jailbreaking (DAN, many-shot, Crescendo, PAIR/TAP, GCG suffix, persona modulation, prefix injection,"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, llm, red, team]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-llm-red-team/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-llm-red-team/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-llm-red-team/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-llm-red-team/guides
---

# Llm Red Team

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `garak` — `pip install garak`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in garak; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v garak >/dev/null 2>&1 || pip install garak
```

## When to Use

LLM red team skill domain covering offensive testing of large language model systems, generative AI applications, RAG pipelines, and agentic tool-using assistants. The skill equips the operator to discover and demonstrate semantic-layer vulnerabilities — prompt injection, jailbreaks, system-prompt extraction, training-data leakage, RAG poisoning, agentic tool abuse, and safety policy bypass — using the current open-source toolkit (`promptfoo`, `garak`, `PyRIT`, `PurpleLlama`, `AI-Infra-Guard`, `llm-guard`). Findings are mapped to the OWASP LLM Top 10 (LLM01-LLM10) and the emerging LLM-ATT&CK t

## Core Tools

| Tool | Purpose | Command / Usage |
|------|---------|-----------------|
| **promptfoo** | Config-driven LLM evaluation and red-team test framework; 100+ built-in strategies; YAML/JSON test matrices; CI-friendly. 22k stars. | `promptfoo eval --config redteam.yaml --output results.json` then `prompt

## Methodology Overview

### Six-Phase LLM Red-Team Engagement

```
Phase 1            Phase 2            Phase 3            Phase 4            Phase 5            Phase 6
Authorize &      →  Recon &         →  Baseline &      →  Attack Sweep    →  Exploit Chains  →  Report &
Scope               Fingerprint        Profiling          (automated)         (manual)            Detect
   │                  │                  │  

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-llm-red-team/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
