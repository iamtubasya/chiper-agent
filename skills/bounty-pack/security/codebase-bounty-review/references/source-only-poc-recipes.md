# Source-only PoC recipes (runtime proof without a live host)

When the program forbids live testing, a **runtime PoC dropped into the repo's own test tree** is the
strongest evidence — the maintainer runs it with the project's own build and sees the insecure
behaviour, not a code-path assertion. Build ONE PoC per finding; ship N findings as N drafts
(1 finding = 1 PDF = 1 draft = 1 email = 1 PoC).

Worked case: `thisisouvik/trustlend-stellar` (Next.js + 19 Soroban/Rust crates), 12 findings,
5 cargo PoCs + 14 vitest assertions, all passing.

---

## Recipe A — Rust / Soroban contract PoC (`cargo test`)

1. **Locate the crate's test module.** Most Soroban crates end `lib.rs` with `#[cfg(test)] mod test;`
   and `src/test.rs` opens with `use super::*;` plus a `setup()` helper that calls `env.mock_all_auths()`.
2. **Append a `#[test] fn poc_<finding>()`.** Reuse `setup()` / the crate's own helpers.

```rust
// contracts/treasury/src/test.rs — proves distribute() has no admin guard.
#[test]
fn poc_non_admin_can_distribute_treasury() {
    let (env, admin, insurance_fund, dao_treasury, asset_token, client) = setup_test();
    let attacker = Address::generate(&env);
    assert_ne!(attacker, admin);

    mint_tokens(&env, &asset_token, &attacker, 1_000_0000000i128);
    client.deposit_fees(&attacker, &asset_token, &1_000_0000000i128);

    // Attacker — NOT the admin — drains the treasury to the configured sinks.
    let (to_ins, to_dao) = client.distribute(&attacker, &asset_token);
    assert_eq!(to_ins + to_dao, 1_000_0000000i128);
}
```

3. **Run it.** From the workspace root (`contracts/`):
   `cargo test -p treasury poc_non_admin_can_distribute_treasury`

### Pitfalls
- ⛔ **`-p` uses the Cargo PACKAGE name (hyphens), not the directory (underscores).**
  `cargo test -p zk-credit-verifier` ✅ · `cargo test -p zk_credit_verifier` ❌
  *"package ID specification did not match any packages"* (the error even suggests the hyphenated name).
- First compile builds `soroban-env-host` (~3-6 min cold). Run `background=true`, then `process wait`.
- Adding a PoC to an existing suite is a bonus sanity check: `cargo test -p lending` should stay green
  (e.g. 109/109 + 19 proptest) — proves the PoC didn't break the crate.
- `rustfmt` may be missing for the toolchain; the edit still compiles — ignore the lint warning.

---

## Recipe B — Next.js / TypeScript route PoC (`vitest`)

1. **Find the harness.** Real Next.js repos ship `vitest.config.ts` (alias `@` → root, excludes
   `e2e/**`, `contracts/**`) and often `__tests__/helpers/fake-db.ts`.
2. **Drop PoCs in `__tests__/poc/*.test.ts`** and run `npx vitest run __tests__/poc`.

### B1 — pure crypto/auth module (no DB)
```ts
import { POST } from "@/app/api/sponsor/route";
import { NextRequest } from "next/server";
// assert an anonymous POST returns a FeeBump signed by the platform admin key
const res = await POST(new NextRequest(url, { method: "POST", body: JSON.stringify({ xdr }) }));
expect((await res.json()).isSimulated).toBe(false);
```

### B2 — DB-backed route via the repo's fake-db
```ts
import { createFakeDb, type FakeDb } from "../helpers/fake-db";
const mockGetDb = vi.fn(); let db: FakeDb;
vi.mock("@/lib/db/client", () => ({ getDb: () => mockGetDb() }));
// mock adjacent heavy modules so the test isolates the auth branch, not the network
vi.mock("@/lib/stellar/sep31", () => ({ discoverSep31Anchor: vi.fn(), verifyAnchorSignature: vi.fn() }));
import { POST } from "@/app/api/webhooks/sep31/route";

beforeEach(() => { db = createFakeDb(); mockGetDb.mockReturnValue(db);
  db.queue([{ id: "ltx-1", status: "pending", metadata: { anchorTxId: "x", poolId: "p" } }]); // awaited in order
  db.queue([]); db.queue([{ id: "pos-1" }]); db.queue([]); db.queue([]); });
// assert an UNSIGNED "completed" event credits a pool position
expect(db.calls.some(c => c.method === "insert")).toBe(true);
```

### Pitfalls
- ⛔ **Never `JSON.stringify` a Drizzle builder's `args`** → circular (`PgTable` → `PgUUID` → `table`).
  Assert the shape: `c.method === "set" && "totalLiquidity" in (c.args[0] as object)`.
- ⛔ **`npm ci` before the first vitest run** — fresh clone has no `node_modules` (~8 min).
- `NextRequest` body as a JSON string works in vitest's node env (matches the repo's own tests).
- Import cost is real on first run (~30-80 s "transform"); the run itself is <2 s.

---

## Finding → PoC map (worked case)

| Finding class | PoC form | Example |
|---|---|---|
| Public money fn trusts caller value (vault) | cargo | `poc_harvest_drains_vault_principal` |
| Security decision reads caller-supplied struct | cargo | `poc_loan_request_without_deposited_collateral` |
| "Verify" is a shape check only | cargo | `poc_fabricated_proof_grants_platinum_tier` |
| Missing admin guard on money fn | cargo | `poc_non_admin_can_distribute_treasury`, `poc_non_admin_can_collect_fees` |
| Conditional webhook signature | vitest + fake-db | `poc-sep31-webhook-bypass.test.ts` |
| Unauth endpoint reaching a privileged helper | vitest (+ `vi.mock` the module) | `poc-sponsor-no-auth`, `poc-treasury-no-auth` |
| Fail-open `if (secret)` guard | vitest (delete env var) | `poc-cron-failopen`, `poc-kyc-failopen` |
| Client-controlled rate-limit key | vitest (A/B) | `poc-ratelimit-ip-spoof.test.ts` |
| Unauth info endpoint | vitest | `poc-metrics-no-auth.test.ts` |

## Evidence capture
- `cargo test ... | tee evidence/rust-poc-all.txt` — grep `poc_|test result:` for the transcript.
- `npx vitest run __tests__/poc | tee evidence/api-poc-vitest.txt`.
- Keep the PoC files themselves in the repo tree (for the maintainer) AND copy them beside the report
  artifacts (`pocs/`) so the delivery bundle is self-contained.

## Cross-skill
- Gmail draft / X-Unsent / attachment staging + "1 finding = 1 draft" → `email-automation`.
- Per-finding PDF generation + geometry QA + attach-to-draft + sha256 verify → `reportlab-security-pdf`.
