---
name: chiper-ad-cs-abuse
description: "Use when Active Directory Certificate Services (AD CS) abuse — ESC1-ESC15 attack patterns, PKINIT, PetitPotam to AD CS to Domain Admin chains, CVE-2022-26923 (Certifried), Shad"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, abuse]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-ad-cs-abuse/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-ad-cs-abuse/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-ad-cs-abuse/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-ad-cs-abuse/guides
---

# Ad Cs Abuse

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `certipy` — `pip install certipy-ad`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in certipy; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v certipy >/dev/null 2>&1 || pip install certipy-ad
```

## When to Use

AD CS abuse skill domain covering enterprise PKI compromise. Active Directory Certificate Services is Microsoft's PKI implementation and is deployed in approximately 90% of enterprise Windows environments. When misconfigured, AD CS becomes one of the most reliable paths from any domain user to Domain Admin or Enterprise Admin, often without touching the DC's LDAP/DRSUAPI interfaces that high-maturity defenders monitor for DCSync and similar attacks.

**Domain**: enterprise-cloud (AD CS / PKI)

**MITRE ATT&CK**: T1552-Unsecured Credentials, T1606-Forged Web Credentials, T1550-Use Alternate Auth

## Core Tools

| Tool | Category | Purpose |
|------|----------|---------|
| Certipy (ly4k fork) | Enumeration + Abuse | Modern Python AD CS attack suite — `certipy find`, `certipy req`, `certipy auth`, `certipy ca`, `certipy account`, `certipy template` |
| Certify (GhostPack / HarmJ0y) | Enumeration + Abuse | C#

## Methodology Overview

### Phase 1: PKI Discovery and CA Mapping

Identify Enterprise CAs, Standalone CAs, Web Enrollment endpoints, and enrollment services via LDAP, RPC, and HTTP reconnaissance.

1. LDAP query the Configuration partition for `pKIEnrollmentService` objects to locate CAs and their `dNSHostName`, certificate templates (`certificateTemplates`), and CA certificate blobs
2. Identify Web Enrollment endpoints

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-ad-cs-abuse/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
