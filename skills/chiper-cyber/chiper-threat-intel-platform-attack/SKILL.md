---
name: chiper-threat-intel-platform-attack
description: "Use when Attacking threat intelligence platforms (MISP, OpenCTI, Anomali ThreatStream, ThreatQuotient, ThreatConnect, IBM Threat Intel, Palo Alto AutoFocus, Ma"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, threat, intel, platform, attack]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-threat-intel-platform-attack/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-threat-intel-platform-attack/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-threat-intel-platform-attack/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-threat-intel-platform-attack/guides
---

# Threat Intel Platform Attack

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

Threat intelligence platforms (MISP, OpenCTI, Anomali, ThreatQuotient, ThreatConnect, IBM Threat Intel, Palo Alto AutoFocus, Mandiant Advantage) are high-value targets: they aggregate IOCs, adversary TTPs, sharing-group trust relationships, and often feed defensive products (firewalls, SIEMs, EDRs). This domain covers offensive testing of TI platforms: platform-specific CVEs (MISP CVE-2022-29527, OpenCTI GraphQL injection), API abuse (write access to IOC databases), sharing-group trust abuse (escalating trust levels, claiming false attribution), false-positive IOC injection (poisoning feeds to

## Core Tools

| Tool | Purpose |
|------|---------|
| `MISP` | Open-source TI platform (most common target) |
| `OpenCTI` | Open-source TI platform (GraphQL-based) |
| `curl` | HTTP API testing |
| `python3` | Scripting for STIX / TAXII |
| `jq` | JSON processing for STIX bundles |
| `burpsuite` | Web proxy for A

## Methodology Overview

### Phase 1 — Recon

Map the TI platform's external surface:

```bash
# Identify MISP instance
curl -sI https://misp.example.com/ | head -5
curl -s https://misp.example.com/servers/checkVersion | jq .

# Identify OpenCTI instance
curl -s https://opencti.example.com/graphql -X POST \
  -H "Content-Type: application/json" \
  -d '{"query":"{ settings { id } }"}'

# Identify Anomali ThreatStream
curl

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-threat-intel-platform-attack/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
