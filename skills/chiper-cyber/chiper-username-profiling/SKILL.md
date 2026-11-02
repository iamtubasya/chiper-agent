---
name: chiper-username-profiling
description: "Use when Build a complete dossier on a person using only a username."
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, username, profiling]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-username-profiling/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-username-profiling/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-username-profiling/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-username-profiling/guides
---

# Username Profiling

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `jq` — install: `sudo apt install -y jq`
- `sherlock` — install: `pip install sherlock-project`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in jq sherlock; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v jq >/dev/null 2>&1 || echo "  sudo apt install -y jq"
  command -v sherlock >/dev/null 2>&1 || echo "  pip install sherlock-project"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Username Profiling skill domain covering osint operations.

**Tools**: Sherlock, WhatsMyName, Holehe, Namechk, Blackbird, jq, Username hygiene audit, Pivot surface reduction (+4 more)

**Domain**: osint

**MITRE ATT&CK**: TA0043-Reconnaissance

## Core Tools

### Primary Tool — Maigret

| Capability | Command Example |
|------------|-----------------|
| Default scan (top 500 sites by traffic) | `maigret <username>` |
| Full scan (all 3,000+ sites) | `maigret <username> -a` |
| Generate HTML report | `maigret <username> --html` |
| Generate PDF report | `

## Methodology Overview

### Username Profiling Five-Phase Process

```
Phase 1            Phase 2            Phase 3            Phase 4            Phase 5
Seed Username   →  Broad Enumeration →  Recursive Pivot →  Cross-Tool        →  Dossier
& Context          (Maigret -a)         (--parse / IDs)    Verification        Synthesis
   │                  │                    │                  │                  │
   ▼     

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-username-profiling/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
