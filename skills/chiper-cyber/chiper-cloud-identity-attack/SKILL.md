---
name: chiper-cloud-identity-attack
description: "Use when Cloud identity provider attacks covering Azure AD/Entra ID, Okta, Auth0, Ping, AWS IAM Identity Center, and Google Workspace — including OAuth 2.0 token thef"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, cloud, identity, attack]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-cloud-identity-attack/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-cloud-identity-attack/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-cloud-identity-attack/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-cloud-identity-attack/guides
---

# Cloud Identity Attack

## When to Use

Cloud identity provider attack skill domain covering modern IdP infrastructure — Azure AD/Entra ID, Okta, Auth0, Ping Identity, AWS IAM Identity Center, and Google Workspace. This skill addresses the modern attack surface that has largely replaced on-premises Active Directory as the primary enterprise identity tier: OAuth 2.0 access tokens, OIDC flows, SAML federation, conditional access policies, MFA enforcement, app registrations, and just-in-time elevation (PIM).

**Tools**: ROADtools (roadrecon, roadtx, roadlib), AADInternals, MicroBurst, MFASweep, TokenTactics, AzureAD/MSOnline PowerShell

## Core Tools

### Azure AD/Entra ID & Federation

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **ROADtools** (roadrecon, roadtx, roadlib) | The reference Azure AD attack suite — recon, auth, token manipulation | `python roadrecon auth --device-code`; `python roadtx.py gettokens` |
|

## Methodology Overview

### Cloud Identity Six-Phase Workflow

```
Phase 1            Phase 2            Phase 3            Phase 4            Phase 5            Phase 6
Tenant Recon   →   User/Group Enum  → Token Acquisition → CA Bypass      →   Lateral via Apps →   Persistence +
& Foothold         (Graph/Okta)      (OAuth/SAML/RT)     (Legacy/MFA        + Federation        Backdoor
                   │                 

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-cloud-identity-attack/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
