---
name: chiper-dns-attacks
description: "Use when DNS Attacks exploit the Domain Name System protocol for reconnaissance, spoofing, tunneling, and data exfiltration. DNS is a foundational infrastructure service that i"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, dns, attacks]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-dns-attacks/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-dns-attacks/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-dns-attacks/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-dns-attacks/guides
---

# Dns Attacks

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `dnsenum` — install: `sudo apt install -y dnsenum`
- `dnsrecon` — install: `sudo apt install -y dnsrecon`
- `fierce` — install: `sudo apt install -y fierce`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in dnsenum dnsrecon fierce; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v dnsenum >/dev/null 2>&1 || echo "  sudo apt install -y dnsenum"
  command -v dnsrecon >/dev/null 2>&1 || echo "  sudo apt install -y dnsrecon"
  command -v fierce >/dev/null 2>&1 || echo "  sudo apt install -y fierce"
else
  echo "✅ All tools installed"
fi
```

## When to Use

DNS is a foundational infrastructure service that is frequently misconfigured, poorly monitored, and trusted by default -- making it an ideal attack vector.

**Tools**: dnsrecon, dnsenum, fierce, dnschef, dns2tcp, dnscat2, dnswalk, iodine

**Domain**: network-attack

**MITRE ATT&CK**: TA0011-Command and Control

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **dnsrecon** | Comprehensive DNS enumeration: zone transfers, record enumeration, brute force, SRV discovery | `dnsrecon -d target.com -t axfr` |
| **dnsenum** | DNS enumeration with zone transfer, brute force, and Google en

## Methodology Overview

### Attack Chain

```
[1] Enumerate              [2] Fingerprint          [3] Exploit
  - Zone transfer (AXFR)     - Server version          - DNS spoofing (dnschef)
  - Record enumeration       - Recursion test          - Cache poisoning
  - Subdomain brute force    - DNSSEC validation       - DNS rebinding
  - Reverse lookups          - Configuration audit     - Response manipulation
       |   

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-dns-attacks/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
