---
name: chiper-secret-management-attack
description: "Use when Secret discovery, SAST code audit, and secrets-management platform attack covering gitleaks, semgrep, trufflehog, infisical, bearer, DeepAudit, apkleaks,"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, secret, management, attack]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-secret-management-attack/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-secret-management-attack/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-secret-management-attack/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-secret-management-attack/guides
---

# Secret Management Attack

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `trivy` — install: `sudo apt install -y trivy`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in trivy; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v trivy >/dev/null 2>&1 || echo "  sudo apt install -y trivy"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Secret Management Attack skill domain covering secrets discovery, SAST (Static Application Security Testing) code audit, and secrets-management platform exploitation.

**Tools**: gitleaks, trufflehog, semgrep, bearer, DeepAudit, apkleaks, cariddi, dive, trivy, grype, HashiCorp Vault CLI, Infisical CLI, AWS Secrets Manager SDK, kubectl (+4)

**Domain**: appsec

**MITRE ATT&CK**: T1552-Unsecured Credentials, T1552.001-Credentials In Files, T1552.004-Private Keys, T1552.007-Container and Cloud

## Core Tools

### Secret Scanners

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **gitleaks** (27k★) | Git history + filesystem secret detection with 100+ built-in rules | `gitleaks detect --source . --report-path leaks.json` |
| **trufflehog** | Deep secret scanning with live verifi

## Methodology Overview

### Secret Attack Six-Phase Process

```
Phase 1            Phase 2            Phase 3            Phase 4            Phase 5            Phase 6
Scope &            Breadth            Triage &           Platform           Lateral            Report &
Inventory      →   Scan          →   Verify        →    Exploit       →    Pivot         →    Rotated-Keys Map
   │                  │                  

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-secret-management-attack/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
