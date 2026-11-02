---
name: chiper-tool-mastery
description: "Use when Verification and assessment of practical proficiency with Kali Linux security tools. Covers tool classification, proficiency levels, verification methods, and combina"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, tool, mastery]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-tool-mastery/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-tool-mastery/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-tool-mastery/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-tool-mastery/guides
---

# Tool Mastery

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `metasploit` — `sudo apt install -y metasploit-framework`
- `nmap` — `sudo apt install -y nmap`
- `sqlmap` — `sudo apt install -y sqlmap`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in metasploit nmap sqlmap; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v metasploit >/dev/null 2>&1 || sudo apt install -y metasploit-framework
command -v nmap >/dev/null 2>&1 || sudo apt install -y nmap
command -v sqlmap >/dev/null 2>&1 || sudo apt install -y sqlmap
```

## When to Use

Covers tool classification, proficiency levels, verification methods, and combination strategies across the 518-tool Kali arsenal. Provides a structured framework for assessing, tracking, and improving practical competency with every security tool available in Kali Linux, from reconnaissance scanners to post-exploitation frameworks. Enables intelligent tool selection based on target type, engagement phase, and operational constraints.

**Domain**: knowledge

## Core Tools

| Tool | Category | Purpose | Key Command |
|------|----------|---------|-------------|
| nmap | Scanning | Network discovery and port scanning | `nmap -sC -sV -oA scan target` |
| sqlmap | Web Exploitation | Automated SQL injection detection and exploitation | `sqlmap -u "url" --dbs` |
| metasploit

## Methodology Overview

1. **Classify** — Map tools to categories (recon, scanning, exploitation, post-exploitation, forensics) and attack phases to enable rapid lookup
2. **Assess** — Evaluate proficiency level per tool (Beginner, Intermediate, Advanced, Expert) using the four-level framework with concrete criteria
3. **Verify** — Execute verification commands to confirm practical knowledge at each proficiency level; ru

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-tool-mastery/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
