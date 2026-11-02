---
name: chiper-cyber
description: >
  Chiper Cyber skill ecosystem — 144 security domains with 302 tools.
  Use this SKILL.md as entrypoint to install, place, and manage all chiper-* skills.
  Supports Kali Linux, Ubuntu, Debian, and other Linux distributions.
tags: [bootstrap, install, placement, skills, chiper, cybersecurity]
author: Chiper (Chiper-Cyber)
---

# Chiper-Cyber — Skill Ecosystem

## Overview

**144 security skill domains** covering:
- Web Exploitation, Network Pentest, Cloud Security
- Active Directory, OSINT, Digital Forensics
- AI/LLM Red Team, Blockchain/Web3, 5G/6G Telecom
- IoT, SCADA/ICS, Wireless, Bluetooth, RF/SDR
- Reverse Engineering, Malware Analysis, Exploit Dev
- And 120+ more domains

**302 tools** referenced across all skills:
- 223 apt packages (system tools)
- 59 pip packages (Python libraries)
- 12 go binaries (Go-based tools)
- 8 manual downloads (GUI/commercial)

---

## Installation

### Quick Start (One Command)

```bash
# Clone and install everything
git clone https://github.com/iamtubasya/chiper-skills.git /tmp/chiper-skills
cd /tmp/chiper-skills

# Copy chiper-cyber to Chiper skills directory
cp -r chiper-cyber ~/.Chiper/skills/

# Install all tools (run bootstrap first)
bash ~/.chiper/skills/chiper-cyber/chiper-bootstrap/scripts/install.sh

# Verify
bash ~/.chiper/skills/chiper-cyber/chiper-bootstrap/scripts/verify.sh
```

### Manual Step-by-Step

```bash
# 1. Copy skills
cp -r chiper-cyber ~/.Chiper/skills/

# 2. Verify skills loaded
Chiper skills list | grep chiper

# 3. Install tools
bash ~/.chiper/skills/chiper-cyber/chiper-bootstrap/scripts/install.sh --phase all
```

---

## Directory Structure

```
~/.chiper/skills/chiper-cyber/
├── chiper-bootstrap/             ← MUST RUN FIRST
│   ├── SKILL.md
│   ├── scripts/install.sh        ← Full installer (302 tools)
│   ├── scripts/verify.sh         ← Verification script
│   └── references/tool-inventory.md
├── chiper-kali-tools/            ← Tool selection reference
├── chiper-kali-identity/         ← 12 Hacker Laws, skill matrix
├── chiper-web-sqli/              ← SQL injection
├── chiper-exploit-development/   ← Exploit dev
├── chiper-network-pentest/       ← Network pentest
└── ... (144 skills total)
```

---

## Skill Priority Order

```
1. chiper-bootstrap        ← Install tools first
2. chiper-kali-tools       ← Tool selection reference
3. chiper-kali-identity    ← 12 Laws, skill matrix
4. chiper-*                ← All other skills
```

---

## Per-Skill Tool Check

Each skill has a `## Prerequisites` section that:
1. Lists required tools for that specific skill
2. Checks which tools are already installed
3. Shows install commands ONLY for missing tools
4. Skips already-installed tools

---

## OS Support

| OS | Status | Notes |
|----|--------|-------|
| Kali Linux (headless) | ✅ Full | Most tools pre-installed |
| Kali Linux (default/large) | ✅ Full | All tools pre-installed |
| Ubuntu 22.04/24.04 | ✅ Full | Adds Kali repo with pin priority |
| Debian 12+ | ✅ Full | Adds Kali repo with pin priority |
| Parrot OS | ✅ Full | Most tools pre-installed |

---

## Updating

```bash
cd ~/.chiper/skills/chiper-cyber && git pull
cp -r chiper-cyber ~/.Chiper/skills/
bash ~/.chiper/skills/chiper-cyber/chiper-bootstrap/scripts/install.sh
```

---

## Links

- **Repo**: https://github.com/iamtubasya/chiper-skills
- **Bootstrap**: `chiper-cyber/chiper-bootstrap/`

---

## License

Unauthorized access to computer systems is illegal.
Use these skills only on systems you own or have explicit written permission to test.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
