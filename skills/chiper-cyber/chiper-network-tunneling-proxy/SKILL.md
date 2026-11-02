---
name: chiper-network-tunneling-proxy
description: "Use when Network tunneling encapsulates one protocol inside another to bypass firewalls, evade detection, and route traffic through restricted networks."
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, network, tunneling, proxy]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-network-tunneling-proxy/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-network-tunneling-proxy/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-network-tunneling-proxy/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-network-tunneling-proxy/guides
---

# Network Tunneling Proxy

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `chisel` — `go install github.com/jpillora/chisel@latest`
- `curl` — `sudo apt install -y curl`
- `ligolo` — `echo "Download: https://github.com/nicocha30/ligolo-ng/releases"`
- `nmap` — `sudo apt install -y nmap`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in chisel curl ligolo nmap; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v chisel >/dev/null 2>&1 || go install github.com/jpillora/chisel@latest
command -v curl >/dev/null 2>&1 || sudo apt install -y curl
command -v ligolo >/dev/null 2>&1 || echo "Download: https://github.com/nicocha30/ligolo-ng/releases"
command -v nmap >/dev/null 2>&1 || sudo apt install -y nmap
```

## When to Use

Network Tunneling Proxy skill domain covering network attack operations.

**Domain**: network-attack

**MITRE ATT&CK**: TA0008-Lateral Movement

## Core Tools

| Tool | Category | Purpose | Key Command |
|------|----------|---------|-------------|
| chisel | HTTP/SOCKS Tunnel | TCP/UDP tunnel over HTTP with SOCKS5 support, NAT traversal | `chisel server -p 8080 --reverse` |
| ligolo-ng | Pivoting | Transparent proxy with TUN interface for multi-hop pivotin

## Methodology Overview

### Phase 1: Network Topology Assessment

Before tunneling, map the network restrictions:

```
1. Identify allowed outbound protocols (nmap, curl, nslookup tests)
2. Determine firewall rules (inbound/outbound filtering)
3. Locate proxy infrastructure (corporate proxies, web gateways)
4. Assess DNS resolution policy (external resolvers allowed?)
5. Check ICMP egress (ping external hosts)
6. Map int

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-network-tunneling-proxy/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
