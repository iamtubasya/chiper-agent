---
name: runonflux-engagement
description: Flux (runonflux.com / runonflux.io) bug-bounty engagement — scope/RoE, estate map, auth model, rewarded findings, and verified-hardened surfaces. Load to resume or re-hunt this decentralized-cloud target.
version: 1.0.0
author: RESEARCHER_NAME
metadata:
  hermes:
    tags: [security, bug-bounty, flux, crypto, disintegration, engagement]
    related_skills: [pgp-email-submission, bug-bounty-disclosure, web2-recon]
---

# Flux (runonflux) bug-bounty engagement

Flux = decentralized cloud (ex-ZelCash). Node operators lock FLUX collateral (tiers Cumulus /
Nimbus / Stratus) to provide compute, paid in FLUX. Money paths: marketplace app hosting, Flux
Cloud console, Zelcore wallet, parallel assets (wrapped FLUX cross-chain). FluxOS = "Arcane OS",
the Node.js daemon/management API on every node; blockchain daemon = `fluxd` (Zcash fork).

## Scope + submission (from runonflux.com/bug-bounty)

- Submit email: **security@runonflux.com** (page's explicit mailto). PGP REQUIRED for CVSS > 2.
  Replies come from `Tadeas Kmenta <tadeas@runonflux.com>` (the "tadeas" the operator references).
- PGP key fingerprint `F324 4FFC 7207 DB2C AA35 5DF5 0613 9DA3 A0B1 3EC1`; UID is
  `Flux Security <security@runonflux.io>` (.io — see To-vs-UID pitfall in pgp-email-submission).
- Rewards: Critical up to 10000 FLUX · High 1000 · Medium 500 · Low 100.
- Qualifying: SQL/NoSQL/OS injection, broken auth/session, sensitive data exposure via insecure
  API, weak/missing access control.
- OOS: 3rd-party software/domains (Github/Gitlab, info.runonflux.com), any app on
  `*.app.runonflux.io` and `*.app2.runonflux.io`.
- RoE: no DoS, use own account/node, no data exfil, blockchain/node exploits valid only on
  testnet/regtest, Zelcore restricted to own account.

## Estate map (from 0B recon, 1738 subs → 869 in-scope)

- `api.runonflux.io` / `api.runonflux.com` — Flux TEAM's own FluxOS node API, fronted by
  `fdm-lb-main.runonflux.io` (DigitalOcean 128.199.246.121); backend origin Hetzner 65.109.86.x.
- `api.status.runonflux.io` — public status endpoint leaking the FULL internal host inventory
  (see findings). `*.node.api.runonflux.io` → CNAME `fdm-lb-nodes` (team's node-reach proxy).
- Marketplace: `api.marketplace.runonflux.io`, `admin.marketplace.runonflux.io`,
  `api-dev.marketplace.runonflux.io` / `admin-dev.*` ("FluxCloud Admin" — dev panels expose
  `/api/v1/marketplace/*`).
- Flux Cloud: `console.runonflux.com` → `/login` (Next.js), `api.console.runonflux.com`
  (`/api/v1/health` only unauth), `cloud.runonflux.com` (Vue FluxCloud marketing). Login =
  Google OAuth (`/api/v1/auth/google/start` 302 confirmed) + PIN (`/auth/pin/request` 404 — not
  deployed yet).
- `paposse.runonflux.com` / `admin.paposse.runonflux.com` / `api.paposse.runonflux.com` — "PA
  Posse" sprint-car streaming, **3rd-party "Powered by Flux" app → OOS** (frontend calls
  `api.paposse.tv`; do not report bugs in it).
- Explorers: `explorer.runonflux.io` (bitcore/Insight), `explorer2.runonflux.io`.
- `awx.runonflux.com` — stale A record → 37.27.42.60 serving unrelated "TOPY.az" (finding).
- `llm.runonflux.com` — **"ownllm hub"** = FluxAI LLM inference (OpenAI-compatible `/v1`, model
  `granite4:tiny-h`, repo RunOnFlux/ownllm). FDM LB sets `FDMSERVERID=<ip>:34000` cookie leaking
  the hub backend pool (see finding 5). `ai.runonflux.com` = FluxAI landing page (under upgrade).

## Auth model

FluxID = Bitcoin-format address; auth via `zelidauth` request header carrying a
`bitcoinjs-message`-signed challenge (no cookies/CORS attack). Privileges: user / admin
(NODE_OPERATOR) / fluxteam / appowner. FluxOS source is open (github.com/RunOnFlux/flux) and has
recently been security-hardened: mutating/signing/restart routes all `verifyPrivilege(...)`, plus
`routeGuards`, `pathSecurity.sanitizePath` on backup/app file ops, and current dep versions.

## Findings (2026-11, validated ≥3x)

1. MEDIUM — `api.status.runonflux.io` returns `{"ok":[...],"errors":[...]}` (199 internal
   hostnames, live, `access-control-allow-origin: *`, any path): fdm-* region nodes,
   `authenticate.internal.zelcore.io`, graphql.erg, simplex payment endpoints, wallet backend fleet.
2. MEDIUM — FluxOS API privileged-identity + node-secret disclosure (all unauth, `cache()`-ed):
   `/flux/fluxids` → `fluxTeamFluxID 1hjy4bCYBJr4mny4zCE85J94RXa8W6q37` + 4 support FluxIDs
   (network-wide FLUX_TEAM admin); `/flux/zelid` & `/flux/id` → node operator FluxID;
   `/flux/pgp` → node Ed25519 public key; `/flux/geolocation` → Finland/Hetzner; plus origin:
   `fluxnode: server76_<ip>` header, `/flux/ip` → `65.109.86.17:16127`, `/flux/apiport`,
   `/benchmark/getinfo` rpcport 16224, `/flux/nodetier` stratus_new, `/apps/listallapps`,
   `/daemon/getinfo`.
3. LOW/MED — `api.marketplace.runonflux.io/api/v1/marketplace/config` leaks 4 admin FluxID
   addresses unauth (same on api-dev).
4. LOW — `awx.runonflux.com` stale/dangling DNS.
5. LOW/MED — ownllm/FluxAI infra disclosure: `FDMSERVERID` cookie on `llm.runonflux.com` leaks the
   hub backend pool (`62.107.25.222` / `78.28.82.44` / `83.195.127.125` :34000), reachable directly
   bypassing Cloudflare; `/health` (unauth) leaks the inference pool architecture — `ownllmdocs`,
   `ownllmpoolsmall`, `ownllmpoolmid`, `ownllmpoolgptoss`, `ownllmtq2` (20 each) + `ownllmfluxai`
   (40), with live healthy/inflight counts.

## Verified hardened (negatives, do not re-test)

`/benchmark/signfluxnodetransaction`, `/benchmark/start|restart`, `/flux/restart`,
`/flux/currentbranch|currentcommitid`, `/flux/getip|getgateway|getmap`, `/daemon/sendrawtransaction`
→ 401 without zelidauth. Marketplace `modify/app|trending|featured` POST require signed message
(`Invalid message` 400 on `{}`). `.git`/`.env` absent on checked hosts. nuclei (exposures/misconfig/tech/default-login/exposed-panels) → only fastly-debug-headers info.
ownllm auth gate (`RunOnFlux/ownllm` `images/gate/server.js`): static `API_KEY` env + constant-time
compare; `/`, `/health`, `/healthz` unauth (readiness only) — the `/v1/*` + `/api/*` (pull/delete/
tags/ps/show) surface is Bearer-gated, not forgeable. The `sk-flu…sig>` key in the hub banner is a
placeholder, not a signed token.

Auth is cryptographically sound — attempted escalation to High/Critical failed:
`signatureVerifier.verifySignature` = `bitcoinMessage.verify` (bitcoinjs-message) or
`ethereumHelper.recoverSigner`; `isValidSigningIdentity` validates bs58check length 21; every
privileged handler calls `verifyPrivilege(...)` with no alg:none/JWT/verify flaw. Knowing the flux
team FluxID does NOT impersonate it (needs private key). `authenticate.internal.zelcore.io` is
Pomerium-gated (302 → `/.pomerium/`, `_pomerium_csrf`, Envoy). FDM nodes (`fdm-usa-1-1`=5.161.211.14,
`fdm-nodes-eu-1-1`=5.39.57.41) return custom 503 placeholders; origin 65.109.86.17 serves the FluxOS
home UI on :16126 (still zelidauth-gated). `hashes.runonflux.io` = app-content MD5 list, not creds.

**Ceiling = Medium.** No High/Critical reached — target well-hardened; do not inflate severity.

## Known blockers / dead ends

Flux Cloud console business-logic testing gated behind Google OAuth (no self-provision; PIN auth
not yet live). Paposse = third-party (OOS). Blockchain exploit validation requires testnet.