---
name: chiper-web-xss
description: "Use when XSS (Cross-Site Scripting) is an attack that injects malicious scripts into trusted websites."
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, web, xss]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-web-xss/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-web-xss/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-web-xss/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-web-xss/guides
---

# Web Xss

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `dalfox` — install: `go install github.com/hahwul/dalfox/v2@latest`
- `xsstrike` — install: `pip install xsstrike`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in dalfox xsstrike; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v dalfox >/dev/null 2>&1 || echo "  go install github.com/hahwul/dalfox/v2@latest"
  command -v xsstrike >/dev/null 2>&1 || echo "  pip install xsstrike"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Web Xss skill domain covering web attack operations.

**Tools**: Burp Suite, Browser DevTools, XSStrike, Dalfox, Custom Payloads

**Domain**: web-attack

**OWASP**: A03:2021-Injection

**MITRE ATT&CK**: T1189-Drive-by Compromise

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **Burp Suite** | Proxy interception, active/passive scanning, payload encoding, Repeater manual testing | Proxy intercept request -> Send to Repeater -> Modify parameters to test XSS |
| **Browser DevTools** | DOM inspection

## Methodology Overview

### Attack Chain

```
[1] Input Point          [2] Payload Testing       [3] Filter Bypass
    Discovery               - Basic probing            - Encoding obfuscation
  - URL parameters          - Context analysis          - Tag/attribute alternatives
  - Form fields             - Response tracing          - WAF fingerprinting
  - HTTP headers            - Render verification       - Mutation ex

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-web-xss/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
