---
name: chiper-ai-fuzzing
description: "Use when AI-assisted fuzzing for automated vulnerability discovery. Coverage-guided fuzzing engines, AI-driven seed generation, intelligent mutation strategies, and systematic c"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, fuzzing]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-ai-fuzzing/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-ai-fuzzing/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-ai-fuzzing/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-ai-fuzzing/guides
---

# Ai Fuzzing

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `boofuzz` — install: `pip install boofuzz`
- `radare2` — install: `sudo apt install -y radare2`
- `wfuzz` — install: `sudo apt install -y wfuzz`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in boofuzz radare2 wfuzz; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v boofuzz >/dev/null 2>&1 || echo "  pip install boofuzz"
  command -v radare2 >/dev/null 2>&1 || echo "  sudo apt install -y radare2"
  command -v wfuzz >/dev/null 2>&1 || echo "  sudo apt install -y wfuzz"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Coverage-guided fuzzing engines, AI-driven seed generation, intelligent mutation strategies, and systematic crash triage.

**Tools**: AFL++, libFuzzer, Honggfuzz, radare2, BooFuzz, wfuzz

**Domain**: ai

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **AFL++** | Advanced coverage-guided fuzzer, fork of AFL with enhanced instrumentation | `afl-fuzz -i seeds/ -o output/ -m none -- ./target @@` |
| **libFuzzer** | LLVM/Clang built-in fuzzer, in-process coverage-guided fuzzi

## Methodology Overview

### Attack Chain

```
  Phase 1              Phase 2              Phase 3
 Target Analysis    Corpus Preparation    Fuzzing Execution
 ┌────────────┐     ┌──────────────┐     ┌──────────────┐
 │ Binary ID  │     │ Seed         │     │ AFL++ /      │
 │ Attack     │────>│ Creation &   │────>│ libFuzzer /  │
 │ Surface    │     │ Minimization │     │ Honggfuzz    │
 │ Map        │     │ Quality     

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-ai-fuzzing/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
