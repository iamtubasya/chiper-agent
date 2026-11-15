# Source-only PoC harnesses — drop a test into the repo's own tree

When the program is source-only (no live host authorised), the strongest PoC is a test dropped into
the target's OWN test suite for the shipped source: it runs with the project's normal build and the
maintainer can execute it verbatim. Verified on a Next.js + Soroban/Rust lending protocol
(19 Rust crates + 41 API routes): 5 cargo PoCs + 14 vitest assertions, all green.

## Rust / Soroban contracts

- Workspace lives at `contracts/` with member crates; `soroban-sdk = "22.0.4"` in the workspace Cargo.toml.
- Each crate is `#![no_std]` ending in `#[cfg(test)] mod test;`. Tests use `env.mock_all_auths()`, so a
  `require_auth()`-gated function can be called from any test `Address` — the PoC proves the *missing*
  admin/authority check, not the auth mechanics.
- **PITFALL — crate directory name != package name for `-p`.** Directories are snake_case
  (`zk_credit_verifier`), packages are hyphenated (`zk-credit-verifier`). `cargo test -p zk_credit_verifier`
  fails with:
  `error: package ID specification 'zk_credit_verifier' did not match any packages / help: a package with a
  similar name exists: 'zk-credit-verifier'`
  Read `[package] name` from the crate's `Cargo.toml`, or just use the hyphen form.
- **First build of a fresh workspace is slow (~2–8 min)** — `soroban-env-host` pulls a large dep tree.
  Run the first `cargo test` with `background=true, notify_on_complete=true`; subsequent
  `cargo test -p <crate>` runs finish in seconds. (`rust-toolchain.toml` targets
  `wasm32-unknown-unknown`, but tests run on the host toolchain — no wasm target needed to execute tests.)
- **PoC shape that works for money/accounting + authz bugs:** generate a fresh `let attacker =
  Address::generate(&env);` that is provably NOT the admin (`assert_ne!(attacker, admin)`), call the
  vulnerable entry point, then assert the observable side effect. Concretely useful assertions:
  - token flow: `token::Client::new(&env, &asset).balance(&attacker)` (attacker paid), `.balance(&vault) == 0`
  - accounting wipe: `client.get_uncollected_fees() == 0` after a non-admin call
  - invariant bypass: `client.get_user_collateral_entries(&borrower).len() == 0` while a loan was created
- **Regression check:** run the FULL suite for the touched crates and quote it (e.g. `cargo test -p lending`
  → `109 passed` + `19 passed` proptest). It proves the added PoC breaks nothing and gives the maintainer a
  clean signal.
- The target may ship a `test_snapshots/` dir; a new test writes `test_snapshots/test/<name>.1.json` — harmless.

## Next.js / TypeScript API routes

- The repo already runs vitest (`"test": "vitest run"`; `vitest.config.ts` excludes `e2e/**` and
  `contracts/**`). Install once with `npm ci` (~8 min on a fresh clone), drop PoCs under `__tests__/poc/`,
  then `npx vitest run __tests__/poc`. First run has a large import cost (~30–90 s), then it's fast.
- **Reuse the repo's own test helpers.** A `__tests__/helpers/fake-db.ts` exporting `createFakeDb()`
  (chain object whose `.then()` shifts a queued result, plus `.queue()`, `.calls`) stubs the Drizzle handle
  so a route handler runs end-to-end with no database. Mock only the boundary:
  `vi.mock("@/lib/db/client", () => ({ getDb: () => mockGetDb() }))` + `let db = createFakeDb()` in
  `beforeEach`, then `db.queue([...])` in the order the handler awaits queries.
- `NextRequest` works in the vitest node env:
  `new NextRequest(url, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(...) })`.
- **PITFALL — asserting on Drizzle args.** `JSON.stringify(call.args)` throws
  `TypeError: Converting circular structure to JSON --> starting at object with constructor 'PgTable'`.
  Assert by key presence instead:
  `c.args[0] && typeof c.args[0] === "object" && "totalLiquidity" in c.args[0]`.
- **PITFALL — `vi.mock` is hoisted.** Declare the mock fns with `const f = vi.fn()` BEFORE the
  `vi.mock(...)` factory that references them (or use `vi.hoisted`), else the factory sees `undefined`.
- **Crypto-only routes need no mocking** — import the handler directly, build a real payload with the SDK,
  assert on the response. Example that landed a clean finding: POST a self-signed inner tx to a fee-bump
  sponsor endpoint and assert the returned `FeeBumpTransaction.feeSource` equals the platform key.
- **Env gates matter:** set/clear `process.env` per test (`delete process.env.CRON_SECRET`) and always add a
  `(control)` test proving the guard works when the env var IS set — it separates "no guard" from "guard
  bypassed".
- **The target's OWN tests are corroboration gold.** They often encode the insecure behaviour; cite the line:
  - `__tests__/api/cron/liquidation.test.ts:88` — "runs without auth when CRON_SECRET is unset (dev mode)"
  - `__tests__/api/kyc/webhook.test.ts:196` — "accepts the webhook in dev mode when no webhook secret is configured"
  This pre-empts a "by design / dev only" dismissal and shows the author knew the behaviour.

## Reporting cadence learned here

One finding = one report = one draft/email = one PoC (see SKILL.md PART 6 and the `email-automation` skill).
Give each finding its own PoC command in its own draft; never bundle N findings into one document unless it
is a genuine chain.
