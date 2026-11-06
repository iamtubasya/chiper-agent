---
name: runonflux-audit
description: Flux / Arcane OS (runonflux.com / runonflux.io) bug-bounty engagement — scope + reward + PGP + OOS, core business, estate map (FluxOS node APIs, marketplace, cloud console, zelcore), the zelidauth/Privilege auth model and where its source lives, 3 validated findings, and the verified-negatives + blockers. Load to resume or re-hunt this target.
---

# Flux / Arcane OS bug bounty (runonflux.com / runonflux.io)

Target is the decentralized-compute platform formerly ZelCash (now "Arcane OS"). Submit reports by
**email to `security@runonflux.com`** only; **PGP encryption is REQUIRED** for anything CVSS>level 2
(else invalidated). PGP key fingerprint `F324 4FFC 7207 DB2C AA35 5DF5 0613 9DA3 A0B1 3EC1`
(User-ID `Flux Security <security@runonflux.io>`). The `pgp-email-submission` skill covers the
encrypt-and-send flow.

## Scope & rules (from https://runonflux.com/bug-bounty/)

Reward tiers: Critical up to **10000 FLUX**, High **1000**, Medium **500**, Low **100**.

Qualifying: SQL/NoSQL/OS injection · broken auth/session · **sensitive data exposure via insecure
API** · weak/missing access control. ("No exhaustive list" — report anything not on the OOS list.)

Out-of-scope (do NOT report, do NOT target):
- 3rd-party software, 3rd-party domains (Github/Gitlab), 3rd-party subdomains (`info.runonflux.com`).
- **Any app running on `*.app.runonflux.io` and `*.app2.runonflux.io`** (FluxOS-hosted customer apps).
- "Flux-branded services operated by third parties" — e.g. `paposse.runonflux.com` ("PA Posse", a
  "Powered by Flux" sprint-car streaming app) is a THIRD-PARTY customer app, not Flux-team software.
  Its real product domain is `paposse.tv` / `api.paposse.tv`. Treat it as OOS.

Testing rules: no service degradation, own accounts/nodes only, blockchain+node exploits confined to
a private testnet/regtest, Zelcore = own account only. Known-issues note: Fluxd is a Zcash/bitcoin
fork (`RunOnFlux/fluxd`); the NodeJS API is FluxOS in the `RunOnFlux/flux` repo.

## Core business & money flow

FluxNode operators lock FLUX collateral (tier Cumulus 1000 / Nimbus 12500 / Stratus 40000) and run
FluxOS (Arcane OS) on a server, providing compute; paid in FLUX block rewards. Money surfaces:
marketplace (app hosting fees / buy-sell compute), Flux Cloud console (decentralized PaaS), Zelcore
multi-asset wallet (own acct only), parallel assets (wrapped FLUX on BSC/ETH/AVAX/Polygon/KDA).

## Estate map (validated live)

- `api.runonflux.io` / `api.runonflux.com` — **FluxOS node management API** (Express/Node). Both are
  the Flux team's OWN FluxNodes behind `fdm-lb-main.runonflux.io` → DigitalOcean LB `128.199.246.121`,
  backend origin Hetzner `65.109.86.15/.17` (this origin is leaked — see findings). `fluxnode`
  response header names the backend node (`server76_65.109.86.17`).
- `*.node.api.runonflux.io` — wildcard (`<ip-dashed>-<port>.node.api...` → CNAME `fdm-lb-nodes.runonflux.io`)
  reaching the whole FluxNode FLEET (3rd-party operators — do NOT mutate; OOS).
- `api.marketplace.runonflux.io` — marketplace API (Express, rate-limit 50/1s). `admin.marketplace.runonflux.io`
  = admin SPA (Vite). `api-dev.marketplace.runonflux.io` = dev twin.
- `explorer.runonflux.io` / `explorer2.runonflux.io` — Flux explorer (bitcore node).
- `console.runonflux.com`/`cloud.runonflux.com`/`api.console.runonflux.com` — Flux Cloud (Next.js +
  JSON API, PIN/magic login). `account.runonflux.com` = Shopify (3rd-party).
- `awx.runonflux.com` — stale record serving unrelated third-party "TOPY.az" (see findings).

## Recon method (works, reuse it)

1. Clone the open-source node: `git clone --depth 1 https://github.com/RunOnFlux/flux fluxos`.
   Routes are NOT in a `routes/` dir — `ZelBack/src/routes.js` is one 67 KB file.
2. Enumerate routes: `grep -rhoE "(app|router|self\.expressApp)\.(get|post|put|delete|patch|all)\(\s*['\"][^'\"]+" ZelBack/src | sort -u`.
3. Auth model lives in `ZelBack/src/services/utils/privileges.js` + `verificationHelper.js` +
   `verificationHelperUtils.js`. `authOf(req)` = `req.headers.zelidauth` (a Bitcoin-signed
   `zelid=<addr>&signature=<sig>&loginPhrase=<phrase>` token). Privilege enum: `user`, `admin`
   (node operator), `fluxteam`, `adminandfluxteam`, `appowner`, `appownerorfluxteam`. Every
   sensitive handler calls `verificationHelper.verifyPrivilege(...)` INTERNALLY (not as route
   middleware), so route-level `asyncRoute()` bareness does NOT mean "unauthenticated".
4. Compare deployed `flux/version` (8.22.0 seen) against your clone (master/HEAD) — deployed may lag.

## Findings (validated ≥3x, evidence in `~/flux-audit/evidence.txt`)

1. **MEDIUM — internal node infra disclosure (unauth)** — `fluxnode: server76_65.109.86.17` header
   on every response; `/flux/ip` → `65.109.86.17:16127`; `/flux/apiport` → 16127;
   `/benchmark/getinfo` → rpcport 16224; `/flux/nodetier` → stratus_new; `/apps/listallapps` →
   docker container inventory; `/daemon/getinfo` → full daemon state. Origin (65.x) ≠ LB (128.x),
   so this is an origin-identity leak behind the LB.
2. **LOW/MED — marketplace admin account disclosure** — `GET /api/v1/marketplace/config` returns
   `data.data.admin` = 4 FluxID addresses unauthenticated. (Fits "sensitive data exposure via
   insecure API".)
3. **LOW — `awx.runonflux.com` stale/dangling DNS** — A→37.27.42.60 serving "TOPY.az" nginx
   default vhost (AWX decommissioned, record left behind).

## Verified negatives (auth actually enforced)

`/benchmark/signfluxnodetransaction`, `/benchmark/start`, `/flux/restart`, `/flux/currentbranch`,
`/flux/currentcommitid`, `/daemon/mutations` all → `401 Unauthorized` without `zelidauth`.
Backup/app-file routes use `sanitizePath` + `verifyRealPathOfExistingPath` (traversal protected).
Deps recent (express 4.21.2, qs 6.14, no known-CVE posture). No `.git`/`.env` on probed hosts.

## Blockers / next leads

- Flux Cloud console auth is PIN/magic-link; `/auth/pin/request` 404'd on api.console (console may
  be invite/beta gated). Account mint + business-logic (plan/entitlement, BOLA on deploys, race at
  deploy) is the highest-value UNTESTED surface.
- Marketplace admin `modify/*` flow is signature-gated (`zelidauth` header over a nonce from
  `/modifyappmessage`) — no bypass found, but the nonce endpoints are spammable (no rate-limit ring
  besides 50/1s).
- Zelcore (`*.zelcore.io`, ~560 subs incl. per-chain `api.*.zelcore.io` + blockbook/electrumx) untested
  (own-acct only).