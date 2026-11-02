---
name: chiper-uav-drone-security
description: "Use when UAV/drone security testing — PX4/ArduPilot autopilot attacks, MAVLink protocol fuzzing, RF link hijacking (2.4GHz control / 5.8GHz video), GPS spoofing/jamming,"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, uav, drone]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-uav-drone-security/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-uav-drone-security/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-uav-drone-security/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-uav-drone-security/guides
---

# Uav Drone Security

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `hackrf` — `sudo apt install -y hackrf`
- `metasploit` — `sudo apt install -y metasploit-framework`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in hackrf metasploit; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v hackrf >/dev/null 2>&1 || sudo apt install -y hackrf
command -v metasploit >/dev/null 2>&1 || sudo apt install -y metasploit-framework
```

## When to Use

UAV/drone security skill domain covering the full aerial vehicle attack surface: open-source autopilot stacks (PX4, ArduPilot), the MAVLink (Micro Air Vehicle Link) telemetry/control protocol, ground control station software (QGroundControl, MAVProxy), RF control links (2.4 GHz FHSS — FrSky, FlySky, CRSF/ELRS — plus DJI OcuSync and Walksnail digital links), 5.8 GHz analog/digital video links, GPS/GNSS dependency, and the DJI closed ecosystem. The domain covers both offensive testing of drone systems (authorized pentests, fleet security audits, vendor red team) and defensive counter-UAS (CUAS) 

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **DroneSploit** | Drone-focused pentest framework (Metasploit-style) — modules for drone discovery, default-password login, MAVLink replay | `dronesploit` → `use auxiliary/scanner/dji/aeroscope_listener` → `set INTERFACE wla

## Methodology Overview

### Phase 1: Reconnaissance — RF Spectrum Survey + DroneID

1. Set up SDR hardware (HackRF/RTL-SDR) and verify with `hackrf_info` / `rtl_test`.
2. Wideband scan of drone bands: 2.4 GHz ISM (`hackrf_sweep -f 2400:2500`), 5.8 GHz FPV (`hackrf_sweep -f 5725:5875`), 900 MHz telemetry (`hackrf_sweep -f 902:928`), 433 MHz telemetry (EU).
3. Identify active drone signals: FHSS bursts in 2.4 GHz, continuo

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-uav-drone-security/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
