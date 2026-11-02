---
name: chiper-kali-tools
description: "Use when Selecting Kali Linux tools. 518 tools inventory by category."
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [kali-linux, tools, nmap, sqlmap, metasploit, burpsuite, tool-inventory]
references:
  - path: /home/chiper/.Chiper/chiper-cyber/TOOLS.md
  - path: /home/chiper/.Chiper/chiper-cyber/KALI_TOOLS_BASELINE_2026_07.md
---

# Kali Linux Tool Inventory (518 Tools)

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `bettercap` — `sudo apt install -y bettercap`
- `dig` — `sudo apt install -y dnsutils`
- `dirb` — `sudo apt install -y dirb`
- `file` — `sudo apt install -y file`
- `gobuster` — `sudo apt install -y gobuster`
- `hydra` — `sudo apt install -y hydra`
- `metasploit` — `sudo apt install -y metasploit-framework`
- `msfconsole` — `sudo apt install -y metasploit-framework`
- `nmap` — `sudo apt install -y nmap`
- `radare2` — `sudo apt install -y radare2`
- `sqlmap` — `sudo apt install -y sqlmap`
- `sublist3r` — `pip install sublist3r`
- `theharvester` — `sudo apt install -y theharvester`
- `tshark` — `sudo apt install -y tshark`
- `whatweb` — `sudo apt install -y whatweb`
- `whois` — `sudo apt install -y whois`
- `wpscan` — `sudo apt install -y wpscan`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in bettercap dig dirb file gobuster hydra metasploit msfconsole nmap radare2 sqlmap sublist3r theharvester tshark whatweb whois wpscan; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v bettercap >/dev/null 2>&1 || sudo apt install -y bettercap
command -v dig >/dev/null 2>&1 || sudo apt install -y dnsutils
command -v dirb >/dev/null 2>&1 || sudo apt install -y dirb
command -v file >/dev/null 2>&1 || sudo apt install -y file
command -v gobuster >/dev/null 2>&1 || sudo apt install -y gobuster
command -v hydra >/dev/null 2>&1 || sudo apt install -y hydra
command -v metasploit >/dev/null 2>&1 || sudo apt install -y metasploit-framework
command -v msfconsole >/dev/null 2>&1 || sudo apt install -y metasploit-framework
command -v nmap >/dev/null 2>&1 || sudo apt install -y nmap
command -v radare2 >/dev/null 2>&1 || sudo apt install -y radare2
command -v sqlmap >/dev/null 2>&1 || sudo apt install -y sqlmap
command -v sublist3r >/dev/null 2>&1 || pip install sublist3r
command -v theharvester >/dev/null 2>&1 || sudo apt install -y theharvester
command -v tshark >/dev/null 2>&1 || sudo apt install -y tshark
command -v whatweb >/dev/null 2>&1 || sudo apt install -y whatweb
command -v whois >/dev/null 2>&1 || sudo apt install -y whois
command -v wpscan >/dev/null 2>&1 || sudo apt install -y wpscan
```

## When to Use

When selecting the right tool for a pentest task, checking tool availability, or reviewing mastery across 518 tools.

## Instructions

- **TOOLS.md** — Local environment config, mastered tools by category
- **KALI_TOOLS_BASELINE_2026_07.md** — Full 127-tool version baseline (July 2026)

## Tools Reference

# TOOLS.md - Local Tool Notes

Skills define _how_ tools work. This file records _your_ specific configuration and quick reference.

---

## Environment

- **OS**: Kali Linux 2025-2
- **Kernel**: 6.18.12+kali-arm64
- **Architecture**: aarch64 (ARM64)

---

## Core Tools (Mastered)

| Category | Tools | Status |
|----------|-------|--------|
| Reconnaissance | nmap, dig, whois, whatweb, wpscan, gobuster, theHarvester, sublist3r, assetfinder, dirb, zenmap | ✅ |
| Web Security | sqlmap, burpsuite, hydra | ✅ |
| Post-Exploitation | msfconsole (Metasploit) | ✅ |
| Binary Analysis | radare2 (Expert level) | ✅ |

---

## Category Index

> Full tool inventory (518 tools / 65 categories) see `docs/tools/full-inventory.md`

| Category | Tool Count | Status | Learning Notes |
|----------|------------|--------|----------------|
| recon-osint | 28 | Mastered | memory/photon.md, memory/dirb.md, etc. |
| osint | 12 | Mastered | skills/osint/SKILL.md |
| web-xss | 8 | Mastered | skills/web-xss/guides/ |
| web-sqli | 6 | Mastered | skills/web-sqli/guides/ |
| web-ssrf | 5 | Mastered | skills/web-ssrf/SKILL.md |
| web-auth-bypass | 6 | Mastered | skills/web-auth-bypass/SKILL.md |
| web-access-control | 5 | Mastered | skills/web-access-control/SKILL.md |
| api-security | 7 | Mastered | skills/api-security/SKILL.md |
| network-pentest | 15 | Mastered | memory/tshark.md, memory/bettercap.md |
| post-exploitation | 11 | Mastered | memory/2026-03-21-post-exploitation-tools.md |
| password-attack | 10 | Mastered | memory/2026-03-21-password-attack-tools.md |
| wifi-pentest | 17 | Mastered | memory/wifi-cracking-course.md |
| binary-reverse | 4 | Expert-level | binary_analysis/ |
| cloud-security | 8 | Mastered | guides/cloud_security_complete_guide.md |
| container-security | 6 | Mastered | skills/container-security/SKILL.md |
| crypto-attacks | 5 | Mastered | skills/crypto-attacks/SKILL.md |
| digital-forensics | 7 | Mastered | skills/digital-forensics/SKILL.md |
| insecure-design | 3 | Mastered | skills/insecure-design/SKILL.md |
| logging-monitoring | 4 | Mastered | skills/logging-monitoring/SKILL.md |
| mobile-security | 6 | Mastered | guides/mobile_security_complete_guide.md |
| security-misconfiguration | 5 | Mastered | skills/security-misconfiguration/SKILL.md |
| social-engineering | 4 | Mastered | memory/2026-03-21-social-engineering-tools.md |
| supply-chain-security | 5 | Mastered | skills/supply-chain-security/SKILL.md |
| vulnerability-assessment | 6 | Mastered | ski

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
