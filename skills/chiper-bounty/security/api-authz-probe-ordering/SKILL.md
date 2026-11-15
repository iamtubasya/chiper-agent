---
name: api-authz-probe-ordering
description: "Map API auth models and hunt BOLA on JSON APIs."
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [security, bug-bounty, api, authz, bola, idor, auth-map, solana, upgrade-authority]
---

# API authz probe ordering (and Solana upgrade-authority decode)

## When to Use

Load when you are mapping an unfamiliar JSON API's auth model, hunting BOLA/IDOR on write routes,
probing `create*`/`claim*`/`submit*` endpoints, or checking whether a Solana program's upgrade
authority matches the vendor's documented governance. Especially valuable on a **re-run of a target
you have already audited**, where the previous pass used empty-body probes and may have
false-negatived the write surface.

**Before you invest hours in API authz on a DeFi/on-chain program, read §4 (vendor N/A pattern).**
Programs whose scope says "locking, loss, or theft of funds" routinely reject API access-control and
info-disclosure findings regardless of demonstrated severity — the N/A arrives after the work is
done. Check the reward table's impact language and, if a prior submission exists, **read the
vendor's reply email before re-hunting the same class.**

Two techniques that keep getting re-derived from scratch. Both were learned on LoopScale
(2026-10-19) and both are framework-generic, not vendor-specific.

## 1. Validation-before-auth: the empty-body false positive

Many backends extract and **deserialise the request body BEFORE the authorisation middleware
runs**. On those, an empty-body probe answers `400`/`422` no matter how well the route is gated,
so the widely-repeated auth-map heuristic —

> `200` → open · `401/403` → gated · `400/422` → reachable without auth (the handler ran)

— is wrong. It produces two failure modes:

1. **False positive**: you record "reachable without auth" on a route that is actually protected.
2. **False negative (worse)**: you stop probing that endpoint and never send the valid body that
   would have exposed the real bug on a *sibling* route.

Observed live on a Rust/Axum API (126-endpoint OpenAPI spec):

| endpoint | empty body `{}` | schema-complete body |
|---|---|---|
| `POST /creditbook/create` | `422 missing field ledgerIndex` | `401 User Wallet not in headers` |
| `POST /creditbook/flash_borrow` | `422 missing field ledgerIndex` | `401` |
| `POST /creditbook/repay_simple` | `422 missing field repayAll` | `401` |
| `POST /creditbook/borrow` | `422 missing field amount` | `401` |
| `POST /creditbook/refinance` | `422 missing field ledgerIndex` | `401` |
| `POST /creditbook/collateral/withdraw` | `422 missing field expectedApy` | `401` |
| `POST /lending_vaults/deposits` | **`200` full depositor ledger** | **`200` (no gate at all)** |
| `POST /lending_vaults/rewards/claim/all` | **`200 {"failedUserClaims":{}}`** | **`200` (no gate at all)** |

The first seven are correctly-gated routes that the empty-body heuristic mislabels; the last two
are the actual findings. The same ordering appears in Hybris/Spring (`hunt-hybris` §4 documents it
independently), so treat it as a framework pattern.

### Rules

1. **Build a schema-complete valid body before classifying any POST/PUT/PATCH route.** Resolve
   `$ref`s in `components.schemas`, honour fixed-length arrays (`expectedLqt` demanded exactly 5
   entries — `invalid length 1, expected an array of length 5`), and use the spec's real types
   (`u64` not string, `u8` enums not strings). A `422 missing field X` message is a free schema
   oracle: keep adding fields until the response flips to `401`, and you have *proven* the gate.
2. Only these are unauth signals **on a valid body**: `200` with data, or a business-logic error
   (`400 Transaction would fail on-chain`, `500`) proving the handler executed past auth.
3. `401` on the valid body = gated. Log it as a verified negative **together with the exact body
   used**, so the next session does not re-litigate it.
4. **The differential is the finding.** An endpoint returning `200`/`500` on a valid body with no
   credentials while its schema-sibling returns `401` is the bug. Sibling endpoints sharing one
   filter schema are the highest-yield comparison set — here `UserLendingVaultFilter` is shared by
   `/lending_vaults/deposits` (200) and `/lending_vaults/user_positions` (401).
5. Watch for **body filters being ignored** on the ungated sibling. `/lending_vaults/deposits`
   accepted `userAddress` in the body and returned every user anyway. A filter that is parsed but
   not applied is stronger evidence than a missing one.
6. **⛔ Before concluding a lead "needs a funded mainnet wallet", exhaust the free paths first.** The
   user pushed back on exactly this — *"knp lead hrs onchain, kn bs d testnet"* — after a
   weight-matrix lead was parked as unprovable. The ladder that was skipped, in order:
   (a) **`simulateTransaction` with `sigVerify: False` + `replaceRecentBlockhash: True`** on the
   server-built tx — free, read-only, mainnet, and it returns `meta.logMessages` naming the exact
   failing instruction and Anchor error code; (b) a **devnet/testnet deployment** if one exists;
   (c) a **real borrower's wallet as the `User-Wallet` header** (public address, no key needed) so
   the API builds a transaction that reaches on-chain simulation instead of dying at
   `InvalidAccountForFee`. Step (c) is what turned the lead from "unprovable" into a definitive
   negative: the simulation returned `InvalidWeightMatrix` (6090), proving the on-chain guard
   exists. **A lead is not blocked until simulation has actually been tried.**

### 6a. Premature-negative protocol — the three failure modes

**Never conclude "NEGATIVE — no findings" until every surface has a tool-backed result.** The
LoopScale v1 session concluded negative after ~3 surfaces; the user pushed back
(*"kok sy merasa kamu cm ambil surface aja tdk deepdive lebih"*) and round 2 found 10+ untested
surfaces including a fully decodable BEAM oracle with 133 price entries, 6+ stale-price assets,
a verified API transaction-builder BOLA, and a decompiled 3.4MB ELF with 42 instructions.

The three failure modes that produce a premature negative:

1. **Vendor-feedback bias.** After 4× N/A, the agent concluded "vendor doesn't care → not worth
   testing." **Wrong.** Vendor payout policy is not a coverage filter. The job is to find bugs;
   the vendor decides what they pay for. A bug they don't pay for today may be payable after a
   fix, or on a re-test, or on a sibling endpoint.
2. **Tool-friction surrender.** A decode failed (BEAM 152-byte entries), an endpoint returned 500
   (CPI injection), a rate limit hit (arjun) — and the surface was dropped. **Rule: tool failure =
   find an alternative approach, not skip the surface.** BEAM was cracked in round 2 by recovering
   the IDL from on-chain zlib (§3d) and decoding entries with the correct struct layout.
3. **Checkpoint-as-claim.** PHASE_LOG said "0C COMPLETE" without an explicit tool→result ledger.
   **Rule: before writing "negative," publish the TOOL-COVERAGE LEDGER as a table** naming every
   tool run AND every tool not run with the reason. A silent omission reads as overclaim.

**The checklist that prevents it** (run before any "negative" conclusion):
- [ ] Every on-chain account type decoded (not just the obvious one — check ALL program accounts by size)
- [ ] Every oracle/price source analyzed (recover IDL from chain if no source repo — §3d)
- [ ] Every API endpoint tested with VALID bodies (not just `{}` — §1)
- [ ] Every write endpoint tested for auth bypass (build tx for arbitrary wallet, decode accounts)
- [ ] Every error message in the binary extracted and cross-referenced
- [ ] Recent on-chain transaction history checked for failed txs (0 failed = mature, N failed = leads)
- [ ] Upgrade authority / admin keys verified against documentation
- [ ] Race conditions tested on state-mutating endpoints
- [ ] Cross-token / value-mismatch operations tested (swap, merge, refinance)
- [ ] TOOL-COVERAGE LEDGER published (tool → result, including negatives and N/A)

Error-message differentials still discover the *header name* (`ApiKeyNotFound` absent vs
`Invalid or disabled API key` present-but-wrong pinned `X-Api-Key`). That step is orthogonal to the
ordering trap and remains valid.

### Corollary: 500 is not automatically an auth bypass

`POST /lending_vaults/create` returned an identical generic `500 Something went wrong` with and
without the credential header, and with a fresh random nonce. Same error both ways ⇒ internal error,
not a missing gate. Always compare with/without the credential before claiming anything from a 500.

### 1b. The error-LAYER differential: a 500 that names a persistence class IS a missing-filter signal

The corollary above kills *generic* 500s. The complement is the highest-value authz signal you can
get from a 500: **read which layer the anonymous request died in, and compare sibling routes.**

Measured 2026-10-29 on `customer-rest-services.api-docs.iot.telekom.com` (in-scope `*.telekom.com`),
a Spring Boot "M2M Customer API" documenting 46 SIM-lifecycle endpoints:

```
GET  /v1/partners                       -> 500  Could not initialize class at.compax.foundation.core.db.HikariDatasource$HikariDataSourceHolder
POST /v1/partners/1/sims/actions/block  -> 403  Forbidden
POST /v1/partners/1/sims/actions/activation -> 403 Forbidden
POST /v1/partners/1/sims/sim/sms        -> 403 Forbidden
GET  /v1/partners/1/sims/{iccid}        -> 500  HikariDatasource init failure
```

