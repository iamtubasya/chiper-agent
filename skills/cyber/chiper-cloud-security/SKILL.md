---
name: chiper-cloud-security
description: "Use when Cloud security covers security assessment for major cloud platforms including AWS, Azure, and GCP, with core focus on IAM misconfiguration detection, storage bucket"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, cloud]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-cloud-security/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-cloud-security/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-cloud-security/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-cloud-security/guides
---

# Cloud Security

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

Cloud Security skill domain covering cloud operations.

**Tools**: pacu, scoutsuite, awscli, s3scanner, kubeaudit, trivy

**Domain**: cloud

**MITRE ATT&CK**: TA0008-Lateral Movement

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **pacu** | AWS penetration testing framework, modular IAM enumeration and exploitation | `pacu -> run iam__enum_users` |
| **scoutsuite** | Multi-cloud security audit, generates compliance reports | `scout aws -p default` |


## Methodology Overview

### Attack Chain

```
Cloud Asset Discovery -> IAM Enumeration -> Storage Bucket Exposure -> Network Misconfig
(awscli, cloud enum)     (pacu, iam__enum)   (s3scanner, awscli)       (scoutsuite, nmap)
      |                      |                      |                      |
      v                      v                      v                      v
Metadata Attack       Container Security     

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-cloud-security/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
