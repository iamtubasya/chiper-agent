---
name: chiper-satellite-leo-security
description: "Use when Satellite and LEO communication security — Starlink, Kuiper, OneWeb, Iridium, Inmarsat, Viasat KA-SAT, HughesNet, DVB-S/S2, VSAT (iDirect/Hughes), GNSS rece"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, satellite, leo]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-satellite-leo-security/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-satellite-leo-security/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-satellite-leo-security/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-satellite-leo-security/guides
---

# Satellite Leo Security

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

Satellite communication security covers the space segment, the ground segment, and the link between them — the radio path that carries broadband, voice, pager, TV, IoT, and navigation data to roughly four billion receivers worldwide. This skill targets commercial satellite communications: LEO broadband constellations (Starlink, Kuiper, OneWeb, Telesat Lightspeed), LEO narrowband (Iridium NEXT, Globalstar), GEO/MEO broadband (Inmarsat BGAN, Viasat KA-SAT, HughesNet Jupiter), GEO broadcast (DVB-S/S2/S2X, DIRECTV, Dish), VSAT enterprise networks (iDirect, Hughes PES, Newtec, Comtech), and the GNS

## Core Tools

| Tool | Purpose | License / Notes |
|------|---------|-----------------|
| **HackRF One / BladeRF 2.0 micro / PlutoSDR** | General-purpose SDRs for the 1 MHz–6 GHz range. Paired with a Ku-band (10.7–12.75 GHz) or Ka-band (19.7–20.2 GHz) LNB downconverter (standard satellite TV LNB, ~$20) for receiv

## Methodology Overview

The engagement methodology is organized in five phases. The default posture is **receive-only / passive**: in most jurisdictions, transmitting in licensed satellite bands (Ku 14.0–14.5 GHz uplink, Ka 28–30 GHz uplink, L-band 1.6 GHz uplink for Iridium/Inmarsat) without a national license is a criminal offense on par with cellular jamming. The only TX-side work this skill covers is GPS-SDR-SIM GNSS

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-satellite-leo-security/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
