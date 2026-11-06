# Cross-Chain Bridge / Intent-Settlement Protocol Audit

Class: Solidity protocols that escrow funds on origin/destination chains and settle
via an off-chain attestation or solver network. Covers BOTH message-passing bridges
and intent/solver settlement bridges (e.g. Relay). Use alongside `web3-audit`
(10 DeFi bug classes) and `onchain-source-recovery` (deployed-source recovery).

## Recon (do this first)

1. **Clone every open-source repo the docs point at** — protocol contracts, vaults,
   AND the off-chain oracle service. The docs' "Source Code" / "Contract Audits"
   section lists them; the off-chain service is usually the least-audited part.
2. **Verify deployed code == repo** before drawing conclusions. Verified source,
   no API key required:
   ```bash
   curl -s -A "Mozilla/5.0" "https://<chain>.blockscout.com/api/v2/smart-contracts/<addr>"
   # -> .source_code + .additional_sources[]  (403 without a User-Agent)
   # Sourcify fallback: https://repo.sourcify.dev/contracts/full_match/<chainId>/<addr>/
   ```
   A repo vs deployed struct mismatch is a **version-drift signal, not automatically
   a bug** — first establish which version the signed payload targets.
3. **Enumerate chain/asset slugs from the public API** (`/chains` →
   `chains[].protocol.v2.chainId` + `vmType`). Those slug strings feed on-chain id
   derivation, so they are attack-relevant inputs, not cosmetics.
4. **Find the settlement chain.** Get its RPC + explorer from the docs/subdomains.
   Enumeration is `curl ".../api/v2/search?q=<ContractName>"` on the explorer's API
   → per-contract address, verified flag; then read config with `cast call`
   (`HUB()`, `ORACLE_MULTISIG()`, `owner()`, `payloadBuilders(chainId,depository)`).
5. **Probe the off-chain oracle service surface.** Swagger UI at `/documentation`
   and its spec at **`/documentation/json`** are commonly UNAUTHENTICATED even when
   `/openapi.json`, `/health`, `/ready` return 401. The spec hands you every
   attestation route + request/response schema — build the route→auth table from it.

## The money paths — name the authorization on each

| Path | Must be gated by |
|---|---|
| Deposit → Hub MINT | on-chain log only; `currency` = the **emitting token contract address** |
| Fill → Hub TRANSFER | re-read of the destination tx + minimum-amount enforcement |
| Withdraw → Hub BURN + depository release | allocator EIP-712 sig over the FULL request; nonce + payload-hash replay guards |
| Recovery / refund | deposit-derived destination + owner/order signature |

**Deposit accounting is bounded by the emitting contract.** A forged
`Transfer(_, depository, amount)` or a bare deposit event from an attacker-deployed
token can only credit the attacker's own worthless asset, because
`currency = log.address`. So a forgeable deposit event is *not* a finding unless
you can make a REAL token address emit while moving no value.

## Concrete checks that pay

1. **`abi.encodePacked` id/alias collision.** Derivation of the form
   `keccak256(abi.encodePacked(chainId, currency))` (or `(chainId, account)`) is
   ambiguous when one chain slug is a prefix of another and the encoded lengths
   compensate. Brute-force it — enumerate real slugs from the public API and, for
   each ordered pair (A,B) + VM encoding lengths, test whether an attacker-chosen
   encoding on A can equal a real `(slugB, encB)`. Report as **latent hardening**
   unless a live pair exists.
   Relay encoding lengths (settlement SDK): evm/xrp/hedera/gateway 20, tvm 21,
   bvm 22 (legacy) / 21 (v0) / 33 (v1), svm & ton 32, hyperliquid currency 16.
   (Relay result: only prefix pair `bob`/`boba`, both `evm` 20-byte → lengths
   differ → NOT constructible. Deposit-address derivation includes `depositor`,
   so no cross-depositor collision.)
2. **Off-chain skip-verification flags.** Grep the oracle repo for `force`, `mode`,
   `recover`. Check the HTTP handler gates them. Relay: the `force` flag on
   `/attestations/solver-fills|refunds/v1` requires `isValidApiKey` —
   `typeof apiKey === "string" && hasOwnProperty(keys, apiKey) && keys[apiKey]`
   — so duplicate/array headers do NOT bypass it (`typeof array !== "string"`).
   Note: solver/operator/oracle-role exploit paths are explicitly OUT of scope on
   most bridge programs.
3. **Fail-closed defaults on limiters/finality.** Rate limiters must reject on
   disabled bucket, zero amount, and zero USD value (Relay's do) — a limiter that
   returns "consumed" on a zero-amount call is an unlimited-spend bug.
4. **Attestation endpoints are usually unauthenticated by design** (anyone can ask
   for a signature). The security question is *what the service verifies before
   signing* — read the service code, not the route.
5. **Commitment schemes.** If a payload carries a `dataHash` commitment to
   calldata supplied later, confirm the on-chain verifier actually recomputes
   `keccak256(data)` and compares it. A commitment nobody checks is a forgery
   primitive.

## Honest reporting shape (protocol track)

The generic 30-vector web-app pipeline does **not** map onto a contract/protocol
audit. Deliver instead:

- `PHASE_LOG.md`: mark 0D **N/A (contract/protocol track — web2 scanner gate not
  applicable)**. Never write it as "passed".
- `findings.json`: `validate_findings: []` when nothing is proven, plus an
  `observations[]` array at honest severity (info/low), each with a one-line
  evidence path and an explicit "unproven / latent" marker where applicable.
- A **coverage ledger**: every contract/route read, every tool run with its result
  (negatives included, tool named), and an explicit **residual-gaps** list.
- Do NOT dress unproven leads as findings. The correct status before a working
  PoC is *"verified-negative + list of controls that provably hold"* (bug-bounty
  Immediate Stop Rule 20).

## Relay case study (2026-10)

relay.link — solver/intent settlement bridge. Reward matrix S1–S4 severity × L1–L3
likelihood, $500 floor / $100k cap, admin-only = S1, solver/operator/oracle-role
paths excluded, email submission to support@relay.link.

- Repos: `relayprotocol/{relay-settlement, relay-vaults, relay-protocol-oracle}`.
- Core: RelayDepository (EIP-712 allocator sig over `CallRequest`),
  RelayGatewayDepository (Circle), RelayHub (ERC-6909), RelayAllocator (withdraw
  auth + `payloadBuilders[chainId][depository]`), RelayOracleV2
  (MINT/BURN/TRANSFER/FAST_MINT), RelayOracleIdempotencyStore, RelayExecutor +
  call resolvers + funding pools, per-VM payload builders.
- Settlement chain: EVM id 537969, public RPC `rpc.chain.relay.link`, Blockscout
  `explorer.chain.relay.link`.
- Result: **no validated exploitable finding.** Observations: (1)
  `oracle.relay.link/documentation/json` unauth while `/openapi.json` 401;
  (2) reference `BasicCallResolver.execute` is permissionless but the executor
  funds+drains it atomically (unproven); (3) `abi.encodePacked` ambiguity latent,
  not constructible.
- Highest-value next round: non-EVM attestors/payload builders
  (solana/bitcoin/ton/tron/xrp/hedera/lighter/hyperliquid), RelayPriceOracle +
  Stork/Chainlink Data Streams adapters, funding-pool draw logic.
