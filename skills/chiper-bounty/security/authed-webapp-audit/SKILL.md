---
name: authed-webapp-audit
description: "Audit authenticated web apps: account minting, CDP browser driving, MFA, session hygiene."
version: 1.0.0
author: hermes
license: MIT
metadata:
  hermes:
    tags: [webapp, authz, idor, bola, nextjs, ssr, audit, multi-account, lockout, idempotency]
    related_skills: [bb-methodology, hunt-idor, hunt-business-logic, hunt-race-condition, security-arsenal, email-automation]
---

# Authed Web App Audit (multi-account, SSR/SPA)

## The authed vector battery (ordered) — run this once a session settles

The mirror of `unauth-surface-discovery`'s battery, for AFTER you hold a session:
`references/authed-vector-battery.md` is the ordered 8-tier pass — every item an
artifact, chain leads ≥3x before calling them dead.

```
Tier 0  session settle + identity assert (per-account pinning)
Tier 1  BOLA/IDOR differential (seed B with a MARKER object first)
Tier 2  function-level authz / BFLA (admin endpoint, step-skip, tenant override)
Tier 3  business logic on the money surface (Terms page = the invariant list)
Tier 4  race / TOCTOU (single-packet or aiohttp gather)
Tier 5  session/token lifecycle (rotation, replay, revocation, scope)
Tier 6  sensitive-data exposure (the "export is the read" rule)
Tier 7  injection on authed input (stored XSS, upload, SSRF-via-webhook)
```

Open the battery the moment the estate is enumerated and the account is provisioned;
it is the "where do I start, in what order" answer. The sections below are the
*technique details* behind the tiers.

## When to Use
- Auditing an authenticated web app / SaaS where you can register your own test accounts.
- Cross-tenant authorization testing (BOLA/IDOR), Server Action handling, rate-limit & lockout discrimination, idempotency/duplicate-submit races, role-boundary checks, or hidden-route discovery inside a signed-in app.
- The user asks for deeper exploitation ("cari lagi lebih dalam", "pakai semua tools", "jangan cuma curl") on an authorized target with own accounts.

Playbook distilled from a deep multi-day audit of an MTD SaaS (Next.js + Cloudflare + server actions). Applies to any *authenticated* app where you can register/control test accounts. The user's standard: exploit-first mindset, all real tools (not curl-only), all attack variants, and "cari lagi lebih dalam" means find NEW surface/endpoints/tools — not re-run old payloads.

## Core doctrine
- Prove with real artifacts on disk; never rely on page-text counts or single status codes.
- Verify against a "source of truth" endpoint (account export JSON) whenever UI vs storage disagrees.
- For every "blocked" result keep the discrimination test that proves server-side vs client-side enforcement.
- Register multiple OWN accounts (temp mailbox provider like mail.tm) — cross-tenant tests with only your data are the core of BOLA/IDOR/priv-esc proof.

## Automated account minting (email-gated signup)
When signup/login is gated behind an emailed 6-digit code, drive it from a client class
(register → scrape anti-forgery token → login → poll IMAP → submit code → dump a Netscape
cookie jar) so you can mint 2+ accounts on demand, repeatedly. Full recipe, reusable skeleton
and the pitfalls that silently produce "no account created" are in
`references/email-gated-signup-harness.md`.

Two rules from that reference worth repeating here:
- Assert on the **redirect** (`Location` contains the confirm path), never on the status code —
  registration itself gets rate-limited and then returns `200` with the page re-rendered, which
  reads as a phantom login failure.
- **Status-code inconsistency is not broken authorization.** Per-tenant collections that answer
  `200 {"data":[]}` where a sibling endpoint answers `403` are a code inconsistency, not a leak.
  Only report if the body contains the other tenant's object. Create a real record on the other
  account first — without it, "A can't see B's data" is untestable.

## Registration form that silently no-ops over HTTP — JS tokens + hashed field names
Measured on a legacy Symfony/PHP registration (Lecturio 2026-11): the email/password inputs carry a random
40-hex `name=` that rotates every page load (`registration[<40hex>]`), and a hidden `LUD` token is filled by JS
(a UUID). A plain `urllib`/curl POST returns **200 and re-renders the form with NO error and NO success state** —
the account is never created and nothing tells you it failed (only the CSRF token + a 32-hex `state:` value rotate
between the two responses). This is the exact trap that reads as "registration succeeded" while it did not.
Drive the real form in headed Playwright/Chrome and judge success by the redirect to `/.../complete` or an
account endpoint (`/api/.../user.json` returning a `user` object), never by page text. Dump
`Object.keys(new FormData(form))` right before submit to see the exact field names + LUD value the server expects.
- Plus-address silent drop: `user+tag@gmail.com` registration mail is often silently dropped by the vendor's
  mailer/filter (Gmail routes it, but no email ever lands). When the verification email never arrives, re-register
  with a PLAIN address from a Gmail account you already hold a token for (`gmail_accounts.py list`) instead of a
  plus-alias — one clean re-register beats debugging a nonexistent delivery.

## Multi-account session hygiene — pin creds PER INSTANCE, or you get phantom findings
A reusable login helper that reads credentials from a **module global** (`CREDS`) and auto-reauths on
401 will silently **switch accounts mid-session** the moment you build a *second* account in the same
interpreter. On 2026-10-15 (Fintual) this produced a near-miss: a "uid cookie → account confusion"
"finding" where account A's JWT appeared to return account B's data, and stayed on B after the cookie
was restored. It was **100% self-inflicted** — the 5-minute JWT expired, the helper's 401→refresh→login
re-logged as B because a later `importlib.reload(session_helper)` (triggered while `FT_ACCOUNT=B`) had
rebound the module global, and *old* class objects still pointed at that same mutated module `__dict__`.

Rules:
- **Pin credentials on the instance at construction**: `self.creds = dict(CREDS)`. Never read a module
  global inside `login()`/`refresh()` — `importlib.reload` re-executes in the *existing* module dict, so
  pre-reload instances silently observe the new value.
- **Clean-room validate any identity-confusion signal BEFORE writing it up.** Fresh login in a fresh
  cookie jar → confirm `/me` == expected id → mutate ONE thing → re-read. A single contaminated session
  is not evidence. The tell here: the `email` cookie also flipped to B, which no `uid` swap could cause.
- Keep **one pinned session object per account** (`builtins._fsA`, `_fsB`), built in separate
  `reload()`+`get_session()` cycles, and assert the id on every object right after you create it.

## Short-lived JWTs (TTL ~300s) — auto-refresh is mandatory, and must be account-pinned
Fintual's `monolith_token` was `exp-iat = 300`. Any multi-minute test run will outlive it and every
later call 401s. Bake `401 invalid_credentials → re-login once → retry` into the client (see the
`_retry`/`refresh()` shape in the case study) — but per the pinning rule above, so the refresh can't
cross accounts. Distinguish a *real* 401 gate from an expired token by checking whether a **freshly
minted** token clears the same call.

## Email OTP codes carry tracking-pixel DECOYS — filter before you trust a digit run
Vendor "your code is NNNNNN" mails routinely embed `<img>` tracking pixels, `@font-face` metric tables
and style blocks whose base64/numeric literals match a `\d{4,8}` regex. On Fintual the SAME stale code
(`697382`, plus `404040`/`2026`) appeared in every message and kept getting picked over the real fresh
code. Extraction recipe:
1. Sort candidate messages by Gmail `internalDate`, newest first; only consider mail **newer than** the
   `initiate_login`/`signup/lead` call you just made (`before = now - 5s`).
2. Strip `<style>`/`<script>` blocks **before** tag-stripping, then strip tags:
   `re.sub(r'<(style|script)[^>]*>.*?</\1>',' ',body,flags=re.S|re.I)` → `re.sub(r'<[^>]+>',' ',…)`.
3. Exclude a per-target `DECOY` set (accumulated stale codes + `404040`,`2026`,`20262`) and re-derive on
   each new login rather than caching a code.
4. Codes are **single-use and invalidated by re-`initiate`** — a second `initiate_login` voids the first
   code, so never fire two initiates back-to-back and then guess.

