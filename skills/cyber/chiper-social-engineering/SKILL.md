---
name: chiper-social-engineering
description: "Use when Social engineering is the art of exploiting human psychological weaknesses rather than technical vulnerabilities to execute attacks. Attack vectors encompass Ph"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, social, engineering]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-social-engineering/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-social-engineering/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-social-engineering/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-social-engineering/guides
---

# Social Engineering

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `gophish` — install: `echo "Download: https://github.com/gophish/gophish/releases"`
- `maltego` — install: `sudo apt install -y maltego`
- `recon-ng` — install: `sudo apt install -y recon-ng`
- `theharvester` — install: `sudo apt install -y theharvester`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in gophish maltego recon-ng theharvester; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v gophish >/dev/null 2>&1 || echo "  echo "Download: https://github.com/gophish/gophish/releases""
  command -v maltego >/dev/null 2>&1 || echo "  sudo apt install -y maltego"
  command -v recon-ng >/dev/null 2>&1 || echo "  sudo apt install -y recon-ng"
  command -v theharvester >/dev/null 2>&1 || echo "  sudo apt install -y theharvester"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Attack vectors encompass Phishing, Pretexting, Baiting, Tailgating, Vishing, and other techniques.

**Tools**: SET (setoolkit), GoPhish, King-Phisher, Maltego, theHarvester, recon-ng

**Domain**: social

**MITRE ATT&CK**: TA0043-Reconnaissance

## Core Tools

| Tool | Purpose | Command/Usage Example |
|------|---------|----------------------|
| **SET (setoolkit)** | Integrated social engineering attack framework, phishing/website cloning/payloads | `sudo setoolkit` -> select attack vector |
| **GoPhish** | Web-managed phishing campaign platform | Dashboa

## Methodology Overview

### Attack Chain

```
Target              Pretext             Attack Vector       Delivery            Harvest &
Reconnaissance  ->  Development     ->  Selection       ->  Execution       ->  Analysis
(OSINT Profiling)   (Pretext Dev)       (Vector Select)     (Delivery)          (Harvest)
    |                   |                  |                  |                   |
    v                   v

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-social-engineering/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
