---
name: chiper-insecure-design
description: "Use when Insecure Design (OWASP A06:2025) focuses on security flaws in system architecture and design phases, rather than code implementation-level bugs."
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, insecure, design]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-insecure-design/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-insecure-design/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-insecure-design/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-insecure-design/guides
---

# Insecure Design

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `burp` — `echo "Download: https://portswigger.net/burp/communitydownload"`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in burp; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v burp >/dev/null 2>&1 || echo "Download: https://portswigger.net/burp/communitydownload"
```

## When to Use

Insecure Design skill domain covering design operations.

**Tools**: Burp Suite, draw.io

**Domain**: design

**OWASP**: A06:2025-Insecure Design

## Core Tools

| Tool | Purpose | Description |
|------|---------|-------------|
| **OWASP Threat Dragon** | Threat modeling diagrams | Open-source cross-platform, supports STRIDE-categorized visual threat models |
| **STRIDE Methodology** | Structured threat classification | Microsoft's 6-category threat framewor

## Methodology Overview

### Attack Chain

```
Trust Boundary Analysis -> Abuse Case Development -> Business Logic Exploitation -> Design Pattern Attack
```

**1. Trust Boundary Analysis**
- Identify all trust boundaries: user input boundary, authentication boundary, authorization boundary, network boundary
- Check each boundary: Is there validation? Is there authorization? Is there logging?
- Look for missing trust bound

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-insecure-design/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
