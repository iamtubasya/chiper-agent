# LoopScale v2 (2026-10-19) — worked application

Target: LoopScale, modular order-book lending on Solana.
`tars.loopscale.com/v1/markets` (Rust/Axum, 126-endpoint OpenAPI spec) · `app.loopscale.com`
(Angular + Privy) · `case.loopscale.com/v1/{mpc,ruby,endurance}` · `auth.loopscale.com` (Auth0
tenant) · `rpc.loopscale.com` (open Solana JSON-RPC).
Program: `security@loopscale.com`, up to $250k Program / $50k App+Services. Scope explicitly
includes "internal API endpoints and supporting backend services/infrastructure".

This was a **fresh re-run** of a target audited the previous day. v1 produced LS-01…LS-05 (1
Medium BOLA, 1 unauth write, 1 RWA read, 1 bundle-secret, 1 upgrade-authority), all of which became
**known issues / previously-reported** and therefore out of scope for re-reporting. The value of the
re-run was entirely in applying the schema-complete-body rule to the surface v1 had probed with `{}`.

## Recon deltas vs v1

- **New host: `auth.loopscale.com`** — a live Auth0 tenant (`x-auth0-l`, `x-auth0-requestid`
  headers). `/.well-known/openid-configuration` and `/.well-known/jwks.json` are public (2 RS256
  signing keys). The app itself authenticates with **Privy**, not Auth0, and no Auth0 `client_id`
  is inlined in either bundle, so the tenant could not be enumerated: every `/authorize` probe
  returned a generic `400` regardless of `client_id`. Recorded as an observation, not a finding.
- `case.loopscale.com/v1/mpc` and `/ruby` → 503 (Cloud Run revisions down); `/endurance` → `200 OK`
  with `access-control-allow-origin: *` (a health endpoint). A 30-path wordlist sweep of `/endurance`
  found nothing.
- OpenAPI spec re-fetched: **126 paths, byte-identical to v1** — 0 new endpoints. Re-fetching the
  spec is still worth doing; a spec delta is the cheapest possible new-surface signal.
- Bundle re-scan: the only "secret" shape found was `pk_live_hirbpu0cVcLHrjktC9l7fbc9ctjv0SL`,
  which is a **MoonPay** publishable key for the Privy on-ramp widget (`api.moonpay.com/v1`), not
  Stripe. Publishable keys are public by design — not a finding. Verify what a key actually belongs
  to before writing it up.

## Findings

### LS2-01 — unauth bulk depositor disclosure (Low–Medium) — **DROPPED, not submitted**

