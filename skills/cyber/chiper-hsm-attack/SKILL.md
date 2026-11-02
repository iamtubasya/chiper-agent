---
name: chiper-hsm-attack
description: "Use when Hardware Security Module attacks — physical (side-channel, fault injection, decapping) and logical (PKCS#11 API abuse, key extraction, M-of-N quorum bypass, RDP, firmwa"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, hsm, attack]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-hsm-attack/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-hsm-attack/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-hsm-attack/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-hsm-attack/guides
---

# Hsm Attack

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `nmap` — `sudo apt install -y nmap`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in nmap; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v nmap >/dev/null 2>&1 || sudo apt install -y nmap
```

## When to Use

Hardware Security Modules (HSMs) are dedicated cryptographic appliances that generate, store, and use keys without ever exposing them in plaintext outside the device. Common HSMs in 2024-2026:

- **Thales Luna (SafeNet) Network HSM 7 / 10** — dominant in enterprise PKI
- **Utimaco SecurityServer** — European gov / banking
- **Entrust nShield n3 / n5** — UK gov, finance, code signing
- **Yubico YubiHSM 2** — cloud-native dev / staging
- **AWS CloudHSM** — HSM-as-a-service
- **Azure Dedicated HSM** — Thales PayShield / Luna as-a-service
- **Google Cloud HSM** — FIPS 140-2 L3
- **Marvell / ATKey 

## Core Tools

### HSM Targets

| Vendor | Product | API | Notes |
|--------|---------|-----|-------|
| **Thales / SafeNet** | Luna Network HSM 7 / 10 | PKCS#11, NTLS, K5, JCE | Dominant enterprise PKI |
| **Thales / SafeNet** | PayShield 10K | Thales proprietary | Payment PIN translation |
| **Utimaco** | Securit

## Methodology Overview

### Phase 1 — Reconnaissance

Identify HSM vendor, model, firmware, and integration points.

```bash
# Network fingerprint
nmap -p 1792,4475,9004,443 hsm.example.com  # Thales / Utimaco / nShield / Cloud

# Luna Network HSM specific
nmap -sV -p 1792 --script=*,default hsm.example.com

# nShield Connect
nc hsm.example.com 9004
echo -ne "\x00\x00\x00\x01" | nc -w 2 hsm.example.com 9004 | xxd

# AWS 

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-hsm-attack/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
