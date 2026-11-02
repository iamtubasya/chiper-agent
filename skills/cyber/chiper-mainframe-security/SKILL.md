---
name: chiper-mainframe-security
description: "Use when IBM z/OS, RACF (Resource Access Control Facility), CICS, DB2, JES2, TSO/ISPF penetration testing; APF library abuse, dataset access control, SNA/Appc attacks, a"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, mainframe]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-mainframe-security/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-mainframe-security/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-mainframe-security/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-mainframe-security/guides
---

# Mainframe Security

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `nmap` — `sudo apt install -y nmap`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in nmap; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v nmap >/dev/null 2>&1 || sudo apt install -y nmap
```

## When to Use

Mainframe security covers authorized penetration testing of IBM z/OS, z/VM, and z/VSE systems that still run the core transaction workloads for the global banking, insurance, airline, retail, and government sectors. Despite the "legacy" label, mainframes process the majority of the world's credit card transactions, social security records, and stock trades. A single compromised RACF user ID or APF-authorized library can expose millions of account records, defeat separation of duties, and enable persistent privileged access that survives normal patch cycles. This skill domain covers the special

## Core Tools

| Tool | Category | Purpose |
|------|----------|---------|
| mainframed/Enumeration | Enumeration | Open-source collection of REXX scripts and TSO commands for z/OS reconnaissance: user/group enumeration, APF list, dataset discovery, RACF info |
| SEAR (Mainframe-Renewal-Project) | API Testing | Se

## Methodology Overview

### Phase 1: TN3270 Recon and Session Acquisition

Reach the mainframe's interactive surface and obtain an initial TSO session.

1. Identify TN3270 listeners (`nmap -p 23,992,1027 --script=tn3270-info`); record the VTAM applid and any banner text.
2. Connect with `x3270 host:port`, negotiate TN3270E, and capture logon screens (TSO, CICS, IMS, NATURAL).
3. Probe default logon IDs against the TSO lo

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-mainframe-security/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
