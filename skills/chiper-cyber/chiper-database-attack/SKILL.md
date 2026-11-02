---
name: chiper-database-attack
description: "Use when Direct attacks against database servers at the protocol level — distinct from web-based SQL injection (covered by web-sqli). This skill targets database listeners,"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, database, attack]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-database-attack/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-database-attack/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-database-attack/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-database-attack/guides
---

# Database Attack

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `hydra` — install: `sudo apt install -y hydra`
- `ncrack` — install: `sudo apt install -y ncrack`
- `patator` — install: `sudo apt install -y patator`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in hydra ncrack patator; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v hydra >/dev/null 2>&1 || echo "  sudo apt install -y hydra"
  command -v ncrack >/dev/null 2>&1 || echo "  sudo apt install -y ncrack"
  command -v patator >/dev/null 2>&1 || echo "  sudo apt install -y patator"
else
  echo "✅ All tools installed"
fi
```

## When to Use

This skill targets database listeners, authentication mechanisms, stored procedures, and protocol-level misconfigurations.

**Tools**: odat, oscanner, sqsh, redis-tools, mongoaudit, patator, ncrack, hydra

**Domain**: database

**MITRE ATT&CK**: TA0006-Credential Access

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **odat** | Oracle database attack toolkit — SID guessing, credential brute-force, file read/write, OS command exec | `odat all -s 192.168.1.100 -d ORCL` |
| **oscanner** | Oracle TNS listener scanning and enumeration | `osca

## Methodology Overview

### Attack Chain

```
Recon & Discovery → Service Enumeration → Authentication Testing → Exploitation → Post-Exploitation
   (nmap/oscanner)    (odat/SID guess)     (hydra/ncrack/patator)   (odat/sqsh)     (xp_cmdshell/file ops)
```

**Phase 1: Recon and Discovery**

- Port scan common database ports: Oracle (1521), MySQL (3306), PostgreSQL (5432), MSSQL (1433), Redis (6379), MongoDB (27017)
- Ide

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-database-attack/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
