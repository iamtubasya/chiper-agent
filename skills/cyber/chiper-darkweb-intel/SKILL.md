---
name: chiper-darkweb-intel
description: "Use when Dark web intelligence gathering — Tor/onion service reconnaissance, marketplace monitoring, breach data markets, threat actor profiling, with strict OPSEC for invest"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, darkweb, intel]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-darkweb-intel/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-darkweb-intel/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-darkweb-intel/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-darkweb-intel/guides
---

# Darkweb Intel

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `spiderfoot` — install: `sudo apt install -y spiderfoot`
- `tor` — install: `sudo apt install -y tor`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in spiderfoot tor; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v spiderfoot >/dev/null 2>&1 || echo "  sudo apt install -y spiderfoot"
  command -v tor >/dev/null 2>&1 || echo "  sudo apt install -y tor"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Darkweb Intel skill domain covering osint operations.

**Tools**: Tor, Tor Browser, Whonix, Tails, Ahmia, Torch, OnionScan, IntelX, HIBP, SpiderFoot

**Domain**: osint

**MITRE ATT&CK**: TA0043-Reconnaissance

## Core Tools

### Access & Proxies

| Tool | Purpose | Command / Setup Example |
|------|---------|-------------------------|
| **Tor** | Routing daemon (SOCKS5 on `127.0.0.1:9050`) | `sudo apt install tor && sudo service tor start` |
| **Tor Browser** | Hardened Firefox bundle for manual `.onion` browsing | Down

## Methodology Overview

### Dark Web Investigation Five-Phase Process

```
Phase 1              Phase 2              Phase 3              Phase 4              Phase 5
Access Setup     →   Discovery &       →  Marketplace &     →  Threat Actor       →  OPSEC-Hardened
                       Search               Forum Monitoring    Profiling              Synthesis
   │                    │                    │              

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-darkweb-intel/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
