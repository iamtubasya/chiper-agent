---
name: chiper-ai-agent-security
description: "Use when Offensive security testing of AI agent systems covering MCP server attacks, tool poisoning, indirect prompt injection against agents, RAG knowledge base poisonin"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, agent]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-ai-agent-security/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-ai-agent-security/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-ai-agent-security/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-ai-agent-security/guides
---

# Ai Agent Security

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `file` — `sudo apt install -y file`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in file; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v file >/dev/null 2>&1 || sudo apt install -y file
```

## When to Use

AI agent security skill domain covering offensive testing of **stateful, tool-using, autonomous** AI agent systems — agents that persist context across turns, call external tools (MCP servers, function-calling APIs, code interpreters), read from RAG knowledge bases, coordinate with other agents, and take real-world actions (file writes, API calls, code execution, financial transactions). The skill equips the operator to discover and demonstrate agent-specific vulnerabilities: MCP server discovery and capability enumeration, tool poisoning via malicious tool descriptions and parameter injection

## Core Tools

| Tool | Purpose | Command / Usage |
|------|---------|-----------------|
| **HexStrike AI** | Multi-agent AI red-team orchestrator — coordinates recon, injection, and exploitation across LLM endpoints and agent surfaces. 9.6k stars. | `hexstrike --target agent-endpoint --recon --inject --exploit --

## Methodology Overview

### Six-Phase Agent Red-Team Engagement

```
Phase 1            Phase 2            Phase 3            Phase 4            Phase 5            Phase 6
Authorize &      →  Agent Recon &    →  MCP Discovery  →  Tool Poisoning  →  Agent Hijack   →  Report &
Scope               Surface Map        & Enumeration      & Indirect         & Chain Build      Detect
   │                  │                  │   

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-ai-agent-security/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
