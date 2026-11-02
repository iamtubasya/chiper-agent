---
name: chiper-macos-security
description: "Use when MacOS red team and security assessment — SIP/TCC bypass, Endpoint Security framework, Apple Silicon/T2/M-series attacks, Mach-O analysis, Keychain extraction, MDM b"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, macos]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-macos-security/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-macos-security/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-macos-security/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-macos-security/guides
---

# Macos Security

## When to Use

macOS security assessment skill covering Apple's desktop/laptop platform from a red team and malware analyst perspective. This skill addresses the modern macOS attack surface: System Integrity Protection (SIP/rootless), Transparency Consent and Control (TCC), Endpoint Security framework (ESF), Apple Silicon (M1/M2/M3/M4 with arm64e and Pointer Authentication Codes), T2 chip on Intel Macs, code signing + notarization enforcement, LaunchAgents/LaunchDaemons persistence, Keychain credential stores, MDM profile abuse, and Mach-O binary analysis.

**Tools**: Objective-See suite (KnockKnock, LuLu, B

## Core Tools

### Objective-See Suite (free, open-source, the de facto standard)

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **KnockKnock** | Enumerate ~50 macOS persistence locations (LaunchAgents, LaunchDaemons, login items, browser extensions, Spotlight importers, kernel extens

## Methodology Overview

### macOS Red Team Five-Phase Workflow

```
Phase 1          Phase 2          Phase 3          Phase 4          Phase 5
Recon &       →  Privilege &   →  Persistence   →  Credential     →  Defense Bypass
Footold          TCC Posture      (LaunchAgents)    Extraction       & ESF Audit
   │                │                │                │                │
   ▼                ▼                ▼    

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-macos-security/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
