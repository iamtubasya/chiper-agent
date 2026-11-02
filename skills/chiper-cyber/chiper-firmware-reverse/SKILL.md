---
name: chiper-firmware-reverse
description: "Use when Firmware reverse engineering covers the full pipeline from raw firmware image acquisition through filesystem extraction, static and dynamic analysis, full-system"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, firmware, reverse]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-firmware-reverse/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-firmware-reverse/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-firmware-reverse/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-firmware-reverse/guides
---

# Firmware Reverse

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `binwalk` — install: `sudo apt install -y binwalk`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in binwalk; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v binwalk >/dev/null 2>&1 || echo "  sudo apt install -y binwalk"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Firmware Reverse skill domain covering firmware operations.

**Tools**: binwalk, unblob, sasquatch, jefferson, firmadyne, firmwalker, qemu-system, yara (+10 more)

**Domain**: firmware

**MITRE ATT&CK**: TA0002-Execution

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **binwalk** | Firmware signature scanning, entropy analysis, and filesystem extraction | `binwalk -Me firmware.bin` |
| **unblob** | Multi-format firmware extraction with recursive unpacking | `unblob -e /tmp/out firmware.bi

## Methodology Overview

### Attack Chain

```
Acquisition          Extraction            Analysis             Emulation            Vulnerability Research
(OTA/vendor/hw)  (binwalk/unblob)    (strings/firmwalker)  (firmadyne/qemu)     (yara/diffing/exploit)
      |                  |                    |                    |                      |
      v                  v                    v                    v       

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-firmware-reverse/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
