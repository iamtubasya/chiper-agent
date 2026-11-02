---
name: chiper-blockchain-web3
description: "Use when Blockchain & Web3 security — Solidity/Vyper smart contract auditing, DeFi attack vectors (flash loans, MEV, oracle manipulation), bridge attacks, wallet security,"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, blockchain, web3]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-blockchain-web3/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-blockchain-web3/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-blockchain-web3/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-blockchain-web3/guides
---

# Blockchain Web3

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `echidna` — install: `echo "Download: https://github.com/crytic/echidna/releases"`
- `mythril` — install: `pip install mythril`
- `slither` — install: `pip install slither-analyzer`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in echidna mythril slither; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v echidna >/dev/null 2>&1 || echo "  echo "Download: https://github.com/crytic/echidna/releases""
  command -v mythril >/dev/null 2>&1 || echo "  pip install mythril"
  command -v slither >/dev/null 2>&1 || echo "  pip install slither-analyzer"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Blockchain & Web3 security skill domain covering smart contract auditing, DeFi economic attacks, and wallet/dApp security.

**Tools**: Slither, Mythril, Echidna, Foundry (forge/cast/anvil), Hardhat, Brownie, Manticore, Certora Prover, Solhint, Medusa (+5 more)

**Domain**: blockchain

**MITRE ATT&CK**: N/A (application-layer; maps loosely to TA0001-Initial Access via compromise)

## Core Tools

### Static Analysis

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **Slither** | Solidity static analysis — 90+ detectors, inheritance graph, upgradeability checks | `slither .` or `slither Contract.sol` |
| **Mythril** | Symbolic execution — finds arithmetic, reentranc

## Methodology Overview

### Smart Contract Audit Five-Phase Process

```
Phase 1            Phase 2            Phase 3            Phase 4            Phase 5
Recon & Source  →  Static Analysis →  Dynamic Testing → Fuzzing &       →  Exploit PoC +
Verification       (Slither, Mythril) (Foundry tests)   Invariants          Report
   │                  │                  │                  │                  │
   ▼          

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-blockchain-web3/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
