---
name: chiper-binary-reverse
description: "Use when Binary reverse engineering covers the complete chain from static analysis, dynamic debugging, to vulnerability discovery, exploit development, and malware analysis."
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, binary, reverse]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-binary-reverse/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-binary-reverse/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-binary-reverse/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-binary-reverse/guides
---

# Binary Reverse

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `binwalk` — install: `sudo apt install -y binwalk`
- `checksec` — install: `sudo apt install -y checksec`
- `gdb` — install: `sudo apt install -y gdb`
- `ghidra` — install: `sudo apt install -y ghidra`
- `objdump` — install: `sudo apt install -y binutils`
- `radare2` — install: `sudo apt install -y radare2`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in binwalk checksec gdb ghidra objdump radare2; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v binwalk >/dev/null 2>&1 || echo "  sudo apt install -y binwalk"
  command -v checksec >/dev/null 2>&1 || echo "  sudo apt install -y checksec"
  command -v gdb >/dev/null 2>&1 || echo "  sudo apt install -y gdb"
  command -v ghidra >/dev/null 2>&1 || echo "  sudo apt install -y ghidra"
  command -v objdump >/dev/null 2>&1 || echo "  sudo apt install -y binutils"
  command -v radare2 >/dev/null 2>&1 || echo "  sudo apt install -y radare2"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Binary Reverse skill domain covering binary analysis operations.

**Tools**: radare2, ghidra, objdump, gdb, checksec, ROPgadget, binwalk, readelf (+2 more)

**Domain**: binary-analysis

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **radare2** | Full-featured reverse engineering framework, static/dynamic analysis, script automation | `r2 -A binary && afl \|\| pdf @ main` |
| **ghidra** | NSA open-source reverse engineering platform, decompiler, GUI, he

## Methodology Overview

### Attack Chain

```
Binary ID           Static Analysis       Dynamic Analysis     Vulnerability Discovery
(file, checksec)  (r2 -A, objdump)     (gdb, r2 -d)        (pattern, fuzz)
     |                 |                 |               |
     v                 v                 v               v
Security Assessment  Exploit Dev         Shellcode          Report & Fix
(ASLR, Canary,     (ROP c

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-binary-reverse/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
