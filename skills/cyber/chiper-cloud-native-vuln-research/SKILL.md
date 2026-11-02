---
name: chiper-cloud-native-vuln-research
description: "Use when CVE research methodology, PoC reproduction, patch gap analysis, and exploit chain composition across container/k8s/cloud-native surfaces; SBOM-driven vu"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, cloud, native, vuln, research]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-cloud-native-vuln-research/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-cloud-native-vuln-research/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-cloud-native-vuln-research/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-cloud-native-vuln-research/guides
---

# Cloud Native Vuln Research

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `nuclei` — `go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in nuclei; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v nuclei >/dev/null 2>&1 || go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
```

## When to Use

Cloud-native vulnerability research skill domain covering the full CVE lifecycle: triage of newly disclosed vulnerabilities against container/k8s/cloud surfaces, lab reproduction of PoCs, patch diff analysis to understand root cause and detect patches in the field, nuclei template authoring and contribution to projectdiscovery/nuclei-templates, SBOM-driven vulnerability management, and composition of exploit chains that link multiple CVEs into a single end-to-end compromise narrative. This is a methodology-and-research skill, not an assessment or defense skill — it operates forward-looking (ne

## Core Tools

### Detection & Template Authoring

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **nuclei** (projectdiscovery) | Template-based vulnerability scanner — runs YAML templates against targets | `nuclei -u https://target -t cves/2026/ -severity critical,high` |
| **nuclei-t

## Methodology Overview

### Five-Phase CVE Research Workflow

```
Phase 1            Phase 2            Phase 3            Phase 4            Phase 5
Triage & Scoring   → Lab Environment → PoC Reproduction → Patch Diff       → Exploit Chain
   │                  │                  │                  │                  │
   ▼                  ▼                  ▼                  ▼                  ▼
 NVD + KEV + EPSS,   

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-cloud-native-vuln-research/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
