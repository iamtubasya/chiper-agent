---
name: chiper-recon-osint
description: "Use when The most critical first step in penetration testing. Information gathering determines the precision and efficiency of subsequent attacks."
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, recon, osint]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-recon-osint/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-recon-osint/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-recon-osint/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-recon-osint/guides
---

# Recon Osint

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `dig` — `sudo apt install -y dnsutils`
- `nmap` — `sudo apt install -y nmap`
- `theharvester` — `sudo apt install -y theharvester`
- `whois` — `sudo apt install -y whois`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in dig nmap theharvester whois; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v dig >/dev/null 2>&1 || sudo apt install -y dnsutils
command -v nmap >/dev/null 2>&1 || sudo apt install -y nmap
command -v theharvester >/dev/null 2>&1 || sudo apt install -y theharvester
command -v whois >/dev/null 2>&1 || sudo apt install -y whois
```

## When to Use

Information gathering determines the precision and efficiency of subsequent attacks.

**Domain**: osint

**MITRE ATT&CK**: TA0043-Reconnaissance

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| nmap | Port scanning and service identification | `nmap -sV -sC -O -p- target` |
| dig / whois | DNS enumeration and domain information lookup | `dig any example.com @8.8.8.8` |
| theHarvester | Email, subdomain, and IP coll

## Methodology Overview

### Attack Chain

**Step 1: Passive Recon**

No direct interaction with the target, minimizing exposure risk. Collect domain registration information, DNS records, search engine caches, and social media data.

**Step 2: Subdomain and Asset Discovery**

Enumerate all subdomains and associated assets to expand the attack surface. Cross-validate with multiple tools to avoid missing targets.

**Step 3

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-recon-osint/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
