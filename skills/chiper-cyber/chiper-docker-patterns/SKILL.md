---
name: chiper-docker-patterns
description: "Use when Setting up a practice lab for penetration testing techniques - Creating isolated environments for exploit development and testing - Building vulnerable application"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, docker, patterns]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-docker-patterns/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-docker-patterns/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-docker-patterns/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-docker-patterns/guides
---

# Docker Patterns

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `docker` — `sudo apt install -y docker.io`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in docker; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v docker >/dev/null 2>&1 || sudo apt install -y docker.io
```

## When to Use

Docker Patterns skill domain covering infrastructure operations.

**Domain**: infrastructure

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-docker-patterns/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
