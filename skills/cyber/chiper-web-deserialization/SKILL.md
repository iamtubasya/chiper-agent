---
name: chiper-web-deserialization
description: "Use when Deserialization vulnerabilities arise when an application reconstructs objects from byte streams (Java), serialized strings (PHP), Base64 blobs (.NET), or pick"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, web, deserialization]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-web-deserialization/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-web-deserialization/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-web-deserialization/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-web-deserialization/guides
---

# Web Deserialization

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `file` — `sudo apt install -y file`
- `strings` — `sudo apt install -y binutils`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in file strings; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v file >/dev/null 2>&1 || sudo apt install -y file
command -v strings >/dev/null 2>&1 || sudo apt install -y binutils
```

## When to Use

Web Deserialization skill domain covering web attack operations.

**Tools**: ysoserial, phpggc, marshalsec, ysoserial.net, gadgetprobe, jackson-deserialization

**Domain**: web-attack

**OWASP**: A08:2021-Software Integrity Failures

**MITRE ATT&CK**: T1190-Exploit Public-Facing App

## Core Tools

| Tool | Language | Purpose | Key Features |
|------|----------|---------|--------------|
| **ysoserial** | Java | Generate Java gadget chain payloads | 50+ gadget chains, custom command execution, file-based payloads |
| **phpggc** | PHP | Generate PHP gadget chain payloads | Laravel, WordPress, Ma

## Methodology Overview

### Phase 1: Detection and Fingerprinting

1. Identify serialization formats in HTTP traffic (magic bytes `0xACED` for Java, `O:` for PHP, Base64 with `AAQAA` for .NET)
2. Map input vectors: cookies, POST body, headers, file uploads, API endpoints
3. Use GadgetProbe to enumerate available classes on the target classpath via DNS callbacks
4. Confirm deserialization by injecting benign objects and o

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-web-deserialization/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
