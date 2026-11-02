---
name: chiper-cps-attack
description: "Use when Cyber-Physical Systems (CPS) attacks — PLCs (Siemens S7, Rockwell ControlLogix, Schneider Modicon, Mitsubishi MELSEC), ICS protocols (Modbus, DNP3, Profinet, EtherNet/I"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, cps, attack]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-cps-attack/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-cps-attack/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-cps-attack/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-cps-attack/guides
---

# Cps Attack

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `tcpdump` — `sudo apt install -y tcpdump`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in tcpdump; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v tcpdump >/dev/null 2>&1 || sudo apt install -y tcpdump
```

## When to Use

Cyber-Physical Systems (CPS) bridge the digital and physical worlds: PLCs (Programmable Logic Controllers), RTUs (Remote Terminal Units), IEDs (Intelligent Electronic Devices), HMIs (Human Machine Interfaces), and the industrial protocols they speak. These systems control power grids, water treatment, oil & gas pipelines, manufacturing lines, building automation (BACnet), and increasingly vehicle infrastructure (V2X, traffic control).

The 2024-2025 threat landscape for CPS attacks is dominated by:

- **Unitronics PLC attack (Nov 2023)** — Iranian threat group attacked water utilities in US
- 

## Core Tools

### Field Device Targets

| Vendor | Product | Protocol | Notes |
|--------|---------|----------|-------|
| **Siemens** | S7-1200, S7-1500, S7-300 | S7comm, S7comm-Plus, Profinet | Dominant European |
| **Rockwell Automation** | ControlLogix, CompactLogix, MicroLogix | EtherNet/IP, CIP | Dominant US

## Methodology Overview

### Phase 1 — Recon (OT Network Discovery)

OT networks are often air-gapped (or "air-gapped") — but rarely. Identify:

- PLC vendor + model + firmware
- HMI vendor + software version
- Engineering workstation + vendor software (TIA Portal, Studio 5000)
- SCADA historian + DB backend
- Network topology (often flat L2)

```bash
# Passive recon (preferred — OT teams hate active scanning)
tcpdump -i 

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-cps-attack/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
