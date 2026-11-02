---
name: chiper-edge-computing-security
description: "Use when Edge computing security testing covering CDN bypass, Cloudflare Workers abuse, AWS Lambda@Edge attacks, cache poisoning, origin IP discovery, WAF bypass, a"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, edge, computing]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-edge-computing-security/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-edge-computing-security/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-edge-computing-security/test-cases.md
---

# Edge Computing Security

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

Edge computing security testing covering CDN bypass, Cloudflare Workers abuse, AWS Lambda@Edge attacks, cache poisoning, origin IP discovery, WAF bypass, and edge function injection.

**Tools**: garak, PyRIT, promptfoo, custom harnesses

**Domain**: edge

**MITRE**: TA0001-Initial Access, T1190-Exploit Public-Facing App

## Core Tools

| **Cloudflare wrangler** | Workers development/deploy | `wrangler deploy` |
| **serverless-cli** | Multi-cloud serverless | `serverless deploy` |
| **waf-bypass** | WAF bypass payloads | Various scripts |
| **Curl with resolver** | Origin IP discovery | `curl --resolve target.com:443:ORIGIN_IP` |
|

## Methodology Overview

### Attack Chain

```
[1] CDN Detection           [2] Origin Discovery      [3] Bypass WAF
  - Cloudflare/Akamai/etc     - DNS history (SecurityTrails)   - Origin direct
  - Worker script analysis    - SSL cert SAN            - HTTP/2 multiplexing
  - Edge function audit       - HTTP headers leak         |
  - Cache key analysis        - IP blocks (Shodan)        v
        |                       

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-edge-computing-security/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
