---
name: chiper-cspm-casb-attack
description: "Use when CSPM/CASB/CNAPP platform bypass and abuse — rule suppression exploitation, IaC state manipulation, CASB proxy evasion, SaaS shadow discovery, Wiz/Prisma/Lacework/"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, cspm, casb, attack]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-cspm-casb-attack/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-cspm-casb-attack/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-cspm-casb-attack/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-cspm-casb-attack/guides
---

# Cspm Casb Attack

## When to Use

CSPM (Cloud Security Posture Management), CASB (Cloud Access Security Broker), and CNAPP (Cloud-Native Application Protection Platform) are the defender's primary instrumentation for cloud. They watch for misconfigurations, posture drift, anomalous SaaS access, and runtime threats. This skill is the offensive counterpart: how to enumerate which posture tools are deployed, identify their coverage gaps, exploit the misconfig-aware attack paths they normalize, suppress their findings via exception and tag abuse, and evade the CASB reverse proxy on the way to SaaS targets.

**Tools**: pacu, scouts

## Core Tools

### CSPM / CNAPP Target Enumeration

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **prowler** (7.4k stars) | AWS/Azure/GCP posture checker, 300+ checks mapped to CIS, MITRE, ISO, GDPR | `prowler aws -c check_id` / `prowler aws --list-checks` |
| **scoutsuite** (6.6k st

## Methodology Overview

### Attack Chain: CSPM/CASB Platform Bypass

```
   1. Enumerate               2. Coverage-Gap             3. Choose Attack Path        4. Suppress / Evade          5. Maintain
   ─────────────────          ───────────────             ──────────────────           ──────────────────           ─────────────
   CSPM presence        ──>   identify blind spots   ──>  pick path outside       ──> tag-tam

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-cspm-casb-attack/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