The 500 names a **DAO/datasource class**, which means the anonymous request was passed all the way
to the persistence layer. If an authentication/authorization filter existed on that path, the request
would have been rejected *before* the DAO was ever constructed. The write siblings answering `403`
prove the app-level authz filter is installed and working elsewhere — so the read paths are
selectively unfiltered, not universally broken.

**Why this is stronger than a generic 500:** the differential is *intra-host* (same app, same deploy,
same filter chain) and the error string is *layer-identifying* (`HikariDatasource`, `EntityManager`,
`SQLException`, `Redis`, `MongoTimeout`). Generic `Something went wrong` tells you nothing; a named
persistence class tells you the depth the request reached.

**Rules**

1. **Classify the 500 by its message.** Layer-identifying (persistence/driver/ORM class) = the handler
   ran past auth. Generic (`Something went wrong`, `Internal error`) = inconclusive, go no further.
2. **Always pair it with a write sibling on the same host.** The finding is the *contrast*
   (`GET`→persistence vs `POST`→403), never the 500 alone. Without the sibling you cannot distinguish
   "no filter anywhere" from "filter is selectively applied", and only the latter is a clean report.
3. **Do not claim data exposure from a 500.** The datasource was down, so zero records were returned.
   Report the *missing check* with the layer proof, state impact as conditional, and say explicitly
   that no data was retrieved (RoE-relevant on vendors whose policy forbids accessing data).
4. **Reproduce ≥2 clean rounds and log the failures too.** Byte-identical status + error shape across
   rounds is the bar; a round that dies at the TLS layer (`SSLEOFError: UNEXPECTED_EOF_WHILE_READING`,
   usually a WAF or connection reset) is a **non-result, not a negative** — record it as such rather
   than silently dropping or averaging it in.
5. **Write the evidence as a differential JSON, not prose** — host, per-request
   `{method, path, status, body, authorization_sent: false}`, and a `differential` block naming what
   each status proves. That artifact is what makes a "no auth on the read path" claim auditable when
   the backend is too broken to demonstrate impact.
6. **A public `/v3/api-docs` on the same host is the amplifier.** Spring Boot publishes it at
   `/v3/api-docs` *and* `/api-docs` *and* `/swagger-ui/index.html` — probe all three. Here it handed
   over the complete 46-endpoint map (SIM activation/block/suspend/termination, `limitoverride`,
   `simtransfer`, SMS send, `apiusage`, `/partners/{partnerId}/sims`) plus the owning team's mailbox.
   Schema disclosure alone is usually Low, but it converts an opaque 500 into a *named, enumerated*
   attack surface — which is what lifts the write-up out of "information disclosure".

Worked detail + evidence shape: `references/telekom-iot-m2m-authz-2026-10-29.md`.

### Corollary: a 422 on a cross-tenant probe is a REQUEST-SHAPE artefact, not an authz signal

The inverse of §1, and it produces the same wrong conclusion from the opposite direction. Measured
2026-10-26 on a share-link SaaS (cleanshot.com, two provisioned accounts):

```
DELETE /api/team/members/185794            body {"delete_mode":"x"}          -> 422 "selected delete mode is invalid"
DELETE /api/team/members/185794?delete_mode=transfer_and_delete               -> 403 "User is not part of your team."
PUT    /api/team/members/185794            body {role:"owner"}                -> 422 "selected role is invalid"
PUT    /api/team/members/185794            body {role:"member"}               -> 403 "User is not part of your team."
```

