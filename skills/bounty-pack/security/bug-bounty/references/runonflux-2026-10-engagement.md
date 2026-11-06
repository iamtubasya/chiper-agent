# RunOnFlux — 2026-10-23 engagement (web2, self-run bounty)

Target: `runonflux.com` ecosystem. Program: `runonflux.com/bug-bounty` (email-only,
`security@runonflux.io`, **PGP encryption REQUIRED** for anything >CVSS 2 — fingerprint
`F3244FFC7207DB2CAA355DF506139DA3A0B13EC1`; unencrypted reports above level 2 are
invalidated). Rewards: Critical 10,000 / High 1,000 / Medium 500 / Low 100 FLUX.
Artifacts: `D:/data hermes/bug-bounty/runonflux_2026-10/`.

## Scope (read first — it is narrow and specific)

- **Qualifying:** SQL/NoSQL/Mongo/OS injection, broken auth/session, sensitive data
  exposure (insecure API / crypto flaws), weak or missing access controls.
- **Rules of engagement:** own accounts only; no data copy/modify; no viewing beyond
  proof; validation-only exploitation; no service degradation.
- **OUT of scope:** previously-disclosed bugs, social engineering, DDoS/MITM/spam,
  any software not produced by the Flux team, **third-party-hosted domains (GitHub
  Pages etc.)**, `info.runonflux.com`, **`*.app.runonflux.io` and `*.app2.runonflux.io`**
  (FluxOS app instances), third-party Flux-branded services.
- Practical consequence: `docs.runonflux.com`, `help.`, `wiki.`, `source.`,
  `docs.fusion.`, `docs.stats.` are GitHub Pages = OOS. `support.runonflux.com` →
  Freshdesk = third-party SaaS = OOS. `libreddit.app.runonflux.com` = FluxOS app = OOS.

## Core business (needed for business-logic hypotheses)

Decentralized Web3 cloud ("AWS on Flux"): users deploy containerised apps onto a
network of community Flux nodes, pay in FLUX, own apps via a Zelcore ZelID. Products:
FluxCloud console, marketplace, decentralized storage (encrypted contacts/messages/
files), FluxAI (self-hosted LLM), Zelcore/SSP wallets, block explorer, Titan shared
nodes. Money path = app registration/update payment; auth path = Zelcore login-phrase
signature + (newer) passkey/WebAuthn + Firebase (`fluxcore-prod`).

## Live host map (215 subs enumerated → 94 live; the ones that matter)

| Host | What | Notes |
|---|---|---|
| `api.runonflux.io` / `.com` | Flux node API (Express/Node) | main API; see endpoint map below |
| `console.runonflux.com` | Flux Cloud Console (Next.js) | SPA, bundles at `/_next/static/chunks/` |
| `api.console.runonflux.com/api/v1` | console backend | cookie auth (`credentials:include`), OAuth Google |
| `home.runonflux.com` | user dashboard (Vue) | bundles at `/assets/<Name>-<hash>.js` — **named service modules** |
| `account.runonflux.com` | account mgmt | 406 without browser Accept; CF bot-gated |
| `passkey.runonflux.com` (+ `-dev`, `-test`) | WebAuthn popup helper | **FINDING F1** |
| `storage.runonflux.io` / `.com` | decentralized storage | `/v1/contacts`, `/v1/messages`, `/v1/files` |
| `ai.runonflux.com` | FluxAI | OpenAI-shaped `/v1/chat/completions` (API-key) |
| `mcp.runonflux.com` | flux-cloud-mcp | CF-challenged; source on GitHub |
| `admin.console.runonflux.com` | "FluxCloud Admin" SPA | login-gated |
| `admin.marketplace.runonflux.io` | "FluxCloud Admin" (Vite/React) | 200 on all paths = SPA catch-all, not a finding |
| `api.marketplace.runonflux.io` | marketplace API (Express) | **all probed routes 404** — see quirks |
| `imagesdev.runonflux.com` | image/artifact server | **FINDING F2** (dir listing) |
| `grafana-edge.runonflux.com` | Grafana 11.3.0 | auth required |
| `explorer.runonflux.com` / `testnet.` | block explorer (AngularJS + Socket.io) | public chain data |
| `awx.runonflux.com` | nginx 1.28.3 default vhost | dead/placeholder |

