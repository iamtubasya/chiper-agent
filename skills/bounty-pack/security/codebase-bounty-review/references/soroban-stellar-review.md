# Soroban / Stellar (and generic Rust) contract review — a codebase-track recipe

Worked case: a Stellar + Soroban P2P lending protocol (`contracts/*` = 19 Rust crates ≈ 18k LOC,
plus a Next.js backend with 41 API routes). Source-only program (SECURITY.md bug bounty, no live
testing). Result: 1 Critical + 3 High + 7 Medium/Low, all re-verified from disk, 11 reproduced at
runtime (3 `cargo test` + 8 `vitest`).

## The five defect classes that paid

1. **Trust-the-argument (caller-supplied value drives an invariant).** A state-changing fn computes
   a safety invariant from a *caller-passed* argument instead of stored state.
   - `create_loan_request(borrower, request)` computed borrowing power over `request.collateral_entries`
     (client-controlled) instead of `get_user_collateral_entries(borrower)` — the same crate's
     `withdraw_collateral`/`get_health_factor` DO use stored entries → isolated defect.
   - `harvest(caller, yield_amount)` paid a keeper fee out of the vault's token balance from a
     caller-supplied yield, with no check any yield arrived → full drain.
   - Grep: entry points taking a `struct`/`Vec`/`i128 amount` param, then `compute_*` /
     `checked_mul` / `+=` on that param before writing state.
2. **No-op verification.** A fn named `verify*` / a "cryptographic proof validation" step that only
   checks shape/non-zero. Here: the ZK credit verifier fetched the provider pubkey into an unused
   `_pubkey_hash` and accepted any 64 bytes with one non-zero byte → forged top-tier credit record.
   Grep: `verify`, `proof`, `signature`, `return true`, `non_zero`, `_unused` bindings of key hashes.
3. **Missing authorization on money movers.** `caller.require_auth()` present but no
   `assert_admin` / `assert_multisig_admin`, while sibling functions in the SAME crate gate properly
   (e.g. `treasury::set_destinations` gates, `treasury::distribute` does not; `lending::collect_fees`
   gated nowhere). This is the isolated-defect contrast that pre-empts "by design".
   Correlate: `for c in contracts/*/; do rg -c require_auth "$c"; done` then read each entry point.
4. **Fail-open guards in the backend.** `if (secret) { check }` (cron routes — unset `CRON_SECRET`
   ⇒ anonymous privileged trigger), `if (!webhookSecret) return true` (HMAC skip), and
   network-conditional signature checks (`else if (!isTestnet) reject` — testnet default ⇒ bypass).
   None of these had a `NODE_ENV` guard.
5. **Client-controlled identity.** Rate limiter keyed on `x-real-ip` / `x-forwarded-for` (spoofable),
   plus fail-open when the shared store is down.

## Recon that finds these fast

```bash
# entry points per crate
rg -n 'pub fn ' contracts/<crate>/src/lib.rs
# auth coverage per crate
for c in contracts/*/; do n=$(rg -c 'require_auth' "$c" | awk -F: '{s+=$2} END{print s}'); echo "$c: $n"; done
# guard matrix over every API route
for f in $(find app/api -name route.ts); do
  g=$(rg -o 'requireApiAdmin|requireApiUser|requireAuthenticatedUser|CRON_SECRET|verifyWebhookSignature' "$f" | sort -u | tr '\n' ',')
  echo "$g |$f"
done
```

## Runtime PoC recipe

**Rust (`cargo test`)** — drop a self-contained `#[test]` into the crate's own `src/test.rs` (the
`#[cfg(test)] mod test;` is already wired) and reuse that file's `setup()` helpers.
- Package names are **hyphenated**: `contracts/zk_credit_verifier` → `cargo test -p zk-credit-verifier`
  (`-p zk_credit_verifier` → "did not match any packages").
- First build compiles `soroban-env-host` (~4–8 min) → run `background=true, notify_on_complete=true`.
- `env.mock_all_auths()` in the harness means `require_auth()` won't block the PoC; that's expected —
  the PoC proves the *missing authz check*, not a signature failure.

**JS/TS (`vitest`)** — the repo usually already has `vitest.config.ts` + `__tests__/helpers/fake-db.ts`
(a chainable Drizzle stub: `db.queue(...)` per awaited query). Reuse it.
- `npm ci` ~8 min → background.
- Mock `@/lib/db/client` (`getDb`) and any module that imports `"use client"` browser-only code
  (e.g. `@/lib/stellar/sep31` → wallet kit) so the route imports under node.
- Assert branch effects via `db.calls` (`.some(c => c.method === "insert")`), NOT via
  `JSON.stringify(args)` — drizzle `set({ col: sql\`...\` })` args contain a circular `PgTable` and
  stringify throws.

**Evidence:** `tee` each run to `_audit/evidence/*.txt`; report `tests=N failures=0`.

## Corroboration trick: the target's own tests may encode the bug

Grep the target's test tree for tests that *assert* the insecure behaviour — they are free evidence
and show the authors' intent:

```
rg -n -i 'without auth|no secret|unset|dev mode|accepts.*without' __tests__ contracts/*/src/test.rs
```

Found: `__tests__/api/cron/liquidation.test.ts:88` ("runs without auth when CRON_SECRET is unset")
and `__tests__/api/kyc/webhook.test.ts:196` ("accepts the webhook in dev mode when no webhook secret
is configured") — cite them, then still report the finding (no `NODE_ENV` guard ⇒ prod-exposed).

## Report shape for this track

- One root cause = one finding; separate `observations[]` (e.g. "bookkeeping fn doesn't enforce the
  token transfer", "bids never collected", "SEP-10 challenge replay window", "upgrade gated on single
  admin not the multisig").
- Header = program / asset / revision / date only (no personal identity); the intro + contact line
  goes in the disclosure **email** body.
- Per finding: file:line, root cause, impact class mapped to the program's paid tiers, PoC path +
  expected output, fix direction. Do not list dependency CVEs or dev-placeholder secrets.
