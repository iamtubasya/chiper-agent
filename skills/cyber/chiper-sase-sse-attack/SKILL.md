---
name: chiper-sase-sse-attack
description: "Use when Secure Access Service Edge (SASE) and Security Service Edge (SSE) platform compromise covering Zscaler (ZIA/ZPA/ZDX/Client Connector), Netskope (Security Cloud, SW"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, sase, sse, attack]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-sase-sse-attack/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-sase-sse-attack/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-sase-sse-attack/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-sase-sse-attack/guides
---

# Sase Sse Attack

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `frida` — `pip install frida-tools`
- `tshark` — `sudo apt install -y tshark`
- `wireshark` — `sudo apt install -y wireshark`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in frida tshark wireshark; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v frida >/dev/null 2>&1 || pip install frida-tools
command -v tshark >/dev/null 2>&1 || sudo apt install -y tshark
command -v wireshark >/dev/null 2>&1 || sudo apt install -y wireshark
```

## When to Use

SASE/SSE attack skill domain covering modern converged cloud security platforms — the SWG (Secure Web Gateway) + CASB (Cloud Access Security Broker) + ZTNA (Zero Trust Network Access) + FWaaS (Firewall-as-a-Service) stack sold by Zscaler, Netskope, Palo Alto, Cisco, CATO, Cloudflare, and Microsoft. The corporate network edge is no longer a VPN concentrator or a perimeter firewall; it is a HTTPS interception proxy in the cloud, a posture-checking agent on every endpoint, and an SSO-bound identity layer that decides which user on which device gets to talk to which app. This skill is the SSE-era 

## Core Tools

### Reconnaissance and Fingerprinting

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **Wireshark / tshark** | Capture and analyze the agent's TLS handshakes, IPC, and DNS — fingerprint the SSE vendor | `tshark -i en0 -Y 'tls.handshake.extensions_server_name contains "zs

## Methodology Overview

### SSE Attack Six-Phase Workflow

```
Phase 1            Phase 2            Phase 3            Phase 4            Phase 5            Phase 6
Vendor Recon   →   Client Connector   →   TLS Inspection →   Policy Bypass  →   Data            →   Detection
& Fingerprint      Reverse Eng.       Bypass              (App-Specific       Exfiltration        Avoidance &
                   (Frida/Hopper)     

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-sase-sse-attack/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
