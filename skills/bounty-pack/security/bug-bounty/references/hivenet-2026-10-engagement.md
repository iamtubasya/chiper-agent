# Hivenet — engagement notes (2026-10-25/26)

Programme: privately managed by HIVE COMPUTING SERVICES SA, brand "Hivenet".
Policy: https://www.hivenet.com/bug-bounty (last updated 24 Sep 2026).
Submit: **bugbounty@antimatter.com**, one issue per e-mail, subject `[BUG BOUNTY] <title>`,
CVSS 3.1/4.0 vector mandatory (submissions without a vector are not processed).
Rewards: Critical $500 / High $250 / Medium $100 / Low $50, CVSS-decided, discretionary.
Operator submitted F1, F2 and F3 himself on 2026-10-26.

## Scope (only these are in scope)

| Asset | URL |
|---|---|
| Store web app | app.hivenet.com |
| Send (file transfer) | send.hivenet.com |
| Compute console | console.hivecompute.ai |
| Store iOS / Android / macOS / Windows apps | store listings / downloads |

Everything else is OUT: www.hivenet.com (marketing), docs, help centre, support, blog,
**staging and dev environments** (the public `env.hivenet.com/dev` config names them —
do not test them), and upstream third-party code (Zitadel, Auth0, Stripe).

The backends the three in-scope web apps call are part of the same feature and were
treated as in-scope: `hive-prod-web-gateway`, `hivenet-mutable-platform-prod`,
`user-profile-prod`, `paymentgateway-v2-prod`, `http-agent-prod.hivedns.net`.

## Architecture that matters

- **Send** = chunks + a share record + a metadata row. Chunk ciphertext lives at
  `GET http-agent-prod.hivedns.net/p2p/storage/chunk/{cid}` and needs only *any* valid
  bearer token. The folder key is `PBKDF2-SHA512(pw = share.name, salt = share.rootMid,
  it = 1e6)`; `blockKey = AES-GCM-decrypt(readKey, share.users[0].encryptedReadKey)`;
  `chunkKey = AES-GCM-decrypt(blockKey, chunks[0].encryptedBlockKey)`. So **possession of
  the link is possession of the content** — that is the design, and it is why F2/F3 land.
- **Anonymous download token**: `GET /auth/download-token` (no auth) mints a 24 h token
  for the shared machine account `319870842026590211`. Any visitor gets one.
- Records API has two generations: `/mutablerecords/v2` (authorised) and the legacy
  `/mutablerecords` v1 (create-only authorisation hole — F1).
- Accounts: e-mail passwordless via `POST /auth/passwordless/start/` + `/verify/`
  (code is bound to the address and single-use). A profile is created lazily by
  `POST user-profile-prod/user` — **several endpoints 503/404 until it exists**, so call
  `ensure_profile()` right after auth in any script.
- Compute console: Auth0 (`hivecompute-prod.eu.auth0.com`, client
  `bxNCOXErxGeC52LIwqCniJYPAgRwyrsu`), open self-signup, API at `api.hivecompute.ai`.

## Findings (all submitted)

- **F1 High 7.1** — `POST /mutablerecords` (v1) accepts a client-supplied
  `indexedMetadata.volumeMid`/`parentMid` and checks only that the volume *exists*
  (fabricated id → 400). Any authenticated user writes records into another user's
  volume; the record shows up in the victim's own children listing. v2 and v2/bulk
  correctly 403; v1 GET/PUT of a foreign record 403 (the hole is create-only).
- **F2 Medium 6.5** — deleting a transfer (`DELETE /sharerecords/{id}` → 204) or letting
  it expire removes the share record and hides the records, but the **chunks are never
  deleted** and stay readable+decryptable by any prior link holder. No delete route
  exists on the chunk path (405/404). 3/3 trials decrypted the original byte-for-byte.
- **F3 High 7.6** — `POST /metadata` performs no ownership check on `shareRecordId`.
  Any user claims a share record that has no metadata row yet, is recorded as the
  **sender**, and the `recipients` field makes Hivenet e-mail an arbitrary third party
  from `no-reply@hivenet.com` with a link to the victim's transfer. The third party then
  derives the key from the share record and decrypts the victim's file.

