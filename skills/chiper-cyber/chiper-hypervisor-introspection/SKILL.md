---
name: chiper-hypervisor-introspection
description: "Use when Hypervisor introspection (VMI) and virtualization escape attacks — VMware ESXi, Hyper-V, KVM/QEMU, Xen, Proxmox, VirtualBox, LibVMI, DRAKVUF, VENOM CVE-20"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, hypervisor, introspection]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-hypervisor-introspection/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-hypervisor-introspection/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-hypervisor-introspection/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-hypervisor-introspection/guides
---

# Hypervisor Introspection

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `volatility` — `pip install volatility3`
- `wireshark` — `sudo apt install -y wireshark`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in volatility wireshark; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v volatility >/dev/null 2>&1 || pip install volatility3
command -v wireshark >/dev/null 2>&1 || sudo apt install -y wireshark
```

## When to Use

Hypervisor Introspection skill domain covering virtualization layer operations.

**Tools**: VMware vSphere CLI (govc, pyvmomi, PowerCLI), ESXi Shell/DCUI/vMA, LibVMI/PyVMI, DRAKVUF, DECAF/PANDA, QEMU (QMP/HMP), virsh/libvirt, Xen xl/xm/xe, Hyper-V PowerShell, Proxmox VE qm/pct, Wireshark (VMware/VNC dissectors), Volatility (VM memory forensics), HyperPlatform/DdiMon

**Domain**: virtualization

**MITRE ATT&CK**: T1068 - Exploitation for Privilege Escalation

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **govc** | Go-based vSphere CLI for ESXi/vCenter management and enumeration | `govc about -u user:pass@vc.example.com` |
| **pyvmomi** | Python SDK for vSphere API; programmatic MOB traversal | `python3 -c "from pyVim.connec

## Methodology Overview

### Attack Chain

```
   Management Plane         Guest Kernel         Device Emulation        Hypervisor           Host / Sibling VMs
   Enumeration              Reconnaissance       Vulnerability           Compromise           Lateral Movement
   (vSphere API, MOB,       (Detect VMware       (QEMU device,           (RCE in vmx,         (vmkloadapp,
    SLP, libvirt, Xen       Tools, Hyper-V     

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-hypervisor-introspection/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
