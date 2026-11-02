---
name: chiper-council
description: "Use when Council provides a structured framework for analyzing security questions from multiple adversarial and defensive perspectives simultaneously."
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, council]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-council/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-council/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-council/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-council/guides
---

# Council

## When to Use

Multi-perspective security analysis providing Attack, Defense, and Audit viewpoints for complex security decisions.

**Tools**: Impact 5 (Critical), Impact 4 (Major), Impact 3 (Moderate), Impact 2 (Minor), Impact 1 (Negligible)

**Domain**: analysis

## Methodology Overview

### Phase 1: Scope Definition

Define the security question, boundaries, and constraints:

- What specific decision needs to be made?
- What systems, data, and processes are in scope?
- What are the time and resource constraints?
- What compliance or regulatory requirements apply?

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-council/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
