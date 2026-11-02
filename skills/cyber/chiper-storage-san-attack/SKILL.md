---
name: chiper-storage-san-attack
description: "Use when Storage/SAN/NAS/Object storage penetration testing — iSCSI, Fibre Channel, NFSv3/v4, SMB3, S3-compatible APIs, NetApp ONTAP, Dell EMC, Pure Storage, QNAP, Synol"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, storage, san, attack]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-storage-san-attack/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-storage-san-attack/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-storage-san-attack/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-storage-san-attack/guides
---

# Storage San Attack

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `file` — `sudo apt install -y file`
- `nmap` — `sudo apt install -y nmap`
- `wireshark` — `sudo apt install -y wireshark`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in file nmap wireshark; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v file >/dev/null 2>&1 || sudo apt install -y file
command -v nmap >/dev/null 2>&1 || sudo apt install -y nmap
command -v wireshark >/dev/null 2>&1 || sudo apt install -y wireshark
```

## When to Use

This skill targets the storage fabric underlying enterprise data — block (SAN), file (NAS), and object storage systems — and the management planes that govern them. It covers protocol-level attacks against iSCSI/Fibre Channel/NFS/SMB, vendor appliance exploitation (NetApp ONTAP, Dell EMC, Pure Storage, QNAP, Synology, TrueNAS), object storage abuse (AWS S3, MinIO, Ceph RGW, Azure Blob, GCP Cloud Storage, OpenStack Swift), and the ransomware patterns that have made NAS appliances a top-tier target since 2021.

**Tools**: nmap (iSCSI/NFS/SMB/SNMP NSE), open-iscsi, Wireshark (SCSI/iSCSI/FCP disse

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **nmap + NSE** | Service discovery, iSCSI/NFS/SMB/SNMP enumeration via built-in NSE scripts | `nmap -sV -p 3260,2049,445,161 --script=iscsi-info,nfs-showmount,smb-enum-shares,snmp-win32-services 10.0.0.0/24` |
| **open-iscsi

## Methodology Overview

### Attack Chain

```
Recon & Discovery → Protocol/Service Enumeration → Auth Testing → Exploitation → Post-Exploitation / Ransomware Simulation
   (nmap/snmpwalk)   (showmount/iscsiadm/aws s3api)  (default creds, ACL)  (LUN mount, S3 GET)  (credential harvest, mass encrypt)
```

**Phase 1: Recon and Discovery**

- Identify storage services on common ports: iSCSI (3260), NFS (2049), SMB (445), S3/

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-storage-san-attack/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
