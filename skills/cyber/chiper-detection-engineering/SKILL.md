---
name: chiper-detection-engineering
description: "Use when Detection-as-code engineering covering Sigma rule authoring, YARA signature development, Splunk SPL / Kusto KQL / Elastic EQL queries, MITRE ATT&CK mapping,"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, detection, engineering]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-detection-engineering/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-detection-engineering/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-detection-engineering/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-detection-engineering/guides
---

# Detection Engineering

## When to Use

Detection Engineering skill domain covering the craft of writing, testing, deploying, and retiring detection rules as code.

**Tools**: SigmaHQ + SigmaCLI, YARA + Yara-Rules, yarGen, Loki, hayabusa, zircollo, Splunk SPL, Microsoft Sentinel KQL, Elastic EQL/Lucene, MITRE ATT&CK, EVTX-ATTACK-SAMPLES, pySigma, sigma-scanner

**Domain**: defense

**MITRE ATT&CK**: TA0040-Detection (detection engineering discipline); rules in this skill provide coverage across every ATT&CK technique via the Sigma taxonomy.

## Core Tools

### Sigma Ecosystem

| Tool | Purpose | Command / Usage |
|------|---------|-----------------|
| **Sigma** | Vendor-neutral YAML signature format for log detection — the "YARA for logs." Author once, translate to any SIEM. | Author `.yml`; the YAML is the source of truth |
| **SigmaHQ/sigma** | The 

## Methodology Overview

### Detection Engineering Six-Phase Lifecycle

```
Phase 1            Phase 2            Phase 3            Phase 4            Phase 5            Phase 6
Threat Intel   →   Rule Draft      →  Unit Test      →  CI Validation   →  Staging Soak   →  Production &
& TTP Intake       Authoring          (pos + neg corpus)  (schema + tags +    (FP measurement)    Retirement
   │                  │        

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-detection-engineering/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