`POST /v1/markets/lending_vaults/deposits`, no credentials, body `{"page":0,"pageSize":1}` →
`200`, 40 vaults each with a complete `userDeposits` array of `{userAddress, amountSupplied}`
(~860 KB for `pageSize=1`). Verified 3×; the first entry differed each time, confirming live data.
Escalation attempts (activity log with txSignatures, history analytics with depositorHhi/top10Share,
cross-referencing with auth'd siblings) all dead-ended at read-only on-chain data.

Two things make this more than a repeat of LS-01:

1. **The `userAddress` body filter is ignored.** Sending `{"userAddress": <any wallet>}` still
   returned every user. A filter that is parsed but not applied is stronger evidence than a missing
   one.
2. **The sibling differential.** `/lending_vaults/deposits` and `/lending_vaults/user_positions`
   take the *identical* `UserLendingVaultFilter` schema; the former is open, the latter returns
   `401 User-Wallet header required`. Same schema, different gate — that is the root cause in one
   line.

**Why dropped:** after the vendor N/A'd LS-01 with "reported previously… no path to the locking,
loss, or theft of funds", this is the same root cause (one missing middleware) on a new endpoint.
The vendor's fix for LS-01 covers it. Impact framing kept honest anyway: the amounts are raw
on-chain data, so this is an enumeration-friction and wallet-profiling issue (mass LP profiling,
targeted phishing of large depositors), not direct theft. Calibrated Low–Medium, not inflated.

### LS2-02 — unauth bulk reward-claim builder (Low, impact unproven) — **DROPPED, not submitted**

`POST /v1/markets/lending_vaults/rewards/claim/all`, no credentials → `200 {"failedUserClaims":{}}`.
The single-claim sibling `/lending_vaults/rewards/claim` returns `401 User Wallet not in headers`
without the header. On a vault with active reward schedules the unauth call returned
`504 upstream request timeout` (and a client-side timeout at 20 s), while the gated sibling answered
`200 []` instantly — evidence the server does real work for an anonymous caller, but **no
demonstrated data exposure or state change**. Dropped: without a vault state that produces a
non-empty response there is nothing to report, and the vendor's bar is a fund-loss path.

## On-chain: LS-05 re-check

Decoded both programs' programdata accounts (recipe in the parent SKILL.md §2):

| program | programdata | upgrade authority |
|---|---|---|
| Core `1oopBoJG58DgkUVKkEzKgyG9dvRmpgeEm1AVjoHkF78` | `8KbXd8ATqDQQTozYv2TsCzHUDoiRyWe4DmzHdmJLgdNj` | `DwBXwJDZ4Av4miT62sEssWJUinkzwkmPPB4Fg3fKEfft` |
| BEAM oracle `beamVVkNmKeXcuZ6zLpC9eM5YgVyAn4Z9xdPrz3gCW2` | `HeLvSLkub7mexFKiAfVWR1ERtXZnMYiByRPkdpgAxXKf` | `DwBXwJDZ4Av4miT62sEssWJUinkzwkmPPB4Fg3fKEfft` |

Both point at the **same bare system wallet** (`owner = 1111…1111`, `len = 0`, 3.49 SOL) — a single
EOA, not the documented 3-of-5 multisig. The address the docs *name* as the governance multisig is
also a plain system wallet. A genuine Squads multisig
(`GLke7iqyB2z82phLpS3TNePpu1LcFGQjofeiQEmJcMsA`, `owner = SQDS4ep65T…`, 495 bytes) exists and
executes operations such as loan creation, but does **not** control upgrades.

v1 had recorded the authority as `7qNW6geC4uFv6Pi85mW3HFXMqYoyLvtK6VKi8UD2Xj8` (now a non-existent
account). **The key was rotated between sessions — to another bare EOA.** Rotation is not
remediation while the documented control is still absent; the report should carry both keys and note
the rotation so the vendor cannot claim it was already addressed.

## Verified negatives (do not re-run)

- All 12 `creditbook/*` write routes and all 8 `lending_vaults` transaction builders
  (`deposit`, `withdraw`, `stake`, `unstake`, `ix/mint_lp`, `ix/redeem_lp`) + `strategy/deposit`,
  `strategy/withdraw` → `401` on a schema-complete body with no credentials. Auth model is
  consistent for writes.
- Signature verification genuinely works on `/loans/refinance_constraint` and
  `/loans/toggle_position`: a malformed signature gives `400 Invalid signature format`, and a stale
  timestamp gives `401 Signature expired: timestamp is too old. Request must be made within 30
  seconds of signing.` A fresh timestamp + valid-format signature gets past both.
- `/lending_vaults/pause` checks the pause-admin **before** the signature (garbage signature still
  yields `403 wallet is not a pause admin for this vault`).
- `/lending_vaults/create` → identical generic `500` with and without the credential and with a
  fresh random nonce ⇒ internal error, not an auth bypass.
- `/deals/submit` and `/deals/{id}/valuation` → `401 ApiKeyNotFound` (write side correctly gated by
  `X-Api-Key`).
- Quote engine: `priceOverride` in `QuoteCollateralInfo` accepts arbitrary client values including
  `0`, `-1` and `999999` — **by design** for simulation; on-chain `expectedLtv`/`expectedLqt`/
  slippage guards protect execution. `minPrincipalAmount: -1` is rejected by `u64` validation.
- Market-config scan over 97 markets / 1,553 asset configs: **0 `lqt<=ltv`, 0 zero-`lqt`**. One
  `98% LTV / 99% LQT` on verified NAV collateral (mkt 87, `AGY5bfTr`) — same observation as v1, not a
  bug. 245 long-`maxAge` entries are explained by provider cadence (`loopscale_nav` 65535 s ≈ 18 h is
  the NAV reporting cadence; `pyth` 900–1200 s is normal).

## Pitfalls hit

- **`arjun` flags are `-d` (delay) and `--stable`, not `--delay`.** Without `--stable` on a
  rate-limited target it prints "Target has a rate limit in place" and skips the endpoint — which
  reads exactly like "no hidden parameters found".
- **`nuclei` on an API host**: 5,763 templates across 6 hosts at `-rl 15 -c 5` ran 17% in 25 min
  with 0 matches and a rising error counter (146 errors, mostly rate-limit/timeouts). Budget for the
  template count and read the error counter, not just `Matched: 0`.
- **`execute_code` runs `cmd.exe`, not bash** — `subprocess.Popen(["nuclei", ...])` fails with
  `FileNotFoundError` even though `nuclei` is on PATH in the terminal tool. Launch long-running
  scanners via the `terminal` tool instead.
- **MSYS path conversion is disabled for native tools**: `nuclei -l /d/data hermes/...` fails with
  "cannot find the path specified"; pass `D:/data hermes/...` forward-slash native paths.
- **Low RAM stalls the orchestrator.** With ~672 MB free the pipeline logged a warning, `subfinder`
  returned 0 subdomains (rc=1) and `httpx` 0 live hosts (rc=2), and the run sat at 0B. The manual
  DoH + curl path in the parent SKILL.md is the fallback; also note `subs.txt seed skipped` when the
  orchestrator's own output dir has no seed file.
- **Responses can exceed a fixed read budget.** `/lending_vaults/deposits` with `pageSize=1` is
  ~860 KB; a 200 KB read truncates mid-JSON and surfaces as `JSONDecodeError: Unterminated string`,
  which looks like a transport fault rather than a buffer limit. Read generously or page smaller.
- **`durationType` is a `u8` enum, `principal` on `/quote` is a mint-address string, and
  `collateral` is an array** — the intuitive types all 422. Read the spec before assuming; a
  `422 invalid type` is a schema hint, not a dead endpoint.

## Vendor N/A feedback (checked after v2 findings were drafted)

The user asked to read the reply emails before submitting LS2-01/LS2-02. All four v1 findings had
been rejected — verbatim reasoning in the parent SKILL.md §4. The two v2 findings were **dropped
before submission** on that basis: LS2-01 is the same root cause as the already-N/A'd LS-01 (missing
auth middleware on a `UserLendingVaultFilter` sibling) and read-only on-chain data; LS2-02 had no
demonstrated impact. **Reading the vendor's reply email is the cheapest triage step in the whole
engagement** — do it before writing any report on a target you have already submitted to.

