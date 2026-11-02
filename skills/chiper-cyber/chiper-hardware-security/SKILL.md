---
name: chiper-hardware-security
description: "Use when Hardware and embedded system security testing covering physical interface exploitation, firmware extraction and analysis, side-channel attacks, RFID/NFC cloning,"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, hardware]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-hardware-security/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-hardware-security/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-hardware-security/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-hardware-security/guides
---

# Hardware Security

## When to Use

Hardware Security skill domain covering hardware operations.

**Domain**: hardware

## Methodology Overview

### Phase 1: Physical Reconnaissance

**Goal**: Identify all external interfaces and collect device intelligence before applying probes.

- Photograph all PCB surfaces; annotate visible chip markings
- Look up FCC ID on fcc.gov to obtain internal photos, test reports, and sometimes full schematics
- Identify chip families from markings: SoC, flash chip, EEPROM, RF modules
- Map all exposed connect

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-hardware-security/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
