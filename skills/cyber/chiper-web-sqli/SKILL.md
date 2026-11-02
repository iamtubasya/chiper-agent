---
name: chiper-web-sqli
description: "Use when SQL injection attacks and defense - covering all major SQLi types including error-based, union-based, blind (boolean/time), double query (error-based), stacked queries, a"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, web, sqli]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-web-sqli/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-web-sqli/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-web-sqli/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-web-sqli/guides
---

# Web Sqli

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `curl` — install: `sudo apt install -y curl`
- `sqlmap` — install: `sudo apt install -y sqlmap`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in curl sqlmap; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v curl >/dev/null 2>&1 || echo "  sudo apt install -y curl"
  command -v sqlmap >/dev/null 2>&1 || echo "  sudo apt install -y sqlmap"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Web Sqli skill domain covering web attack operations.

**Tools**: sqlmap, Burp Suite, curl, manual injection, browsetool DevTools

**Domain**: web-attack

**OWASP**: A03:2021-Injection

**MITRE ATT&CK**: T1190-Exploit Public-Facing App

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-web-sqli/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
