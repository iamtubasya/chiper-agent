---
name: chiper-voip-sip-attack
description: "Use when Voice over IP (VoIP) systems use the Session Initiation Protocol (SIP) for call signaling, the Real-time Transport Protocol (RTP) for media streaming, and the Inte"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, voip, sip, attack]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-voip-sip-attack/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-voip-sip-attack/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-voip-sip-attack/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-voip-sip-attack/guides
---

# Voip Sip Attack

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `sipvicious` — `pip install sipvicious`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in sipvicious; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v sipvicious >/dev/null 2>&1 || pip install sipvicious
```

## When to Use

Voip Sip Attack skill domain covering voip operations.

**Tools**: svmap, svwar, svcrack, sipsak, voiphopper, iaxflood, inviteflood, rtpflood

**Domain**: voip

**MITRE ATT&CK**: TA0046-Initial Access

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **svmap** (sipvicious) | SIP device scanning and fingerprinting on a network range | `svmap 10.0.0.0/24` |
| **svwar** (sipvicious) | SIP extension enumeration via OPTIONS/REGISTER probing | `svwar -e 100-999 10.0.0.1` |
| *

## Methodology Overview

### Attack Chain

```
Discovery → Enumeration → Authentication Testing → Eavesdropping → DoS Assessment → Reporting
```

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-voip-sip-attack/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
