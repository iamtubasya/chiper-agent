---
name: chiper-osint
description: "Use when A specialized skill for intelligence gathering using publicly available sources."
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, osint]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-osint/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-osint/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-osint/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-osint/guides
---

# Osint

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `dig` — `sudo apt install -y dnsutils`
- `recon-ng` — `sudo apt install -y recon-ng`
- `spiderfoot` — `sudo apt install -y spiderfoot`
- `subfinder` — `go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest`
- `theharvester` — `sudo apt install -y theharvester`
- `whois` — `sudo apt install -y whois`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in dig recon-ng spiderfoot subfinder theharvester whois; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v dig >/dev/null 2>&1 || sudo apt install -y dnsutils
command -v recon-ng >/dev/null 2>&1 || sudo apt install -y recon-ng
command -v spiderfoot >/dev/null 2>&1 || sudo apt install -y spiderfoot
command -v subfinder >/dev/null 2>&1 || go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
command -v theharvester >/dev/null 2>&1 || sudo apt install -y theharvester
command -v whois >/dev/null 2>&1 || sudo apt install -y whois
```

## When to Use

Osint skill domain covering osint operations.

**Domain**: osint

**MITRE ATT&CK**: TA0043-Reconnaissance

## Core Tools

### Comprehensive Frameworks

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| SpiderFoot | Automated OSINT collection (200+ modules) | `spiderfoot -s target -t ALL -u passive` |
| Recon-ng | Modular web reconnaissance framework | `recon-ng > use recon/domains-hosts/brute_

## Methodology Overview

### OSINT Five-Phase Process

**Phase 1: Passive Collection**

No direct interaction with the target; use only public data sources.

```bash
# WHOIS domain registration information
whois example.com

# DNS record collection
dig any example.com @8.8.8.8
subfinder -d example.com -o subdomains.txt
dnsx -d example.com -a -silent

# Certificate Transparency query
theHarvester -d example.com -b crtsh

#

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-osint/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
