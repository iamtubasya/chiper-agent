---
name: chiper-digital-forensics
description: "Use when Digital forensics covers the complete workflow of disk forensics, memory forensics, network forensics, file recovery/carving, and chain of custody."
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, digital, forensics]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-digital-forensics/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-digital-forensics/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-digital-forensics/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-digital-forensics/guides
---

# Digital Forensics

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `autopsy` — install: `sudo apt install -y autopsy`
- `binwalk` — install: `sudo apt install -y binwalk`
- `foremost` — install: `sudo apt install -y foremost`
- `volatility` — install: `pip install volatility3`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in autopsy binwalk foremost volatility; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v autopsy >/dev/null 2>&1 || echo "  sudo apt install -y autopsy"
  command -v binwalk >/dev/null 2>&1 || echo "  sudo apt install -y binwalk"
  command -v foremost >/dev/null 2>&1 || echo "  sudo apt install -y foremost"
  command -v volatility >/dev/null 2>&1 || echo "  pip install volatility3"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Digital Forensics skill domain covering forensics operations.

**Tools**: autopsy, sleuth kit, volatility, wireshark/tshark, binwalk, foremost, Autopsy, SleuthKit (+2 more)

**Domain**: forensics

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **autopsy** | Web-based forensics platform built on SleuthKit | `autopsy -p 8080 -d /case/evidence` |
| **sleuth kit** | Command-line filesystem forensics toolset | `mmls image.dd && fls -r -o 2048 image.dd` |
| **volatility

## Methodology Overview

### Attack Chain

```
Evidence Collection    Disk Analysis        Memory Analysis      Network Reconstruction
(Imaging/Hash/         (Partition/          (Process/Injection/  (PCAP/C2/Data
 Write-Blocking)        Filesystem/Deleted)  Rootkit)             Exfiltration)
       |                    |                     |                      |
       v                    v                     v     

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-digital-forensics/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
