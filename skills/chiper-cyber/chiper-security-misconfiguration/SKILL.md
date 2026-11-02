---
name: chiper-security-misconfiguration
description: "Use when Security misconfiguration detection (OWASP A02:2025) covering default credentials, unnecessary services, verbose errors, missing security headers, and di"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, misconfiguration]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-security-misconfiguration/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-security-misconfiguration/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-security-misconfiguration/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-security-misconfiguration/guides
---

# Security Misconfiguration

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `nikto` — install: `sudo apt install -y nikto`
- `nmap` — install: `sudo apt install -y nmap`
- `whatweb` — install: `sudo apt install -y whatweb`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in nikto nmap whatweb; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v nikto >/dev/null 2>&1 || echo "  sudo apt install -y nikto"
  command -v nmap >/dev/null 2>&1 || echo "  sudo apt install -y nmap"
  command -v whatweb >/dev/null 2>&1 || echo "  sudo apt install -y whatweb"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Security Misconfiguration skill domain covering defense operations.

**Tools**: Nmap, Nikto, testssl.sh, Burp Suite, WhatWeb

**Domain**: defense

**OWASP**: A02:2025-Misconfiguration

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-security-misconfiguration/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
