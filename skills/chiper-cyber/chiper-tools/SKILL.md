---
name: chiper-tools
description: "Use when selecting security tools across 518 tools & 65 categories, checking tool availability, or mapping target types and pentest phases to exact CLI commands."
version: "0.3.5"
author: Chiper (Chiper-Cyber)
metadata:
  chiper:
    tags: [tools, nmap, sqlmap, metasploit, burpsuite, tool-inventory, chiper-cyber]
---

# Chiper Security Tool Inventory (518 Tools)

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `bettercap` — `sudo apt install -y bettercap`
- `dig` — `sudo apt install -y dnsutils`
- `dirb` — `sudo apt install -y dirb`
- `file` — `sudo apt install -y file`
- `gobuster` — `sudo apt install -y gobuster`
- `hydra` — `sudo apt install -y hydra`
- `metasploit` — `sudo apt install -y metasploit-framework`
- `msfconsole` — `sudo apt install -y metasploit-framework`
- `nmap` — `sudo apt install -y nmap`
- `radare2` — `sudo apt install -y radare2`
- `sqlmap` — `sudo apt install -y sqlmap`
- `sublist3r` — `pip install sublist3r`
- `theharvester` — `sudo apt install -y theharvester`
- `tshark` — `sudo apt install -y tshark`
- `whatweb` — `sudo apt install -y whatweb`
- `whois` — `sudo apt install -y whois`
- `wpscan` — `sudo apt install -y wpscan`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in bettercap dig dirb file gobuster hydra metasploit msfconsole nmap radare2 sqlmap sublist3r theharvester tshark whatweb whois wpscan; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
```

## When to Use

When selecting the right security tool for a bug bounty or pentest task, checking tool availability, or reviewing tool baselines across 518 tools in 65 categories.

## Bundled References & Scripts

- `references/TOOLS.md` — Mastered tools by category & environment configuration
- `references/full-inventory.md` — Full 518-tool inventory across 65 security categories
- `references/CHIPER_TOOLS_BASELINE_2026_07.md` — 127-tool version baseline (July 2026)
- `references/CHIPER_TOOLS_BASELINE_2026_08.md` — Tool baseline update (August 2026)
- `references/CHIPER_TOOLS_BASELINE_2026_09.md` — Tool baseline update (September 2026)
- `references/TOOLS_LIFECYCLE.md` — Tool lifecycle, upgrade & deprecation matrix
- `references/DOMAIN_MATRIX.md` — Mapping of all skill domains to toolsets
- `references/QUICK_REFERENCE.md` — Quick command reference card
- `scripts/chiper-tool-selector.sh` — Automated target-to-tool mapping engine (`--target-type web|cloud|network|mobile|api --phase recon|scan|enum|vuln|exploit|postexp`)
- `scripts/chiper-check-tool-versions.py` — Automated installed tool version checker

# TOOLS.md - Local Tool Notes

Skills define _how_ tools work. This file records _your_ specific configuration and quick reference.

---

## Environment

- **OS**: Kali Linux 2025-2
- **Kernel**: 6.18.12+kali-arm64
- **Architecture**: aarch64 (ARM64)

---

## Core Tools (Mastered)

| Category | Tools | Status |
|----------|-------|--------|
| Reconnaissance | nmap, dig, whois, whatweb, wpscan, gobuster, theHarvester, sublist3r, assetfinder, dirb, zenmap | ✅ |
| Web Security | sqlmap, burpsuite, hydra | ✅ |
| Post-Exploitation | msfconsole (Metasploit) | ✅ |
| Binary Analysis | radare2 (Expert level) | ✅ |

---

## Category Index

> Full tool inventory (518 tools / 65 categories) see `docs/tools/full-inventory.md`

| Category | Tool Count | Status | Learning Notes |
|----------|------------|--------|----------------|
| recon-osint | 28 | Mastered | memory/photon.md, memory/dirb.md, etc. |
| osint | 12 | Mastered | chiper-osint/SKILL.md |
| web-xss | 8 | Mastered | chiper-web-xss/guides/ |
| web-sqli | 6 | Mastered | chiper-web-sqli/guides/ |
| web-ssrf | 5 | Mastered | chiper-web-ssrf/SKILL.md |
| web-auth-bypass | 6 | Mastered | chiper-web-auth-bypass/SKILL.md |
| web-access-control | 5 | Mastered | chiper-web-access-control/SKILL.md |
| api-security | 7 | Mastered | chiper-api-security/SKILL.md |
| network-pentest | 15 | Mastered | memory/tshark.md, memory/bettercap.md |
| post-exploitation | 11 | Mastered | memory/2026-03-21-post-exploitation-tools.md |
| password-attack | 10 | Mastered | memory/2026-03-21-password-attack-tools.md |
| wifi-pentest | 17 | Mastered | memory/wifi-cracking-course.md |
| binary-reverse | 4 | Expert-level | binary_analysis/ |
| cloud-security | 8 | Mastered | guides/cloud_security_complete_guide.md |
| container-security | 6 | Mastered | chiper-container-security/SKILL.md |
| crypto-attacks | 5 | Mastered | chiper-crypto-attacks/SKILL.md |
| digital-forensics | 7 | Mastered | chiper-digital-forensics/SKILL.md |
| insecure-design | 3 | Mastered | chiper-insecure-design/SKILL.md |
| logging-monitoring | 4 | Mastered | chiper-logging-monitoring/SKILL.md |
| mobile-security | 6 | Mastered | guides/mobile_security_complete_guide.md |
| security-misconfiguration | 5 | Mastered | chiper-security-misconfiguration/SKILL.md |
| social-engineering | 4 | Mastered | memory/2026-03-21-social-engineering-tools.md |
| supply-chain-security | 5 | Mastered | chiper-supply-chain-security/SKILL.md |
| vulnerability-assessment | 6 | Mastered | chiper-vulnerability-assessment/SKILL.md |
| security-bounty-hunter | 4 | Mastered | chiper-security-bounty-hunter/SKILL.md |
| social-intelligence | 6 | Mastered | chiper-social-intelligence/SKILL.md |
| username-profiling | 6 | Mastered | chiper-username-profiling/SKILL.md |
| deep-research | 8 | Mastered | chiper-deep-research/SKILL.md |
| codebase-onboarding | 5 | Mastered | chiper-codebase-onboarding/SKILL.md |
| knowledge-ops | 3 | Mastered | chiper-knowledge-ops/SKILL.md |
| article-writing | 4 | Mastered | chiper-article-writing/SKILL.md |
| browser-qa | 2 | Mastered | chiper-browser-qa/SKILL.md |
| data-scraper-agent | 4 | Mastered | chiper-data-scraper-agent/SKILL.md |
| exa-search | 1 | Mastered | chiper-exa-search/SKILL.md |
| ai-fuzzing | 4 | Mastered | chiper-ai-fuzzing/SKILL.md |
| ai-security | 3 | Mastered | chiper-ai-security/SKILL.md |
| council | 2 | Mastered | chiper-council/SKILL.md |
| security-review | 5 | Mastered | chiper-security-review/SKILL.md |
| repo-scan | 4 | Mastered | chiper-repo-scan/SKILL.md |
| terminal-ops | 3 | Mastered | chiper-terminal-ops/SKILL.md |
| verification-loop | 3 | Mastered | chiper-verification-loop/SKILL.md |
| docker-patterns | 5 | Mastered | chiper-docker-patterns/SKILL.md |
| search-first | 3 | Mastered | chiper-search-first/SKILL.md |
| autonomous-loops | 2 | Mastered | chiper-autonomous-loops/SKILL.md |
| safety-guard | 2 | Mastered | chiper-safety-guard/SKILL.md |
| chronicle | 2 | Mastered | chiper-chronicle/SKILL.md |
| continuous-learning | 3 | Mastered | chiper-continuous-learning/SKILL.md |
| hardware-security | 4 | Mastered | chiper-hardware-security/SKILL.md |
| multi-agent-collaboration | 3 | Mastered | chiper-multi-agent-collaboration/SKILL.md |
| mcp-server-patterns | 3 | Mastered | chiper-mcp-server-patterns/SKILL.md |
| engagement-manager | 7 | Mastered | chiper-engagement-manager/SKILL.md |
| tool-mastery | 518 | Mastered | chiper-tool-mastery/SKILL.md |
| network-sniffing-mitm | 9 | Mastered | chiper-network-sniffing-mitm/SKILL.md |
| privilege-escalation | 8 | Mastered | chiper-privilege-escalation/SKILL.md |
| exploit-development | 8 | Mastered | chiper-exploit-development/SKILL.md |
| payload-generation | 7 | Mastered | chiper-payload-generation/SKILL.md |
| av-edr-evasion | 7 | Mastered | chiper-av-edr-evasion/SKILL.md |
| dns-attacks | 8 | Mastered | chiper-dns-attacks/SKILL.md |
| web-xxe | 6 | Mastered | chiper-web-xxe/SKILL.md |
| file-inclusion | 6 | Mastered | chiper-file-inclusion/SKILL.md |
| cms-framework-attack | 7 | Mastered | chiper-cms-framework-attack/SKILL.md |
| steganography | 6 | Mastered | chiper-steganography/SKILL.md |
| bluetooth-rfid-nfc | 13 | Mastered | chiper-bluetooth-rfid-nfc/SKILL.md |
| network-tunneling-proxy | 10 | Mastered | chiper-network-tunneling-proxy/SKILL.md |
| firmware-reverse | 9 | Mastered | chiper-firmware-reverse/SKILL.md |
| scada-ics-security | 8 | Mastered | chiper-scada-ics-security/SKILL.md |
| database-attack | 8 | Mastered | chiper-database-attack/SKILL.md |
| voip-sip-attack | 8 | Mastered | chiper-voip-sip-attack/SKILL.md |
| anti-forensics | 7 | Mastered | chiper-anti-forensics/SKILL.md |
| pentest-reporting | 7 | Mastered | chiper-pentest-reporting/SKILL.md |
| ad-ldap-attack | 15 | Mastered | chiper-ad-ldap-attack/SKILL.md |
| web-deserialization | 6 | Mastered | chiper-web-deserialization/SKILL.md |
| email-protocol-attack | 8 | Mastered | chiper-email-protocol-attack/SKILL.md |
| sdr-rf-attack | 12 | Mastered | chiper-sdr-rf-attack/SKILL.md |
| vpn-attack | 10 | Mastered | chiper-vpn-attack/SKILL.md |
| darkweb-intel | 10 | Mastered | chiper-darkweb-intel/SKILL.md |
| threat-hunting | 12 | Mastered | chiper-threat-hunting/SKILL.md |
| blockchain-web3 | 14 | Mastered | chiper-blockchain-web3/SKILL.md |
| payment-security | 12 | Mastered | chiper-payment-security/SKILL.md |
| llm-red-team | 12 | Mastered | chiper-llm-red-team/SKILL.md |
| deception-honeypot | 12 | Mastered | chiper-deception-honeypot/SKILL.md |
| kubernetes-attack | 14 | Mastered | chiper-kubernetes-attack/SKILL.md |
| secret-management-attack | 14 | Mastered | chiper-secret-management-attack/SKILL.md |
| ai-agent-security | 12 | Mastered | chiper-ai-agent-security/SKILL.md |
| iot-pentest | 12 | Mastered | chiper-iot-pentest/SKILL.md |
| detection-engineering | 14 | Mastered | chiper-detection-engineering/SKILL.md |
| agentic-pentest | 12 | Mastered | chiper-agentic-pentest/SKILL.md |
| cloud-identity-attack | 14 | Mastered | chiper-cloud-identity-attack/SKILL.md |
| physical-security-testing | 12 | Mastered | chiper-physical-security-testing/SKILL.md |
| quantum-crypto-attack | 12 | Mastered | chiper-quantum-crypto-attack/SKILL.md |
| email-security-deep | 14 | Mastered | chiper-email-security-deep/SKILL.md |
| 5g-telecom-attack | 13 | Mastered | chiper-5g-telecom-attack/SKILL.md |
| automotive-vehicle-security | 13 | Mastered | chiper-automotive-vehicle-security/SKILL.md |
| mobile-app-instrumentation | 13 | Mastered | chiper-mobile-app-instrumentation/SKILL.md |
| cloud-native-vuln-research | 13 | Mastered | chiper-cloud-native-vuln-research/SKILL.md |
| macos-security | 13 | Mastered | chiper-macos-security/SKILL.md |
| uav-drone-security | 13 | Mastered | chiper-uav-drone-security/SKILL.md |
| game-anticheat-bypass | 13 | Mastered | chiper-game-anticheat-bypass/SKILL.md |
| mainframe-security | 13 | Mastered | chiper-mainframe-security/SKILL.md |
| ics-fieldbus-attack | 13 | Mastered | chiper-ics-fieldbus-attack/SKILL.md |
| hf-vhf-radio-attack | 13 | Mastered | chiper-hf-vhf-radio-attack/SKILL.md |
| blockchain-l2-attack | 13 | Mastered | chiper-blockchain-l2-attack/SKILL.md |
| embedded-rtos-security | 13 | Mastered | chiper-embedded-rtos-security/SKILL.md |
| storage-san-attack | 13 | Mastered | chiper-storage-san-attack/SKILL.md |
| hypervisor-introspection | 13 | Mastered | chiper-hypervisor-introspection/SKILL.md |
| satellite-leo-security | 13 | Mastered | chiper-satellite-leo-security/SKILL.md |
| ad-cs-abuse | 13 | Mastered | chiper-ad-cs-abuse/SKILL.md |
| ci-cd-supply-chain-attack | 13 | Mastered | chiper-ci-cd-supply-chain-attack/SKILL.md |
| pam-privilege-attack | 13 | Mastered | chiper-pam-privilege-attack/SKILL.md |
| cspm-casb-attack | 13 | Mastered | chiper-cspm-casb-attack/SKILL.md |
| sase-sse-attack | 13 | Mastered | chiper-sase-sse-attack/SKILL.md |

---

## Learning Strategy

### Current Phase
All 518 tools mastered across 139 skill domains. Current focus: quality consolidation, new skill domain development, Distinguished sprint, engagement orchestration, and cross-skill scenario execution.

### Continuous Improvement
- Cross-skill composite attack chain practice
- Real-world scenario validation on authorized targets
- Scoring system v2: guide quality metrics and depth differentiation
- Tool proficiency deepening through engagement-driven practice

### Methodology
1. Attack chain integration: practice tools in realistic multi-step scenarios
2. Scenario-driven learning: design kill chain scenarios that exercise multiple tools
3. Knowledge sharing: distill engagement insights into skill guides and MEMORY.md

---

_Last updated: 2026-06-21_
