# Paxos Cantina Bounty — Session State & Findings

**Platform:** Cantina (cantina.xyz) — Spearbit
**Bounty:** $1M total reward pool (Core Smart Contracts group)
**Status:** In progress (as of 2026-09-08)
**Program URL:** https://cantina.xyz/bounties/94d2fb37-a827-46da-bd10-1972b43301f6
**Reporter:** BC_USERNAME (RESEARCHER_NAME)

## Reward Structure (Core Smart Contracts)
- Critical: $1,000,000
- High: $250,000
- Medium: $25,000
- Low: $5,000

## Repos on Disk (`D:/data hermes/bugbounty/paxos/`)
| Repo | Framework | Slither Status | Notes |
|---|---|---|---|
| paxos-token-contracts | Foundry | ✅ Compiles + scans (9.4MB JSON) | 436 findings — ALL proxy false positives (uninitialized-state, external-function, constable-states). Real bugs likely in SupplyControl, ClaimableRewardsBase, SharesLib, MultiplierGrowthLib |
| busd-contract | Truffle | ✅ npm installed | Not yet scanned post-fix |
| usdg-contract | Hardhat | ✅ npm installed | Needs RPC URL removed from hardhat.config.js for Slither |
| paxg-contract | Hardhat | ❌ Missing imports | `@openzeppelin/contracts-upgradeable/security/PausableUpgradeable.sol` not found |
| pyusd-contract | Hardhat | ❌ Missing RPC URL | `YOUR_PAXOS_API_KEY` not set in hardhat.config.js |
| ybs-contract | Hardhat | ❌ Corrupted node_modules | `ENOTEMPTY` error, needs `rm -rf node_modules && npm install --legacy-peer-deps` |
| cross-chain-contracts | Hardhat | ❌ No hardhat installed | Missing `node_modules/hardhat/package.json` |
| solana-programs | Anchor | Not checked | Rust/Anchor — separate toolchain needed |
| stellar-paxos-token-contracts | Soroban | Not checked | Rust/Soroban — separate toolchain |
| usdp-contract | Hardhat | Not checked | Not yet examined |

## Code Under Review (Highest Priority)
1. **SupplyControl.sol** — Gating mechanism for minting/burning PAXG/PAXUSD. Controls mint/burn/transfer permissions.
2. **ClaimableRewardsBase.sol** — Reward calculation with SharesLib, Math.mulDiv overflow patterns.
3. **SharesLib.sol** — Share/reward math with unchecked multiplication, rounding direction.
4. **MultiplierGrowthLib.sol** — Linear growth tracker for reward multipliers.
5. **OFTWrapper / cross-chain** — LayerZero OFT (Omnichain Fungible Token) for EVM+Solana bridging.

## Findings So Far
- Slither paxos-token-contracts: 436 findings, ALL false positives (proxy patterns)
- Code review started on ClaimableRewardsBase, SharesLib, SupplyControl — no confirmed finding yet
- Need to: (1) fix remaining repo compilation, (2) deep-dive reward calculation logic, (3) check OFT bridging for cross-chain issues

## Slither False Positives (paxos-token-contracts)
- `uninitialized-state` on proxy contracts — storage initialized via `initialize()`, standard EIP-1967
- `external-function` on proxy admin routing — admin-only via TransparentUpgradeableProxy
- `constable-states` on implementation — proxy storage slots, not mutable state
- `arbitrary-send-eth` on TimelockController — executeBatch is its purpose
- `incorrect-exp` on OZ Math.sol — XOR swap misidentified as exponentiation