## Weight-matrix manipulation lead (needs on-chain exploit to confirm)

`POST /creditbook/create` accepts `weightMatrixUpdate: [i32; 5]` per collateral entry. The values
are spliced **verbatim** into the on-chain instruction data — confirmed by decoding the
`serializedTransaction` returned in the 400 simulation-failure response: `999999` (`0x000F423F`)
appeared 5× at offset 512, and distinctive test values `[100,200,300,400,500]` appeared at
consecutive 4-byte offsets 512/516/520/524/528.

**Why it matters:** if the on-chain program does not validate these values, an attacker could set
collateral weight to 0 (or inflate it) → overborrow / undercollateralized positions. The API
accepts the parameter without complaint; only a live exploit with a funded wallet can prove whether
the on-chain guard exists. Recorded as a lead, not a finding.

## Transaction-builder API pattern (decode the server-built transaction)

Endpoints that build Solana transactions (`/creditbook/create`, `/lending_vaults/fee/claim`,
`/lending_vaults/rewards/schedule/create`) return the full base64 `serializedTransaction` in the
`400` error body when on-chain simulation fails:

```json
{"error":{"code":400,"message":"Transaction would fail on-chain: InvalidAccountForFee",
 "simulation":{"decoded":"...","serializedTransaction":"AgAAAA..."}}}
```

