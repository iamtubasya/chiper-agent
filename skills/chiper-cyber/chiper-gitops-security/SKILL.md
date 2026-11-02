---
name: chiper-gitops-security
description: "Use when Attacks against GitOps control planes (Argo CD, FluxCD, Jenkins X, Tekton, Fleet, Rancher) — repo impersonation, manifest tampering, RBAC bypass, sync-wave abuse,"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, gitops]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-gitops-security/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-gitops-security/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-gitops-security/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-gitops-security/guides
---

# Gitops Security

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `kubectl` — `sudo apt install -y kubectl`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in kubectl; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v kubectl >/dev/null 2>&1 || sudo apt install -y kubectl
```

## When to Use

GitOps (Argo CD, FluxCD, Jenkins X, Tekton, Fleet, Argo Rollouts, Flux Helm Controller, Argo Image Updater) is the dominant Kubernetes continuous-deployment pattern of 2024-2026. The control plane holds:

- **Cluster-admin equivalent RBAC** (it must, to deploy workloads)
- **Direct Git access** with deploy keys / PATs across hundreds of repos
- **Cluster-API credentials** to every production cluster it manages
- **Plaintext or recoverable secrets** (Sealed Secrets private keys, SOPS AGE/GPG private keys, External Secrets OAuth tokens, Vault tokens)

A single GitOps compromise typically yields 

## Core Tools

### GitOps Controllers (Targets)

| Tool | Vendor / Project | Role |
|------|------------------|------|
| **Argo CD** | CNCF Graduated | Pull-based GitOps, Application CRD, AppProject, ApplicationSet |
| **Argo Rollouts** | CNCF Incubating | Progressive delivery, AnalysisTemplate |
| **Argo Image Up

## Methodology Overview

### Phase 1 — Reconnaissance (External + Internal)

Identify the GitOps control plane, its version, RBAC model, and source-of-truth repos. From outside: fingerprint via `/api/v1/`, `/-/healthy`, default ports (2746 Argo, 9000-9090 Flux webhook). From inside a pod: enumerate CRDs (`kubectl api-resources`), find the controller namespace (`kube-system`, `argocd`, `flux-system`, `fleet-system`, `tekto

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-gitops-security/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
