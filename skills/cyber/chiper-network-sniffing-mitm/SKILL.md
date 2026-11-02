---
name: chiper-network-sniffing-mitm
description: "Use when Network Sniffing and MITM attacks focus on intercepting, analyzing, and manipulating network traffic between two communicating parties."
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, network, sniffing, mitm]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-network-sniffing-mitm/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-network-sniffing-mitm/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-network-sniffing-mitm/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-network-sniffing-mitm/guides
---

# Network Sniffing Mitm

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `bettercap` — install: `sudo apt install -y bettercap`
- `dsniff` — install: `sudo apt install -y dsniff`
- `ettercap` — install: `sudo apt install -y ettercap-text-only`
- `responder` — install: `sudo apt install -y responder`
- `tcpdump` — install: `sudo apt install -y tcpdump`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in bettercap dsniff ettercap responder tcpdump; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v bettercap >/dev/null 2>&1 || echo "  sudo apt install -y bettercap"
  command -v dsniff >/dev/null 2>&1 || echo "  sudo apt install -y dsniff"
  command -v ettercap >/dev/null 2>&1 || echo "  sudo apt install -y ettercap-text-only"
  command -v responder >/dev/null 2>&1 || echo "  sudo apt install -y responder"
  command -v tcpdump >/dev/null 2>&1 || echo "  sudo apt install -y tcpdump"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Network Sniffing Mitm skill domain covering network attack operations.

**Tools**: wireshark/tshark, tcpdump, ettercap, bettercap, mitm6, responder, dsniff, driftnet (+2 more)

**Domain**: network-attack

**MITRE ATT&CK**: TA0006-Credential Access

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **wireshark/tshark** | Protocol analysis, PCAP triage, credential extraction, protocol hierarchy statistics | `tshark -r capture.pcap -Y "http.request"` |
| **tcpdump** | Lightweight packet capture with BPF filters, suitable

## Methodology Overview

### Attack Chain

```
  Survey              Capture              Poison              Harvest
 (arp-scan)    →   (tcpdump/tshark)  →  (ettercap/bettercap)  →  (responder/dsniff)
                                                                    │
         Manipulate          Exfiltrate                            │
  (bettercap caplets) ←  (driftnet/filesnarf)  ←─────────────────┘
```

**Phase Deta

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-network-sniffing-mitm/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
