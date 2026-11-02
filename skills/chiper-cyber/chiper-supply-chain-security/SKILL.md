---
name: chiper-supply-chain-security
description: "Use when Software supply chain security covering the entire lifecycle from code development to deployment: dependency vulnerabilities (known-vulnerable third-party pa"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, supply, chain]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-supply-chain-security/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-supply-chain-security/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-supply-chain-security/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-supply-chain-security/guides
---

# Supply Chain Security

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

Supply Chain Security skill domain covering supply chain operations.

**Tools**: Trivy, Snyk, Dependabot, OWASP Dependency-Check, npm audit, Safety / pip-audit

**Domain**: supply-chain

**OWASP**: A08:2021-Software Integrity

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **Trivy** | Comprehensive container/filesystem/Git repository vulnerability scanning with SBOM generation | `trivy fs --severity HIGH,CRITICAL ./project` |
| **Snyk** | SaaS dependency vulnerability scanning with remediation

## Methodology Overview

### Attack Chain

```
[1] Dependency Analysis   [2] Vulnerability Mapping  [3] Malicious Package Detection
  - Direct/transitive       - CVE database matching     - Typosquatting identification
    dependency enumeration  - CVSS score assessment     - post-install script auditing
  - Version range           - Exploit feasibility       - Anomalous network request
    identification            analy

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-supply-chain-security/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
