---
name: chiper-embedded-rtos-security
description: "Use when RTOS penetration testing — VxWorks WDB debug agent (Urgent/11), QNX microkernel, FreeRTOS+TCP CVEs, ThreadX/Azure RTOS, Zephyr, Mbed OS, TI-RTOS, MicroC/OS,"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, embedded, rtos]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-embedded-rtos-security/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-embedded-rtos-security/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-embedded-rtos-security/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-embedded-rtos-security/guides
---

# Embedded Rtos Security

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `gdb` — `sudo apt install -y gdb`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in gdb; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v gdb >/dev/null 2>&1 || sudo apt install -y gdb
```

## When to Use

Real-Time Operating System (RTOS) security covers the exploitation of deterministic operating systems used in safety-critical and embedded devices — VxWorks, QNX Neutrino, FreeRTOS (+ FreeRTOS+TCP), ThreadX/Azure RTOS, Zephyr, Arm Mbed OS, TI-RTOS/SYS/BIOS, MicroC/OS-II and III, NuttX, RIOT OS, and Contiki-NG. These operating systems are the runtime for avionics (ARINC-653 partitions on VxWorks 653 and LynxOS-178), automotive ECUs (QNX on multiple IVI platforms, AUTOSAR OS on OSEK derivatives), industrial controllers (VxWorks, MicroC/OS on PLCs, RTU/IED firmware), medical devices (ThreadX on i

## Core Tools

### Disassembly and Static Analysis

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **IDA Pro** (Hex-Rays) | Commercial disassembler with ARM/MIPS/RISC-V/PowerPC support and decompiler; standard for VxWorks symbol table recovery | `idat64 -A -B vxworks_image.bin` |
| **G

## Methodology Overview

### RTOS Attack Chain

```
Fingerprinting            Debug Agent Exploit          Kernel/Task Compromise        Persistence
(Banner/Behavior)   (WDB RPC, qconn, GDB stub)   (RCE in IP-task, MPU bypass)   (Patch image / OTA)
       |                       |                              |                              |
       v                       v                              v                  

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-embedded-rtos-security/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
