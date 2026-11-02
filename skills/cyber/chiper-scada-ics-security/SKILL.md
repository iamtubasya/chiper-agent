---
name: chiper-scada-ics-security
description: "Use when SCADA/ICS security assessment covering industrial control system protocols including Modbus TCP, S7comm (Siemens), DNP3, EtherNet/IP (CIP), OPC UA, BACnet, and"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, scada, ics]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-scada-ics-security/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-scada-ics-security/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-scada-ics-security/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-scada-ics-security/guides
---

# Scada Ics Security

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `tcpdump` — `sudo apt install -y tcpdump`
- `tshark` — `sudo apt install -y tshark`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in tcpdump tshark; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v tcpdump >/dev/null 2>&1 || sudo apt install -y tcpdump
command -v tshark >/dev/null 2>&1 || sudo apt install -y tshark
```

## When to Use

Scada Ics Security skill domain covering ics operations.

**Tools**: conpot, plcscan, s7scan, modbus-cli, mbpoll, enip-client, csric, python-opcua

**Domain**: ics

**MITRE ATT&CK**: TA0100-ICS Attack

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **conpot** | ICS/SCADA honeypot emulating Modbus, IPMI, and other industrial protocols | `conpot -f --template default` |
| **plcscan** | Scan networks for PLCs and enumerate device models, firmware versions | `plcscan -i 19

## Methodology Overview

### Phase 1: Passive Reconnaissance

1. **Network Traffic Capture** — Capture traffic on ICS-typical ports (502/Modbus, 102/S7comm, 44818/EtherNet/IP, 4840/OPC UA, 20000/DNP3) using `tcpdump` or `tshark`
2. **Protocol Identification** — Identify which ICS protocols are in use by analyzing captured traffic patterns and port activity
3. **Topology Mapping** — Map device communication patterns to und

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-scada-ics-security/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
