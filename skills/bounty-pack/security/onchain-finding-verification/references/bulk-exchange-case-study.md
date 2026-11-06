# Bulk Exchange (Solana) — Case Study

## Summary
Solana perpetual DEX with $8.57M USDC TVL. On-chain BPF program is upgradeable (BPFLoaderUpgradeab1e).
Source code NOT public — only client SDK (`Bulk-trade/bulk-client`) available on GitHub.
Analysis done entirely via RPC calls + client SDK cross-reference + API endpoint enumeration.

## Program
- Program ID: `BULK2CNYn3mbgfYXEXiBBFxmmDChznpjQ4oRfce8w6R4`
- Program data account: `23M4ZyUfCzzXZBvuUT7yNji9xccQMhhTWwBv84S5g6mz` (81,229 bytes)
- Upgrade authority: `MjmHxT8fatkVeQ93NjHduqoZpM2fcZmCPtoqLvSLMyY` (resolves to EOA — not confirmed Squads)
- Vault USDC ATA: `HwdwwKH1tMXo7ggTKcA5cdQrpcgqSoVib2eQh3BiyEQL` — balance: $8,572,438.73
- Vault owner (PDA): `7Wpp33Dn5KKUFjaij4zKYy1XZ9kdBtHjUatAT6NcjjGt`
- CPI program: `L2TExMFKdjpN9kozasaurPirfHy9P8sbXoAN1qA3S95` (IMMUTABLE — authority option = 0)

## Architecture (from on-chain + SDK analysis)
1. **Deposits**: User → SPL Token Transfer to vault PDA → opcode 2 instruction
2. **Withdrawals**: Offchain matching engine → FROST threshold signature → opcode 4 + CPI
3. **Orderbook**: Fully centralized off-chain (bulk.trade exchange API)
4. **Signing**: Dual system — ClearSign (user-facing) + Canonical (server-facing)

## Source code available (SDK only)
GitHub: `Bulk-trade/bulk-client` (Rust)
Crates: api, common, msgs, solana, transaction
Key files: pda.rs, ix.rs, signer.rs, transaction.rs, clear_sign.rs, deploy.rs, order.rs, risk.rs

## Findings (verified on-chain)

### B1: Upgrade Authority EOA Risk (CRITICAL candidate)
- Docs claim 5-of-8 multisig governance
- On-chain upgrade authority resolves to single pubkey, not verifiable as Squads
- If EOA → single key compromise = full program upgrade = drain $8.57M
- Mitigation: verify authority against Squads multisig PDA derivation

### B2: Clear-Sign / Canonical Signing Divergence (HIGH)
- V1: `bincode(commission_signable_actions)` — includes commission
- V2: `u64_max_le || bulk-actions_utf8 || version_u8(2)` — max slippage
- Both produce DIFFERENT hashes for the same order
- User signs V1 clear-sign; server validates V2 canonical
- If server accepts V1 → signature mismatch possible
- Test in `tests/v1/signing.rs` confirmed divergence

### B3: FROST Bypass via Program Upgrade (HIGH)
- Main program (BULK2) is upgradeable
- CPI program (L2TEx) is immutable — enforces FROST threshold
- But upgrade to BULK2 could add withdrawal path WITHOUT CPI
- This bypasses the FROST threshold entirely
- Only protected by upgrade authority governance

### B4: Correlation Matrix Admin Manipulation (HIGH)
- `RiskConfigChange { buf: Vec<u8> }` — completely opaque binary payload
- Admin controls: margin requirements, portfolio risk parameters, correlation matrix
- No on-chain validation of parameter ranges
- Could set correlation = 1.0 → inflate margins → mass liquidation
- Could set margin_buffer = 0 → over-leverage → systemic risk

### B5: BuilderCode Fee Not Displayed (MEDIUM)
- `BuilderCode { to: Pubkey, fee: u8 }` — recipient NOT shown in clear-sign message
- User signs trade without knowing fee destination
- Fee cap u8 = 255 bps (2.55%) — but unclear server-side enforcement

### B6: Offchain Orderbook Settlement Gap (MEDIUM)
- Order matching is 100% centralized
- No on-chain validation of match price
- Settlement only happens when user withdraws
- MEV: server could front-run large orders before settlement

### B7: IDOR — API Exposes Full Account Data Without Auth (CRITICAL)
**Endpoint:** `POST https://mainnet-api1.bulk.trade/api/v1/account`
**Payload:** `{"type":"fullAccount","user":"<ANY_PUBKEY>"}`
**Result:** Full position data, margin, equity, leverage, liquidation price, agent wallet — NO AUTH REQUIRED.

Additional sub-types tested:
- `positions`, `orders`, `balances`, `margin`, `equity`, `subAccounts` — ALL return data without auth
- Tested on 5+ real user accounts obtained from on-chain transactions
- Agent wallet addresses exposed for each user

**Why this is real:** Bulk Exchange is a KYC'd platform (Discord-only, email invite). Users expect account privacy. The API exposes ANY user's full portfolio to ANY requester.

## Zellic Audit Comparison (2026)
Bulk Exchange published a Zellic audit: `https://github.com/Bulk-trade/audits/releases/download/bulk-program-zellic-2026/bulk-program-zellic-security-assessment.pdf`

Zellic found 6 findings (all remediated before our audit):
| ID | Severity | Title | Our Status |
|----|----------|-------|------------|
| Z1 | Critical | Admin key bypass FROST, drain all vaults | Docs claim 5-of-8 multisig — requires privileged access |
| Z2 | High | Reversible pre-deposit shutdown double claims | Pre-deposit not live, funds gated by insurance vault |
| Z3 | High | Nested tuple layout not stable across upgrades | Requires program upgrade (governance-controlled) |
| Z4 | Medium | Migrated accounts cannot reclaim rent | Low value, ~0.002 SOL per account |
| Z5 | Medium | Initialization doesn't verify authority control | Requires deploying malicious program |
| Z6 | Low | max_balance doesn't cap total deposits | Budget/volume management, not security |

**Our finding B7 (IDOR) is NOT in Zellic scope** — Zellic audited the on-chain BPF program only, not the offchain API. This is a blind spot in their audit.

**B1-B3 overlap with Z1** — but our analysis added concrete EOA vs multisig evidence and the CPI bypass path that Zellic's finding Z1 didn't explicitly cover.

## On-chain transaction analysis
Recent 10+ transactions: ALL deposits (opcode 2)
- User: `EyqLVA2Z7MoUWoA8M9rShBXgV5v2ZA2EXxWomYRtLgvP`
- Amounts: 20.28 USDC, 106.00 USDC
- Program is ACTIVE with real user flow
- Batch IDOR tested on 5+ accounts from these transactions

## Immunefi bounty status
NOT FOUND — all 404 on immunefi.com/bounty/bulk/

## Lessons
1. Client SDK is a viable audit source when BPF is closed-source
2. Cross-reference SDK PDA derivation with on-chain PDA to verify account validation
3. Decode instruction opcodes from transaction data to map program functionality
4. Upgrade authority on Solana is THE critical security control — always verify
5. FROST threshold is meaningless if main program can be upgraded to bypass it
6. Offchain orderbook = no on-chain settlement guarantees = trust assumption
7. **API endpoints are attack surface** — Zellic only audited on-chain; API IDOR is a blind spot
8. **PDF audit extraction** — use MCP `extract_text_from_pdf` + Python JSON parsing for structured finding comparison
9. **First pass must be exhaustive** — user demanded ALL skills, tools, toolkit used from the start. Surface-level then expand wastes trust.
