---
name: chiper-mobile-app-instrumentation
description: "Use when Dynamic instrumentation of iOS/Android apps via Frida, Objection, r2frida, and Introspy; runtime SSL pinning bypass, jailbreak/root detection bypass, na"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, mobile, app, instrumentation]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-mobile-app-instrumentation/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-mobile-app-instrumentation/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-mobile-app-instrumentation/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-mobile-app-instrumentation/guides
---

# Mobile App Instrumentation

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `frida` — install: `pip install frida-tools`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in frida; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v frida >/dev/null 2>&1 || echo "  pip install frida-tools"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Mobile app instrumentation is the **runtime** counterpart to static mobile-app analysis. Where `mobile-security` reads the `Info.plist`, the `AndroidManifest.xml`, the binary's strings, and the Smali bytecode to discover *what the app could do*, this skill attaches a live Frida/Objection/r2frida bridge to a running process and observes *what the app actually does* at execution time — then forces it to behave otherwise. The operator spins up a jailbroken iOS device (checkm8 on A7-A11 or newer arm64e on A12+ with appropriate exploits) or a Magisk-rooted Android device (Android 13/14/15), acquire

## Core Tools

| Tool | Purpose | Command / Usage |
|------|---------|-----------------|
| **Frida** | Industry-standard dynamic instrumentation toolkit (JavaScript bridge to a live process on iOS/Android/Windows/Linux/macOS). ~19.7k stars. | `frida -U -f com.example.app -l hook.js --no-pause`; `frida-ps -Uai`; `f

## Methodology Overview

### Phase 1 — App Acquisition

Before any instrumentation, the operator needs the app binary on disk:

- **iOS**: The App Store delivers FairPlay-encrypted binaries. On a jailbroken device, use `Clutch -d <bundle-id>` or `iPAA` to dump the decrypted binary from memory into a usable `.app` bundle. For development-signed apps (TestFlight, sideloaded), no decryption is needed. Document the iOS versio

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-mobile-app-instrumentation/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
