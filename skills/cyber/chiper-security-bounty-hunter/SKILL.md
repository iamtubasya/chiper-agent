---
name: chiper-security-bounty-hunter
description: "Use when Hunt for exploitable, bounty-worthy security issues in target systems. Focuses on remotely reachable vulnerabilities that qualify for real reports and respo"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, bounty, hunter]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-security-bounty-hunter/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-security-bounty-hunter/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-security-bounty-hunter/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-security-bounty-hunter/guides
---

# Security Bounty Hunter

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `burp` — `echo "Download: https://portswigger.net/burp/communitydownload"`
- `sqlmap` — `sudo apt install -y sqlmap`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in burp sqlmap; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v burp >/dev/null 2>&1 || echo "Download: https://portswigger.net/burp/communitydownload"
command -v sqlmap >/dev/null 2>&1 || sudo apt install -y sqlmap
```

## When to Use

Focuses on remotely reachable vulnerabilities that qualify for real reports and responsible disclosure, not broad best-practices reviews or theoretical findings.

**Domain**: assessment

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| semgrep | Static analysis with custom rules | `semgrep --config=auto --severity=ERROR --severity=WARNING --json` |
| Burp Suite | Web proxy and attack platform | Intercept → Repeater → Intruder |
| SQLMap | Automated SQL inj

## Methodology Overview

### Bounty Hunter Workflow

**Step 1: Scope Check**

Before any testing:
- Read the program's scope, rules, and exclusions (SECURITY.md, policy pages)
- Identify in-scope domains, IP ranges, and application types
- Note any out-of-scope targets and testing restrictions
- Check for existing reports on the same target

**Step 2: Find Real Entrypoints**

Focus on network-reachable attack surfaces:
- 

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-security-bounty-hunter/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
