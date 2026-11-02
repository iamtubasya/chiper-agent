---
name: chiper-data-exfiltration-attack
description: "Use when Attacks for exfiltrating data from compromised networks and bypassing DLP/egress controls. Covers DNS tunneling, ICMP/HTTPS tunneling, protocol smuggling,"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, data, exfiltration, attack]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-data-exfiltration-attack/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-data-exfiltration-attack/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-data-exfiltration-attack/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-data-exfiltration-attack/guides
---

# Data Exfiltration Attack

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `chisel` — `go install github.com/jpillora/chisel@latest`
- `dig` — `sudo apt install -y dnsutils`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in chisel dig; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v chisel >/dev/null 2>&1 || go install github.com/jpillora/chisel@latest
command -v dig >/dev/null 2>&1 || sudo apt install -y dnsutils
```

## When to Use

Exfiltration is the final stage of the kill chain — once attackers have collected data, they must move it out without tripping DLP, IDS/IPS, SWG, or CASB controls. This domain covers the full exfiltration landscape: DNS tunneling (the most common C2/exfil channel in restricted environments), ICMP/HTTP(S) tunneling, protocol smuggling over legitimate services (Google Drive / OneDrive / GitHub / Cloudflare), steganographic exfiltration (PNG/BMP/PDF steg), cloud-native exfil (S3 cross-account, OpenSearch collection, BigQuery external tables), and DLP bypass techniques. Includes operator playbooks

## Core Tools

| Tool | Purpose |
|------|---------|
| `dnscat2` | DNS tunnel C2 + exfil |
| `iodine` | DNS tunnel (IP-over-DNS) |
| `dns2tcp` | DNS tunnel (TCP-over-DNS) |
| `chisel` | HTTP/WebSocket tunnel with mTLS |
| `merlin` | HTTP/2 C2 (Go) |
| `sliver` | HTTP/HTTPS/DNS C2 |
| `gost` | Multi-protocol tunnel

## Methodology Overview

### Phase 1 — Reconnaissance

Map the egress surface: what protocols are allowed, where DLP sits, what cloud services are reachable.

```bash
# Test outbound protocols
for proto in 53/udp 53/tcp 80/tcp 443/tcp 123/udp 4444/tcp 8080/tcp; do
  nc -vz -w 2 exit-proxy.example.com ${proto/\/*/} -p ${proto/*\//} 2>&1 | grep -E "succeeded|failed"
done

# Check DNS egress (most permissive)
dig +short AAAA

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-data-exfiltration-attack/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
