---
name: chiper-ad-ldap-attack
description: "Use when Active Directory is the backbone of enterprise identity and access management, making it a primary target during internal network penetration tests."
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, ldap, attack]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-ad-ldap-attack/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-ad-ldap-attack/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-ad-ldap-attack/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-ad-ldap-attack/guides
---

# Ad Ldap Attack

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `impacket` — `pip install impacket`
- `nbtscan` — `sudo apt install -y nbtscan`
- `secretsdump` — `pip install impacket`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in impacket nbtscan secretsdump; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v impacket >/dev/null 2>&1 || pip install impacket
command -v nbtscan >/dev/null 2>&1 || sudo apt install -y nbtscan
command -v secretsdump >/dev/null 2>&1 || pip install impacket
```

## When to Use

Ad Ldap Attack skill domain covering enterprise operations.

**Domain**: enterprise

**MITRE ATT&CK**: TA0006-Credential Access

## Core Tools

| Tool | Category | Purpose |
|------|----------|---------|
| impacket-secretsdump.py | Credential Harvesting | Extract hashes from NTDS.dit, perform DCSync attacks, dump SAM/SYSTEM |
| impacket-psexec.py | Lateral Movement | Execute commands via SMB using Pass-the-Hash or credential authentication 

## Methodology Overview

### Phase 1: Reconnaissance

Discover live hosts, identify domain controllers, map network topology, and gather NetBIOS/DNS information about the target domain.

1. Scan the target network for live hosts and open ports (88/Kerberos, 389/LDAP, 445/SMB, 636/LDAPS, 135/RPC)
2. Use `nbtscan` for NetBIOS discovery to identify domain names and machine roles
3. Perform DNS enumeration to locate domain co

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-ad-ldap-attack/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
