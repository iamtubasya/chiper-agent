---
name: chiper-reverse-engineering-advanced
description: "Use when Advanced reverse engineering covering symbolic execution (angr, KLEE, manticore), decompiler confusion (Hex-Rays, Ghidra deobfuscation), binary diffin"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, reverse, engineering, advanced]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-reverse-engineering-advanced/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-reverse-engineering-advanced/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-reverse-engineering-advanced/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-reverse-engineering-advanced/guides
---

# Reverse Engineering Advanced

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `angr` — `pip install angr`
- `binwalk` — `sudo apt install -y binwalk`
- `file` — `sudo apt install -y file`
- `ghidra` — `sudo apt install -y ghidra`
- `readelf` — `sudo apt install -y binutils`
- `strings` — `sudo apt install -y binutils`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in angr binwalk file ghidra readelf strings; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v angr >/dev/null 2>&1 || pip install angr
command -v binwalk >/dev/null 2>&1 || sudo apt install -y binwalk
command -v file >/dev/null 2>&1 || sudo apt install -y file
command -v ghidra >/dev/null 2>&1 || sudo apt install -y ghidra
command -v readelf >/dev/null 2>&1 || sudo apt install -y binutils
command -v strings >/dev/null 2>&1 || sudo apt install -y binutils
```

## When to Use

Advanced reverse engineering is the discipline of analyzing obfuscated, packed, or firmware binaries using automated program analysis: symbolic execution (angr, KLEE, manticore) for path exploration, decompiler confusion techniques (Hex-Rays deobfuscation, Ghidra script automation), binary diffing (BinDiff, Diaphora, Kam1n0) for variant analysis, firmware RE workflow (binwalk, FACT, EMBA) for embedded device analysis, and obfuscated code analysis (LLVM obfuscation, OLLVM, Tigress). This domain covers modern program-analysis techniques that scale beyond manual reverse engineering, with industry

## Core Tools

| Tool | Purpose |
|------|---------|
| `angr` | Python symbolic execution framework |
| `KLEE` | LLVM-based symbolic execution |
| `manticore` | Symbolic execution (Trail of Bits) |
| `Ghidra` | NSA open-source RE tool |
| `IDA Pro` | Industry-standard disassembler + decompiler |
| `Binary Ninja` |

## Methodology Overview

### Phase 1 — Static triage

```bash
file binary
sha256sum binary
strings binary | head -20

# Architecture
file binary

# Imported functions
nm -D binary 2>/dev/null | head
readelf -d binary 2>/dev/null | head

# Section entropy (packed indicator)
python3 -c "
import sys
with open('binary', 'rb') as f:
    data = f.read()
import math
entropy = -sum((data.count(b)/len(data)) * math.log2(data.count

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-reverse-engineering-advanced/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