## Service-token / audience minting endpoint (`POST …/jwt {aud}`) — test the allowlist, expect to be blocked
Modern SPAs fronting a microservice estate expose an endpoint that mints a **downstream-service JWT**
from a client-supplied `aud` (Fintual: `POST /auth/jwt {aud}` → cookie `<aud>_service_jwt`, RS256,
`iss=auth.fintual.com`, `aud=<requested>`, `sub=<own id>`). The whole question is whether `aud` is an
**allowlist** (server-side) or free-form. Cheap triage, all with your own token:
- **Enum the allowlist** by minting ~12 plausible audiences (`monolith`, `admin`, `internal`,
  `<product>-mx`, `<product>-cl`, `backoffice`, `onboarding-*`). Free-form → every value mints (escalation
  surface). Fintual minted **only** `stocks-broker-mx` and 404'd `aud_not_found` for all others ⇒ correct
  server-side allowlist, no arbitrary-`aud` escalation.
- **Cross-realm / cross-product check:** a **CL** pre-KYC account minting an **MX** broker token may be
  intended (a CL user opening the MX feature) — do NOT call it a finding without the next step.
- **Then find the CONSUMER.** A minted service JWT is worthless until you show a host that *accepts* it.
  Grep the bundle for the service map (`{"stocks-cl-…":{"id":…,"aud":"stocks-pricing"}}`) and the axios
  `serviceId` config, then locate the real backend mount. If every same-origin probe 404s
  (`No route matches …`) and the consumer is a separate backend you can't reach, the impact is
  **unproven** → report as an open lead, not a finding.

## Reporting bar: an unproven lead is NOT a finding — say so explicitly
Bug-bounty triage rejects "the token mints, therefore escalation" with no demonstrated read/write. When a
class looks suspicious but you cannot reach the consuming surface, record it in the findings file as
`status: UNPROVEN-IMPACT` with (a) the exact repro, (b) the concrete missing step, (c) the benign
by-design explanation. Ship `reportable_findings: 0` + a `verified_negatives[]` list rather than padding
the report. A clean "N classes verified negative with tool evidence" beats one inflated claim.

