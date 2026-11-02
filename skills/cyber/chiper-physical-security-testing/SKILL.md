---
name: chiper-physical-security-testing
description: "Use when Physical penetration testing covering mechanical lock bypass (pin-tubular/wafer), RFID/NFC badge cloning (Proxmark3/ESP-RFID-Tool/Walrus), HID iCLASS/Mif"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, physical, testing]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-physical-security-testing/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-physical-security-testing/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-physical-security-testing/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-physical-security-testing/guides
---

# Physical Security Testing

## When to Use

Physical security testing covers the on-site operations that gain physical access to a target facility — lock picking, badge cloning, drop-box deployment, USB-weapon delivery, hidden-camera placement, and the social engineering that gets a human through the door. This skill is the physical-access complement to radio and firmware skills: where `bluetooth-rfid-nfc` analyzes the wireless protocol and `hardware-security` analyzes chips and firmware, this skill asks "how do I get *through the door*?"

**Tools**: Proxmark3, ESP-RFID-Tool, Walrus, Hak5 LAN Turtle, Hak5 Packet Squirrel, USB Rubber Duc

## Core Tools

### Lock Bypass & Mechanical

| Tool | Purpose | Notes |
|------|---------|-------|
| **Lock pick set** (Peterson, SouthOrd, Sparrows) | Pin-tumbler picking with hooks, rakes, and tension wrenches | Standard 0.025" or 0.018" thickness; transparent practice locks first, then progressively harder belt

## Methodology Overview

### On-Site Engagement Six-Phase Process

```
Phase 1            Phase 2          Phase 3              Phase 4          Phase 5            Phase 6
Scope & Legal  →   Pre-Engagement →  Entry Vector      →  Execution &   →  On-Site Ops &   →  Exit &
                   Recon            Selection              Access           Persistence          Evidence
   │                  │                  │    

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-physical-security-testing/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
