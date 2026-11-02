---
name: chiper-ai-safety-redteam-advanced
description: "Use when Advanced AI safety red team operations covering OWASP LLM Top 10 (2025), prompt injection (direct/indirect/multi-turn), jailbreak techniques (DAN, cogni"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, safety, redteam, advanced]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-ai-safety-redteam-advanced/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-ai-safety-redteam-advanced/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-ai-safety-redteam-advanced/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-ai-safety-redteam-advanced/guides
---

# Ai Safety Redteam Advanced

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `garak` — install: `pip install garak`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in garak; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v garak >/dev/null 2>&1 || echo "  pip install garak"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Advanced AI safety red team operations against Large Language Model (LLM) systems, agent frameworks, and Retrieval-Augmented Generation (RAG) applications.

**Tools**: garak, PyRIT, promptfoo, Giskard, Counterfit, Lakera Guard, Llama Guard, Neptune, GPT-4 as judge, custom fuzzers

**Domain**: ai-safety

**OWASP**: LLM Top 10 (2025)

**MITRE ATLAS**: Multiple adversarial techniques

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **garak** | LLM vulnerability scanner; probes for known weaknesses | `python -m garak --model_type openai --model_name gpt-4 --probes promptinject,jailbreak` |
| **PyRIT** | Python Risk Identification Toolkit (Microsoft); au

## Methodology Overview

### Attack Chain

```
[1] Reconnaissance        [2] Probe & Fuzz         [3] Vulnerability Discovery
  - Provider detection      - OWASP LLM Top 10      - LLM01-LLM10 mapping
  - Model version           - Jailbreak suites      - Prompt injection confirmed
  - Context limits          - Adversarial examples   - Data leak verified
  - Tool/API discovery      - Model inversion          |
  - RAG ident

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-ai-safety-redteam-advanced/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