## Verified NEGATIVES (hardened — do not re-burn time on a re-hunt)

- **Flux node API auth is enforced.** Every privileged route (`/id/activeloginphrases`,
  `/id/logoutallusers`, `/flux/updateflux`, `/daemon/restart`, …) returns
  `{"status":"error","data":{"code":401,...}}`. **HTTP 200 with an error body is the
  norm here** — never read a 200 as "accessible"; read the JSON `data.code`.
- **Console API CORS is locked.** `access-control-allow-credentials: true` is sent for
  every Origin but **no `access-control-allow-origin` is ever reflected** → browser
  blocks it. Not exploitable.
- **OAuth `return_to` is safe.** `api.console.../api/v1/auth/google/start?return_to=`
  encodes it into the `state` param, not into the redirect. No open redirect.
- **Storage GET is auth-gated (not IDOR).** `GET /v1/contacts/<any-hash>` → **403 for
  every hash including invalid ones** = universal auth wall. Distinguish this from an
  IDOR by probing an invalid hash: 404 = existence oracle, universal 403 = auth gate.
- **AI gate (ownllm `images/gate/server.js`) is solid.** Constant-time Bearer compare,
  only `/`, `/health`, `/healthz` exempt (readiness, leaks model name+digest by design).
- **Firebase `fluxcore-prod` locked.** RTDB/Firestore/Storage all 404 without a
  collection/token; no open rules found.
- **Grafana** anonymous access off. **Admin panels** login-gated.

## FINDINGS

**F1 — MEDIUM — `passkey.runonflux.com` WebAuthn assertion leaked via `postMessage(..., "*")`.**
The popup helper reads `action`/`challenge`/`rpId`/`user`/`rp` from the query string,
runs `navigator.credentials.create/get`, then returns the credential to
`window.opener` with **target origin `"*"`** (3 call sites: success, error,
beforeunload-close; no `event.origin` validation). The assertion (signature,
authenticatorData, clientDataJSON, userHandle) therefore reaches **any origin that
opened the popup**. Attack: attacker page opens the legit passkey URL with a challenge
from a login flow it initiated, user completes the prompt (domain looks authentic),
assertion lands on the attacker → completes login as the user. `rpId` is
browser-validated so the RP can't be swapped, but that does not stop the leak.
Validated 3x (`curl ... | grep -c '"\*"'` → 3, consistently). Fix: name the exact
opener origin(s). **Staged as a Gmail draft + PDF PoC (2 pages), not sent.**

**F2 — LOW — `imagesdev.runonflux.com` open directory listing.** `Index of /` with
`apps/fluxshare/`, `arcane/releases/<ts>/` (FluxLive ISO, `FluxUpgrade-<ts>-signed.tar`,
`root-hash`, `severity`, `sums.sha256`), `content/` (ToS PDFs), `fluxbenchd/`
(benchmark binaries), `fluxd/{bootstraps,chain-params,depends-sources}/`. Mostly
intended-public node-update artifacts → info-disclosure, low impact. Not auto-drafted
(Low/Info EV).

