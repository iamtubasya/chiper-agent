---
name: chiper-quantum-cryptography-transition
description: "Use when Post-Quantum Cryptography (PQC) transition security covering NIST standards (ML-KEM, ML-DSA, SLH-DSA), hybrid TLS weaknesses, Quantum Key Distribut"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, quantum, cryptography, transition]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-quantum-cryptography-transition/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-quantum-cryptography-transition/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-quantum-cryptography-transition/test-cases.md
---

# Quantum Cryptography Transition

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `garak` — install: `pip install garak`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in garak; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v garak >/dev/null 2>&1 || echo "  pip install garak"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Post-Quantum Cryptography (PQC) transition security covering NIST standards (ML-KEM, ML-DSA, SLH-DSA), hybrid TLS weaknesses, Quantum Key Distribution (QKD) attacks, HNDL (Harvest Now, Decrypt Later), and migration vulnerability windows.

**Tools**: garak, PyRIT, promptfoo, custom harnesses

**Domain**: crypto

**MITRE**: TA0048-Crypto Attack; emerging quantum-specific

## Core Tools

| **OQS (Open Quantum Safe)** | PQC library + OpenSSL provider | `openssl3 -provider oqsprovider` |
| **liboqs** | PQC algorithm C library | Link in custom apps |
| **PQClean** | Reference PQC implementations | Testing reference |
| **Cloudflare PQC test** | Public PQC TLS endpoint | `curl --pqc htt

## Methodology Overview

### Attack Chain

```
[1] Reconnaissance        [2] HNDL Capture          [3] PQC Migration Audit
  - TLS version             - Record encrypted traffic  - Hybrid combiner check
  - Algorithm negotiation     - Long-lived secrets       - Side-channel potential
  - PQC support               - Asymmetric sessions        |
  - QKD infrastructure          |                          v
        |         

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-quantum-cryptography-transition/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
