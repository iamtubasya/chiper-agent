# Self-Hosted & Direct Web3 Bug Bounty Programs (Non-Third-Party)

Directory and reconnaissance reference for Web3 protocols, core L1/L2 networks, and crypto infrastructure maintaining **direct, self-hosted bug bounty and vulnerability disclosure programs** without reliance on third-party aggregators (no HackerOne, Bugcrowd, Immunefi, HackenProof, Cantina).

---

## 1. Core Layer-1 & Protocol Programs

### Ethereum Foundation
- **Portal / Entrypoint:** `https://bounty.ethereum.org`
- **Submission Method:** Direct web form on `bounty.ethereum.org` / PGP secure drop to EF legal/security team.
- **Reward Cap:** Up to **$1,000,000 USD** (includes network upgrade multipliers, e.g., Glamsterdam 0.5x–2.0x).
- **Payout Asset:** ETH or DAI.
- **In-Scope Targets:**
  - Consensus Layer Specs & Execution Layer Specs.
  - Core Clients: Geth, Nethermind, Besu, Erigon, Reth, Lighthouse, Prysm, Teku, Lodestar, Nimbus.
  - Compilers: Solidity and Vyper compiler bugs resulting in vulnerable bytecode.
  - Critical Contracts: Beacon Chain deposit contract, `go-kzg` cryptographic primitives.
- **Key Rules:** Requires local testnet/reproducible PoC. Live mainnet testing prohibited.

### Solana Foundation (Anza Agave Validator)
- **Portal / Entrypoint:** `https://bounty.anza.xyz/`
- **Submission Method:** Authenticate with GitHub at `bounty.anza.xyz`; automatically files a private GitHub Security Advisory (GHSA) against `anza-xyz/agave`.
- **Security Contact:** `security@anza.xyz` (escalation only).
- **Reward Cap:**
  - Loss of Funds: **6,250 – 25,000 SOL** (denominated directly in SOL, 12-month staked lockup).
  - Consensus / Safety Violations: **3,125 – 12,500 SOL**.
  - Liveness / Network Halt: **1,250 – 5,000 SOL**.
  - Remote DoS (Non-RPC): **315 – 1,250 SOL**.
- **In-Scope Targets:** `anza-xyz/agave` monorepo, validator consensus, turbine/gossip protocols.
- **Key Rules:** Inline exploit PoC mandatory. Requires non-refundable micro-SOL burn per submission to deter spam.

### Parity Technologies (Polkadot / Substrate)
- **Portal / Entrypoint:** `https://parity.io/bug-bounty`
- **Submission Method:** Dedicated submission form at `https://security-submission.parity.io/`.
- **Policy on Third Parties:** Strictly prohibits hosting reports on external third-party sites or paste services.
- **Payout Asset:** Polkadot (DOT).
- **In-Scope Targets:**
  - Polkadot SDK (FRAME pallets, Substrate primitives, host node consensus).
  - Polkadot Fellowship Runtimes (Kusama, Polkadot system parachains).
  - Release pipeline & distributed binary integrity.
  - Polkadot-JS UI (`apps`, `extensions`, `common`).

### Monero Project (XMR)
- **Policy Doc:** `https://github.com/monero-project/meta/blob/master/VULNERABILITY_RESPONSE_PROCESS.md`
- **Submission Method:** PGP Encrypted Email directly to core team:
  - `luigi1111@getmonero.org` (PGP: `8777 AB8F 778E E894 87A2 F8E7 F4AC A018 3641 E010`)
  - `moneromooo` via Libera IRC (PGP: `48B0 8161 FBDA DFE3 93AD FC3E 686F 0745 4D6C EFC3`)
- **Payout Asset:** Monero (XMR) funded via Community Crowdfunding System (CCS).
- **In-Scope Targets:** `monerod` daemon, RingCT, Bulletproofs+, stealth address logic, official wallet implementations.
- **Special Rules:** AI usage must be explicitly disclosed; speculative or unproven AI reports result in permanent ban.

---

## 2. Crypto Exchanges & Custody Infrastructure

### Kraken Cryptocurrency Exchange
- **Portal / Entrypoint:** `https://www.kraken.com/features/security/bug-bounty`
- **Submission Method:** Direct PGP email to `bugbounty@kraken.com` (Key: `https://www.kraken.com/.well-known/pgp-key.txt`).
- **Reward Range:** Minimum $500 USD, Critical: **$100,000 – $1,500,000 USD** (paid in Bitcoin / BTC).
- **In-Scope Targets:**
  - Web & API: `www.kraken.com`, `api.kraken.com`, `futures.kraken.com`.
  - Mobile: Kraken Pro iOS/Android apps.
  - Custody & Ledger: Order execution engine, withdrawal authorization flows, multi-sig signing services.

### Bitfinex
- **Portal / Entrypoint:** `https://www.bitfinex.com/bug-bounty/`
- **Submission Method:** Direct self-hosted web form on `bitfinex.com`.
- **Payout Asset:** Crypto / USD.
- **In-Scope Targets:** `bitfinex.com`, trading APIs, iOS App Store Bitfinex App, Android APK.

---

## 3. Hardware Wallets & Cold Storage

### Trezor (SatoshiLabs)
- **Portal / Entrypoint:** `https://trezor.io/other/partner-portal/for-developers/bug-bounty-program`
- **Submission Method:** Direct email to `security@satoshilabs.com`.
- **Reward Range:**
  - Low: up to $2,000 USD
  - Medium: $250 – $5,000 USD
  - High: $500 – $10,000 USD
  - Critical: **$1,000 – $100,000+ USD** (paid in BTC).
- **In-Scope Targets:**
  - Devices: Trezor Safe 7, Safe 5, Safe 3, Model T, Model One.
  - Software: Trezor Suite (desktop & web), Trezor Connect API, bridge/daemon, device firmware.

---

### Metaplex Foundation (Solana digital asset standard)
- **Portal / Entrypoint:** `https://metaplex.foundation/bounty-program`
- **Submission Method:** Direct **email** to `bounty@metaplex.foundation` — exploit code + reproduction steps required; submissions without clear repro may be ineligible.
- **Scope:** **On-chain programs ONLY.** Websites/domains are explicitly OUT of scope. Only the latest mainnet-deployed versions count.
- **Tiering (2026-10-29):** Tier 1 = `Core` (mpl-core); Tier 2 = Token Auth Rules, Bubblegum; Tier 3 = Core Candy Machine, Bubblegum v2.
- **Rewards (Tier 1):** Critical $10k–$20k+ · High $3k–$10k · Medium $400–$3k · Low $40–$400. Critical has a soft cap, reviewed case-by-case.
- **Disclosure rule:** No public writeup until Metaplex confirms a fix — publishing early forfeits the reward.
- **Audit methodology:** see `solana-program-audit.md` in this skill.

---

## 4. RFC 9116 Discovery Workflow for Direct Web3 Bounties

To identify whether a Web3 target has an independent / self-hosted disclosure channel before touching any third-party platform:

```bash
# 1. Fetch RFC 9116 security.txt
curl -sSL "https://<target-domain>/.well-known/security.txt" | grep -Ei "contact|policy|bounty|encryption"

# 2. Check GitHub repository security policy
curl -sSL "https://raw.githubusercontent.com/<org>/<repo>/main/SECURITY.md" | head -n 40
curl -sSL "https://raw.githubusercontent.com/<org>/<repo>/main/.github/SECURITY.md" | head -n 40
```
