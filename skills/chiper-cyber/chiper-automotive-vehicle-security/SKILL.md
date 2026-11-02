---
name: chiper-automotive-vehicle-security
description: "Use when CAN/CAN-FD bus analysis, UDS diagnostics, IVI pentest, OBD-II exploitation, key fob replay/relay attacks, GNSS spoofing, EV charging station (ISO 15118"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, automotive, vehicle]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-automotive-vehicle-security/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-automotive-vehicle-security/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-automotive-vehicle-security/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-automotive-vehicle-security/guides
---

# Automotive Vehicle Security

## When to Use

Automotive & vehicle security skill domain covering CAN (ISO 11898) / CAN-FD bus analysis, UDS (ISO 14229-1) diagnostic exploitation, OBD-II (ISO 15031) PID enumeration, in-vehicle infotainment (IVI) pentest of Android Automotive / QNX / automotive Linux, key fob rolling-code and PKES relay attacks, GNSS spoofing of connected navigation/ADAS, and EV charging station attacks against ISO 15118 Vehicle-to-Grid (V2G) Plug & Charge. The skill spans the full vehicle attack surface: from physical OBD-II port through internal CAN buses to telematics control units (TCU), the cloud-connected back-end, a

## Core Tools

### Bus Analysis & Sniffing

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **can-utils** (Linux Foundation) | Reference SocketCAN userland: candump, cansend, cansniffer, cangen | `candump -L can0` (timestamped capture) |
| **python-can** | Python library for SocketCAN /

## Methodology Overview

### Five-Phase Automotive Red Team Workflow

```
Phase 1           Phase 2           Phase 3            Phase 4            Phase 5
Recon & Setup  →  Bus Sniffing   →  Protocol Reversing→  ECU Compromise →  Physical Effect
(OBD-II pinout,   (candump,         (DBC decode,        (UDS enum,          (replay, injection,
 hardware bringup, cansniffer,       ISO-TP/UDS,         0x27 seed/key,      brake

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-automotive-vehicle-security/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
