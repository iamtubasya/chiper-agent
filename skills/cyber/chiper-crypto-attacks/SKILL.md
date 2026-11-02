---
name: chiper-crypto-attacks
description: "Use when Cryptographic Attacks target implementation flaws and algorithm weaknesses in encryption systems, covering OWASP A04: Cryptographic Failures."
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, crypto, attacks]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-crypto-attacks/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-crypto-attacks/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-crypto-attacks/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-crypto-attacks/guides
---

# Crypto Attacks

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `hashcat` — install: `sudo apt install -y hashcat`
- `sslscan` — install: `sudo apt install -y sslscan`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in hashcat sslscan; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v hashcat >/dev/null 2>&1 || echo "  sudo apt install -y hashcat"
  command -v sslscan >/dev/null 2>&1 || echo "  sudo apt install -y sslscan"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Crypto Attacks skill domain covering cryptography operations.

**Tools**: openssl, sslscan, testssl.sh, hashcat, CyberChef, padbuster, RsaCtfTool

**Domain**: cryptography

**OWASP**: A04:2021-Cryptographic Failures

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **openssl** | Certificate analysis, protocol testing, encryption/decryption operations | `openssl s_client -connect target:443 -tls1` |
| **sslscan** | Quick TLS configuration scan, detect supported protocols and cipher suit

## Methodology Overview

### Attack Chain

```
[1] Crypto ID            [2] Algorithm Analysis    [3] Key/IV Attacks
  - Protocol version       - Weak algorithm detect   - Hardcoded key search
  - Cipher suite enum      - Block size/mode detect  - IV predictability
  - Hash type ID           - Key length assessment   - Key reuse detection
  - Token format parse     - Padding mode analysis   - ECB mode detection
       |  

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-crypto-attacks/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
