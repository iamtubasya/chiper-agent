---
name: chiper-command-injection-advanced
description: "Use when Advanced injection attacks beyond SQL - covering OS command injection, LDAP injection, NoSQL injection, template injection (SSTI), XPath injection, and"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, command, injection, advanced]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-command-injection-advanced/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-command-injection-advanced/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-command-injection-advanced/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-command-injection-advanced/guides
---

# Command Injection Advanced

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `commix` — install: `sudo apt install -y commix`
- `ldapsearch` — install: `sudo apt install -y ldap-utils`
- `sqlmap` — install: `sudo apt install -y sqlmap`
- `tplmap` — install: `pip install tplmap`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in commix ldapsearch sqlmap tplmap; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v commix >/dev/null 2>&1 || echo "  sudo apt install -y commix"
  command -v ldapsearch >/dev/null 2>&1 || echo "  sudo apt install -y ldap-utils"
  command -v sqlmap >/dev/null 2>&1 || echo "  sudo apt install -y sqlmap"
  command -v tplmap >/dev/null 2>&1 || echo "  pip install tplmap"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Advanced Command Injection skill domain covering web attack operations beyond SQL injection.

**Tools**: commix, Burp Suite, ldapsearch, nosqli, tplmap, sqlmap, payload generators, filter analyzers, encoding scripts, callback servers

**Domain**: web-attack

**OWASP**: A03:2021-Injection

**MITRE ATT&CK**: TA0002-Execution

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **commix** | Automated OS command injection detection and exploitation | `commix -u "http://target/ping?host=127.0.0.1" --batch --technique=TFBSC` |
| **Burp Suite** | HTTP interception, parameter tampering, injection testin

## Methodology Overview

### Attack Chain

```
[1] Input Point             [2] Injection Testing      [3] Filter Bypass
    Discovery                  - Syntax probes            - Encoding obfuscation
  - Command execution          - Context analysis         - Keyword alternatives
  - LDAP authentication        - Error message analysis   - Space/separator tricks
  - NoSQL query endpoints      - Behavior comparison      - 

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-command-injection-advanced/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
