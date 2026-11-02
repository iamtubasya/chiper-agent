---
name: chiper-ci-cd-supply-chain-attack
description: "Use when CI/CD pipeline and software supply chain compromise covering Jenkins (script console, Jenkinsfile injection, shared library abuse, CVE-2024-23897 args4j)"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, supply, chain, attack]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-ci-cd-supply-chain-attack/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-ci-cd-supply-chain-attack/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-ci-cd-supply-chain-attack/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-ci-cd-supply-chain-attack/guides
---

# Ci Cd Supply Chain Attack

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `kubectl` — install: `sudo apt install -y kubectl`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in kubectl; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v kubectl >/dev/null 2>&1 || echo "  sudo apt install -y kubectl"
else
  echo "✅ All tools installed"
fi
```

## When to Use

CI/CD & Supply Chain Attack skill domain covering the build-and-deliver layer that ships code from developer laptops to production. This is where the modern breach lives: SolarWinds, Codecov, 3CX, xz-utils, CircleCI, tj-actions/changed-files all walked through the build system, not the application.

**Tools**: Jenkins CLI + script console, GitLab runner CLI, gh (GitHub Actions), circleci CLI, argocd CLI, flux CLI, kubectl, ko/syft (SBOM), cosign (Sigstore), in-toto, slsa-verifier, OpenSSF Scorecard, StepSecurity Harden-Runner, Socket CLI, Sonatype Nexus, Snyk CLI, Anchore Syft + Grype, KICS, C

## Core Tools

### CI/CD Platform CLIs

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **Jenkins CLI** | Job enumeration, script console, agent management | `java -jar jenkins-cli.jar -s http://jenkins/ groovysh` |
| **GitLab Runner CLI** | Runner registration, executor introspection |

## Methodology Overview

### CI/CD Supply Chain Attack Six-Phase Process

```
Phase 1            Phase 2            Phase 3            Phase 4            Phase 5            Phase 6
CI/CD Recon   →    Initial Access →   Pipeline           Lateral           Persistence    →   Detection &
& Inventory        via Workflow/      Compromise    →    Movement →             & Backdoor       Reporting
                   Runner/Dep  

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-ci-cd-supply-chain-attack/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
