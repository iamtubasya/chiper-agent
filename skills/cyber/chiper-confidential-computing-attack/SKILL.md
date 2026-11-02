---
name: chiper-confidential-computing-attack
description: "Use when Attacks against Trusted Execution Environments (TEEs) and confidential computing platforms — Intel SGX (Foreshadow/SGAxe/LVI/ÆPIC Leak), Intel TDX, A"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, confidential, computing, attack]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-confidential-computing-attack/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-confidential-computing-attack/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-confidential-computing-attack/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-confidential-computing-attack/guides
---

# Confidential Computing Attack

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `file` — `sudo apt install -y file`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in file; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v file >/dev/null 2>&1 || sudo apt install -y file
```

## When to Use

This skill targets confidential computing — the technology that protects data in *use* via hardware-isolated enclaves. While at-rest and in-transit encryption are well-understood, TEEs introduce a new attack surface: **enclave attestation forgery, microarchitectural side channels, ABI misuse between enclave and untrusted host, and host-to-enclave breakout**.

**Tools**: sgx-step, sgvisor, sev-tool, snp-lab, marblerun-cli, ccf-client, occlum-tools, gramine-direct, rust-sgx, edgelessrt, intel-sgx-sdk, sgxs-tools, libsgx, sgx_emulate

**Domain**: confidential-computing

**MITRE ATT&CK**: T1046 Ne

## Core Tools

### Intel SGX
- **Intel SGX SDK** — official SDK; includes `sgx_sign`, `sgx_edger8r`
- **sgx-step** — single-step enclave execution, page-fault side channels (Ard et al., TU Wien)
- **sgvisor** — enclave hypervisor framework for research
- **sgxs-tools** — Rust utilities for SGX enclave file manipul

## Methodology Overview

### Phase 1 — Reconnaissance
- Identify SGX/TDX/SEV-SNP usage in target (binary inspection for SGX instructions like `encls`, `enclu`, `enclv`)
- Identify attestation provider (Intel IAS, Intel DCAP, AMD VCEK, Azure CCF, custom attestation service)
- Map enclave binary: identify ECALLs, OCALLs, edge routines
- Identify attestation report format (EPID, DCAP, ECDSA)
- Identify sealed-secret storage 

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-confidential-computing-attack/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
