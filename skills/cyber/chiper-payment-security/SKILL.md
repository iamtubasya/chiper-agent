---
name: chiper-payment-security
description: "Use when Payment systems security — PCI-DSS compliance testing, payment API security (Stripe/Adyen/PayPal), EMV chip/PIN, 3-D Secure, mobile wallets (Apple Pay/Google Pay)"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, payment]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-payment-security/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-payment-security/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-payment-security/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-payment-security/guides
---

# Payment Security

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `frida` — install: `pip install frida-tools`
- `mitmproxy` — install: `sudo apt install -y mitmproxy`
- `objection` — install: `pip install objection`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in frida mitmproxy objection; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v frida >/dev/null 2>&1 || echo "  pip install frida-tools"
  command -v mitmproxy >/dev/null 2>&1 || echo "  sudo apt install -y mitmproxy"
  command -v objection >/dev/null 2>&1 || echo "  pip install objection"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Payment Systems Security skill domain covering financial operations.

**Tools**: Stripe CLI, Burp Suite (payment extensions), OWASP ZAP, mitmproxy, Postman, Frida, objection, MobSF, Nessus/Qualys (ASV), PCI-DSS Quick Reference, EMVCo test cards (+3 more)

**Domain**: financial

**MITRE ATT&CK**: T1566-Phishing (credential harvesting) + domain-specific

## Core Tools

### Interception & Proxying

| Capability | Command Example |
|------------|-----------------|
| Capture Stripe / Adyen / PayPal API traffic | Configure Burp upstream proxy, install Burp CA on test device |
| Inspect mobile wallet (Apple Pay / Google Pay) traffic | `mitmproxy --mode transparent --sh

## Methodology Overview

### Payment Pentest Six-Phase Process

```
Phase 1            Phase 2            Phase 3            Phase 4            Phase 5            Phase 6
Scope & PCI        Compliance         API & Flow         Mobile Wallet      Fraud System       Report
Delineation    →   Check          →   Testing        →   Review         →   Assessment     →   & SAQ Mapping
   │                  │                  │ 

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-payment-security/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