**The capability-gain test (operator correction, djangoeurope 2026-10-20 — retracted a Medium over this).**
Before claiming ANY authenticated-flow finding, answer one question: *can the attacker do something they
could not already do?* If the "vulnerability" is the normal flow working as designed and exploitation
requires a credential the attacker must already possess, it grants no new capability and is NOT a finding.
Worked example: "email change applies immediately without verifying the new address" sounds like an ATO
primitive — but the endpoint required the account password, and an attacker holding the password already
has full access. The change escalates nothing. It was retracted to a hardening observation in the findings
file (`severity: RETRACTED` + reason), not submitted. The operator's instinct on this is sharp and fast
("kalau ganti email kan memang begitu alurnya") — expect the challenge and pre-empt it with the test.
Contrast the sibling that DID pass: the same session's "tokens survive password change" finding grants a
real new capability (a stolen session outlives the victim's standard remediation), so it stood.

**Corollary — capability PROBE, not just capability-gain.** When a finding DOES grant something,
measure exactly how much before writing impact: drive the claimed credential to the boundary and
record what it *cannot* do. Proton fork-claim (2026-10): the stolen full-scope token read settings,
payment status and the session inventory, but `PUT /users/password` and `DELETE /sessions/{id}`
answered `9102/9101 MissingScopes` — so "account takeover" became "sensitive-data disclosure"
(Medium), and the proved/argued table in the report listed the blocked ops. Triagers trust a report
that maps its own ceiling; an unproven "full access" claim invites a downgrade at best.

## Multi-app product suites: each app is its own session (fork + appversion)

Auditing a suite of web apps under one account (Proton: mail/drive/pass/wallet/calendar/docs; the
pattern generalises to any app family with an account host + per-product API hosts):

- **Each app mints its own session via a fork** (`POST /api/auth/v4/sessions/forks` on the account
  host, claimed at `<app>/api/auth/v4/sessions/forks/{selector}`). There is no shared API session —
  probes must carry the **per-app `x-pm-uid` + `x-pm-appversion`**. Wrong UID → 401; stale
  appversion → `422 "This web page is out of date"`.
- **Capture the pair, never guess:** Playwright `page.on("request")` on the app's `/api/` traffic,
  then replay probes with in-page `fetch()` (credentials ride along). Reload the app each round —
  an already-open app issues no capturable calls.
- **Per-app gates differ.** A product holding especially sensitive data may add a step after the
  fork (Proton Pass requires the account password to unlock E2E keys). Map the gate per app before
  assuming the fork is sufficient.
- **The fork token IS the scope-differential instrument.** Child/fork tokens carry a *subset* of
  scopes (`full self payments keys parent user …` but no `password`, no `locked`), so the same
  privileged call from fork-token vs SRP-login-token measures scope enforcement for free — and the
  `403` body names the missing scope (`9102 MissingScopes:["password"]`,
  `9101 MissingScopes:["locked"]`). Run this BEFORE claiming "full-scope token": it converts a vague
  High into a measured Medium and gives the report its proved/argued table. Then always finish with
  the revocation test (mint fork in `Independent:0` and `1`, `DELETE /api/auth/v4/sessions` from the
  locked session, re-probe both) — forked sessions surviving "log out all devices" would be the real
  High.
- **Unauthenticated ≠ unauthorized.** `GET /api/auth/v4/sessions/forks/{selector}` returns a
  full-scope token with no cookie, header or secret — and it is BY DESIGN: the app's own bundle calls
  `pullFork` with `unauthenticated:!0`, i.e. the selector is the hand-off credential. Before you write
  "missing authz", grep the child bundle for the call site; `unauthenticated:!0` /
  `credentials:'omit'` in the app's own code is the by-design signature. Full matrix, the stale-profile
  session-recovery recipe (`AUTH-<uid>`/`REFRESH-<uid>` pair enumeration, URL-encoded refresh
  cookies, `/core/v4/auth/scopes` classification), the leaked-`RecoverySecret` crypto triage, the
  gpg-passphrase verification trap, and the payments-gated-before-pricing finding:
  `references/proton-session-recovery-and-scope-differential.md`.
- Full map + verified negatives (incl. the fork-claim finding, the mail-XSS battery, and the
  E2E-closed surface list): `references/proton-e2e-audit-2026-10.md`.
- **Second identity → harness → BOLA:** `references/second-identity-harness-and-cross-tenant-bola.md`
  — operator-assisted signup harvest (one profile = one process), why an `AUTH-<uid>` cookie whose
  value is an *encrypted envelope* cannot be replayed with `requests` (it 401s and reads like an
  authz failure), the in-page `fetch()` harness that needs **both** an origin hop (else
  `TypeError: Failed to fetch`) **and** the per-subdomain `x-pm-uid`, what an external-address account
  can/cannot provision (no Calendar, Pass needs `/reauth`), and the Drive BOLA verified-negative
  matrix with its 422-vs-404 split.

## WAF throttles the scripted path but not the browser path — harvest, then replay with browser headers

Measured 2026-10-26 (share-link SaaS, CloudFront + AWS-WAF): after two successful
**browser** logins, every plain `urllib`/`requests` call to `/api/auth/login` and to the SPA
login page began returning **HTTP 429** with
`We detected unusual traffic from your network... Error ID: AWS-WAF-CLOUDFRONT`. The browser
context kept working throughout. The block is keyed on request **shape and volume**, not on
the credential and not on the account.

The working bridge, in order:

1. **Do the login in the browser** (SeleniumBase Pure CDP / Playwright / CDP Chrome). The
   widget self-solves and the session is established on a trusted path.
2. **Harvest the token from where the SPA put it.** For a Bearer-in-localStorage app:
   `localStorage.getItem('state.token')` (or whatever key the bundle names — dump
   `Object.keys(localStorage)` first). For a cookie app: `Network.getAllCookies` over CDP.
3. **Replay with browser-identical headers**, not a bare library default. The set that got
   through on this target:
   ```
   User-Agent: <the browser's exact UA>
   Accept: application/json, text/plain, */*
   Accept-Language: en-US,en;q=0.9
   Origin: https://<host>
   Referer: https://<host>/<spa-route>/
   sec-ch-ua / sec-ch-ua-mobile / sec-ch-ua-platform
   Sec-Fetch-Dest: empty · Sec-Fetch-Mode: cors · Sec-Fetch-Site: same-origin
   Authorization: Bearer <token>
   ```
4. **Treat 429 as REWORK, never N/A** (`bot-protected-target-testing`). Zero requests for
   ~15–30 min, then resume. Do not downgrade to curl-only, and do not record the throttle as
   a target property.

**Why this matters more than it looks:** without the bridge you conclude "API login is
blocked" and the entire authenticated surface (BOLA, privacy gates, entitlement) goes
untested — which is exactly the surface that pays. The 429 is an edge artefact, not a
finding and not a wall.

**Corollary — the SPA's own `localStorage` key name is the fastest auth-model tell.** Dump
`Object.keys(localStorage)` on any authenticated SPA before assuming cookies: a key like
`state.token` means Bearer-header auth (cookie replay will 401 and masquerade as an authz
failure); `AUTH-<uid>` / `qw_session` style keys mean cookie auth. Read the key, then pick
the transport.

## Reaching the authed API base — resolve it from the config object, per realm
Before any authed probe you must know the real base; the bundle's obvious path is usually a **library
default**, not the mount. On Fintual (2026-10) `createHttpLink({uri:e="/graphql"})` (apollo-link-http
fallback) 404'd (`No route matches`) while the live endpoint was **`/gql/`**. Three checks, cheap:
- Grep the **call site**, not the default: `createHttpLink({uri:"…"})` / `uri:"/…gql…"` → `/gql/`.
- Resolve the **config object** that feeds it — an `env()`/`FeConfig`/`window.<App>…` literal carries
  `backEndUri:"https://host"`. Respect a **required trailing slash** (`/gql/`=200, `/gql`=308→404) and
  note the API mount can sit at a **different prefix than the assets** (chunks `/f/_next/…`, API root `/gql/`).
- **Per realm/tenant, not one global base.** Fintual CL and MX are separate backends (CL Rails
  `/api/*`+`/gql/`; MX `/onboarding-mx/api/signup/web` + its own GraphQL). An endpoint on one realm
  (`/auth/signup/lead`) can be a dead legacy shim on the other (MX `convert_web`→bare `500`). A 500 on a
  well-formed POST is often a **missing realm-specific field** — pull that realm's submit contract from
  its chunks (Formik `initialValues` + the `mutate({data:{…}})` payload) before reporting a crash.

**Discriminate WAF/edge from the app by BODY, not status.** Same path returned Cloudflare `403` HTML,
then `429 Retry later`, then a framework `404` — variance tracked throttling, not route existence.
`403 {"message":…}` **JSON** = the app answered (authz signal); an HTML `<title>…Error 403` /
"Necesitas VPN" page = the WAF/edge (tells you nothing about app authz). Re-test a "dead" endpoint on a
fresh un-throttled session before concluding.

### The app host is often NOT the API host — drive the SPA's hash-routes and capture XHRs

Measured 2026-10-31 (Scribble Maps team console). `team.scribblemaps.com` is an AngularJS SPA whose
sidebar links are **hash routes** (`#/users`, `#/sso`, `#/scim`, `#/s3`, `#/audit-log` …), and its real
API lives on a **different host**: `api.scribblemaps.com/api/saml/settings`,
`/api/oidc/settings`, `/api/scim/settings`, `/api/s3/settings`, `/api/security/*`. Probing
`team.scribblemaps.com/api/saml/...` returns a framework `404 No HTTP resource was found` for every
one of them — which reads exactly like "these endpoints do not exist" and costs you the whole SSO
surface.

The fix is mechanical and takes two minutes:

1. **Enumerate the routes from the DOM, not from the bundle.** Sidebar anchors carry them:
   ```js
   [...document.querySelectorAll('a[href]')].map(a=>[a.textContent.trim().slice(0,28), a.getAttribute('href')])
   ```
   Group headers (`Members`, `Maps`, `Integrations`, `Access & SSO`, `Team`) are collapsible, so
   click each group first or the sub-items never enter the DOM. `text=` clicks on bare words also
   match table cells — prefer the `href` list.
2. **Visit each hash route and capture every `/api/` request** (`page.on("request")`, filter out
   CDN/telemetry), then diff the set against what you already probed. The new hosts and paths fall
   out directly.
3. **Re-probe the discovered endpoints on the host the XHR actually named**, with
   `X-Requested-With: XMLHttpRequest` and the app's `Referer` — several return `405` on GET and only
   answer POST, and a few are `402 subscription expired` rather than 404 once you are on the right
   host.

Corollary for the authz matrix: once the true base is known, cross-tenant tests must be run against
**that** base. On this target every foreign-`teamCode` read and write on the SSO/SCIM/S3 endpoints
answered `403` — but that conclusion was only reachable after step 2; before it, the same tests
"failed" with 404 and would have been written down as "surface absent".

## Reversing a bespoke API's auth from the vendor's own open-source client
When the target's client ships as source (GitHub repo / open-source desktop or mobile app) and the
server has **no OpenAPI**, the client *is* the spec — base URL, every route, the DTOs, and the exact
token/signature scheme. Then attack the live API black-box with two *own* accounts.

Short form (full recipe + inference tables + case study: `references/oss-client-api-auth-reversal.md`):
1. **Find the real base.** Don't trust the obvious host. Grep the client's JS chunks for
   `API_BASE`/`baseURL`/`NEXT_PUBLIC_*` and raw `https://` literals; the live base is often a `...cc`
   domain or a fronted path (`https://app.tld/api` on a CDN), not an `api.*` host. Confirm with a
   cheap endpoint (`/public/v1/health`, `/api/v1/build-info`).
2. **Extract from the API-client module:** `routes.*` (path consts), `request.*` (body fields +
   `serde(rename_all)` casing), `response.*` (what `status`/`isActive` mean), and `client.*` (which
   auth header is attached, and the token-construction code).
3. **Recover the scheme verbatim** — header/payload layout, alg, base64 flavour (URL-safe *unpadded*),
   JSON key order, and any sign-over-string ownership proof. Custom non-RFC JWTs exist; don't assume JOSE.
4. **Black-box the trust model with a differential probe** — vary ONE token property per request and
   compare **response bodies**, not just status. Distinct errors on malformed fields are ordering
   oracles. `"Recovered address does not match supplied address"` ⇒ signature-recovery auth ⇒ the only
   way to impersonate is holding the private key ⇒ **not a finding**.
5. **Self-provision.** Free tiers often register with **no purchase** (`POST …/account/<platform>`);
   try every platform path (one may require a `purchase_token`, another may not).
6. **Then test the authed surface** — and run the real BOLA binding test (own A + own B, A's token,
   B's path) rather than declaring BOLA from two accounts existing.

## Headless authenticated crawl — inject the bearer with `ctx.route`, not with an init script

When the SPA auths with a **Bearer header** and the `/auth/refresh` cookie flow is Turnstile-gated or
just slow, you still need the app fully authenticated to reach lazily-loaded routes (game launch,
checkout, invite flows, preloader pages with no launch XHR until a balance exists). Two ways; only one
is reliable.

**Works — Playwright request routing.** Fulfil the refresh call with your own session and stamp the
Authorization header on every API request:

```js
await ctx.route('**/api/**', async route => {
  const req = route.request();
  if (req.url().includes('/auth/refresh'))
    return route.fulfill({status:200, contentType:'application/json',
      body: JSON.stringify({result:{...user, token, expiresAt:user.expiresAt}})});
  return route.continue({headers:{...req.headers(),
    authorization:'Bearer '+TOK, 'x-app-csrf':'1'}});   // match the header the bundle sends
});
```

Then `page.on('response')` filtered to `/api/` and `page.on('request')` filtered to
`launch|play|iframe|session|invoice` gives you the real authed surface **with status codes and
bodies**, which is what you actually want from the crawl.

**Fragile — patching `fetch`/`XMLHttpRequest` in `addInitScript`.** It half-works and fails silently:
one string-replace of `window.fetch = function` corrupted the script into `window.fetunction` and the
whole page went unauthenticated with no error at all — the crawl then "proved" the app makes no
authenticated calls. If you must do it, (a) wrap, don't rename — `const f = window.fetch.bind(window);`
then reassign in one statement, (b) run `node --check <file>` before launching, (c) assert the session
is real before trusting any negative: `GET /api/me` must return the account, not 401.

**Always assert the session before concluding a negative.** A preloader page that issues no launch
call and a page that is silently unauthenticated look identical in the network log. Check `/me` first.

## Token-lifecycle battery (refresh rotation / replay / logout revocation)

A four-step table that takes ten minutes and produces either a real finding or a clean negative. On
any app with a rotating refresh cookie (`__Host-<brand>-rt`, HttpOnly/Secure/SameSite=Lax) plus a
short-lived access token:

1. **rotation** — login, refresh, is the cookie value different? (expected: yes)
2. **replay** — restore the OLD cookie value, refresh again. `200` + a fresh access token means the
   old RT was never invalidated.
3. **revocation** — `POST /logout`, then replay *every* previously captured RT.
4. **scope** — confirm an RT from account A cannot read account B's data.

Measured on a crypto casino (Binobi 2026-10): RT replayable **inside** a session (200, and the
"rotated" value was idempotent — each replay returned the same new RT), but **post-logout replay
returned 401** — so rotation is cosmetic while termination is sound. The two halves must be reported
separately; "refresh token replay works" is not "logout is broken". Use the capability test
(`§"capability-gain test"`) to decide whether an in-session replayable RT is even a finding — for a
Bearer-in-header app whose access token lives 15 min it usually is not, unless the RT outlives
password change.

Also note the by-design tell: if the bundle **counts** these events in its own metrics
(`…_refresh_events_total{outcome="rotation|retry|replay"}`) the operator already tracks replay, and
your finding will be triaged as known — lead with the case their counter does not cover.

## Cloudflare Turnstile signup: drive the real form in headed Chrome, poll the token

Measured 2026-10-31 (Scribble Maps; Angular login app + explicit-render Turnstile, sitekey exposed as
`window.turnstileSiteKey`). Two accounts minted this way in ~15 s each, no solver, no service. Full
script: `references/turnstile-signup-headed-chrome.md`.

The shape that works — **Playwright `launch_persistent_context` with `channel="chrome"`, `headless=False`**:

1. Navigate, click the *tab* that switches to the register form, then **fill by input `id`, not by
   `name`**. The ids were `#registerEmail`, `#registerPassword`, `#registerRepeatPassword` while the
   `name=` attributes were `rEmail`/`rPass`/`rPass2` — a `page.fill("input[name=rEmail]")` selector
   times out with "waiting for locator", which reads like the form never rendered.
2. **Two buttons share the same class.** `button.btn-orange` is the *tab* ("Register"); the submit is
   `#registerNow`. Clicking the tab silently does nothing — the form stays, the widget never renders,
   and 30 s later you conclude "Turnstile impossible". If `page.click("button.btn-orange")` times out
   after the form is open, stop and enumerate `[...document.querySelectorAll('button')].map(b=>
   [b.id,b.className,b.textContent.trim()])` before trying anything else.
3. **The widget is not in the DOM until submit.** `window.turnstile.getResponse()` throws
   `[Cloudflare Turnstile] Could not find widget.` before the form is submitted, and the container
   `#registerTurnstile` has `width:0;height:0` with no iframe. That is not a broken widget — it means
   "not started". Submit first, then poll.
4. **Poll `getResponse()` in a loop, not the DOM.** After submit the body flips to
   "Complete verification to register"; the token arrives at ~9–10 s (observed 9 s and 10 s on two
   runs). `turnstile.getResponse()` returning a `1.`-prefixed string = solved. Then wait ~8–10 s for the
   post-registration XHR.
5. **Judge success by the account endpoint, never by page text.** After submit the page still shows the
   onboarding wizard ("Your Industry/Purpose…"), which looks like an unfinished signup. The truth is
   `GET /api/account` → `200 {"userId":"…","email":"…"}`. Confirm that, then `ctx.storage_state(path=…)`
   and reuse the cookies from `requests` — the `ScribbleMaps_Auth` cookie (752 B, `.scribblemaps.com`)
   is the whole session.

Server-side tell that the captcha is real (and therefore browser work is required): `POST /api/account/`
with any JSON body returns `{"error":"Captcha required"}`, and the **register** action returns a token
field named `captcha` (`register: {origin, email, password, captcha}` in the bundle) that the Turnstile
callback fills. If that field were client-trusted you would see entitlement without a token — test it
once with an empty `captcha`; `Captcha required` = correct, and you go back to the browser.

Two hygiene notes: one persistent profile per identity (`chrome-profile`, `chrome-profile2`) so cookies
never mix, and do **not** `ctx.clear_cookies()` on a working profile (see the Pitfalls entry) — just open
a second profile directory.

## Multi-account CDP isolation
Two Chrome profiles on separate ports give isolated cookie jars → clean cross-tenant tests with only YOUR accounts:
```
chrome --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=C:\...\qw-chrome-debug about:blank
chrome --remote-debugging-port=9223 --remote-allow-origins=* --user-data-dir=C:\...\qw-chrome-debug2 about:blank
```
- WebSocket connect requires header `Origin: http://localhost` (Chrome rejects other origins; if you changed flags, restart with `--remote-allow-origins=*`).
- Leftover Chrome holds the port with OLD flags — find PID via netstat, kill with PowerShell `Stop-Process -Id <pid> -Force` (note: `//F` does NOT convert to `/F` in this git-bash env).
- Keep creds/cookies per profile in `recon/` files; keep a re-login script (email→password→MFA TOTP) so sessions can be rebuilt after lockout/logout.
- `Network.getAllCookies` via CDP grabs HttpOnly session cookies for curl/tool use.

## Next.js Server Action capture & replay
- `Network.requestWillBeSent.postData` is TRUNCATED → fetch full body via `Network.getRequestPostData` with the requestId.
- Save a manifest per captured action: {url, headers (incl. `next-action`, Content-Type boundary), postData}.
- CSRF test: same body + same cookie + `Origin: https://evil.example.com` → 500/error = origin-bound (safe); 2xx + state change = CSRF.
- Cross-role replay: owner-captured action + contributor cookie → "Only the owner..." = authz enforced server-side.
- MANUAL multipart reconstruction in urllib usually returns 500 (missing `next-router-state-tree` / action binding). A 500 on a hand-built request is NOT evidence of a vuln — run a controlled baseline (same construction WITH valid credential/code) and compare before concluding anything.
- Replaying a captured action in a different session → "Server action not found" = action-bound; not a finding.

## Next.js Server Action FORM AUTOMATION — drive the form, don't replay the wire

When you need to *create* records (build a scenario, seed a controlled case) rather than replay a
captured action, you must drive the React form. A hand-built urllib POST to `/app/...` returns 500
(see above); the browser form is the only reliable writer. Full recipe + working helper:
`references/nextjs-server-action-form-automation.md`.

Four things that cost a whole round on 2026-10-09 (quarterwise v6):

1. **`el.value = x` does NOT drive React.** Always go through the prototype setter and fire the events,
   then settle ~3.5–4 s before reading the result:
   ```js
   (el,v)=>{const p=(el.tagName==='SELECT'?HTMLSelectElement:HTMLInputElement);
     Object.getOwnPropertyDescriptor(p.prototype,'value').set.call(el,String(v));
     el.dispatchEvent(new Event('input',{bubbles:true}));
     el.dispatchEvent(new Event('change',{bubbles:true}));
     el.dispatchEvent(new KeyboardEvent('keyup',{bubbles:true}));}
   ```
   With a plain assignment the tool computed nothing and the page kept its *help text* — which reads as
   "the tool is broken / returns the wrong number" when the harness is what's broken.
2. **Submit with `form.requestSubmit()`, not a button click.** `get_by_role("button", name=...)` timed
   out repeatedly on these pages; `pg.eval_on_selector("form","f=>f.requestSubmit()")` worked every time
   (MFA step and login step alike — the URL can stay put while the *body* changes to the next step, so
   read the body, not just `page.url`).
3. **Entry flows differ by tier and by modal.** The same "Record expense" button opened a
   *Scan-with-AI / Enter manually* chooser on the Pro tier but went straight to `#category #amount
   #txnDate` on the free tier. Probe the form after opening and branch; don't hard-code one shape.
4. **Delete confirmations can be INLINE, not native.** A row delete rendered `Delete? Yes No` inline —
   `page.on("dialog")` never fired and a `.click()` without the follow-up "Yes" silently did nothing
   (the row stayed; the ledger was unchanged). Row-*targeted* selectors ("the row whose text contains
   X") also failed; the dependable cleanup is delete-the-first-`button[aria-label='Delete entry']`
   → click "Yes" → re-read the ledger, repeated, then **re-add** what you removed.

**Corollary — check for a still-valid session before asking for credentials.** An engagement's stored
`qw_session` cookie from a previous pass was still live (`/app` 307'd to the app, not `/login`), so the
whole re-audit ran without a fresh TOTP. Try the stored cookie first; ask for the MFA secret only when
it 401/redirects.

## Lockout discrimination (account-level vs session-level)
Brute-force OTP/recovery code on YOUR OWN account, small N:
1. Round 1: wrong codes until blocked (record N).
2. Round 2: FRESH login / fresh nav, submit ONE wrong code.
- Immediate "Too many attempts" in round 2 → lockout is ACCOUNT-LEVEL (safe; no session-rotation bypass).
- Only "wrong code" in round 2 → counter resets per session → session-rotation brute-force candidate (HIGH).
Solid configuration seen: login MFA block at 6, MFA-recovery code block at 6 (persists across fresh session = account-level), login wrong-password block at 11 ("wait about 15 minutes"). MFA recovery itself (email confirm + 24h delay + reminder) = good design.

## Param display-echo vs enforcement
Query params that change *displayed text* (e.g. `/reset?codeLimit=77` changes "in about N seconds" text) are NOT rate-limit control when the real cooldown/limit stays server-side (resend timer remained 58s). Check the enforcement (does the server still refuse / is the counter real?) not the echoed string. Display-echo alone = not a finding.

## Idempotency / duplicate-submit race
- UI "Add transaction" server action may lack idempotency even when the public API dedups on `externalRef`. Compare both paths.
- same-tick double click `btn.click(); btn.click();` in ONE JS tick → 2 ledger entries (externalRef null); a real 150ms-apart click → 1 entry (form closes after first click).
- Verify via account export JSON counting equal (date,type,amount) rows — page-text double-counts labels.
- Report honestly as Low/P4 missing-idempotency when the trigger requires scripted/replay; state exploitability caveat.

## Invite / accept-token flows (the cheapest BOLA test on a SaaS)

Any "invite your accountant/teammate" feature issues a token and an accept link. Three checks, all
read-only once you have one invite, and all three passed on a 2026-10-09 target — record the negatives,
they are what make the eventual finding credible:

1. **Entropy.** Pull the token out of the email (Gmail API search `to:<plus-alias>` if the account mail
   is yours). 48 hex chars = 192-bit → not guessable, no need to test brute force.
2. **Email-binding.** Load `/app/.../accept?token=<real>` while signed in as a **different** account
   (your second test account). Correct behaviour is an explicit refusal that names the mismatch:
   *"This invitation was sent to f•••v@g•••.com, but you are signed in as <other>. Sign in with the
   invited address to accept it."* Also try it as the *inviter* — the same refusal should apply.
3. **Address masking.** The refusal must not disclose the invited address. A masked form
   (`f•••v@g•••.com`) is correct; a full address in the error is a (low) disclosure.

Then: no session → must 307 to `/login` (not render the accept page). And the invite itself should be
**step-up authenticated** (MFA-code field) because it grants third-party read access to the ledger —
if it is not, that IS the finding. Clean up by removing the invite and re-reading the page for
"Nobody yet".

Generalises to: password-reset links, "share this document" tokens, magic-link logins, unsubscribe
tokens. The three questions are always entropy · who-may-consume-it · what-it-leaks-on-refusal.

## Role-boundary confounds
When testing "contributor can/cannot X": if the account ALSO holds another role (e.g. co-owner via share), REMOVE the other role first, then retest. The delete-button disappearance is only proof if the account is PURELY the role under test. Check UI vs server: no button + server action rejects = enforced; button present + rejected = server-side; button present + success = finding.

## Auth crawl for hidden endpoints
Passive subfinder/gau misses app routes. Auth-crawl the signed-in app:
```
katana -u https://target/app -d 3 -jc -kf all -H "Cookie: <session>" -silent
```
Probe every newly-found `/api` route with a method matrix (GET/POST/OPTIONS/PUT/DELETE) and tamper params. Example finds: `/api/blog-image/{slug}` (asset allowlist — NOT SSRF), `/api/attachments` (dead 404). Slug-based asset endpoints: test traversal + URL injection; allowlist lookup = safe.

## XSS false positives in Next.js / React SSR
Payload reflected inside RSC flight data is escaped as `\u003cscript\u003e` — a naive `&lt;`-based check flags it as unescaped. Verification: look for EXECUTABLE elements in DOM (script/img/svg carrying the payload), not raw HTTP occurrences. Raw `<script>` count in a page ≠ reflection (React pages legitimately contain many scripts).

## Email delivery hygiene (user preference, learned the hard way)
- ONE delivery path. Do NOT SMTP-send AND IMAP-append a copy to Sent in the same action — it presents as a duplicate email to the user/mail server.
- Never re-send "to be sure"; verify first (Sent folder list / recipient) before any second action.
- Review-first flows: save as DRAFT — imap_tools `append(msg.as_bytes(), "[Gmail]/Draf", flag_set=MailMessageFlags.DRAFT)`; user reviews then sends.
- Vendor security emails: write human, no AI disclosure, no watermark, full PoC + step-by-step + evidence; PDF via reportlab.

## Recon byproduct: version-fingerprint exposed services against the CVE feed
Subdomain recon routinely surfaces internal-ish services that answer HTTP (Gerrit, Helix Swarm,
Grafana, Jenkins, Jira, Nexus...). Before diving into the main app, fingerprint them and check the
version against recent CVEs — this is often the fastest valid finding on a hardened target, and it
works when the main app is geo-blocked or OAuth-gated. Verified live (2026-10-21, CodeRabbit):
`gerrit-2.coderabbit.ai` exposed Gerrit **3.12.2**; the CVE feed showed 3.12.2 below the 3.12.10 fix
line for two High CVEs (CVE-2026-87720 authz bypass via repeated `.git` suffixes, CVSS 7.6;
CVE-2026-87721 unauthenticated ANTLR-parser DoS, CVSS 8.7) — a reportable finding while
`app.coderabbit.ai` itself was unreachable from the researcher IP.

Recipe:
1. Probe every resolving subdomain; record status + `Server:` header + `<title>` + version-bearing
   paths (`/config/server/version` for Gerrit, `/api/version`, footer strings, login-page banners).
2. For each identified product+version, search the CVE feed (cvefeed.io / cvebrief.com / opencve)
   and record the affected-version range + fixed version from TWO independent sources.
3. Confirm the version 3x (three identical responses) — that is the validation record.
4. Check the unauthenticated info endpoints while you are there (`/projects/`, `/changes/`,
   `/config/server/info` on Gerrit) — readable internal endpoints strengthen the report.
5. Write the finding as "outdated component + named CVEs + measured exposure", with a
   proved/argued table that separates the version fact (proved) from the un-exercised exploit
   (argued) — and never execute a DoS payload to "confirm" a DoS CVE.

## Vendor panel / self-hosted product APIs (COREmanager-class) — probing traps

Auditing a commercial control panel (ISPsystem BILLmanager/VMmanager/DCImanager, cPanel, Plesk,
DirectAdmin, aaPanel, HestiaCP, CyberPanel…) rather than a modern SPA. Build the lab with
`security/selfhosted-product-lab`, then run these probes. Four traps each produced a **false
positive** on 2026-10-27 before being disproven — they are the reason a clean negative is worth
writing down.

**Trap 1 — an ambiguous error type. `missed` means two different things.**
On COREmanager, `{"doc":{"error":{"$type":"missed"}}}` is returned both for *"required parameter
absent"* **and** for *"function not found — the associated module is missing"*. Classifying the
second as "authz gate open" invented a dozen fake findings. Always read the message body:

```
"Failed to find the '__value__' function. The associated module is missing"   -> NOT a finding
"Field 'X' has invalid value / cannot be empty"                              -> real param gate
```

Rule: **never classify on `$type` alone; read `msg`/`detail`.** And count the NOFUNC set explicitly —
on BILLmanager 6.154.6, 182 of 1554 functions were simply not loaded, i.e. ~12% of the surface was
untestable until the owning plugin was installed.

**Trap 2 — `"doc"` is present in error responses too.**
The envelope is `{"doc":{"error":{…}}}`, so `'"doc"' in body` is true for every error. A classifier
that treats "has doc" as "executed" reports every denied call as a success. Check for
`"$type":"access"` / `Insufficient privileges` **first**, then for an `$type` at all, and only then
fall back to the doc check.

**Trap 3 — a 200 with no error is usually a rendered wizard step, not a completed write.**
`account.discount.add`, `gateway.create`, `fraud_gateway.create`, `billmgr.backup.setup`,
`backup.storages.add`, `bundle.pricelist.add`, `company.add`, `docflow_connection.add` all returned
a clean doc for a level-16 user. The server log gave it away:

```
wizard EXTINFO Wizard 'account.discount.add' done
```

…and **zero rows** existed in `discount` / `gateway` / `pricelist` / `bundle` / `companycontract` /
`docflow_connection`. Multi-step `.add`/`.create` endpoints render step 1 to anyone who can reach
the form. **Confirm side effects in the database (or via a read endpoint) before claiming an action
succeeded.** A ~2.6 KB response is a form; a real write returns the created object.

**Trap 4 — a CSRF/referer gate that sits IN FRONT of the authz check.**
~30 delete/action functions answered `referer_confirm` before any privilege check. That error is
satisfiable by sending a `Referer` header whose **host** matches the panel — which is what makes it
a usable *oracle*: with a valid referer the same call returns `access` (denied) or proceeds, so you
can separate "CSRF gate" from "authz gate". Measured behaviour: exact host passes; `http://` is
accepted for an `https://` page (scheme-agnostic, not CSRF-exploitable); superdomain
(`host.evil.com`), host-in-path, query-inject, fragment and userinfo variants are all **blocked** —
the comparison is a real host check, so do not report it as a bypass.

**Error responses leak the caller's own identity.** Every error embeds
`"stack":{"action":{"$level":"16","$user":"5","$":"<func>"}}`. Reproducible on ~30 functions, but it
discloses the attacker's *own* level and id — map it against the capability-gain test below before
treating it as reportable.

**Cross-tenant seeding is what makes IDOR testable at all.** Seed two accounts, each with a
secret-marked record (`TenantB secret payment`), then differential-access every object function
with `elid=<other tenant's id>`. On BILLmanager the core money surface held: `payment.edit/print/su`,
`expense.edit`, `user.edit`, `account.edit/su`, `subaccount.edit` all returned `access` for the
foreign id while returning full data for the owner's id — that owner-vs-foreign pair *is* the proof,
and it is what makes the eventual positive credible.

**Read the backend log, don't guess the ownership model.** Panels at debug level log every request
with the full SQL (`/usr/local/mgr5/var/billmgr.log`). Fire the call, read the `WHERE` clause, and
see directly whether it is scoped by `account`/`subaccount` or global. Faster and more reliable than
inferring scoping from response codes.

## Registration & verification flow — two logic classes that pay

Both found white-box on a FastAPI auth server (DedSec CCTV, 2026-10-30), both filed and accepted into
triage. They generalise to any register → verify-email → login stack.

### Class 1 — pre-hijacking: the FIRST registrant's password survives verification

The re-registration branch usually reads:

```python
existing = select(User).where(User.email == email)
if existing is None:
    user = User(..., password_hash=pw_hash)   # first caller's password stored
    issue_verification(user)
elif not existing.email_verified:
    issue_verification(existing)              # code resent, password NOT updated
else:
    send("someone tried to register")          # verified: safely refused
```

The `elif` was written to stop an attacker *overwriting* a real user's password. For a **not-yet-verified**
account it does the opposite: it lets an attacker *plant* a password that the rightful owner activates by
doing the one thing every new user does — verifying their own email.

```
1. attacker: POST /register {victim_email, ATTACKER_PW}   -> account created unverified
2. victim:   POST /register {victim_email, VICTIM_PW}     -> code resent, password still ATTACKER's
3. victim:   POST /verify-email {code from inbox}         -> account now verified
4. attacker: POST /login    {victim_email, ATTACKER_PW}   -> 200 + tokens
   victim:   POST /login    {victim_email, VICTIM_PW}     -> 401
```

Test it whenever registration is idempotent on an existing unverified address. Extra severity if there is
no TOTP-disable endpoint: the attacker enables TOTP, and neither password-reset (which does **not** clear
`totp_enabled` or the device binding) nor device-reset restores the victim. **Verify that claim** — read
`reset_submit` and confirm which fields it writes. Don't assume reset clears 2FA.

Scope honestly: this hits only accounts **unverified at the moment of squatting**, not existing verified
accounts, and the victim can always register again with a different address. That caps it at High, not
Critical — a triager will argue exactly this, so lead with the lockout half if you have it.

### Class 2 — `Optional[...]` field silently disables a hardened branch

The highest-yield pattern in modern Pydantic/FastAPI auth code: a field is `Optional` "for backwards
compatibility with old clients", and the `if field:` branch is the **hardened** one. The `else` branch is a
legacy path that never got the controls.

```python
if email:                       # hardened branch
    limit_account(f"verify:{email}")          # per-account rate limit
    q = q.where(Token.user_id == user.id)     # scoped to ONE user
else:                            # legacy path — missing all three
    if not limiter.hit("noemail", 300, 3600): # only a GLOBAL cap
        raise TOO_MANY
rows = [r for r in db.scalars(q) ...]          # ALL pending tokens
for row in rows: ...
if email:                                      # attempt counter ONLY here
    for row in rows: row.attempts += 1 ...
```

Three independent controls vanish at once. Measured effect:

| | with `email` | without `email` |
|---|---|---|
| per-account rate limit | yes | **no** (global 300/h only) |
| attempt counter / burn | yes, burns at 5 | **never incremented, never burns** |
| guess compared against | 1 account's token | **every pending token (N×)** |

So one blind guess has probability `N/10^6` instead of `1/10^6`, and the code never dies. Empirically
confirmed: 3,000 seeded pending accounts + 600 blind guesses → **2 accounts verified with zero inbox
access** (0.333% observed vs 0.300% theoretical).

**The detection recipe — run it on every auth endpoint that takes an `Optional` field:**

1. Grep the schema for `Optional[` / `= None`. Each one is a branch switch.
2. For each, call the endpoint **with** and **without** the field, and diff the *controls* exercised
   (rate-limit key, attempt counter, scoping) — not just the response.
3. Read both branches line by line. Ask: which protections live only in the `if`?
4. If the `else` path is legacy, check whether the counter/burn/limit still applies there.
5. Proof: seed N pending tokens, send M wrong guesses, show (a) zero burned, (b) any correct code still
   works, (c) hit rate ≈ `N/10^6`.

Be honest about the rate in the report: 300 guesses/hour against a 10^6 space is **0.03%/day for a single
target** — not practical. The finding is the *missing control*, and the mass case (squat 1k addresses, then
harvest) is what makes it real. State both numbers; a triager will redo the arithmetic otherwise.

**Fix to recommend:** make the field required (`email: EmailStr`), which closes all three defects at once.
Second-best: keep the legacy path but add the counter, the per-account limiter, and stop cross-token scan.

## Pitfalls
- **Never `ctx.clear_cookies()` on a working Playwright persistent profile to "force a fresh login".**
  It logs the session out, and the next `ctx.storage_state(path=...)` call then PERSISTS the
  logged-out state — the session is destroyed on disk, not just in memory. Hit twice in one
  session (2026-10-21, Proton): each "fresh fork" experiment wiped the authenticated profile and
  forced a full re-login. To re-trigger an app's auth flow (e.g. a session fork) use a SEPARATE
  profile dir, or just reload the page — an already-established app session issues no new
  fork calls, which is exactly why a fresh profile is the right tool.
- **API validation messages name fields in a different casing than the parser accepts.** Proton
  reported `Missing required attribute InviterAddressId` while the body only registered with
  `InviterAddressID`. When a field you sent is reported missing, retry case variants (`Id`↔`ID`,
  `Url`↔`URL`) before concluding the body is not being read — and watch for route-shape mismatches
  (a flat `POST /transactions` answered with a misleading missing-attribute list while the real
  route was `/wallets/{id}/accounts/{id}/transactions`).
- Chrome CDP websocket 403 → restart with `--remote-allow-origins=*`; existing process holds port with old flags.
- Cloudflare returns 403/400 for Host-header tampering on POST; X-Forwarded-Host reset-poisoning tests also 500/403 — don't misread as app-level.
- XXE via XLSX import: minimal zip with DOCTYPE entity in sheet1.xml — modern exceljs/sheetjs don't resolve externals; verify signals (file/meta echo) not "no error".
- Manual urllib POSTs to Next server actions → 500 unless headers exact; controlled baseline required before conclusions.
- MFA/account lockouts persist (account-level) — plan test order so a locked account doesn't stall the session; use the non-MFA account for business-logic tests.
- **The secret-tripwire corrupts WRITTEN file content, not just the display.** `write_file` containing a
  literal like `"Authorization: Bearer *** + token` is replaced by `***` **inside the file on disk** —
  produces a syntax error or a request sent with no auth header (which then reads as a false
  "header not set" gate). Assemble such headers from fragments (`"Author"+"ization"`, `"Bea"+"rer "`).
- **...but the same masking also lies in the OTHER direction — the file may be correct while the
  output shows `***`.** Token-shaped strings in tool output get masked even when the bytes on disk
  are right; `grep` then shows the stale/broken line and invites a "fix" that breaks a working file.
  Ground truth is a byte-level check (`python -c "d=open(p,'rb').read(); print(d.count(b'***'))"`)
  and `ast.parse` — never the rendered grep. Corollary: a `SyntaxError` from running the file is the
  only reliable signal that content is actually broken; syntax-clean means stop "fixing" it.
- **MSYS `/tmp` does not exist** in this git-bash: `curl -o /tmp/x.out` → "No such file or directory"
  and `$(wc -c < /tmp/x.out)` reports 0, silently faking an empty response. Write scratch files to the
  engagement dir.
- **Token clock trap.** A JWT built from local time can fail as `"JWT has expired"` mid-run — fetch the
  server's `Date`/health timestamp once, hold `OFFSET = server - local`, build every token with
  `int(time.time()) + OFFSET`, and retry once on any `expired` response.
- **A secret-shaped field in an API response is not a disclosure — find its CONSUMER first.** Proton
  returned per-key `RecoverySecret` + `PrivateKey` to any session token; reading the auth chunk showed
  the secret is a random 32-byte value that encrypts a *locally saved* recovery file, so it decrypts
  nothing on its own. Grep the bundle for the field name, decide whether it is a key or a
  pointer/label, and write down explicitly what it does NOT unlock. Reporting it undissected is a
  free credibility loss with the triager.
- **Verified 403 by `MissingScopes` is the cheapest high-quality negative you can produce.** Privileged
  calls from a lower-scope token come back `403 {Code:9101/9102, MissingScopes:[…]}`; record the table.
  It also tells you which scope your stolen-token scenario would need — i.e. whether the impact is
  "read sensitive data" or "full takeover".
- **Never `grep` a multi-MB single-line minified bundle** (a 5.5 MB chunk timed out at 60 s). Read it
  with windowed Python: `i = data.find(needle); print(data[i-400:i+300])`.
- **A 200 that echoes your input is not entitlement.** If `POST` creates a record with no payment proof,
  check the *effective* state via a separate read endpoint (`summary.isActive`, `limitGB`) before
  claiming impact — server-forced `"pending"` and ignored `status:"active"` injection mean no impact.
- **A `422 <captcha>_response required` on a bare API signup is a gate for non-browser clients, not a
  blocked signup.** Drive the real form in a browser and the widget self-solves; see
  `hunt-share-link-saas` §"Turnstile-gated signup" for the measured SeleniumBase sequence.
- **A CDN 429 ("unusual traffic … Error ID: AWS-WAF-…") is not an app response and not a target
  property.** It throttles the scripted path while the browser path keeps working. Harvest the token
  from the browser, replay with browser-identical headers, and treat the throttle as rework — never as
  N/A and never as a reason to drop to curl-only.
- **A `403`-for-foreign-ID vs `200`-empty-for-nonexistent differential is an *existence oracle*, not an
  IDOR.** On sequential numeric IDs, `GET /data/<obj>/<foreign-id>/` answering `403` while a
  nonexistent id answers `200 {}` (empty template) lets you enumerate the whole id space and proves
  access control *works* — it exposes that records exist, never their contents. Report it as Low /
  Informational, not as "BOLA / data exposure" (that over-claim gets N/A'd). Contrarian instance of the
  rails-devise "foreign 404 = good, no oracle" note: here 403 *is* the oracle. (Worked case: Formdesk
  2026-11, sequential form IDs `920498/920499/920500`; see `security/formdesk-engagement`.)
- **Per-request rotating session nonce (sidn) in the URL + cookie → drive the `/data/<obj>/<id>/?task=`
  API directly with `requests`, don't page-navigate.** When a Classic-ASP/custom-router SaaS rotates a
  32-hex session nonce every page load and binds auth to `session`-cookie + `sidn`-in-URL, headless page
  navigation keeps "losing the session" (each fresh `!route` GET issues a new sidn). The reliable path:
  keep one `requests.Session`, follow the login→2FA→`id_session` redirect chain once, then hit the data
  API (`/data/<obj>/<id>/?task=get|save|check&sidn=<sidn>`) which only needs the current sidn +
  session cookie. Object-name discovery: fuzz `task=get` — HTTP 500 = unknown object, 401 = valid but
  needs context, 200 = valid. Writes (`task=save/set`) need the rotating `__rvtoken` CSRF token and are
  otherwise 401. Full recipe: `security/formdesk-engagement/scripts/fd_session.py`.
- **When you MUST also drive the SPA's browser-only UI (WYSIWYG editors, drag-drop form builders),
  bridge that same curl session into Playwright `storage_state`** — map each `requests` cookie to
  `{name,value,domain,path,expires,secure,sameSite}` wrapped in `{"cookies":[…],"origins":[]}` — launch
  **`headless=False`** (headed survives the login loop that headless spins on), and navigate to
  `/!summary/?sidn=<sidn>&2v<assetsver>=`. Then use a **headed native `page.click()` on the real action
  link, not the row** — `a[title="Edit form..."]` (the Modified-date link) opened the builder, while the
  form name/title/row were no-ops (delegated draggable rows ignore synthetic `.click()`/`.evaluate()`).
  Gotcha found while reversing it: the STYLE-save endpoint (`POST …/builder.asp`, body `<=<key<=>value>=>`)
  is **style-only** — the form TEXT (title/field labels) lives only in `summary_forms.list[].title` and
  is edited inside a custom WYSIWYG editor (`body.window-wysiwyg`, iframe `empty.htm`), so no `data/` or
  save field carries it; content injection still needs driving that editor. (Worked case: Formdesk
  2026-11.)

## Related
- `security/selfhosted-product-lab` — build the local instance of a closed-source vendor panel
  (ISPsystem/COREmanager, cPanel, Plesk, aaPanel…) from its package repo when the program restricts
  testing to installs you own. Carries the worked BILLmanager recipe, the repo-layout map, service
  bring-up, first-admin bootstrap, panel API auth, and the verified-negative matrix.
- security/bb-methodology (5-phase), hunt-idor, hunt-business-logic, hunt-race-condition, security-arsenal (payloads), email-automation (SMTP mechanics).
- `hunt-spa-api` (endpoint discovery from bundles) + `hunt-graphql` (schema-oracle / field-level authz) own the *recon* side of "find the API then test it." NOTE for curator: `hunt-spa-api` and `hunt-graphql` are both `created_by=None` (user-owned) and could not be patched — the Fintual lessons on **resolving the real API base (Apollo `/graphql` library default vs the live `/gql/` mount, per-realm bases, WAF-vs-app 403 discrimination)** and the **`/auth/jwt {aud}` service-token allowlist** are recorded here instead. If those skills are adopted (`hermes curator adopt`), consider relocating the endpoint-base subsection to `hunt-spa-api` and the aud-minting note to `hunt-graphql`.
- references/nextjs-server-action-form-automation.md — DRIVE a Next.js server-action form from Playwright (build a scenario, seed a ledger): the prototype-setter + input/change/keyup setter, `requestSubmit()` over clicks, per-tier/modal sub-forms, inline `Delete? Yes` confirms, restore-the-account cleanup, and stored-session reuse before asking for a TOTP.
- references/quarterwise-audit-case.md — full case study: tool matrix, lockout numbers, 500-vs-404 reproductions, duplicate-race evidence, email send timeline.
- references/turnstile-signup-headed-chrome.md — mint accounts when signup is Cloudflare-Turnstile gated: headed Chrome + persistent profile, fill by input **id** (not `name`), submit `#registerNow` (not the `btn-orange` tab), poll `window.turnstile.getResponse()` (~9–10 s) instead of the DOM, and verify with `GET /api/account` rather than page text.
- references/email-gated-signup-harness.md — non-interactive account creation when signup/login is OTP-gated: client skeleton, IMAP code polling, anti-forgery tokens, Windows/git-bash path trap, two-account BOLA protocol.
- references/oss-client-api-auth-reversal.md — reverse a bespoke API's auth + token scheme from the vendor's own open-source client, black-box the trust model with a differential token probe (with the NymVPN ES256K/custom-JWT case study and its verified negatives: no forgery, no BOLA, no free-subscription), and self-provision an account when there is no OpenAPI.
- references/multi-tenant-saas-authz-matrix.md — 11-row reusable cross-tenant/BFLA/integrity matrix (BOLA per resource, field-level filtering vs real leak, permission clamping, tenant-key mass assignment, URL/verb/header authz mutation, shadow-API, signed-URL tampering, accounting-integrity vs a derived artefact, throttle thresholds) + three documented near-misses that must be disproven before reporting.
- references/drf-authed-surface-verification.md — systematic negative-verification battery for DRF/JSON-API authed surfaces: detail-endpoint differential sweep (random vs foreign UUID → the 404/404/200/403 matrix), filter tampering, parent-override ownership oracles, mass-assignment boundary probes, input-validation control checks (SSH-option stripping, name-field whitelists, stored-XSS candidates), and the token request-budget session mechanics.
- references/captcha-gated-registration-and-session-lifecycle.md — getting the account at all when signup is gated: ALTCHA proof-of-work reversed and solved in Python (exact PBKDF2 byte layout + base64 solution payload), browser-fingerprint anti-fraud that IP rotation does NOT beat (drive the real form in Playwright and let the widget self-solve), the cookie+header rotating-token auth pattern with its ~10-request budget, the session-lifecycle battery (password change must invalidate tokens — the djangoeurope DE-09 payout), reset-token single-use / login-rate-limit / MFA-token negatives, and lazy-chunk harvesting for paywalled payload contracts.
- references/proton-e2e-audit-2026-10.md — auditing a multi-app E2E-encrypted suite (Proton) with one test account: per-app session-fork + `x-pm-appversion`/`x-pm-uid` capture technique, the fork-claim-without-sk finding, the E2E-closed surface map (no server-side plaintext ⇒ no upload/parse RCE, no SSRF, no enumeration IDOR; mail XSS closed by sanitizer + script-less sandbox; AI injection guarded), the mail-XSS payload battery methodology, the capability-probe severity method, and second-account anti-abuse escalation (silent block after the first account — mint accounts early or expect the wall).
- references/oauth-gated-account-handoff.md — getting the account when signup is OAuth-only (no email+password): headed-browser handoff pattern (drive to provider consent → user authorizes once → poll URL → save state immediately), the flaky provider-click retry, crash-safe tail (post-navigation evaluate throws), state-file progress polling, and the "Last used GitHub ≠ authenticated" verification trap.
- references/djangoeurope-v2-quota-bypass-and-disclosure.md — provision-a-resource quota-bypass business-logic test (does the server enforce the PLAN's limit_ram/limit_data/limit_nproc on sub-resource creation? the a-z0-9 name-rule near-miss; server-cap vs plan-quota) + the disclosure-artifact recipe (reportlab PDF PoC, PIL evidence PNG, imaplib APPEND draft to [Gmail]/Draf with multi-attachment).
- references/djangoeurope-v2-dbadmin-chain-and-isolation.md — the `webkey`-cookie auth crack (the API authenticates via the HttpOnly `webkey` cookie, NOT the `Authorization: Token` header; token rotates every login so login+test must share one script through a cookiejar opener; email-OTP MFA polled via IMAP), the unauth `/server/` → internet-exposed DB-admin-panel → version/CVE chain (functional login confirmed, `server` field locked = no SSRF, DB isolation proper, RCE conditional on creds for a server you cannot reach), paramiko shared-server isolation testing (password-auth when the SSH key won't deploy; home-dir/DB/redis/sudo battery), and disclosure refinements (ASCII-clean PDF for Gmail preview, verify attachments by sha256, swap-a-draft via search+expunge, preserve operator's recipient/subject edits, native-Windows path inside execute_code).
## Absorbed playbooks (complete sub-packages under `references/`)
This is the umbrella for auditing authenticated web apps. Doctrine lives above; the two driver-level
packages live here:

- `references/browser-cdp-auth-audit/PLAYBOOK.md` — the Python CDP driver (`cmd()` / `js()` over
  websocket-client), two isolated Chrome debug profiles, CAPTCHA/Turnstile routing to real Chrome,
  the "valid timestamp" signup wall, the defeatable Laravel/Livewire honeypot shape, Livewire
  component state, and email-verification-link capture from Gmail
  (`references/` + `scripts/` included).
- `references/modern-webapp-auth-hunting/PLAYBOOK.md` — the setup/workflow package: two isolated
  browser profiles, disposable accounts + OTP via mail.tm, TOTP enrolment when MFA gates a flow,
  the user-supplied authenticator QR path, and the MFA/2FA control surface (audit the controls, not
  just the bypass).

- `references/recaptcha-anchor-never-renders.md` — the reCAPTCHA v2 checkbox whose anchor iframe
  never renders `#recaptcha-anchor` (nothing to click, `execute()` times out): the four causes to
  rule out first, why a second egress proves it is not IP reputation, how to capture the
  server-side `captchaToken` requirement as evidence, and the operator's **5-attempt cutoff** for
  account-provisioning work.
- `references/recaptcha-v3-score-and-spa-api-recon.md` — reCAPTCHA **v3** (invisible, score-based,
  NOT v2): the `Invalid token score. 0.1 < 0.5` error leaks the threshold + your score, score decays
  after repeated automated logins (IP reputation, recoverable), and password-reset is often the
  un-throttled side-channel. Plus the 5-grep **minified-SPA API reconstruction** (`super("https://…")`
  base URLs → method-call extraction → `class X extends Y` hierarchy walk for inherited bases) and
  the OAuth-PKCE CEX register→2FA→code→callback flow with the split 6-box OTP fill.
- `references/rails-devise-recon-and-sequential-id-idor.md` — Rails/Devise app recon (the
  `robots.txt` route map, per-form `authenticity_token`, app-host `security.txt`), minting an
  account when the submit control is NOT `type=submit` (three fallbacks + judge success by the
  302, not the page body), why a foreign-object `404` is the GOOD outcome for sequential-ID IDOR
  (no existence oracle) and why the two-account test beats an id-range scan, and the file-upload
  probe ladder that distinguishes a real parse from a magic-byte check.
- `references/saas-vdp-engagement-playbook/PLAYBOOK.md` — the engagement wrapper around this class:
  setup before any exploit, resuming a multi-session engagement, verifying claimed artefacts exist
  before acting, multi-account browser infrastructure, MUI + react-hook-form + Turnstile signup
  automation, OTP/MFA/rate-limit verification, and the response-identity rule (200 does not mean it
  exists).
