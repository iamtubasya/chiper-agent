---
name: chiper-web-access-control
description: "Use when Broken Access Control (OWASP Top 10 2025 - A01) attacks and defense — covering core attack surfaces including IDOR (Insecure Direct Object Reference), vertical/"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, web, access, control]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-web-access-control/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-web-access-control/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-web-access-control/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-web-access-control/guides
---

# Web Access Control

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `curl` — install: `sudo apt install -y curl`
- `ffuf` — install: `go install github.com/ffuf/ffuf/v2@latest`
- `sqlmap` — install: `sudo apt install -y sqlmap`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in curl ffuf sqlmap; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v curl >/dev/null 2>&1 || echo "  sudo apt install -y curl"
  command -v ffuf >/dev/null 2>&1 || echo "  go install github.com/ffuf/ffuf/v2@latest"
  command -v sqlmap >/dev/null 2>&1 || echo "  sudo apt install -y sqlmap"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Web Access Control skill domain covering web attack operations.

**Tools**: Burp Suite, ffuf, Autorize, curl, sqlmap, fimap

**Domain**: web-attack

**OWASP**: A01:2021-Broken Access Control

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **Burp Suite** | Intercept and modify requests, permission comparison testing, Autorize plugin for automatic privilege escalation detection | Professional edition + Autorize extension |
| **ffuf** | IDOR endpoint fuzzing, pa

## Methodology Overview

### Attack Chain

```
Recon → IDOR Discovery → Privilege Escalation → Forced Browsing → Parameter Tampering
```

**1. Recon**
- Crawl all API endpoints, record URLs containing ID parameters (user_id, order_id, file_id, etc.)
- Identify authentication mechanisms: Cookie / JWT / API Key / OAuth Token
- Build role matrix: functions and resources visible to each role

**2. IDOR Discovery**
- Replace n

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-web-access-control/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
