---
name: chiper-hardware-side-channel-advanced
description: "Use when Advanced hardware side-channel attacks covering power analysis (SPA/DPA), electromagnetic emanation, timing attacks, cache-timing attacks (Spectre/M"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, hardware, side, channel, advanced]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-hardware-side-channel-advanced/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-hardware-side-channel-advanced/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-hardware-side-channel-advanced/test-cases.md
---

# Hardware Side Channel Advanced

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `garak` — install: `pip install garak`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in garak; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v garak >/dev/null 2>&1 || echo "  pip install garak"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Advanced hardware side-channel attacks covering power analysis (SPA/DPA), electromagnetic emanation, timing attacks, cache-timing attacks (Spectre/Meltdown variants), glitching (voltage/clock), optical fault injection, and countermeasure evaluation.

**Tools**: garak, PyRIT, promptfoo, custom harnesses

**Domain**: hardware

**MITRE**: T1041-Physical Attacks; emerging hardware-specific

## Core Tools

| **ChipWhisperer** | Power analysis / glitching | `chipwhisperer-capture` |
| **glitchcat** | Glitching framework | Various hardware |
| **sgax** | SGX attack framework | SGX side-channel |
| **Inspector** | SCA tool (Riscure) | Commercial |
| **Picoscope** | Oscilloscope for power analysis | Hardw

## Methodology Overview

### Attack Chain

```
[1] Reconnaissance        [2] Side-channel Setup     [3] Trace Acquisition
  - Identify chip            - Power measurement       - 10K-1M traces
  - Clock frequency            - EM probe placement      - Triggered on crypto op
  - Power supply             - Glitch injection            |
  - Physical access            |                          v
        |                    

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-hardware-side-channel-advanced/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