**F3 — LOW/INFO — internal node IP leak.** `api.runonflux.io` responses carry
`fluxnode: server85_65.109.90.205` (and `x-forwarded-for`/`x-real-ip`/`x-flux-node-ip`
are read by the client's `ApiClient` for backend selection). Internal node IPs
disclosed. Informational.

## Target quirks that cost time (re-hunt shortcuts)

- **Storage API rate limit is brutal:** `ratelimit-policy: 300;w=600` on
  `storage.runonflux.com`, but it 429s ("Too many requests, please try again later")
  after a handful of calls and the reset is slow. Space requests ≥3–5 s, and do the
  auth-classification probes (invalid-hash 403 test) in ONE batched run, not iteratively.
- **`.io` vs `.com` route asymmetry:** `.com` serves `POST /v1/contacts` (validation
  errors, wants a numeric-ish `id`) but 404s `POST /v1/messages`; `.io` is the reverse
  (`Cannot GET /v1/messages`, `POST` exists). Same product, different edge config —
  probe both before concluding a route is absent.
- **Marketplace API routes are hidden.** `api.marketplace.runonflux.io` returns
  Express `Cannot GET/POST` (404) for every guessed path and ffuf with a 40-word
  product/auth wordlist found nothing. The admin SPA (`admin.marketplace...`) only
  reveals `/id/verifylogin`, `/apps/deploymentinformation`, `/games` in its bundle,
  and those 404 on the API too — the real routes are behind a prefix not yet found.
  Next step for a re-hunt: pull the marketplace *storefront* bundle (not admin) and
  grep its axios `baseURL` calls.
- **`admin.marketplace.runonflux.io` returns 200 for every path** (SPA catch-all) —
  that is routing, not an exposed admin. Same for other Vite SPAs.
- **CF bot walls:** many hosts (`ai.`, `runonflux.com`, `stats.`, `shop.`, game-server
  hosts) answer 429 "Just a moment..." to non-browser clients. `ai-preview.` and
  `llm.` were reachable with a browser UA. Use the browser stack for those, and treat
  a uniform 429 as a wall, not a result.
- **Business-logic gap (by design, likely non-paying):** `flux-cloud-mcp/src/pricing.ts`
  documents two tables — the **USD price** Flux Cloud charges vs the **chain consensus
  minimum** (`messageVerifier.js`, several times lower, no USD floor) that the
  blockchain actually enforces. Anyone can register an app paying only the consensus
  minimum via the raw API/Zelcore. This is inherent to the decentralized protocol, so
  frame carefully (probably "by design") before reporting.
- **FluxOS auth model (from `flux-cloud-mcp/src/keys.ts`):** FluxOS accepts a
  **self-issued login phrase** (13-digit ms timestamp <16 h old, 40–70 chars, signed by
  the ZelID) — one signed phrase authenticates against every node, stateless, no
  round-trip. Implication: a captured `(zelid, signature, loginPhrase)` tuple is
  replayable until the timestamp ages out. Relevant if any signature-leak primitive
  (e.g. F1) is ever chained.

## SPA endpoint-extraction pattern that worked

`home.runonflux.com` ships **named service modules** (`ApiClient-*.js`, `http-*.js`,
`session-*.js`, `AppsService-*.js`, `FluxService-*.js`, `DaemonService-*.js`,
`firebase-*.js`) under `/assets/`. `curl -sL` (the assets 301 without `-L`), then grep
for `https?://...runonflux...` and quoted `/path` strings → the full API surface
(`/id/loginphrase`, `/id/verifylogin`, `/apps/*`, `/daemon/*`, `/flux/*`) plus the
Firebase config (`fluxcore-prod`, apiKey/authDomain/appId — public by design).
`ApiClient` also revealed the backend-selection logic and the
`*.node.api.runonflux.io` per-node host scheme.

## Disclosure-workflow note (durable routing fact)

On this host the OAuth token `~/google_token.json` is **Calendar-scoped only** (its
refresh token is dead), so the Gmail-API draft route fails. Gmail drafts with PDF
attachments go through **IMAP + App Password**: creds in `~/check_basabasi_email.py`
(`APP_PASSWORD`), account `RESEARCHER_EMAIL`, `imap.gmail.com`, folder
`[Gmail]/Draf` (Indonesian locale). Working pattern: `~/make_superstate_draft.py` —
`EmailMessage` + `set_content` + `add_attachment` + `X-Unsent: 1`, `imaplib` APPEND
with `(\Draft)`, delete-then-append on a **bracket-free** subject token (IMAP SEARCH
chokes on `[` in the subject), verify by re-fetching RFC822 and parsing the attachment
(pypdf page count + `%PDF-` magic + sha256 vs local).

## Blocker for a deeper re-hunt

The storage and marketplace **authenticated IDOR** classes (the highest-value
remaining surface) need a real Flux identity: a Zelcore wallet / funded test account
to obtain a valid login-phrase session and a second account to test cross-tenant
access. Ask the operator for one test wallet before investing more unauthenticated
time — everything unauthenticated on those two services is now verified-negative.
