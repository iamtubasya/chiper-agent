---
name: chiper-steganography
description: "Use when Steganography is the practice of concealing data within non-secret carrier files such as images, audio, video, and documents. Unlike encryption, which makes data unr"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, steganography]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-steganography/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-steganography/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-steganography/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-steganography/guides
---

# Steganography

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `binwalk` — install: `sudo apt install -y binwalk`
- `exiftool` — install: `sudo apt install -y exiftool`
- `foremost` — install: `sudo apt install -y foremost`
- `steghide` — install: `sudo apt install -y steghide`
- `zsteg` — install: `gem install zsteg`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in binwalk exiftool foremost steghide zsteg; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v binwalk >/dev/null 2>&1 || echo "  sudo apt install -y binwalk"
  command -v exiftool >/dev/null 2>&1 || echo "  sudo apt install -y exiftool"
  command -v foremost >/dev/null 2>&1 || echo "  sudo apt install -y foremost"
  command -v steghide >/dev/null 2>&1 || echo "  sudo apt install -y steghide"
  command -v zsteg >/dev/null 2>&1 || echo "  gem install zsteg"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Unlike encryption, which makes data unreadable but visibly present, steganography hides the very existence of the hidden data.

**Tools**: steghide, stegcracker, zsteg, binwalk, foremost, exiftool

**Domain**: forensics

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **steghide** | Embed and extract data in JPEG, BMP, WAV, and AU files with passphrase support | `steghide extract -sf carrier.jpg -p password` |
| **stegcracker** | Brute-force steghide passphrases using wordlists | `stegcra

## Methodology Overview

### Analysis Chain

```
[1] Identify              [2] Analyze             [3] Detect
  - Carrier format          - File metadata          - Format-specific stego
    (JPEG/PNG/BMP/          - Size anomalies          detection
     WAV/PDF)               - Entropy analysis      - steghide info / zsteg /
  - True file type          - Comment fields           binwalk signatures
    vs extension      

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-steganography/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
