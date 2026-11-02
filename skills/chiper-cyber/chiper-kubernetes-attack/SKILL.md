---
name: chiper-kubernetes-attack
description: "Use when Kubernetes cluster attack and red team covering RBAC abuse, pod escape (privileged pods, hostPath, capabilities, hostPID/hostIPC, container runtime sockets, kern"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, kubernetes, attack]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-kubernetes-attack/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-kubernetes-attack/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-kubernetes-attack/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-kubernetes-attack/guides
---

# Kubernetes Attack

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `kubectl` — install: `sudo apt install -y kubectl`
- `trivy` — install: `sudo apt install -y trivy`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in kubectl trivy; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v kubectl >/dev/null 2>&1 || echo "  sudo apt install -y kubectl"
  command -v trivy >/dev/null 2>&1 || echo "  sudo apt install -y trivy"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Kubernetes attack skill domain covering cluster reconnaissance, RBAC privilege escalation, pod-to-host escape, service account token theft, API server exploitation, etcd attacks, supply chain (image and admission controller), and cloud-managed K8s (EKS/GKE/AKS) IAM pivoting.

**Tools**: kubectl, CDK (Container penetration Toolkit), peirates, kube-hunter, kubescape, stratus-red-team, kubernetes-goat, kube-bench, kubeaudit, kubeletctl, dive, trivy, cosign, falco

**Domain**: cloud-native

**MITRE ATT&CK**: TA0008-Lateral Movement (containers), maps to MITRE ATT&CK for Containers matrix

## Core Tools

### Cluster Reconnaissance & Discovery

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **kubectl** | The universal cluster CLI — enumerate, create, exec, apply | `kubectl auth can-i --list --as=system:anonymous` |
| **kube-hunter** (Aqua) | Active hunter that fingerprint

## Methodology Overview

### K8s Red Team Six-Phase Workflow

```
Phase 1           Phase 2           Phase 3           Phase 4           Phase 5           Phase 6
Recon &          → API Discovery → RBAC Abuse     → Pod Escape     → Lateral +      → Persistence +
Foothold          + Auth Bypass     + Priv Esc       + Runtime Esc    Cloud IAM Pivot  Detection Evasion
   │                  │                  │              

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-kubernetes-attack/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