The first row *looks* like the request sailed past authorisation and died in validation — which
reads as "authz never ran, this is a finding". It is nothing of the kind. The parameter belongs in
the **query string**, not the body, and the enum values are `delete` / `transfer_and_delete`
(recovered from the bundle's `DeleteUserModal`, not guessed). Once the shape is right the tenant
check answers immediately and consistently.

**Rules:**
1. **Before treating a 422 on a cross-tenant probe as an authz bypass, find the real parameter
   shape from the client bundle.** Grep for the call site (`W.delete(\`team/members/${e.id}?delete_mode=${t}\`)`)
   and for the modal/enum that produces the value. The bundle is the authority on shape; your
   guess is not.
2. **A 422 that names a field is a schema oracle, not a gate report.** It tells you the handler
   reached validation. It tells you nothing about whether authz ran before or after — that is
   exactly what §1 says, and the fix is the same: send the schema-complete, correctly-shaped
   request and read *that* status.
3. **Re-probe with at least two valid enum values.** One valid value returning 403 could be
   coincidence; two different valid values both returning the same tenant error is the control
   holding. Record both rows.
4. **Log the artefact row too.** "422 with wrong shape → 403 with right shape" is a verified
   negative *and* a pitfall warning for the next session, which would otherwise repeat the
   false positive.

### Corollary: 504 on an unauthenticated heavy endpoint

`POST /lending_vaults/rewards/claim/all` on a vault with active reward schedules returned
`504 upstream request timeout` with no credentials, while the gated single-claim sibling returned
`200 []` instantly. A timeout on an unauthenticated call is evidence the server does real work for
an anonymous caller — record it, but it is not by itself demonstrated impact. Find the vault state
that makes the response non-empty before claiming data exposure.

## 1c. Guard-envelope fingerprinting: the error SHAPE names the gate you hit

On one host you can be facing several unrelated applications. The 401 *body* is the fingerprint that
tells them apart. Measured on `mainnet.api.cloud.ngrave.io` (2026-10-29):

| body | bytes | what it actually is |
|---|---|---|
| `{"message":"Unauthorized","statusCode":401}` | 43 | simple token/API-key guard (the swaps service) |
| `{"errors":[{"id":"<uuid>","status":"401","code":"MISSING_HEADERS","title":"Missing headers"}]}` | 149 | a **different** app with a JSON:API error envelope that requires *named headers* |
| `<html><title>401 Authorization Required</title>` (nginx) | 172 | `/docs`, behind HTTP basic auth at the proxy — not app code at all |

Consequences that change how you spend the session:

1. **Store the full body, never just the status.** Bucketing by `401` merges three gates and you aim
   every bypass at the wrong one. Same rule as the fuzz-status trap: shape is the signal.
2. **Look for the unguarded sibling in the same app.** `/api/v1/info` and `/health` answered `200`
   while `/api/v1/{currencies,portfolio,nfts,support}` on the *same* host demanded the header guard.
   Per-route guards mean the route namespace *is* the authz map — sweep all of it instead of testing
   one member and generalising.
3. **Presence-vs-validation test for a required header — this distinguishes two very different walls.**
   Send the header with a junk value:
   - still `MISSING_HEADERS` → the **name** is wrong; you have not found the header yet
   - flips to `UNAUTHORIZED` → the header **is** validated server-side, and a forged value fails
   Run this before concluding "auth is unbreakable". It is also how `X-Firebase-AppCheck` was
   identified from an app bundle and confirmed in one request.
4. **Firebase App Check is a cryptographic wall, not a decorative header.** Junk token →
   `UNAUTHORIZED` means the backend calls `verifyToken()`. Paired with Firebase Auth locked to Google
   SSO only (`accounts:signUp` → `OPERATION_NOT_ALLOWED`, anonymous → `ADMIN_ONLY_OPERATION`), the
   entire authenticated API needs a Play-Integrity-passing device plus a real Google account.
   **Report that as a coverage gap with the probes that prove it** — do not spend the session
   hammering a wall you have already shown is cryptographic. (Recovering the key/providers from an
   APK: `mobile-pentest` §2h-i.)
5. **`OPTIONS` → `200` while every real verb → `401` is not a bypass.** That is CORS preflight being
   answered before the guard. One line of notes stops the next session re-testing it.
6. **A route namespace that 404s everything is not an empty namespace.** `api.cloud.ngrave.io` did
   not resolve at all while `mainnet.api.` and `testnet.api.` served the same build — the flagship
   hostname was the dead one. Resolve every host from the bundle before concluding a service is gone.

### 1d. The X-Requested-With CSRF gate: a bare 403 on every write is a MISSING HEADER, not authz

FastAPI/JSON backends that harden state-changing routes with the `X-Requested-With:
XMLHttpRequest` header (a lightweight CSRF defence) answer a flat `403 {"detail":"Forbidden"}`
to EVERY `POST`/`PUT`/`PATCH`/`DELETE` sent without it — including cross-tenant BOLA probes that
would otherwise return `404 "…not found or not authorized"` or `200`. Measured on cubepath.com
(2026-11-02, FastAPI cloud API + React dashboard + OIDC SSO): `curl … -X PUT /projects/<victim-id>`
returned `403 Forbidden` for every write, which reads as "authorization holds everywhere". It was
the **missing header**, not a permission decision — and re-sending with the header flipped the same
probes to the real answer, exposing that I had nearly written a false "authz is solid" negative.

Rules:

1. **Before concluding "authz solid" from a bare 403, re-send with the header set:**
   `-H "X-Requested-With: XMLHttpRequest" -H "Origin: https://<dashboard-host>"`. The 403 flips to
   the real result: `200` (your abandoned probe was the bug) · `400 "Account not verified"` (the
   gate is a verification tier, not authorization) · `404 "…not found or not authorized"` (authz
   IS enforced and redacted — now you may claim the negative) · `403 "…not a member…"` (a real
   authorization refusal).
2. **The flip is diagnostic in both directions.** `403 → 404 redacted` is a *verified* negative;
   `403 → 200` is the false negative you almost walked away from. The bare `{"detail":"Forbidden"}`
   is byte-identical to a real refusal, so the **with/without-header differential is the only way
   to tell them apart** — the CSRF-header analogue of §1c's guard-envelope fingerprinting.
3. **Push through all three layers before classifying a write route.** Validation runs before the
   verification gate, which runs before authorization. curl without the header *and* without a
   schema-complete body (§1) gives 403; with the header gives `400 "field required"`; then `400
   "Account not verified"`; then the true result. Stop too early and you mislabel layer three.
4. **Two-account cross-tenant proof only reads correctly once the header is set.** Without it, every
   cross-tenant probe "properly 403s" and the §6 matrix produces a false SOLID verdict. Gmail
   `+alias` signup (e.g. `RESEARCHER_USERNAME+cubepathTA1@gmail.com`) works on many hosting panels and gives
   you the second identity; both must be yours, per §6.
5. **Tiered verification is a real gate shape worth naming in the coverage ledger.** Here the API
   had two flags: `email_verified` (email-confirm link — unlocks basic writes like SSH-key create)
   and `verified` (account/KYC/payment — unlocks deploy + API-token + DNS/CDN/storage writes).
   When the higher tier blocks the write plane, state it as a coverage gap (§9) — "deploy/billing
   surface untested: `POST /…` returns `400 Account not verified` and mass-assigning `verified:true`
   is whitelist-rejected" — never as "no findings".

Worked detail (hardened-target honest-negative + the header discovery + signup/Turnstile
automation): `references/cubepath-2026-11-02.md`.

## 2. Solana BPF-upgradeable program: decode the real upgrade authority

For "is this program actually governed by the documented multisig?" — do not trust a docs claim or
an account's `len == 0`. Decode the programdata account in three `getAccountInfo` calls:

```python
# 1. program account (base64) -> 4-byte slot + 32-byte programdata pubkey
slot        = int.from_bytes(raw[0:4], 'little')
programdata = b58encode(raw[4:36])

# 2. programdata account (base64) -> variant(4) + slot(8) + Option<pubkey> authority
variant  = int.from_bytes(pd[0:4], 'little')      # 3 = deployed/upgradeable
slot2    = int.from_bytes(pd[4:12], 'little')
has_auth = pd[12] == 1
authority = b58encode(pd[13:45]) if has_auth else None   # None => immutable
```

Then classify the authority address itself:

| on-chain state of the authority | meaning |
|---|---|
| `owner = SQDS4ep65T869zMMBKyuUq6aD6EgTu8psMjkvj52pCf`, `len ≈ 495` | real Squads multisig |
| `owner = 1111…1111`, `len = 0`, some SOL | **bare EOA — single key** |
| account absent | never initialised |

**Observed:** both the core lending program and the BEAM price oracle had their upgrade authority
set to the same bare system wallet (`len=0`, 3.49 SOL), while the address the docs named as the
"3-of-5 governance authority" was *also* a plain system wallet. A genuine Squads multisig existed
on-chain and executed operations (e.g. loan creation) but did **not** control upgrades. The finding
is the docs-vs-chain contradiction, and it is only provable by decoding the programdata account —
never by reading the docs or eyeballing the authority address.

**Re-check on every run.** Between two sessions the authority key was rotated to a *different* bare
EOA. Rotation is not remediation when the documented control is still absent; note both keys and the
rotation in the report so the vendor cannot claim it was already fixed.

3. **Market-config anomaly scan (lending protocols)**

`POST /oracles/data/market_informations` returns every market with per-asset config. `ltv` and
`liquidationThreshold` are **basis points where 1e6 = 100%** (`900000` = 90%). Scan for:

- `lqt <= ltv` — liquidation threshold must exceed LTV or positions liquidate instantly.
- `ltv > 0 and lqt == 0` — no liquidation protection at all.
- `ltv > 95%` on `verified` markets.
- `maxUncertainty > 20%` (and note whether `ltv == 0`, which makes it harmless).
- `maxAge` extremes — but check the oracle provider first: `loopscale_nav` at 65535 s (~18 h) is the
  NAV reporting cadence and by design; `pyth` at 900–1200 s is normal. Only flag a long `maxAge`
  when the provider's cadence does not explain it.

A clean scan (0 `lqt<=ltv`, 0 zero-`lqt`) is a **verified negative worth recording** — it proves the
control works and stops the next session re-running it.

### 3b. Transaction-builder API pattern (decode the server-built transaction)

Endpoints that build Solana transactions (`/creditbook/create`, vault fee/reward builders) return
the full base64 `serializedTransaction` in the `400` error body when on-chain simulation fails.
Decode it to inspect exactly what the server builds — account metas, instruction data, program IDs.
Search the raw bytes for injected parameter values to prove verbatim splicing (this is how the
`weightMatrixUpdate` lead was confirmed: `999999` = `0x000F423F` appeared 5× at offset 512).

**Corollary:** a `400 Transaction would fail on-chain` on a *valid body with no credentials* proves
the handler ran past auth — but only if the same body WITH credentials also reaches simulation.
Compare both before claiming anything. Worked detail: `references/loopscale-v2-2026-10-19.md`.

### 3c. Deployed sBPF bytecode decompilation (no source needed)

When the program source is closed but the IDL is public, extract the **deployed sBPF ELF** from the
programdata account and mine `.rodata` for instruction names, the full error enum, source file
paths, and `assertion failed:` invariants — then cross-check the auth model against the IDL's
signer flags. Also covers simulating a server-built transaction with `sigVerify: False` (and why
`InvalidAccountForFee` is an environment limit, not a program behaviour), and decoding a legacy/v0
transaction to prove an API built it for an arbitrary wallet.
Full recipe: `references/solana-sbpf-bytecode-decompilation.md`.

### 3d. Recover an Anchor IDL from on-chain zlib (no source repo, no PDA derivation)

When a Solana program's IDL is not in any public repo and `findProgramAddress(["anchor:idl"])`
fails, scan every program account for zlib-compressed JSON (magic `0x78 0x9c` at offset 44). This
recovers the full instruction list, account structs, and error enum from mainnet — read-only and
free. Worked example: BEAM oracle IDL + 133 price-entry decode + staleness-vs-maxAge cross-check.
Full recipe: `references/beam-oracle-idl-recovery-and-decode.md`.

## 5. DRF/Django self-enumeration and throttle scoping (hosting-panel pattern)

Django REST Framework APIs hand you the map for free, and their throttles are usually
per-endpoint — both verified live on a hosting control panel (djangoeurope, 2026-10-19:
55-endpoint DRF API + Angular panel, no published program).

1. **`GET /` on a DRF root returns the full endpoint index unauthenticated** — every router
   registration with its absolute URL. Dump it to disk; that is your complete probe list,
   including the sensitive names (`user`, `token`, `otpdevice`, `domain`, `sshkey`,
   `stripe/card`, `invoice`). No directory brute-forcing needed.
2. **Sweep every listed endpoint unauthenticated and classify**: `200` (open — usually
   reference data: language/country/timezone/imprint/plan), `401/403` (gated), `405`
   (exists, wrong method — note it), `404` (route absent). Record the classification; the
   open set is where info-disclosure findings live (`/server/` leaked hostnames, hardware,
   OS/package versions, hosting provider).
3. **Per-method permission check on the open set**: `POST` a minimal body to every
   GET-open endpoint. `401 Authentication credentials were not provided` = correct
   `IsAuthenticatedOrReadOnly`-style per-method permissions — log as a verified negative.
   A `200`/`201` on POST is the finding.
4. **Throttle scoping — check before concluding "blocked"**. Account-creation endpoints
   (`POST /user/`, `POST /test/`) carried a 24 h IP throttle (`429 Retry-After: 86399`)
   after anti-fraud rejection, but `POST /login/`, `POST /password_reset/`,
   `POST /contact/` and all GETs kept working. After any throttle, re-probe the *other*
   flows before declaring the surface blocked — the login/MFA/reset/contact paths often
   remain testable and are where enumeration oracles would live.
5. **Detail paths on open reference endpoints**: try `/doc/{slug}/`, `/faq/{slug}/` with
   published and unpublished-looking slugs. Slug-gated lookups that 404 cleanly on
   `unpublished`/`draft` = verified negative (no IDOR on hidden content).
6. **The Angular panel bundle is the endpoint oracle**: grep `panel_main.js` for
   `\.(get|post|put|patch|delete)\("([a-z0-9/_-]+)"\)` to recover every service call the
   UI makes — including routes the DRF root does not list (`/login/mfa/`,
   `/login/mfa/send/`, `/password_reset/`, `/test/`, `/su/`). Test each unauthenticated;
   MFA endpoints that return field-validation errors (not 401) are reachable but should
   validate a server-issued token before any processing — verify that ordering before
   claiming anything.
7. **Adjacent mail-surface check** (same engagement): SMTP `VRFY` and `RCPT TO` over
   STARTTLS that distinguish existing mailboxes (`252`/`250`) from unknown (`550 User
   unknown`) is a low-severity user-enumeration finding. Also test: anonymous FTP, open
   relay (`MAIL FROM`+`RCPT TO` external without auth), and whether `VRFY`/relay require
   STARTTLS (they should). Note rate-limiting on RCPT (connection closed after ~30
   probes) as a partial control — enumeration still succeeds within that budget.

### 5b. The browsable-API HTML form is the FK-choice oracle (slugs OPTIONS hides)

DRF's `OPTIONS` metadata tells you a field is `{"type":"field"}` and stops there — it does not tell you
*what value the field accepts*. `GET /<endpoint>/` with `Accept: text/html` renders the browsable-API
HTML form, whose `<select>` elements contain every foreign-key choice as
`<option value="<pk-or-slug>">label</option>`:

```python
r = requests.get(f"{API}/websitelocation/", headers={K: "Token " + TOK, "Accept": "text/html"})
for name, body in re.findall(r'<select[^>]*name="(\w+)"[^>]*>(.*?)</select>', r.text, re.S):
    print(name, re.findall(r'<option value="([^"]*)"', body))
```

Recovered on djangoeurope: `directive` FK accepts the **slug** (`root`, `redirect`, `proxy`, `uwsgi`,
`webdav`, `ws`, `error_page`, `svn`) — not a UUID, which is why three create attempts failed with
`"WebsiteDirective does not exist"` while the field was non-empty. The same trick enumerates the real
choice lists for `ip` (24 shared IPs), `systemgroup.server` (19 servers), `ssl.ca` (67 CAs), `dbuser.dbms`.

Two more things the HTML form gives you for free: the CSRF field name (`csrfmiddlewaretoken`), and the
**list of fields the UI actually posts**, which is often narrower than the serializer's write surface —
useful for separating mass-assignment candidates from fields nobody sends.

### 5c. Mint a long-lived API key immediately after MFA (escape token rotation)

Panels whose `/login/mfa/` returns a token that rotates on every login (and is bound to the `webkey`
cookie) make multi-hour testing miserable: one re-auth invalidates every in-flight script. Fix on the
first successful login — `POST /token/ {"description": "...", "expires_in": 2592000}` returns a key that
authenticates standalone, no cookie, for the whole engagement. Self-mints are safe to keep and cheap to
revoke; do not re-login for every probe.

Corollary trap: the MFA token is often **bound to the `webkey` cookie** — same `requests.Session` works,
a fresh session with only `Authorization: Token <t>` returns `Invalid API token`. That is not evidence
the token is wrong.

### 5d. Validation trust inheritance: child checks a parent row the caller just wrote

§1 covers body-before-auth ordering. This is the sibling failure: a child resource validates against a
*parent row the same caller created in the previous request*, so the composite path is unguarded while
each error message reads correct (`/website/` → "Domain does not exist. Add the domain and make sure you
have access to it." while adding a domain has no ownership check at all).

For every child resource, ask **"what am I validating against, and who wrote that row?"** Full class
recipe with the authoritative-DNS proof ladder (AA bit + unclaimed-name control query), the
record-publication upgrade (`POST /domainrecord/` → your own `A` record answers `AA=1`), the
publication-delay rule (**asynchronous — never write "immediately publishes"**; poll with timestamps),
impact-tier split, and cleanup discipline (revocation also lags ~15–20 s):
`references/unverified-ownership-and-authoritative-dns.md`.

### 5e. Metered-quota fields: the create path and the update path enforce DIFFERENT, both-wrong bounds

For any paid resource that has a quantity (RAM, disk, processes, seats, storage, bandwidth, API calls),
do **not** test one write path and generalise. Create and update are usually separate serializers with
separate validators, and the pair commonly fails in two different ways at once. Measured on
djangoeurope, X12 plan (2 GB RAM / 400 procs / 50 GB disk, 8.00 EUR/mo):

| path | payload | result |
|---|---|---|
| `POST /systemuser/` (create) | `limit_ram 64, limit_nproc 2000, limit_data 500` | **201 — no validation at all**; 500 became a 500G disk quota, 5x the platform's own 100 GB global cap |
| `PATCH /systemuser/<id>/` (update) | `limit_ram 8, limit_nproc 800, limit_data 80` | **200**, read-back `8.0 / 800 / 80.0` — 4x the plan |
| `PATCH /systemuser/<id>/` | `32 / 5000 / 500` | **400** `"Max RAM limit is 16GB"`, `"Max nproc limit is 1600"`, `"Max disk space limit is 100GB"` |

That third response is the finding in one line: **the validator knows how to refuse, and the number it
refuses is the platform's global ceiling — not the plan the customer paid for.** The plan value never
appears in any error because it is never read. So "the API rejects 32 GB" is NOT evidence the control
works; it is evidence the control is aimed at the wrong bound.

Recipe:

1. Read your own entitlement from the billing objects, not the marketing page — `GET /productinfo/`,
   `/plan/`, `/systemgroup/` gave `limit_ram 2.0, limit_nproc 400, limit_data 50.0, monthly_price 8.0`.
2. Write the *same* field on **both** paths: create a fresh resource with the field set, and PATCH an
   existing one. Different status codes on the same value = two validators.
3. Binary-search the refusal to find which bound is enforced: send a value above the plan but below the
   global cap (accepted => plan not consulted), then above the cap (refused => cap is the real bound).
4. **Prove it at the OS layer, not in the API response.** The API echoing `limit_ram: 64` proves only
   that a column was written. Create a **control resource with no overrides at all** on the same parent,
   SSH in as each, and diff what the kernel enforces:

```bash
ulimit -u                                                    # 2050 (override) vs 450 (control) vs plan 400
cat /sys/fs/cgroup/user.slice/user-<uid>.slice/memory.max    # 17179869184 vs 2147483648 vs plan 2 GiB
quota -s | tail -3                                           # 500G/550G block vs "none"
cat /proc/self/limits                                        # Max processes / Max open files
```

The control account matching the plan *exactly* is what isolates the client field as the cause — without
it you cannot distinguish "quota bypassed" from "quota broken for everyone".
5. **Also try the parent object** — `PATCH /systemgroup/` with the same fields returned **200 but was
   silently ignored** on read-back. A silent no-op is a *protected* path; say so, because it converts
   "quotas are fake" into "one specific per-user path is unguarded", which is a much stronger report.
6. **Do not consume the extra allocation.** Filling 16 GiB or 500 GB on a shared node degrades other
   tenants. State the aggregate risk (N users x cap) as argued, not measured, and say so explicitly.

Adjacent field-trust checks that usually come back clean — run them so the report can list them as
verified negatives: client-supplied SQL grants on `POST /dbuser/` (`perms="ALL PRIVILEGES ON *.* WITH
GRANT OPTION"` stored as `[]`), client-supplied `user`/owner on child objects (forced to the caller),
and impersonation fields on token creation (`su` => `400 "Does not exist"` for every foreign id).

## 6. Two-account IDOR matrix (username/tenant-scoped REST APIs)

For APIs whose paths embed the owner (`/api/v2/{username}/feeds`, `/api/v1/orgs/{slug}/...`) or
that gate on a per-user Bearer/API key, the empty-body and single-account probes cannot
distinguish "correctly scoped" from "accidentally open". The decisive test needs **two independent
identities** and a full CRUD matrix. Worked on Adafruit IO (2026-10-21, Rails, Bearer JWT from an
OAuth `access_token` exchange): result SOLID, documented as a verified negative.

1. **Provision account #2 on a genuinely independent address.** If the vendor canonicalizes
   `+` aliases (Adafruit: "The canonical form of your email is already taken"), use a disposable
   inbox — see `saas-test-account-provisioning` §1. Log account #2 into the target app once so its
   server-side profile exists (Adafruit IO only created the IO user record on first IO login; before
   that every `/api/v2/{user2}/...` answered "that username does not exist").
2. **Seed account #2 with private resources**: one feed/dashboard/group each, and confirm
   `visibility: private` in the create response. Note the numeric ids (they are usually sequential
   and make good cross-account probes).
3. **Run the matrix with account #1's token against account #2's resources** — every verb, not
   just GET:

   | probe | expected on a SOLID api | what a bug looks like |
   |---|---|---|
   | `GET /api/v2/{u2}/feeds` (list) | `200` with `[]` — private resources not listed | `200` with u2's private items |
   | `GET /api/v2/{u2}/feeds/{private-key}` | `404 "not permitted"` | `200` with the feed |
   | `GET .../feeds/{key}/data` | `404` | `200` with u2's data points |
   | `POST .../feeds/{key}/data` (write) | `404`/`401` | `200/201` — you wrote to their stream |
   | `PUT`/`DELETE .../feeds/{key}` | `401` | `200` — you mutated/deleted their resource |
   | `GET /api/v2/feeds/{id}` (direct id, no username) | `404` — path is owner-scoped | `200` — id-only access |
   | `GET /api/v2/users/{numeric-id}` | `404` | `200` with the user object |

   Record the matrix as a table with the exact status + error string per row. "SOLID" with that
   table is a deliverable — it stops the next session re-running the same eight probes.
4. **Direct-ID paths are the highest-value probe.** Owner-scoped APIs frequently forget the
   username-less route (`/api/v2/feeds/{id}`) or register it without the scoping middleware.
   Probe every resource type both ways: with the owner segment and by bare id.
5. **Discover enum values through the validation-error differential.** When a create endpoint
   rejects your payload with "Operator is not included in the list", send each candidate value in
   its own request and read which one flips the error. On Adafruit IO the trigger operators turned
   out to be the words `lt`/`gt`, not the symbols `<`/`>` — six symbol probes all failed, two word
   probes passed. The error string is a free oracle for the server's allowed set.
6. **Recover the schema from the app's JS bundle when the API docs are a JS shell.** The docs page
   returned 4.8 KB of shell; the trigger create-schema came from grepping the main app bundle for
   the form's initial-state object (`form:{id:null,feed_id:null,operator:null,...,trigger_type_id:
   null,trigger_type:null,...}`) — that literal is the exact field list the UI posts. Same trick
   recovers action-type enums (Adafruit triggers support to-feed / set-value / email actions only —
   **no webhook action**, which kills the SSRF hypothesis before you spend time on it).
7. **A `200` with an empty list is not the same as a `200` with data** — but on a list endpoint it
   IS the correct scoping behaviour and must be logged as such, not as "endpoint open".

### Corollary: the SSRF hypothesis dies at the action enum

Before building an SSRF PoC against any trigger/automation/webhook system, confirm the action type
exists in the deployed schema (§6.6). Adafruit IO's docs mention webhook *receivers* (inbound data
posts) while its trigger *actions* are to-feed/value/email — inbound receivers are a different
surface from outbound fetches. Reading the enum first saved a full SSRF workstream.

- **⛔ NEVER imply you hold keys for an on-chain address.** Public addresses recovered from RPC or
  from a previous engagement's probe script (borrowers, vault managers, upgrade authorities) are
  **strings you can put in an API header — nothing more**. The user asked directly
  *"wallet dr onchain v1 itu kamu bs akses?"* after a report leaned on "attacker wallet" framing.
  Search the engagement dir for keypair/cred files and state the negative explicitly before writing
  any impact narrative. `InvalidAccountForFee` on a simulation is the honest signal that you cannot
  sign; do not paper over it.
- **Rate limits are tight and per-IP.** A 126-endpoint probe 429s partway; a 30-endpoint
  valid-body probe 429s too. Run probes as background processes with ≥0.3 s spacing, and re-run the
  429'd subset after a cooldown rather than treating the gap as a negative.
- **`arjun` needs `--stable` on rate-limited targets** and its delay flag is `-d`, not `--delay`.
  Without `--stable` it prints "Target has a rate limit in place" and skips the endpoint entirely —
  which looks identical to "no hidden parameters found".
- **`nuclei` on an API host mostly yields nothing**; budget the run for the template count and read
  the error counter, not just `Matched: 0`.
- **`web_extract` may be search-only** depending on the configured backend; plain `curl` is faster
  for static docs/spec pages and needs no browser bring-up.

## 4. The vendor N/A pattern: fund-loss-scoped DeFi programs reject API findings

**The most expensive lesson of the LoopScale engagement.** All four v1 findings — a verified Medium
BOLA, an unauthenticated state write, an unauthenticated internal-data read, and a documented-vs-
on-chain governance contradiction — were rejected with the same sentence:

> *"It does not create a path to the locking, loss, or theft of funds, so it is not eligible for a
> reward under the program."*

Verbatim vendor replies (LoopScale Security, 2026-10-18):

| finding | vendor response |
|---|---|
| BOLA on user-scoped endpoints | *"reported to us previously and is tracked under that earlier report… does not create a path to the locking, loss, or theft of funds"* |
| unauth state write | *"reported to us previously and is already being addressed… does not create a path to the locking, loss, or theft of funds"* |
| unauth internal RWA read | *"not confidential: it corresponds to information that is discoverable on-chain, and the endpoints are read-only. This was also reported to us previously."* |
| single-key upgrade authority | *"consistent with our multisig setup… a program derived address with no private key, owned by the System Program with no account data"* |

### Rules

1. **Read the program's impact language before choosing a hunting surface.** If the brief says the
   primary focus is "to prevent exploits resulting in the locking, loss, or theft of any funds",
   API access control and info disclosure are near-certain N/A — no matter how clean the PoC is.
   Spend the budget on on-chain economic vectors instead (oracle manipulation, liquidation gaming,
   flash-borrow abuse, collateral pricing bypass, weight-matrix manipulation).
2. **"On-chain discoverable" is a standing rebuttal to any read-only API finding on a chain
   protocol.** Aggregation, computed analytics, and enumeration-friction arguments did not move the
   triager. Do not re-litigate this class.
3. **"Reported previously" kills duplicates even on NEW endpoints under the same root cause.** A new
   ungated sibling endpoint is still the same bug to the vendor if the fix is one middleware change.
   Only report a new endpoint when the root cause is genuinely different (different missing control,
   not the same missing middleware).
4. **Check the reply email before a re-run.** This session only discovered the N/A pattern after the
   user asked to look — the v2 findings (LS2-01/02) were then correctly dropped instead of written
   up. Reading vendor feedback first is a 2-minute step that saves a full report cycle.
5. **A governance/centralization finding needs a demonstrated fund path, not just a docs
   contradiction.** "Single key can upgrade the program" was reframed by the vendor as "Squads vault
   PDA, no private key" — technically disputable, but without a demonstrated theft path it does not
   meet their bar. Chain it to an actual exploit or drop it.

## 7. OpenAPI `security`-field triage: is anonymous reachability by-design or broken-AC?

Before reporting "endpoint X is reachable without auth = broken access control", read the API's own
OpenAPI/Swagger spec and classify the endpoint by its **declared** `security`. Learned on Zenya/iProva
(2026-10-24, .NET REST API, 1.9 MB spec); it was decisive for separating one real finding from two
by-design ones, and it is the step that stops a false "broken-AC" report.

**Round 2 on the same target (2026-10-30) added four rules that generalise to every spec-bearing API.**

**Rule 1 — read the vendor's CVD policy out-of-scope list VERBATIM before hunting.** Some vendors
pre-emptively declare the exact classes you would otherwise report. Zenya's policy states, in its own
words, that these are *not* vulnerabilities: "An API route that returns 200 without credentials, when
it serves one of the functions above"; "A different response for 'no credentials' than for 'invalid
credentials'"; "The public API documentation (OpenAPI/Swagger), feature flags and version
information" — and it explains that anonymous requests are handled as "a built-in anonymous account
that has no permissions", with routes anonymous users are not meant to use refusing it with 403.
Reading that paragraph first saved an entire session of filing by-design endpoints as broken-AC.
**Fetch the policy page and extract its exclusion list before the first probe**, then carry the
exclusions into the report so the triager is not surprised by a clause.

**Rule 2 — enumerate EVERY spec version, not just v1.** `GET /api/swagger/v1/swagger.json` is the
path every writeup names. On Zenya `v2`/`v3`/`v4`/`v5` also served, and **v5 held 538 paths against
v1's 428 — 112 routes that do not exist in v1** (the whole `/risks/*` module, `/users`,
`/users/password_requests`, `/agents/*`, `/support_access`, `/tokens/*`). Sweeping only v1 would have
missed every one. Probe `v1..v6` (a 404 on v6 is the terminator), diff the path sets, sweep the union.

**Rule 3 — a feature-gate error is an authz-ordering probe, and `/features` is its oracle.** When a
gated endpoint answers `400 "License required"` or `400 "Consent required"` to an *anonymous* request
instead of `403`, the authorization check is running **after** the licence/consent gate. On Zenya
`POST /api/agents/chat` answered "License required" on 131 of 164 tenants and "Consent required" on
one — only when both gates passed did the real `403` appear. Pair it with `GET /api/features/<name>`
(anonymous here too, returning `has_license` / `feature_switch_enabled` / `consent_enabled` /
`all_dependencies_enabled`) and any tenant's entitlement state is mappable without a credential. The
policy excluded it as "feature flags", but the ordering is a reusable signal: **an error naming a
licence, consent, plan or quota proves the request reached application logic and the authz gate sits
behind it.**

**Rule 4 — a sanitizer that takes a caller-controlled allowlist is bypassable by design.** See §7c.
Fetch the spec once — `GET /api/swagger/v1/swagger.json` (also `/openapi.json`, `/api/swagger` which
may 301 to `/api/swagger/index.html`). Then per operation:

| `security` value | meaning | action |
|---|---|---|
| contains an **empty `{}`** (e.g. `[{}, {basic}, {bearer}]`) | anonymous access is an ALLOWED option → **by-design anonymous endpoint** | do NOT report reachability as broken-AC |
| `<global>` / inherits `[{basic},{bearer}]`, no `{}` | **auth-REQUIRED** per spec | test anonymously; a 200-with-data here IS a broken-AC candidate |

```python
sw = requests.get(f"{T}/api/swagger/v1/swagger.json").json()
def anon_allowed(path, m='get'):
    sec = sw['paths'].get(path,{}).get(m,{}).get('security','<global>')
    return sec != '<global>' and any(s == {} for s in sec)
```

Then **systematically sweep the auth-required set anonymously** and flag any 200-with-data. On Zenya,
226 auth-required GET endpoints swept → only `/themes` leaked (trivial theme metadata, likely needed
by the pre-auth login page → still by-design). The other 225 returned 403/empty/404 = **verified
negatives**. That sweep is what let me honestly write "no significant broken-AC" instead of guessing,
and it is the concrete form of the premature-negative protocol in §6a.

### 7b. Multi-tenant estates: the tenant is the subdomain, and the Host header is the routing key

Zenya/iProva is SaaS-per-customer: every customer gets `<customer>.<vendor>.work` and the API lives at
`https://<customer>.<vendor>.work/api`. 165+ tenants were enumerable with one `subfinder -d` call
(hospitals, labs, care organisations). Three things this changes:

1. **Confirm isolation by overriding the Host header, not by trusting it.** Send a request down
   tenant A's connection with `Host: tenantB.<vendor>.work`. If the edge routes on Host you get tenant
   B's data (correct); if you get A's data the header is ignored (also correct). Then repeat with
   `X-Forwarded-Host`, `X-Original-Host`, `X-<Vendor>-Tenant`, `X-Tenant-Id`, and `?tenant=`. On Zenya
   every spoof header was ignored and only the real Host routed — a clean verified negative worth one
   table in the report.
2. **The token endpoint binds to whatever Host you send.** `GET /api/zenya_url_tokens` returned a JWT
   whose `tenant_id` and `Zenya_domain_url` claims matched the Host header (118 for trial, 806 for
   lumc). That is consistent routing, not a bug — but it means a token minted through a Host override
   is scoped to that tenant, so test whether it is *accepted* anywhere else before claiming anything.
   Here it was rejected with 401 on every protected route.
3. **Anonymous configuration differs per tenant, so sweep the estate, not one host.** `/api/objects`
   returned card-file data on some tenants and 403 on others; `/agents/chat` answered "License
   required" on 131 and 403 on 30. One tenant tells you nothing about the platform default. A
   165-host sweep at concurrency 4-5 with ~0.3 s spacing is cheap, and it is what turns "this endpoint
   is open" into "open on N of M tenants — which is / is not the platform default".

### 7c. Sanitizer APIs with a caller-controlled allowlist — and how to prove (or kill) the impact

`POST /api/sanitizer` on Zenya takes `{"input": "<html>", "whitelisted_nodes": [{"name": "...",
"attributes": [...]}]}`. Default behaviour is strict — `<script>`, `onerror`, `onload`, `onclick`,
`<iframe>`, `<meta refresh>` and `<style>@import>` are all stripped, and `<b>` is rewritten to
`<strong>`. But the caller supplies the allowlist, so:

```
{"input":"<img src=x onerror=alert(1)>",
 "whitelisted_nodes":[{"name":"img","attributes":["src","onerror"]}]}
→ {"result_code":"ok","result":"<img src=x onerror=alert(1)>"}
```

`result_code: "ok"` means "no changes were needed" — the caller is being told the payload is safe. The
same trick passes `<svg onload>`, `<div onclick>`, `<iframe src>`, `<meta http-equiv=refresh
content="javascript:…">` and `<link rel=stylesheet href=…>`. **A sanitizer must never let the caller
whitelist `on*` attributes or resource-loading elements; that is the entire control, handed over.**

**The impact-verification step that decides Medium vs noise:** before claiming stored XSS, establish
whether anything actually consumes the endpoint. Grep the target's own JS bundles:

```python
for b in bundles:
    if re.search(r'sanitize-|DOMPurify|\$sanitize|dompurify', b): print("client-side sanitizer:", b)
```

On Zenya the front-end imported `./sanitize-*.js` and called `e.$sanitize(...)` — i.e. **DOMPurify in
the browser, not the API**. The API sanitizer was therefore not on the stored-content path, and the
honest finding is "the endpoint is bypassable; impact depends on consumers I could not enumerate
without credentials" — Medium with a stated caveat, not a High. Filing it as proven stored XSS would
have been the false positive.

Report shape: the bypass (with the control run showing the same payload stripped when the allowlist is
omitted), the design rule it violates, and an explicit statement of which consumers were ruled out and
which remain untested.

### 7d. Anonymous WRITE endpoints: the business-object error text is the reachability oracle

§1 covers validation-before-auth on authenticated routes. The same ordering trap runs in the opposite
direction on the **anonymous perimeter**, and the tell is different: a write route that answers a
*business-object* error rather than `403` has already let you past the gate.

Measured on Zenya/iProva (2026-10-30, round 3), `POST /api/cases` — the public anonymous
incident-report form:

| tenant | body | response | reading |
|---|---|---|---|
| `trial` | `{form_id:151, fields:[…]}` | `404 Not Found` | route not deployed for anonymous use |
| `zgvtest`, `dedimo`, `treant`, `sherpa`, `radboudumc`, `sevagram-test` | same shape | `400 "Form is not found"` | **handler ran** — auth passed, died in lookup |
| `trijn`, `heilighartlier`, `arubahospital`, `lunetzorg`, `meandermc`, `mgzl`, `haprijnmond` | valid form_id | `400 "Case type of the form does not allow reporting new cases"` | handler ran, business rule refused |
| `azsintblasius`, `meandermc` | valid form_id | `400 "The reporter form is not enabled"` | handler ran, feature flag off |

**Rules:**

1. **A 400 naming a business object proves reachability.** `"Form is not found"`,
   `"Case type … does not allow reporting"`, `"The reporter form is not enabled"`,
   `"License required"`, `"Consent required"` — every one of these is emitted *after* the
   authorization middleware. A `403 "Anonymous user not allowed"` is the only answer that means
   "gated". Sweep the whole estate and bucket by error *text*, not status: `400` splits into
   "reached the handler" and "schema rejected my body", and only the first is interesting.
2. **The error text is a free object-model oracle.** `"Field 1 has an invalid value"` +
   `extrainfo: ["Subject with name or external id 'probe' not found"]` disclosed the field's real
   type and lookup semantics without any credential. Keep adding fields until the message changes.
3. **Mass-assignment on an anonymous create is worth one probe, and usually closes clean.** Send a
   `field_id` that is not in the form:
   - `999999` → `400 "Non existing field_id 999999 found"` — membership validated
   - `2`, `3` (valid ids, wrong form) → `400 "Illegal field passed"` — form-scoped
   - extra top-level props (`state`, `case_id`, `reporter_id`) → ignored
   Record all three as verified negatives; they are what let you write "no mass assignment" instead
   of "untested".
4. **Find the valid identifiers from the anonymous read surface first.** `GET /cases/reporter_forms`
   returned `form_id` + `case_type_id` + `visibility: public` for 20+ tenants, and
   `GET /cases/case_types/{id}/fields` returned the full field list — so the write probe was built
   from the target's own contract, not guessed. Do the read sweep before the write sweep.
5. **Do not create data you cannot read back.** A `201` on an anonymous create proves nothing about
   stored-XSS impact when you have no authenticated view to re-read it. State the limit explicitly
   rather than claiming the chain.

### 7e. Third-party SaaS platforms on an in-scope subdomain — classify by ASSET ORIGIN, then declare OOS

The eligibility gate above checks TLS `CN`. On modern estates the faster tell is **which domain the
page's own assets come from**, because a SaaS platform always loads its runtime from its own host.

| asset origin in the page | platform | what the host really is |
|---|---|---|
| `static.homerun.co/employers/v3/*.js`, `feed.homerun.co/<org>` | **Homerun** | careers/ATS site |
| `portal-library.devrev.com/_next/static/chunks/remoteEntry.js`, `x-devrev:` response headers | **DevRev** | support/ticketing portal |
| redirect to `sentby.spotler.com/sendpro` | **Spotler** | transactional email |

Three consequences:

1. **Declare it OOS before spending probes.** Most CVD policies exclude "services running at third
   party service providers". Zenya's does, verbatim. `werkenbij`, `e`, and `support` were all
   third-party-operated despite living on `*.zenya-software.com`.
2. **Beware the SPA catch-all masquerading as a finding.** On the Homerun host,
   `/wp-json/wp/v2/users` returned 35,011 bytes — byte-identical to the homepage, i.e. the SPA
   shell, not a WordPress user list. `sha256` the body against `/` before believing any path result
   on a catch-all host (same rule as §1c/`bounded-exposure-sweep`).
3. **A 302-to-third-party at the edge leaves no pre-redirect surface.** `update`, `status`, `my`,
   `community` all 302'd to `infoland.eu/.nl` for *every* path including `/.env`, `/wp-login.php`,
   `/xmlrpc.php`. Probe three sensitive paths once; if all three 302 identically, the host is a
   redirector and is closed.

### 7f. Module Federation portals: the portal origin has NO API surface — stop probing it

When a Next.js app loads `remoteEntry.js` from a third-party domain it is a **micro-frontend host**:
the route components are fetched at runtime from the vendor, and every data call is made by *that*
code against *that* vendor's origin. `support.zenya-software.com` served 19 routes
(`/[portalSlug]/directories/[directoryId]`, `/hc/[lang]/articles/[articleId]`,
`/[portalSlug]/[revSlug]/tickets/…`) and **every one of them was a dead end on its own origin**:

- `/api/v2/*` → the Next.js catch-all page (including `/api/v2/tickets`, the one non-404)
- `/internal/rev-users.self.get`, `/internal/parts.get`, `/internal/projects.get`,
  `/internal/custom-objects.get`, `/internal/plug-settings.get`,
  `/internal/translations.languages.list`, `/internal/experience.toggles.get|set` → **all 404**
  here, because the micro-frontend calls them on the DevRev origin
- `/directories/1` … `/directories/5` and `/directories/abc` → byte-identical 13,053 B
  (client-rendered, no server-side IDOR)
- `/hc/nl/articles/1` … `4`, `abc` → byte-identical 6,782 B
- `portalSlug` reflected XSS → `406` at the edge

**Tell:** the `webpack` chunk contains `https://<vendor-domain>/_next/static/chunks/remoteEntry.js`,
or response headers name the vendor (`x-devrev: backend=support,slug=zenya`). Once you see it, the
profitable move is to enumerate the *vendor's* origin (and its own CVD programme), not to keep
fuzzing `/api/*` on the customer's host. `_buildManifest.js` still gives you the complete route list
for free — use it to prove the surface is client-rendered, then stop.

Worked detail for round 3 (anonymous write sweep, third-party classification, Module Federation
dead-end proof, the nuclei concurrency diagnostic): `references/zenya-iprova-2026-10-30-round3.md`.

### 7g. The acting-user-in-URL parameter: existence is checked, ownership is not

Some endpoints take the **actor** as a request parameter instead of reading it from the session —
typical of "server-to-server" APIs and of AI-agent submission endpoints that publish copy-paste
instructions. `POST /api/vulnerability/aisubmit?userId=<id>` (Scribble Maps, 2026-10-31) resolved the
supplied id, verified it existed, and filed the record against it. The session was never compared.

**The oracle is validation-error ORDER, and it costs three requests:**

| userId sent | response | meaning |
|---|---|---|
| your own id | `400 {"error":"Title is required"}` | reached field validation → authz passed |
| **a different account's id** | `400 {"error":"Title is required"}` | **same stage as your own → ownership never checked** |
| a non-existent id | `400 {"error":"Invalid userId"}` | existence lookup, one stage earlier |
| omitted | `400 {"error":"userId is required"}` | presence check, earlier still |

The distinguishing signal is that the *foreign* id produces byte-identical output to your own. If a
foreign id produced the same "invalid" error as a nonexistent one you would have a well-scoped
endpoint; identical-to-own is the bug.

**Then prove attribution, not just acceptance.** Send ONE complete, clearly-labelled submission using
the second own account's id, and read what the response says:

```
POST /api/vulnerability/aisubmit?userId=<victim-own-id>   (multipart: title, description, attachments)
200 {"success":true,"pendingConfirmation":true,"referenceId":"6F50F5",
     "message":"... We've emailed fz***********@gmail.com a link to approve this submission ..."}
```

The masked address in the message belongs to the **resolved** user, not the caller — that single
sentence proves the record was bound to the other identity, which "200 OK" alone does not.

**Ethics/mechanics for that write test (mandatory):**
1. **Both identities must be yours.** Never file a record into a stranger's account to prove it.
2. **Label the artefact in its own content**: title prefixed `[TEST - ignore]`, description saying
   "authorization test, both accounts belong to the researcher, please delete after triage". It lands in
   a human triage queue; make deletion trivial.
3. **Expect and report the rate limit honestly.** These portals often cap one report per day per
   *network*, so the third repetition returns `429 "Too many submissions from your network"`. That is a
   network-scoped throttle, not an account-scoped one — do not claim "victim's quota exhausted" from it
   without a second network.
4. Submitting is the *only* way to prove attribution here; do it once, then stop.

**Impact framing.** Not data exposure — it is **Integrity/attribution**: reports (with referenceId and
free-text) created under another researcher's identity, the victim's daily allowance consumed, and the
victim receiving an unexpected "approve your submission" mail that files it in their name if clicked.
`AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:L/A:L` = 5.4 when the write path is authenticated. Tie it to the
program's own forfeiture rules (duplicate/misrepresentation) — that is what makes a triager care.

**Remediation to recommend:** derive the actor from the session and ignore the client-supplied id
(403 on mismatch, not silent substitution); bind the approval token to the session identity as well as
the report id; rate-limit per account, not per network.

Worked detail for the whole round: `references/zenya-iprova-2026-10-30-round2.md`.

### The `{}` nuance: api_key-model endpoints
An endpoint with `{}` that ALSO takes an `api_key` in the body (e.g. `POST /tokens`) is not "anonymous
enumeration intended" — the `{}` reflects that it authenticates via api_key, not basic/bearer. The bug
there is **validation order**, not reachability: if the handler checks username existence and returns a
differential (`"User not found"` vs `"Invalid api_key passed"`) BEFORE validating the api_key, that is
a CWE-204 enumeration oracle reachable with a dummy api_key. Report the *order* (leak-before-auth), not
"the endpoint is anonymous".

### Sibling-consistency is the tie-breaker
When endpoints share a schema/`{}` marking but behave differently anonymously, the one returning data
while its sibling returns empty/403 is the outlier — a candidate. On Zenya `/cases/fields` returned 612
rows while `/objects/data_types`, `/objects/custom_fields`, `/cases/case_types` (same `{}`) returned
`[]`. But the outlier was explained by "the public FLOW report form needs the field schema," so it was
by-design, not a bug. Use sibling behaviour to *find* candidates, then confirm intent against the
policy/spec (§ `artifact-backed-claims` "by-design" rule) before claiming. A schema/metadata endpoint
that is `{}`-anonymous and returns definitions (not records) is almost always by-design.

### 7-Swagger. Public Swagger UI over a GATED API = spec disclosure only, not "unauthenticated API"

The most tempting false positive in this whole class: `/api/v1/doc/` serves Swagger UI to anonymous
users, `/api/v1/openapi.json` returns a 290 KB spec listing 81 operations including
`POST /vistacockpit/stopProduct/{product}/{host}` and `stopWorkflow/{jobId}`. Every instinct says
"unauthenticated access to a destructive internal API". Measured on `on1.perf-mgmt.telekom.net`
(2026-10-29) it was **nothing of the kind** — and the two checks that proved it take four requests.

**Check 1 — the operations, not the UI.** Swagger UI is a static bundle; serving it anonymously says
nothing about the handlers behind it. Probe a sample of the declared paths:

```
GET /vistacockpit/products   → 401 {"status":401,"message":"Unauthorized"}
GET /vistacockpit/hosts      → 401
GET /vistacockpit/status     → 401
GET /vistacockpit/workflows  → 401
GET /vistacockpit/jobs       → 401
GET /vistacockpit/productEvents → 401
```

6/6 gated. The finding is the **spec**, not the API.

**Check 2 — the bogus-identifier write test (this is the useful new discriminator).** Send a mutating
operation with an identifier that cannot exist:

```
POST /vistacockpit/stopProduct/zzz-notreal-x4hd2k9pq/host-notreal-x4hd2k9pq  → 401
```

`401` and not `404` means **authentication is evaluated before the identifier is looked up** — the
handler never got as far as resolving the product. That ordering is correct and it kills the
"destructive action reachable" hypothesis in one request.

| bogus-ID status | what it proves |
|---|---|
| `401` | auth precedes lookup — correct, no finding |
| `404` | auth is **after** the lookup — the endpoint is an existence oracle for real IDs |
| `403` | authenticated but unauthorised — correct |
| `200` / `500` | the handler ran — a real finding, escalate immediately |

**⛔ Never use a real identifier for that probe.** `stopProduct` / `delete` / `terminate` with a
plausible real value is an availability attack on production, whatever the auth outcome. Placeholder
identifiers (`zzz-notreal-<random>`) give you the ordering answer with zero blast radius. If you
cannot think of a safe identifier for an operation, do not send it — a read-only sibling answers the
same question.

**Third thing to check before writing anything: does the leaked spec name internal hosts, and do they
resolve?** Here the spec's `servers`/oauth blocks gave `http://ivporosp51/api/v1` and
`http://ivporosp51.itenos.biz/SSO/oauth2/*`. Both returned `gaierror` from public DNS, so there is no
pivot from the internet. Internal-hostname disclosure in a spec is only a finding when the name is
resolvable or reachable from where you sit — test that, don't assume either way.

**Verdict shape for this case:** Low / informational — schema disclosure + internal naming, no auth
bypass, no data, no pivot. On a programme whose table pays P1/P2/P3 only, a Low earns nothing and
consumes a triage slot; record it in the negatives ledger and tell the operator it exists rather than
staging a report unasked. Distinguish it explicitly in the write-up from the *good* version of this
finding (finding §1b of this skill): there the read handlers returned `5xx` from behind the auth layer,
which is proof the filter was missing. Here everything answers `401`, which is proof it is present.

### 7a. The full sweep: spec discovery → declaration → live probe → chain

§7 classifies *one* endpoint you already suspect. When the target publishes a full spec, run the
whole surface instead — it is one request for the spec plus ~180 cheap probes, and it finds the
endpoints you would never have thought to test. Worked on RunOnFlux (2026-10-27): 339-path spec,
180 no-auth-declared operations, **169 live-200 unauthenticated**, and the High IDOR sat on a
*sibling API host* (`api.titan.<t>`) whose routes appear in no spec at all.

Full recipe — spec discovery by grepping the docs HTML for `/fluxapi.json`-style links, the
three-bucket declaration split (`security: []` vs `security: [{'Scheme': []}]` vs undeclared),
the placeholder-param live sweep, the error-string layer oracle, the GET-open/POST-gated
inconsistency as the reportable shape, and the identifier-leak → per-identifier-detail chain:
`references/openapi-auth-surface-sweep.md`.

Three rules worth carrying inline:

1. **`security: []` is not `{}`-in-a-list.** `[]` is an explicit "no auth" statement; `[{}, {basic}]`
   means "anonymous is one allowed option among others". Both need live probing, but `[]` is the
   stronger prior and the easier one to over-report.
2. **A 200 carrying an error envelope still proves unauthenticated reachability.**
   `{"status":"error","data":{...}}` on a declared-public route means the handler ran — that is the
   signal, not a reason to discard the row.
3. **Probe sibling API hosts, not just the flagship.** `api.<t>.io` / `api.<t>.com` often mirror each
   other while `api.console.<t>` / `api.titan.<t>` / `api.paposse.<t>` are separate deployments with
   separate route sets and weaker gates. Recover their routes from the frontend bundle when no spec
   exists, and keep concurrency at 8 — a parallel ffuf run on the same estate drew Cloudflare
   `1015` rate-limits and burned a host for the session.

## 8. API generation parity: the LEGACY route is often the one missing the ACL

When a product ships two generations of the same resource (`POST /mutablerecords` **and**
`POST /mutablerecords/v2`, `/api/v1/x` **and** `/api/v2/x`, `/rest/x` **and** `/rest/v2/x`), the newer
one usually carries the authorization middleware added after launch, and the older one is still routable
because shipped clients have not fully migrated. Test them as a **pair**, never as one endpoint.

The parity matrix that turns this into a finding (Hivenet mutable-platform, 2026-10, High 7.1):

| probe | v2 | v1 |
|---|---|---|
| create with **foreign** tenant id in body | `403 User does not have access to this V2 document` | **`201 Created`** |
| bulk create, same payload | `403 transaction failed ... does not have access` | n/a (no bulk gate) |
| create with a **fabricated** id | n/a | `400 inserting mutable record` → existence-only check |
| create with an existing id | — | `409 Duplicate key` (so no upsert/overwrite path) |
| GET of another tenant's unshared object | `403` | `404` (read side is scoped — log as negative) |

Reading the matrix: v1 checks that the object **exists** and not that the caller **owns** it. That is
the whole bug, and it is provable in four requests. Write-side impact is real even when the read side
is clean, because the row lands in the victim's namespace (`/…/{victimId}/children` returns it to the
victim) and, if the legacy row cannot be addressed by the v2 delete/expire routes (`405` / `404`),
**the victim cannot remove it**.

### How to find the pair cheaply

1. **Grep the client bundle for sibling paths**, not for one path:
   `re.findall(r'["\'`](/[A-Za-z0-9_\-./{}$:]{2,70})["\'`]', bundle)` then filter
   `v1|v2|v3|legacy|compat|deprecated|old`. API-client codegen (openapi-generator `XxxApiAxiosParamCreator`)
   leaves every route as a literal in one place — that is the complete map, including routes the UI no
   longer calls.
2. **Diff the *shape* of the two handlers.** v2 payloads often gained `contentVersion`/`version`
   fields and `x-trace-id`; v1 takes the raw row. A field the newer payload requires but the older one
   accepts is a tell that they are different code paths.
3. **Compare error *vocabulary* per generation**: `"does not have access to this V2 document"` vs
   `"inserting mutable record"` — differing strings mean differing middleware, and the weaker one is v1.
4. After any success, **re-read the object through the victim's own authenticated view** (its listing
   endpoint, not the attacker's). "201 Created" is not the finding; "the victim sees the row" is.

### The same shape in zero-knowledge storage / file-share products

If the product is client-side encrypted, the namespace write is only half the impact — show that the
injected object is *decryptable* by the link holder. In products of the Send / Drive / share-link
family the folder key is usually derivable from public share metadata (here:
`readKey = PBKDF2-SHA512(password = share.name, salt = share.rootMid, 1e6)`), and per-object keys sit
in `encryptedBlockKey` fields decryptable with it. Derive it, decrypt a victim chunk to prove the
derivation is right, then craft the injected object with an attacker chunk + attacker-chosen encrypted
name. Two implementation traps: AES-GCM blobs are `nonce(12) || ciphertext`, and inner keys come back
as **hex strings** — `bytes.fromhex()` before use or you get `key must be 128/192/256 bits`.
Worked detail: `bug-bounty/references/hivenet-2026-10-engagement.md`.

### Severity honesty for this class

Namespace-write-only is **Integrity**, not Confidentiality. Score
`AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:L` and keep the availability leg low unless you can reproduce
quota exhaustion on demand (Hivenet: seen once, not reproducible → A:L and said so). Do not inflate to
Critical on the strength of "cross-tenant" alone; the triager will ask what was read.

## 9. Tenant-substitution sweep: the admin SPA bundle IS the cross-tenant test plan

For any multi-tenant product whose routes embed the tenant (`/v1/companies/{company_id}/games/{game_id}/…`),
the admin SPA bundle ships the vendor's own codegen'd client — every route, including ones the UI never
calls. That converts "hunt for BOLA" into a mechanical 240-request matrix. Verified on a DTC
payments/liveops platform (Aghanim, 2026-10-27): 13.5 MB bundle → 389 `/v1/…` paths → 352 tenant-scoped
→ one sweep, 240× `403`, 3 false-positive `200`s, 0 findings — and the negative is *trustworthy* because
every route was hit.

Runnable: `scripts/tenant_sweep_from_bundle.py` (extract → substitute → sweep → auto-diff the 200s).

### Extraction: they are BACKTICK literals, not string literals

```python
paths = sorted(set(re.findall(r'`(/v1/[^`]{2,120})`', bundle)))     # 389 here
# a ["']…["'] regex returns ZERO on the same bundle — try both, the client is template-literal based
scoped = [p for p in paths if '{company_id}' in p or '{game_id}' in p]  # 352
```

Also grab the base path from the SDK init (`setConfig({baseURL:'https://dashboard-api.<t>/dashboard'})`)
— the same host often serves several prefixes, and `/dashboard/v1/...` vs `/v1/...` misses everything.

### Sweep rules

1. Substitute **your** company/game ids → **victim** ids, and replace every remaining `{param}` with one
   fixed junk value (`aaBBccDDeeFF`, never a guessable real id — §4.2.14 kills identifier-guessing
   findings anyway).
2. GET only, concurrency ≤ 6, one pass. Bucket by status and **write the bucket counts down**:
   `403` = tenant gate holding; `405` = route exists, wrong verb (the bundle has the right one);
   `404` = not registered in prod; `400/422` = schema reached (that is §1, not a bypass);
   `200` = candidate, go to the diff step.
3. Skip `/v1/admin/...` on the first pass (usually global-admin and it 403s on everything); run it second.

### ⛔ A cross-tenant `200` is a CANDIDATE, not a finding — diff it against your own tenant first

Three of the 200s here were **global/template data**: `email_templates`, `creators/platforms`,
`creators/platforms/define`. Fetching the identical path with *your* company id returned a
**byte-identical body** (per-record `md5(json.dumps(rec, sort_keys=True))` matched for all 7 templates).
A shared template catalogue is not another tenant's data — reporting it is a self-inflicted false positive.

The classification step is two requests:

| same path, my id | same path, their id | verdict |
|---|---|---|
| `200`, body A | `200`, body A (hash-equal) | global/by-design → drop |
| `200`, body A | `200`, body B | **real cross-tenant read** → escalate |
| `403` | `200` | **sibling inconsistency** → escalate, §7 tie-breaker logic |

Corollary: if your own tenant is *empty* (fresh sandbox company with no data), the diff is inconclusive —
say so, and prefer a sibling-based argument or a second victim-visible projection over a body-diff claim.

### Header-scoping bypass, one request each

The SPA sends tenancy in headers too (`X-Company-Id`, `X-Game-Id`, used for upload/analytics scoping).
Re-run the sweeps with the victim's header values on the path that already carries the victim id, and with
*your* url id + victim header. On this target the header changed nothing (403 both ways) — one request
each, and it closes the "maybe it trusts the header" question permanently.

### Role is the other axis, and it is the real coverage gap

Every write (`items`, `coupons`, `api_keys`, `customer_roles`, `game_settings`) answered `403` for the
auto-provisioned read-only `user` role, and `POST …/api_keys` (the S2S credential that unlocks a whole
179-operation API) was equally gated. **When the role ceiling blocks the write plane, that is the finding
to state as a coverage gap** — "write surface untested: cannot obtain write role without an invite/creator
path" — never as "no findings". Record which credential you lacked and which endpoints it would have
unlocked, so the next session starts at that gate instead of re-deriving it.

### 9a. "200 OK" is not "applied" — verify writes through the POST projection, not the echo

The companion trap in the same session. `PATCH /order/v1/orders/{id}` returned the **full order object,
`200`**, while silently ignoring every field sent — `items[].price`, `items[].quantity`, `amount`,
`total`, `subtotal`, `currency`, `payment_amount`, `email`, `return_url`, `player_id`, `user_id` — and
only honoured `country` (which then re-priced *correctly* across IDR/JPY/USD/BRL/TRY/NGN).

Two rules:

1. **Re-read state before believing a write.** `GET /order/v1/orders/{id}` was `405`; the read oracle was
   the SPA's own projection `POST /order/v1/orders/{id}/resolve` (grep the bundle for the path the page
   renders). When the GET sibling is 405, the POST projection is the canonical state read — use it.
2. **A `200` that echoes your payload is not even weak evidence.** Echo + silent-drop is the *designed*
   behaviour of allow-listed PATCH handlers (Pydantic `model_config = {'extra': 'ignore'}`). The status
   code tells you the route ran; only a re-read tells you the field landed.

Worked detail and the full negative matrix: `references/aghanim-2026-10-engagement.md`.
