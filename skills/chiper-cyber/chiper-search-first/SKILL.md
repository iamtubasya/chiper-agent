---
name: chiper-search-first
description: "Use when Systematizes the \"search for existing tools, exploits, and techniques before writing custom ones\" workflow."
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, search, first]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-search-first/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-search-first/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-search-first/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-search-first/guides
---

# Search First

## When to Use

Search First skill domain covering workflow operations.

**Domain**: workflow

## Methodology Overview

### Search-First Decision Flow

```
┌─────────────────────────────────────────────┐
│  1. NEED ANALYSIS                           │
│     Define what capability is needed         │
│     Identify target technology/constraints   │
├─────────────────────────────────────────────┤
│  2. PARALLEL SEARCH                         │
│     ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│     │ ExploitDB│ │  GitH

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-search-first/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