Decode it to inspect exactly what the server builds — account metas, instruction data, program IDs.
This is how the weight-matrix splicing above was confirmed. Solana legacy tx format:
`num_sigs(1) + sigs(64 each) + message`. Search the raw bytes for injected parameter values to
prove verbatim splicing.

**Corollary:** a `400 Transaction would fail on-chain` on a *valid body with no credentials* proves
the handler ran past auth — but only if the same body WITH credentials also reaches simulation.
Compare both before claiming anything.

## BEAM NAV oracle decode attempt (negative)

BEAM program (`beamVVkNmKeXcuZ6zLpC9eM5YgVyAn4Z9xdPrz3gCW2`) has 8 accounts total: 2 config
(1034/2024 bytes), 3 price history (69512/76656 bytes), 1 price feed. The 2024-byte account
appeared to hold 13 entries × 152 bytes, but the entry layout did not decode cleanly (no valid
timestamps found at any plausible offset). The API's `/oracles/prices/history` was sufficient for
health analysis. Not worth more time unless oracle manipulation becomes the primary vector.

## On-chain loan health scan (pivot after API findings were dropped)

With the API surface closed by the N/A pattern, the session pivoted to on-chain economic analysis.
The full decode is reusable for any Anchor lending protocol with a public IDL:

1. **Account size from one known account**: `getAccountInfo` on a known loan → 1,658 bytes.
2. **Bulk fetch**: `getProgramAccounts` with `filters:[{dataSize:1658}]`, `limit:10000` → all 5,825
   loans in one call. **`paginationKey` is ignored by this RPC** — every page returned the same 5,825
   accounts, so a naive pagination loop inflated the count to 116,500. Verify uniqueness (first/last
   pubkey overlap) before trusting a paginated total.
3. **Decode bytemuck packed-C layout** from the IDL: disc(8) + version(1) + bump(1) + loan_status(1)
   + borrower(32) + nonce(8) + start_time(8) + ledgers[5]×182 + collateral[5]×73 + 3 matrices×100.
   Ledger size was confirmed empirically (182) by checking which offset made `collateral[0]` decode
   to a valid mint + plausible amount.
4. **Health ratio** = `collateral_usd / outstanding_usd` where:
   - `outstanding = principal_due − principal_repaid` — **not `principal_due` alone**. Most loans
     are partially repaid; using gross due produced 962 false "risky" loans, several at ratio 0.000.
   - `value_usd = (raw_amount / 10^decimals) × price` — **decimals MUST come from
     `market_informations` per asset, never assumed**. Two traps hit live: an RWA/NAV token with
     `decimals=0` (amount=1 means one whole token worth $463k), and a collateral mint with
     `decimals=9` in one market (a 6-decimal assumption made a $1.9M position look like $1,920).
     The same mint can carry different decimals in different markets.
5. **Result**: 3,940 active loans, all healthy — riskiest ratio 1.02×, above the liquidation
   threshold. Zero bad debt. Recorded as a strong verified negative.

The decimals trap generalises: **any protocol-wide health/TVL computation you do by hand must pull
decimals from the protocol's own asset config, per market**, or you will manufacture both false
positives (assuming 0 decimals on a 6-decimal token) and false negatives (assuming 6 on a 9-decimal
token).
