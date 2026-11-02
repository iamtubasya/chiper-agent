---
name: chiper-container-security
description: "Use when Container security covers the complete lifecycle from image building, registry management, runtime protection, to orchestration platform (Kubernetes) security."
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, container]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-container-security/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-container-security/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-container-security/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-container-security/guides
---

# Container Security

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

Container Security skill domain covering cloud operations.

**Tools**: trivy, docker-bench-security, kubeaudit, falco, clair, grype

**Domain**: cloud

**MITRE ATT&CK**: TA0008-Lateral Movement

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **trivy** | All-in-one image/filesystem/repository/K8s configuration scanner | `trivy image nginx:latest` |
| **docker-bench-security** | CIS Docker Benchmark automated checks | `docker-bench-security -c 1,2,3` |
| **kubeaud

## Methodology Overview

### Attack Chain

```
Image Analysis      Registry Security   Runtime Escape     Orchestration      Host Compromise
(trivy scan,      (Unauthenticated    (Privileged       Attack             (Post-escape
 CVE matching)     access, image       container,        (RBAC abuse,       privilege
                    tampering)         kernel vuln)      ServiceAccount)    escalation)
    |               | 

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-container-security/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
