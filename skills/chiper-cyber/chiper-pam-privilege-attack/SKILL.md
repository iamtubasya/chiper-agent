---
name: chiper-pam-privilege-attack
description: "Use when Privileged Access Management (PAM) vendor abuse — CyberArk PVWA/PSM/EPV/AIM/CFE, BeyondTrust PRA/Password Safe/Identity Security Insights, Delinea Secret Serv"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, pam, privilege, attack]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-pam-privilege-attack/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-pam-privilege-attack/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-pam-privilege-attack/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-pam-privilege-attack/guides
---

# Pam Privilege Attack

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `curl` — `sudo apt install -y curl`
- `nmap` — `sudo apt install -y nmap`
- `nuclei` — `go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in curl nmap nuclei; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v curl >/dev/null 2>&1 || sudo apt install -y curl
command -v nmap >/dev/null 2>&1 || sudo apt install -y nmap
command -v nuclei >/dev/null 2>&1 || go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
```

## When to Use

PAM Privilege Attack skill domain covering vendor-specific compromise of Privileged Access Management platforms. PAM systems (CyberArk, BeyondTrust, Delinea, One Identity, ManageEngine, WALLIX, Devolutions, Xton) sit at the very top of the enterprise trust stack — they hold the credentials for root, Domain Admin, cloud root, database SA, and network device enable accounts. Compromising the PAM is equivalent to compromising every privileged asset the PAM manages. Recent ransomware operators (BlackCat/ALPHV, LockBit, Royal/BlackSuit) explicitly target PAM infrastructure as the first step in thei

## Core Tools

### Cross-Vendor Tools

| Tool | Category | Purpose |
|------|----------|---------|
| `curl` / `httpie` / `python-requests` | HTTP/HTTPS Recon & API | Universal vendor HTTP API probing |
| `websocat` / `python-websockets` | WebSocket Recon | CyberArk WebSocket safe enumeration |
| `nmap` / `nuclei` 

## Methodology Overview

### Phase 1: PAM Presence Reconnaissance

Identify which PAM product(s) the target runs before attempting vendor-specific attacks.

1. Identify web-facing PAM consoles via URL patterns (`/PasswordVault/` → CyberArk, `/SecretServer/` → Delinea, `/login.aspx` + BeyondTrust cookies → PRA, `/api/json/...` → ManageEngine PMP, `/sps/` → One Identity Safeguard, `/wab/` → WALLIX)
2. Fingerprint via TLS ce

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-pam-privilege-attack/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
