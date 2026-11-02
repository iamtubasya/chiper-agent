---
name: chiper-quantum-crypto-attack
description: "Use when Post-quantum and modern national cryptography attack surface testing covering NIST PQC candidates (ML-KEM/ML-DSA/SLH-DSA), hybrid TLS analysis, QKD/BB84 prot"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, quantum, crypto, attack]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-quantum-crypto-attack/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-quantum-crypto-attack/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-quantum-crypto-attack/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-quantum-crypto-attack/guides
---

# Quantum Crypto Attack

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `cryptography` — `pip install cryptography`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in cryptography; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v cryptography >/dev/null 2>&1 || pip install cryptography
```

## When to Use

Post-quantum and modern national cryptography attack surface testing. This skill is **forward-looking and preparation-focused**: it does not assume a cryptographically relevant quantum computer (CRQC) exists today, but evaluates whether systems will survive the day one becomes available, and tests the implementation correctness of the post-quantum and national algorithms that defenders are racing to adopt.

**Tools**: liboqs, OQS-OpenSSL, GmSSL, cloudflare/circl, PQCrypto-Break, TNO Penguin, Qiskit (simulator), RsaCtfTool (ROCA), openssl s_client (TLS 1.3 groups), oqs-provider, sphincs-utils, 

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **liboqs** | Reference C library implementing all NIST PQC candidates; foundation for OQS-OpenSSL, oqs-provider | `git clone https://github.com/open-quantum-safe/liboqs && cmake -B build && cmake --build build` |
| **OQS-Ope

## Methodology Overview

### Attack Chain

```
[1] Quantum Exposure Inventory     [2] Shor/Grover Impact Modelling
  - RSA/ECC key discovery             - Per-key forgeability timeline
  - Key lifetime / purpose            - Symmetric key strength reduction
  - SNDL data-flow mapping            - Hash function collision horizon
  - CA / root / signing key map       - Stateful-sig state-reuse check
        |               

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-quantum-crypto-attack/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
