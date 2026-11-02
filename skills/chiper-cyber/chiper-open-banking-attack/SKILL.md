---
name: chiper-open-banking-attack
description: "Use when Open Banking / PSD2 / Open Finance attacks — FAPI (Financial-grade API), OpenID Connect for Financial APIs, OAuth2 PKCE, Strong Customer Authentication (SCA) b"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, open, banking, attack]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-open-banking-attack/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-open-banking-attack/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-open-banking-attack/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-open-banking-attack/guides
---

# Open Banking Attack

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `curl` — `sudo apt install -y curl`
- `jq` — `sudo apt install -y jq`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in curl jq; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v curl >/dev/null 2>&1 || sudo apt install -y curl
command -v jq >/dev/null 2>&1 || sudo apt install -y jq
```

## When to Use

Open Banking (formerly PSD2) is the API-driven banking standard that lets customers share account data with Third-Party Providers (TPPs) and initiate payments via API. As of 2024-2026:

- **UK Open Banking**: ~10M active users, 400+ regulated TPPs
- **EU PSD2/PSD3**: every EU bank exposes AIS/PIS APIs
- **Brazil Open Finance**: 800M+ API calls/month
- **India Account Aggregator**: 1.4B+ AA transactions
- **US FDX**: 200M+ accounts accessible via FDX API
- **Singapore MAS APIX**: cross-border pilots
- **Australia CDR**: Consumer Data Right, mandatory for banks

The standard stack is:
- **FAPI 2

## Core Tools

### Open Banking Standards (Targets)

| Standard | Region | Notes |
|----------|--------|-------|
| **FAPI 1.0 Baseline** | UK, EU, BR | OAuth2 profile for finance |
| **FAPI 1.0 Advanced** | UK, EU | mTLS or DPoP sender-constrained |
| **FAPI 2.0** | UK, EU, BR | Security profile (2024+) |
| **FAPI

## Methodology Overview

### Phase 1 — Reconnaissance

```bash
# Discover Open Banking endpoints via well-known
curl -s https://bank.example.com/.well-known/openid-configuration | jq .

# Output includes:
# - authorization_endpoint
# - token_endpoint
# - userinfo_endpoint
# - jwks_uri
# - scopes_supported
# - code_challenge_methods_supported (should include S256 for FAPI)
# - request_object_signing_alg_values_supported (s

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-open-banking-attack/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
