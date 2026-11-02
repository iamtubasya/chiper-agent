---
name: chiper-terminal-ops
description: "Use when Evidence-first execution workflow for running security commands, inspecting system state, debugging tool failures, and making verified changes. This skill enforces a"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, terminal, ops]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-terminal-ops/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-terminal-ops/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-terminal-ops/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-terminal-ops/guides
---

# Terminal Ops

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `curl` — `sudo apt install -y curl`
- `nmap` — `sudo apt install -y nmap`
- `tcpdump` — `sudo apt install -y tcpdump`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in curl nmap tcpdump; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v curl >/dev/null 2>&1 || sudo apt install -y curl
command -v nmap >/dev/null 2>&1 || sudo apt install -y nmap
command -v tcpdump >/dev/null 2>&1 || sudo apt install -y tcpdump
```

## When to Use

This skill enforces a disciplined approach: inspect before acting, keep changes narrow, and report exact execution state.

**Domain**: workflow

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| nmap | Network scanning | `nmap -sV -sC -oA scan_results target` |
| curl | HTTP requests with evidence capture | `curl -v -o response.html http://target 2>&1 \| tee curl_log.txt` |
| tcpdump | Packet capture for evidence | 

## Methodology Overview

### Terminal Ops Five-Phase Process

**Phase 1: Resolve the Working Surface**

Before executing, confirm:
- Target system / IP / URL
- Current network position (local, VPN, pivoted)
- Authorized scope
- Requested mode: `inspect` | `exploit` | `verify` | `cleanup`
- Output destination for evidence

**Phase 2: Read the Failing Surface First**

If debugging or following up:
- Inspect the error messag

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-terminal-ops/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
