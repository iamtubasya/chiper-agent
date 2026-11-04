---
name: chiper-bootstrap
description: >
  Use when setting up a new environment for chiper-* skills.
  Installs ALL dependencies (apt, pip, go, manual) required by 145 chiper-* skills.
  MUST BE RUN FIRST before any other chiper-* skill.
  Run on Kali, Ubuntu, Debian, or any Linux-based system.
tags: [setup, bootstrap, installation, environment, prerequisites]
---

# chiper-bootstrap

## ⚠️ RUN THIS FIRST

**Before using ANY `chiper-*` skill, run this bootstrap.**

This skill installs all 302 tools referenced across 145 `chiper-*` skills:
- 223 apt packages (system tools)
- 59 pip packages (Python libraries)
- 12 go binaries (Go-based tools)
- 8 manual downloads (GUI/commercial tools)

---

## Quick Start

```bash
# One-liner: run the full installer
chmod +x ~/.chiper/skills/chiper-cyber/chiper-bootstrap/scripts/install.sh
~/.chiper/skills/chiper-cyber/chiper-bootstrap/scripts/install.sh
```

---

## Phases

### Phase 1: System Detection
Detect OS (Kali/Ubuntu/Debian) and adjust package sources.

### Phase 2: apt Packages (223 tools)
Install all system-level security tools via package manager.

### Phase 3: Python Packages (59 libraries)
Install Python dependencies via pip in a virtual environment.

### Phase 4: Go Binaries (12 tools)
Install Go-based security tools.

### Phase 5: Manual Downloads (8 tools)
Guide for tools that require manual download (Burp, IDA, etc).

### Phase 6: Verification
Run `chiper-verify` to confirm all tools are installed.

---

## Skill Priority

```
1. chiper-bootstrap    ← YOU ARE HERE (run first)
2. chiper-tool-mastery   (tool selection reference)
3. chiper-cyber (skill matrix, 12 Laws)
4. chiper-*            (all other skills)
```

---

## After Installation

```bash
# Verify installation
~/.chiper/skills/chiper-cyber/chiper-bootstrap/scripts/verify.sh

# Expected output:
# ✅ apt packages:    223/223
# ✅ pip packages:    59/59
# ✅ go binaries:     12/12
# ⚠️  manual:          0/8 (requires manual download)
```

---

## OS Support

| OS | Status | Notes |
|----|--------|-------|
| Kali Linux (headless) | ✅ Full | Most tools pre-installed |
| Kali Linux (default/large) | ✅ Full | All tools pre-installed |
| Ubuntu 22.04/24.04 | ✅ Full | Adds Kali repo for missing packages |
| Debian 12+ | ✅ Full | Adds Kali repo for missing packages |
| Parrot OS | ✅ Full | Most tools pre-installed |
| Arch Linux | ⚠️ Partial | Uses pacman + AUR |

---

## Pitfalls

1. **Kali repo on Ubuntu** — Can break `apt upgrade`. Use pinned preferences.
2. **pip as root** — Always use virtualenv to avoid system conflicts.
3. **Go PATH** — Ensure `~/go/bin` is in `$PATH`.
4. **Disk space** — Full install needs ~8-15GB. Check with `df -h`.
5. **Network** — Some downloads are large. Use stable connection.

---

## Troubleshooting

```bash
# If apt fails on Ubuntu: reset Kali repo priority
sudo rm /etc/apt/preferences.d/kali-pin
sudo apt update

# If pip fails: recreate venv
rm -rf ~/.Chiper/venv
python3 -m venv ~/.Chiper/venv
source ~/.Chiper/venv/bin/activate

# If Go tools fail: check Go version
go version  # need 1.21+
```

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
