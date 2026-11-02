---
name: chiper-password-attack
description: "Use when Password attacks encompass the complete attack chain from hash extraction, hash type identification, dictionary attacks, rule-based attacks, and bruteforcing to on"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, password, attack]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-password-attack/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-password-attack/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-password-attack/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-password-attack/guides
---

# Password Attack

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `cewl` — install: `sudo apt install -y cewl`
- `crunch` — install: `sudo apt install -y crunch`
- `hashcat` — install: `sudo apt install -y hashcat`
- `hydra` — install: `sudo apt install -y hydra`
- `john` — install: `sudo apt install -y john`
- `medusa` — install: `sudo apt install -y medusa`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in cewl crunch hashcat hydra john medusa; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v cewl >/dev/null 2>&1 || echo "  sudo apt install -y cewl"
  command -v crunch >/dev/null 2>&1 || echo "  sudo apt install -y crunch"
  command -v hashcat >/dev/null 2>&1 || echo "  sudo apt install -y hashcat"
  command -v hydra >/dev/null 2>&1 || echo "  sudo apt install -y hydra"
  command -v john >/dev/null 2>&1 || echo "  sudo apt install -y john"
  command -v medusa >/dev/null 2>&1 || echo "  sudo apt install -y medusa"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Password Attack skill domain covering credential access operations.

**Tools**: hashcat, john, hydra, medusa, cewl, crunch

**Domain**: credential-access

**MITRE ATT&CK**: TA0006-Credential Access

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **hashcat** | GPU-accelerated offline hash cracking, 300+ hash types | `hashcat -a 0 -m 1000 hashes.txt wordlist.txt` |
| **john** | Automatic hash detection, excels at single cracking and file passwords | `john --wordlist=r

## Methodology Overview

### Attack Chain

```
Hash Extraction     Hash Identification   Dictionary/Rule      Offline Cracking
(secretsdump,      (hash-iid,           Selection            (hashcat/john,
 /etc/shadow)       hashcat -I)          (rockyou/cewl/        rules/masks)
                                         crunch/mangling)         |                   |                  |                  |
       v            

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-password-attack/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
