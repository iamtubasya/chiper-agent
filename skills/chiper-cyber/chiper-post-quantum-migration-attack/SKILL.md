---
name: chiper-post-quantum-migration-attack
description: "Use when Attacks against cryptographic systems during the PQC migration period. Covers Harvest-Now-Decrypt-Later (SNDL/HNDL), hybrid PQC downgrade abuse, KEM"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, post, quantum, migration, attack]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-post-quantum-migration-attack/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-post-quantum-migration-attack/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-post-quantum-migration-attack/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-post-quantum-migration-attack/guides
---

# Post Quantum Migration Attack

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `cryptography` — `pip install cryptography`
- `testssl` — `sudo apt install -y testssl.sh`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in cryptography testssl; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v cryptography >/dev/null 2>&1 || pip install cryptography
command -v testssl >/dev/null 2>&1 || sudo apt install -y testssl.sh
```

## When to Use

Attackers target cryptographic systems during the multi-year window before quantum computers break RSA/ECC but after adversaries begin capturing long-lived ciphertext ("Harvest Now, Decrypt Later"). The migration to Post-Quantum Cryptography (PQC) introduces new attack surfaces: hybrid PQC downgrade abuse, KEM combiner flaws, signature stripping in mixed protocols, side-channels in lattice implementation (MatrixVector multiplication timing), and Classical/Post-Quantum (CPQ) certificate chain inconsistencies. This domain covers red-teaming PQC deployments, auditing migration agility, and exploi

## Core Tools

| Tool | Purpose |
|------|---------|
| `oqs-provider` | OpenSSL 3.x provider enabling ML-KEM/ML-DSA in TLS |
| `liboqs` | Reference C library for PQC algorithms |
| `oqs-openssl111` | OpenSSL 1.1.1 fork with PQC (legacy) |
| `testssl.sh` | TLS scanner with PQC cipher detection |
| `ssh-audit` | SSH

## Methodology Overview

### Phase 1 — Discovery & Inventory

Identify classical, hybrid, and PQ-only deployments. Map protocol → algorithm posture:

```bash
# TLS PQC cipher detection
testssl --wide --color 0 https://target.example.com | grep -iE "kyber|dilithium|pqc|x25519kyber|secp256r1kyber"

# SSH PQC kex detection
ssh-audit target.example.com | grep -iE "sntrup|pq|post-quantum"

# IPsec proposal audit (StrongSwan)
i

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-post-quantum-migration-attack/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
