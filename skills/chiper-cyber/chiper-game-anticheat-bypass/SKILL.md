---
name: chiper-game-anticheat-bypass
description: "Use when Security research on game anti-cheat systems (EAC/BattlEye/Vanguard/Ricochet) — kernel-mode driver architecture, BYOVD attacks, memory access interception, i"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, game, anticheat, bypass]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-game-anticheat-bypass/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-game-anticheat-bypass/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-game-anticheat-bypass/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-game-anticheat-bypass/guides
---

# Game Anticheat Bypass

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `ghidra` — `sudo apt install -y ghidra`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in ghidra; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v ghidra >/dev/null 2>&1 || sudo apt install -y ghidra
```

## When to Use

Game anti-cheat bypass, positioned strictly as **security research and anti-cheat developer education**, covers the architecture of modern commercial anti-cheat systems (Easy Anti-Cheat, BattlEye, Riot Vanguard, Activision Ricochet, FACEIT AC), the kernel-mode driver model they rely on, and the offensive techniques studied in academic and red-team contexts to defeat them. The domain emphasizes understanding how detection works (signature, integrity, telemetry, behavioral) so defenders can harden their products and so researchers can responsibly disclose flaws through coordinated disclosure.

T

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **WinDbg** | Kernel-mode debugging of anti-cheat drivers and live memory inspection | `!process 0 0` / `lm` / `!devobj` / `bp nt!MmCopyVirtualMemory` |
| **Cheat Engine** | Memory scanning (value, pointer, signature), struct

## Methodology Overview

### Research Pipeline

```
[1] Recon                 [2] Driver Analysis       [3] Memory Pattern Mapping
  - Enumerate services     - Load driver in IDA       - Identify protected
    (sc query)               / Ghidra / WinDbg           processes & handles
  - List loaded drivers    - Identify DriverEntry      - Trace ObRegisterCallbacks
    (lm, driverquery)        and IRP handlers            - 

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-game-anticheat-bypass/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
