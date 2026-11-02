---
name: chiper-web-ssrf
description: "Use when Server-Side Request Forgery (SSRF) attacks including basic, blind, and advanced bypass techniques, internal port scanning, cloud metadata extraction (AWS/GCP/Azure), prot"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, web, ssrf]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-web-ssrf/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-web-ssrf/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-web-ssrf/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-web-ssrf/guides
---

# Web Ssrf

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `curl` — install: `sudo apt install -y curl`
- `ffuf` — install: `go install github.com/ffuf/ffuf/v2@latest`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in curl ffuf; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v curl >/dev/null 2>&1 || echo "  sudo apt install -y curl"
  command -v ffuf >/dev/null 2>&1 || echo "  go install github.com/ffuf/ffuf/v2@latest"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Web Ssrf skill domain covering web attack operations.

**Tools**: Burp Suite, curl, ffuf, Gopherus, SSRFmap, Burp Collaborator

**Domain**: web-attack

**OWASP**: A10:2021-SSRF

**MITRE ATT&CK**: T1190-Exploit Public-Facing App

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-web-ssrf/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
