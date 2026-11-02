---
name: chiper-engagement-manager
description: "Use when End-to-end penetration test project management skill. Orchestrates the full engagement lifecycle from scoping through reporting, managing skill composition, evi"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, engagement, manager]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-engagement-manager/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-engagement-manager/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-engagement-manager/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-engagement-manager/guides
---

# Engagement Manager

## When to Use

Orchestrates the full engagement lifecycle from scoping through reporting, managing skill composition, evidence chains, phase transitions, and stakeholder communication. Serves as the command center that coordinates specialized security skills, enforces scope boundaries, tracks progress across kill chain phases, and ensures deliverables meet professional standards.

**Domain**: management

## Core Tools

| Tool | Category | Purpose | Key Command |
|------|----------|---------|-------------|
| orchestrator.sh | Engagement Orchestration | End-to-end penetration test workflow execution | `orchestrator.sh --target web --phase all` |
| tool-selector.sh | Tool Selection | Target-to-tool mapping by attack 

## Methodology Overview

1. **Scope & Plan** — Define target, scope rules, and skill chain based on target type. Review Rules of Engagement, identify in-scope and out-of-scope assets, establish communication channels and notification thresholds.
2. **Execute Kill Chain** — Progress through recon, scan, enum, vuln, exploit, and post-exp phases with structured data handoff between each phase. Each phase has defined entry/ex

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-engagement-manager/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
