---
name: chiper-identity-provider-attack
description: "Use when Identity Provider (IdP) attack patterns covering OAuth 2.0/OIDC, SAML, JWT, token theft/replay, MFA fatigue, service principal abuse (Azure AD/Entra ID),"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, identity, provider, attack]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-identity-provider-attack/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-identity-provider-attack/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-identity-provider-attack/test-cases.md
---

# Identity Provider Attack

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

Identity Provider (IdP) attack patterns covering OAuth 2.0/OIDC, SAML, JWT, token theft/replay, MFA fatigue, service principal abuse (Azure AD/Entra ID), Okta, Auth0, Keycloak, and modern identity-based attacks.

**Tools**: garak, PyRIT, promptfoo, custom harnesses

**Domain**: identity

**MITRE**: TA0006-Credential Access, T1556-Modify Authentication Process

## Core Tools

| **jwt_tool** | JWT analysis and exploitation | `python3 jwt_tool.py <JWT>` |
| **tokenhero** | OAuth token analysis | `tokenhero --token <access_token>` |
| **AADInternals** | Azure AD/Entra ID reconnaissance | `Get-AADIntTenantDomains` |
| **MFASweep** | MFA bypass testing | `Invoke-MFASweep -Tar

## Methodology Overview

### Attack Chain

```
[1] Reconnaissance          [2] Token Analysis       [3] Vulnerability Discovery
  - IdP identification        - JWT decode              - Algorithm confusion
  - Tenant enumeration        - Refresh token swap      - State reuse
  - User enumeration          - Token replay              |
  - App registration audit      |                        v
        |                     

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-identity-provider-attack/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
