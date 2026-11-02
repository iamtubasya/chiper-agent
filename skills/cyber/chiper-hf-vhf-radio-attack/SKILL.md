---
name: chiper-hf-vhf-radio-attack
description: "Use when Licensed HF/VHF/UHF radio attack — ADS-B 1090 MHz, AIS, ACARS, VDL Mode 2, POCSAG/FLEX pagers, APRS, NDB, ATC/maritime VHF, DSC, weather fax, MLAT"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, vhf, radio, attack]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-hf-vhf-radio-attack/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-hf-vhf-radio-attack/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-hf-vhf-radio-attack/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-hf-vhf-radio-attack/guides
---

# Hf Vhf Radio Attack

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `hackrf` — `sudo apt install -y hackrf`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in hackrf; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v hackrf >/dev/null 2>&1 || sudo apt install -y hackrf
```

## When to Use

HF/VHF/UHF licensed radio attack covers the spectrum **above** Sub-GHz ISM (handled in `sdr-rf-attack`) and **below** cellular operator bands (handled in `5g-telecom-attack`). This skill targets **licensed radio services** in the 9 kHz - 1500 MHz range that have safety-of-life or commercial licensing implications: aircraft ADS-B broadcasts at 1090 MHz, maritime AIS at 161.975/162.025 MHz, airline ACARS data link at 131.550 MHz, VDL Mode 2 at 136.975 MHz, HFDL oceanic comms across multiple HF bands, POCSAG/FLEX/APOC pager networks, amateur radio APRS position reporting, aviation NDB beacons (19

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **HackRF One** | TX/RX SDR for wideband capture and (authorized) transmission from 1 MHz to 6 GHz | `hackrf_transfer -r capture.raw -f 1090000000 -s 2000000 -l 32 -g 40` |
| **BladeRF 2.0 micro** | Full-duplex TX/RX SDR from

## Methodology Overview

### Phase 1: Reconnaissance -- Licensed Band Survey

1. Conduct wideband spectrum scan across the HF/VHF/UHF range relevant to the engagement scope using `rtl_power` or `hackrf_sweep`
2. Identify active licensed services (aviation, maritime, paging, amateur) by their characteristic frequencies and modulations
3. Document the baseline RF environment at the engagement site including expected and une

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-hf-vhf-radio-attack/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