## Chains that died, with the fact that killed them

- **Anon mass-disclosure**: public token → enumerate the machine account's share records
  → decrypt everything. DIES: `GET /sharerecords` (with and without `ownerAccountId`)
  returns 404 "share records not found" for the machine account; the 93 volumes / 41
  dirs / 282 files it does own carry no key material.
- **F1 → victim quota DoS**: DIES — the quota is charged to the *creator*, not the volume
  owner. Verbatim: `403 adding 3221225472 bytes to the 3091202586 used of 3221225472
  bytes`, while the victim's own 5 MB writes still returned 201.
- **Metadata → bulk spam**: argued, not proved. Caps are 5/10/50 recipients and 10
  transfers per month per account, accounts are free — but no mail was sent beyond the
  researcher's own addresses.

## Verified negatives worth not re-burning

Share ACLs (update/delete/add-user/expire cross-tenant all 403/404), profile writes
(409, keyed by JWT sub), KEK wrap/unwrap ownership (401), payment-gateway scoping,
mass assignment on metadata (server-controlled fields ignored), e-mail template escaping
(title/description come out HTML-escaped), monthly send cap (enforced, 403), chunk
poisoning via the `HashCID` header (server recomputes the CID), Zitadel redirect_uri
allowlist (7 variants rejected), device_code binding (cross-client → unauthorized_client),
M2M client_credentials without a secret (rejected), compute API cross-tenant (org read,
chat thread_id, api keys, compute profile all scoped), LLM assistant (5 system-prompt
extraction variants + catalog dump + other-org + tool abuse + context leak all refused),
delta-sync `updatedSince` (404 for others), S3 bucket write (401/412).

## Desktop / supply chain (round 5)

EV Authenticode signature valid; Tauri app; NetSparkle Ed25519 with a **real** embedded
key `aYBrBRYkvajUS7Ckk7G4scWLPfg2DO7U0Tx2BFwmZuA=` verifying appcast *and* downloaded
file; bucket writes 401/412. `env.hivenet.com/prod` serves the client bootstrap config
unauthenticated with no secrets. Observations recorded but NOT reported: update URL read
from a user-writable per-user env file (downgrade-only, undemonstrated), `hivenetdev://`
protocol handler, shell namespace extension CLSIDs, `tokens.dat` + wrapped `read_key`
local storage, and a `127.0.0.1:8085` OAuth listener that never bound without a login.
Method detail: `references/desktop-app-supply-chain-analysis.md`.

## State changes on the target (for disclosure / cleanup)

~20 free accounts on plus-aliases of the researcher's Gmail, 2 Compute accounts, 2
inference API keys, several Send transfers (some with `expire: 0` records that no API
route can delete), 1 unpaid Stripe checkout session, €0 spent, nothing deployed.

## Evidence hygiene — read this before quoting any log in this folder

Three artifacts in `evidence/` look like failures and are not. A future session that quotes
them without this note will draw the wrong conclusion, so the note ships next to the logs.

- `f3_validation.log` line `mail to third party: False` / `successful trials: 0 of 2` — the
  script searched only the 8 most recent messages while the inbox was full of Hivenet
  verification codes. `f3_mailcheck3.log` (search by `AND(from_="hivenet.com")`) finds both
  recipient e-mails. The trials were successes.
- `f3_validation.log` line `503 Could not verify the share record contents` — the attacker
  account had no user profile yet; the same request returned 200 after `ensure_profile()`.
- `f3_validation.log` line `attacker auth failed` — the passwordless code did not arrive
  inside the retry window (rate limited). That pair was never tested and is counted nowhere.
- `f2_validation.log` (round 2, deleted-transfer test) is genuine: 3/3 decrypted.

General rule: when a background job's log contains a line that reads as a negative, either
fix the script and re-run, or write a `*_NOTE.txt` beside it naming each apparent failure,
its cause, and the authoritative artifact. Never leave a misleading log as the only record.
