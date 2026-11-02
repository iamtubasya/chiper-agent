---
name: chiper-email-security-deep
description: "Use when Phishing infrastructure and email gateway bypass covering AiTM MFA interception (evilginx2/modlishka/evilgophish), campaign platforms (gophish/King-Phisher), e"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, email, deep]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-email-security-deep/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-email-security-deep/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-email-security-deep/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-email-security-deep/guides
---

# Email Security Deep

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `gophish` — install: `echo "Download: https://github.com/gophish/gophish/releases"`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in gophish; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v gophish >/dev/null 2>&1 || echo "  echo "Download: https://github.com/gophish/gophish/releases""
else
  echo "✅ All tools installed"
fi
```

## When to Use

Email Security Deep covers the **campaign-operations layer** of email-based compromise: standing up phishing infrastructure (evilginx2, modlishka, evilgophish, gophish, King-Phisher), bypassing enterprise email gateways (Proofpoint, Mimecast, Cisco ESA, Microsoft Defender for Office), executing adversary-in-the-middle MFA bypass, running email-bomb flooding, and engineering sender reputation for spoofing success. This is the application/social-engineering layer above raw SMTP protocol abuse.

**Tools**: evilginx2, evilgophish, modlishka, gophish, King-Phisher, ThePhish, espoofer (chenjj), Mail

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **evilginx2** | AiTM reverse-proxy phishing — captures credentials + session cookies, bypassing MFA | `sudo ./evilginx -p phishlets -d` |
| **evilgophish** | Combines evilginx2 + gophish for combined AiTM + campaign manageme

## Methodology Overview

### Six-Phase Campaign Operations Workflow

```
Phase 1           Phase 2           Phase 3           Phase 4           Phase 5           Phase 6
Pretext &         Infrastructure    Gateway           Payload           AiTM /            Exfil & Exit
Target Profiling  Stand-up          Evasion Tuning    Delivery          Click-Time        (Clean Exit)
     │                 │                 │      

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-email-security-deep/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
