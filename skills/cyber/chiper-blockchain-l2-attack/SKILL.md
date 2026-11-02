---
name: chiper-blockchain-l2-attack
description: "Use when Layer-2 blockchain attack — Lightning Network (BOLT, HTLC), Optimistic Rollups (Optimism/Arbitrum/Boba/Base), ZK Rollups (zkSync/StarkNet/Polygon zkEVM/Scroll"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, blockchain, attack]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-blockchain-l2-attack/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-blockchain-l2-attack/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-blockchain-l2-attack/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-blockchain-l2-attack/guides
---

# Blockchain L2 Attack

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

Layer-2 (L2) blockchain security skill domain covering everything *above* the L1 base layer: payment channels, Optimistic and ZK rollups, sidechains, cross-chain bridges, account abstraction, and data-availability layers.

**Tools**: Foundry (forge/cast/anvil/chisel), Hardhat, Brownie/Ape, Slither, Mythril, Manticore, Echidna, Etheno, web3.py/ethers.js, Tenderly, Forta, OpenZeppelin Defender, Revoke.cash/Etherscan tools

**Domain**: blockchain-l2

**MITRE ATT&CK**: TA0006-Credential Access (validator key compromise, sequencer key theft, multisig social engineering)

## Core Tools

### L1 Forking + Rollup Node Devnets

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **Anvil (Foundry)** | Local mainnet fork — required for bridge replay at a specific block | `anvil --fork-url $MAINNET_RPC --fork-block-number 14282107 --port 8545` |
| **OP Stack devnet

## Methodology Overview

### L2 Audit Seven-Phase Process

```
Phase 1           Phase 2           Phase 3           Phase 4           Phase 5           Phase 6           Phase 7
Threat Model   →  Component Map  →  Contract Audit →  Off-Chain Audit → Cross-Chain     →  Exploit PoC    →  Report +
(Scope, chain     (Bridge,           (Slither/Mythril/ (Sequencer,        Replay +         (Fork replay,      Defense
ID, trust 

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-blockchain-l2-attack/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
