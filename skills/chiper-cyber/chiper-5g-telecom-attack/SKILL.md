---
name: chiper-5g-telecom-attack
description: "Use when 5G core (AMF/SMF/UPF), RAN, signaling (PFCP/GTP/Diameter/SS7), IMSI catchers, O-RAN security, roaming abuse, SMS interception, and telecom infrastructure red tea"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, telecom, attack]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-5g-telecom-attack/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-5g-telecom-attack/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-5g-telecom-attack/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-5g-telecom-attack/guides
---

# 5G Telecom Attack

## When to Use

5G telecom attack skill domain covering the operator-side cellular stack: the 5G Core (5GC) components (AMF, SMF, UPF, AUSF, UDM, PCF, NRF, NSSF), the Radio Access Network (gNodeB, O-RAN), and the signaling protocols that carry subscriber identity, session state, and roaming traffic (NGAP, PFCP, GTP-U, GTP-C, Diameter, MAP/SS7, NAS). This is the cellular network as target — the infrastructure that authenticates 5 billion subscribers, routes their data, and hands them off between cell sites and roaming partners. Where `bluetooth-rfid-nfc` covers the last 10 meters of local radio, this skill cov

## Core Tools

| Tool | Purpose | License / Notes |
|------|---------|-----------------|
| **srsRAN_Project** | Open-source 5G CU/DU (gNodeB) — software radio stack. Runs with USRP/BladeRF hardware. Used in lab bring-up and attack reproduction. | AGPL-3.0. github.com/srsran/srsRAN_Project |
| **Open5GS** | Open-so

## Methodology Overview

The engagement methodology is organized in five phases, each scoped against one of the three cellular network tiers (RAN, 5GC, Interconnect).

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-5g-telecom-attack/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
