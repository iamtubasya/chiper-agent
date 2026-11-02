---
name: chiper-5g-6g-telecom-attack-advanced
description: "Use when Advanced 5G/6G telecom attacks covering 5G Core (SBA) exploitation, IMSI catcher evolution (5G Stingray), SIP/Diameter protocol attacks, Open RAN vul"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, telecom, attack, advanced]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-5g-6g-telecom-attack-advanced/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-5g-6g-telecom-attack-advanced/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-5g-6g-telecom-attack-advanced/test-cases.md
---

# 5G 6G Telecom Attack Advanced

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `garak` — install: `pip install garak`
- `wireshark` — install: `sudo apt install -y wireshark`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in garak wireshark; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v garak >/dev/null 2>&1 || echo "  pip install garak"
  command -v wireshark >/dev/null 2>&1 || echo "  sudo apt install -y wireshark"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Advanced 5G/6G telecom attacks covering 5G Core (SBA) exploitation, IMSI catcher evolution (5G Stingray), SIP/Diameter protocol attacks, Open RAN vulnerabilities, network slicing abuse, and early 6G research vectors (THz comms, AI-native air interface).

**Tools**: garak, PyRIT, promptfoo, custom harnesses

**Domain**: telecom

**MITRE**: TA0001-Initial Access, T1557-Adversary-in-the-Middle

## Core Tools

| **srsRAN** | Open-source 5G RAN + Core | `srsran-enb` / `srsran-gnb` |
| **Open5GS** | Open-source 5G Core | `open5gs-pgwd` |
| **sipp** | SIP/Diameter testing | `sipp -sf scenario.xml` |
| **WireShark** | Protocol analysis | Decode 5G protocols |
| **Py Crate** | Protocol testing | `pycrate_diame

## Methodology Overview

### Attack Chain

```
[1] Reconnaissance         [2] Signaling Attack      [3] Core Exploitation
  - PLMN identification      - Diameter relay            - NF API abuse
  - UE attachment              - SIP REGISTER flood         - Cross-slice access
  - NF discovery              - SMS interception             - AUSF bypass
  - Slice mapping               |                            |
        |   

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-5g-6g-telecom-attack-advanced/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
