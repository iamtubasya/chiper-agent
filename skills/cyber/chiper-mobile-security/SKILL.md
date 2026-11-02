---
name: chiper-mobile-security
description: "Use when Mobile security covers the complete attack/defense chain of Android/iOS application security testing, APK/IPA reverse engineering, runtime manipulation, certificat"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, mobile]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-mobile-security/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-mobile-security/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-mobile-security/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-mobile-security/guides
---

# Mobile Security

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `apktool` — install: `sudo apt install -y apktool`
- `drozer` — install: `pip install drozer`
- `frida` — install: `pip install frida-tools`
- `jadx` — install: `sudo apt install -y jadx`
- `objection` — install: `pip install objection`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in apktool drozer frida jadx objection; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v apktool >/dev/null 2>&1 || echo "  sudo apt install -y apktool"
  command -v drozer >/dev/null 2>&1 || echo "  pip install drozer"
  command -v frida >/dev/null 2>&1 || echo "  pip install frida-tools"
  command -v jadx >/dev/null 2>&1 || echo "  sudo apt install -y jadx"
  command -v objection >/dev/null 2>&1 || echo "  pip install objection"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Mobile Security skill domain covering mobile operations.

**Tools**: frida, objection, apktool, jadx, mobsf, drozer

**Domain**: mobile

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **frida** | Dynamic instrumentation framework, runtime hooks, function tracing, memory read/write | `frida -U -f com.target.app -l hook.js` |
| **objection** | Frida-based mobile runtime exploration toolkit | `objection -g c

## Methodology Overview

### Attack Chain

```
App Decompilation     Static Analysis       Dynamic Analysis     Runtime Manipulation
(apktool, jadx)     (Code audit, Manifest) (Proxy, traffic)   (Frida, objection)
      |                 |                 |                |
      v                 v                 v                v
Information          Vulnerability      Communication        Data Extraction
Collection  

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-mobile-security/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
