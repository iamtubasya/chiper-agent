---
name: chiper-ics-fieldbus-attack
description: "Use when Industrial fieldbus protocol penetration testing beyond Modbus — Profibus/PROFINET, EtherCAT, DNP3, IEC 61850 (GOOSE/SV/MMS), IEC 60870-5-101/104, Foundation F"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, ics, fieldbus, attack]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-ics-fieldbus-attack/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-ics-fieldbus-attack/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-ics-fieldbus-attack/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-ics-fieldbus-attack/guides
---

# Ics Fieldbus Attack

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `boofuzz` — install: `pip install boofuzz`
- `scapy` — install: `pip install scapy`
- `wireshark` — install: `sudo apt install -y wireshark`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in boofuzz scapy wireshark; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v boofuzz >/dev/null 2>&1 || echo "  pip install boofuzz"
  command -v scapy >/dev/null 2>&1 || echo "  pip install scapy"
  command -v wireshark >/dev/null 2>&1 || echo "  sudo apt install -y wireshark"
else
  echo "✅ All tools installed"
fi
```

## When to Use

ICS fieldbus protocol penetration testing covering all major industrial protocols BEYOND Modbus TCP. This domain specializes in the protocols that govern power utilities, oil & gas, water treatment, building automation, and discrete manufacturing. The skill targets protocols that `scada-ics-security` either omits or only covers superficially.

**Tools**: wireshark, scapy, plcscan, redpoint, opendnp3, lib60870, iec104attack, profishark, boofuzz, conpot, nmap-nse, ettercap/bettercap, claroty/nozomi

**Domain**: ics-fieldbus-attack

**MITRE ATT&CK ICS**: T0817 - Program Logic Controller Software,

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **Wireshark** | Full protocol dissection of 30+ fieldbus protocols via built-in dissectors | `tshark -i eth0 -Y "dnp3 || iec60870_104 || goose || pn_rt || ethercat"` |
| **Scapy** | Layered packet crafting with IEC 61850/104

## Methodology Overview

### Phase 1: Passive Reconnaissance (Read-Only, Safe)

1. **Traffic Capture Setup** — Configure span port or network tap on OT switch; never introduce active devices into a fieldbus segment without explicit authorization. For PROFIBUS/PROFINET, use a ProfiShark tap.
2. **Protocol Dissection** — Use Wireshark with fieldbus-specific display filters to identify protocols in use: `dnp3`, `iec60870_asd

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-ics-fieldbus-attack/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
