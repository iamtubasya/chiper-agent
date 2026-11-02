---
name: chiper-bluetooth-rfid-nfc
description: "Use when Near-field wireless penetration testing skills covering Bluetooth Classic device enumeration and exploitation, BLE GATT service attacks against IoT devices, RFI"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, bluetooth, rfid, nfc]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-bluetooth-rfid-nfc/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-bluetooth-rfid-nfc/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-bluetooth-rfid-nfc/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-bluetooth-rfid-nfc/guides
---

# Bluetooth Rfid Nfc

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `bluelog` — install: `sudo apt install -y bluelog`
- `btscanner` — install: `sudo apt install -y btscanner`
- `redfang` — install: `sudo apt install -y redfang`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in bluelog btscanner redfang; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v bluelog >/dev/null 2>&1 || echo "  sudo apt install -y bluelog"
  command -v btscanner >/dev/null 2>&1 || echo "  sudo apt install -y btscanner"
  command -v redfang >/dev/null 2>&1 || echo "  sudo apt install -y redfang"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Bluetooth Rfid Nfc skill domain covering wireless operations.

**Tools**: spooftooph, redfang, bluelog, btscanner, bluehydra, crackle, ubertooth-tools, gatttool (+5 more)

**Domain**: wireless

**MITRE ATT&CK**: TA0046-Initial Access

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **spooftooph** | Bluetooth device identity spoofing (name, class, MAC) | `spooftooph -i hci0 -a XX:XX:XX:XX:XX:XX -n "TargetPhone"` |
| **redfang** | Discover non-discoverable Bluetooth devices via brute force | `redfang -r 

## Methodology Overview

### Attack Chain

```
1. Device Discovery      -> Active/passive scanning (bluelog, blescan, redfang)
2. Target Selection       -> Evaluate device type, signal strength, services advertised
3. Protocol Fingerprint   -> Identify Bluetooth version, pairing method, service profiles
4. Service Enumeration    -> GATT service/characteristic mapping (gatttool, ubertooth-tools)
5. Exploitation
   +-- BT C

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-bluetooth-rfid-nfc/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
