---
name: scribblemaps-engagement
description: >-
  Scribble Maps (scribblemaps.com) bug-bounty engagement — scope hosts, bounty table,
  out-of-scope list, API route map, the three findings (paid-map content disclosure,
  vulnerability-portal userId impersonation, SSRF via SAML/OIDC metadata import), the
  controls that were verified as working, and the surfaces that stayed closed.
metadata:
  hermes:
    tags: [security, bug-bounty, engagement, scribblemaps, saas, gis, sso, ssrf]
---

# Scribble Maps — engagement notes (2026-10-31)

Target: `scribblemaps.com` (Scribble Maps, GIS/annotation SaaS). Program is **live and paid**;
the target-pool entry for the domain says `status: retired`, which is stale — always read the
policy page before trusting pool metadata.

## 1. Scope and rules (read the policy, it is short and specific)

Policy: `https://help.scribblemaps.com/help/a/vulnerabilities-and-bounties` (updated 2026-10-04).
Submission: `https://api.scribblemaps.com/vulnerabilities` (**login required**).
Contact for e-mail: `support@scribblemaps.com`. Payments via Wise/PayPal only.

Hosts named by the program (treat as in-scope; the apex wildcard is the program's own wording):

```
www.scribblemaps.com   team.scribblemaps.com   manage.scribblemaps.com
widgets.scribblemaps.com   api.scribblemaps.com   data.scribblemaps.com
```

Bounty table (their words, condensed): RCE $200–800 · unrestricted FS/DB access $500–2,000 ·
logic flaw leaking or bypassing significant security controls (IDOR, priv-esc, remote user
impersonation, ATO) $200–1,000 · map security (improper map exposure, secure-map data leak)
$100–500 · client code execution (stored/reflected XSS) $100–500 · other (CSRF, clickjacking,
info disclosure, open redirect) $25–200. Payout inside a range depends on privilege required,
blast radius, reversibility, and report quality.

**Out of scope, explicitly** — do not report these:
- Anonymous community maps (no owner, editable by anyone).
- Unlisted URL-as-credential maps: *"Accessing or saving such a map by knowing its map code is
  by design."* This kills the whole "read any map by code" class.
- Third-party stacks they host but do not maintain (GeoServer, Tomcat).
- Missing security headers without a concrete attack scenario.
- Rate limiting in isolation.

They also ask scanners to **skip the `/maps/` path** and prefer no heavy scanning. Honour it:
run nuclei with a tech-targeted tag set and a low rate, and record the run as completed rather
than claiming a blanket sweep.

## 2. Core business (drives where the money bugs are)

Map annotation SaaS. Free / Pro / Pro Business plans; API keys; team seats; **Sell Access**
(paid maps — one-time or subscription); **Secure** maps (password to view) and **Encrypted**
maps (client-side AES-256 + PBKDF2, Pro-only). Team app adds SSO (SAML/OIDC), SCIM, S3 bucket,
Slack, data connectors, audit log — all behind a paid team product.

Map access modes: `public` / `unlisted` / `secure` / `encrypted` / `paid`. Save payload
(`POST /api/maps/{code}/stream/new`) carries `password`, `secure`, `isPaid`, `paidDetails`;
the editor sets `secure=true` when a map is saved as paid
(`"paid"==d&&(a.listed=!1,a.secure=!0)`).

## 3. Findings

### F1 — HIGH (7.5) unauthenticated disclosure of paid-map content
`GET /api/maps/paidsample/raw` (and `/smjson`, `/smjsonbase64`, `/lzsbase64`, `/kml`,
`/geojson`) on **www** returns the complete 16,908-byte map document to an anonymous client,
for a map that is `listType:"paid"`, `free:false`, priced $199 / $19.99-mo / $99.99-yr with
`allowCopy:false`. Four independent signals prove it is a control bypass, not by design:
1. the identical path on **api**.scribblemaps.com returns `401 application/problem+json`;
2. `/api/maps/images/800/600/paidsample.png` returns 401 on www;
3. a password-protected (Secure) map returns 401 from all six data endpoints;
4. the shipped editor marks paid maps `secure=true` and the public widget masks the title to
   "Secure Map".
Root cause: the data endpoints authorise on the map **password** only and never consult
`isPaid`/`secure`. Validated 3x, byte-identical SHA-256
`REDACTED_********`.
Submitted via portal, reference **FF3179**, pending e-mail approval.

### F2 — MEDIUM (5.4) vulnerability portal accepts a foreign userId
`POST /api/vulnerability/aisubmit?userId=<id>` checks that the userId *exists* but never that
it belongs to the session. Differential: own id → `"Title is required"`; a different account's
id → `"Title is required"`; non-existent id → `"Invalid userId"`. A full submission under
another account's id returned `success:true`, `referenceId 6F50F5`, and the approval e-mail
went to that account's address. Impact: report impersonation/attribution fraud, burning the
victim's one-report-per-day allowance, and a social-engineering lever via the approval mail.

### F3 — LOW/MEDIUM constrained SSRF via SSO metadata import
`POST /api/saml/import-metadata` and `/api/oidc/import-metadata` (`{teamCode, metadataUrl}`)
make the server fetch the URL. Confirmed OOB 3x (DNS from 20.42.77.69, HTTP from 13.72.78.248,
Azure). Oracle: `"Failed to parse metadata XML"` = fetched 200, `"Could not fetch"` = failed.
Controls verified in place and stated in the PoC so it is not overstated: HTTPS-only;
private/loopback/link-local/zero blocked after DNS resolution (15 variants tested); no
redirects; 5 s / 512 KB limits; the fetch carries **no** cookies (auth-required endpoints on
scribblemaps.com return 401 to it). Public-only, therefore Low-Medium.

## 4. Verified NEGATIVES (with the control that makes them real)

- **Map password gate is solid.** 16 path/method/param/header bypass variants on a Secure map
  → all 401. Correct password via `?password=` → 200; wrong/empty → 401.
- **BOLA on `/api/maps/{code}/users`** — non-owner POST → 401.
- **Team multi-tenant authz holds.** `/api/users?teamCode=<other>` and POSTs to
  `saml/oidc/scim/s3 settings`, `saml/domains`, `scim/token`, `security/block-personal-saving`
  with a foreign teamCode → 403 on every one. The control that proves it: create a **second
  team** for the second account so the session has valid team context, then retry — without
  that the app answers with the SPA login HTML and the test is meaningless.
- **Subscription/credit entitlement.** `plan-status`, `checkout`, `validateSession` on an
  unpaid Stripe session grant nothing; `credits/purchase/validate` → `"Payment not completed"`.
- **Account mass assignment.** `/api/account/email` change → 204 but e-mail unchanged
  (confirmation flow); `/api/account/settings` and `/api/account/aiSaveSettings` ignore
  `isBusiness`/`userTypeId`/`vipExpires`.
- **Stored XSS via SVG upload is NOT exploitable.** `POST /api/account/uploadOverlay` accepts
  an SVG containing `<script>` and serves it as `image/svg+xml`, but the response carries
  `CSP: default-src 'none'; style-src 'unsafe-inline'; sandbox` + `X-Content-Type-Options:
  nosniff`, and Chrome logged *"Blocked script execution … 'allow-scripts' is not set"*.
  Verified in a real browser before discarding — do not report this.
- **SSRF private-IP filter is robust** (see F3). Hostnames that resolve to private ranges
  (`localtest.me`, `*.nip.io`) return the same error as a non-resolving domain, so internal
  reachability through the domain-verification path is **unproven** — say that, do not claim it.
- **No client-callable paid-map purchase endpoint** (14 candidates probed, all 404/405), so
  the paywall decision is server-side only.

## 5. Surfaces that stayed CLOSED (not negatives)

- **Encrypted maps**: `encrypted:true` is accepted on a free account but behaves exactly like a
  Secure map; no proven bypass of the encryption control.
- **Connectors / data connections**: `createConnector` → 426 (paid), both `sm` and `gs` types.
- **Team paid features** (S3 presign/list, SAML/OIDC enable, SCIM, audit log, billing, seats):
  `/api/maps` → `402 "Team subscription has expired"`; enabling SSO requires a verified e-mail
  domain (DNS TXT or `https://<domain>/.well-known/scribblemaps-verify.txt`), and without
  controlling a domain's DNS or web root the flow cannot be completed.
- **SAML ACS signature validation**: could not be tested. The ACS resolves the IdP from the
  assertion `Issuer` and only honours **enabled** configurations, so unsigned-assertion /
  XML-signature-wrapping / replay tests are blocked at that depth. Configure via
  `POST /api/saml/settings` (entityId, ssoUrl, certificate) — that part works.
- **OIDC callback**: `401 "Invalid or expired state"`; state is validated.
- **Blanket CVE sweep**: deliberately not run (4,583 templates would be tens of thousands of
  requests and the program asks to avoid that). Tech-targeted nuclei only.

### 1n. A SECOND front door — the widget/embed host is a separate authz surface

A product that serves a map/board/document as an embeddable widget exposes **the same resource
through a second host** with its own front-end JS, its own route table, and its own authz filter.
That filter is written separately from the main app's, so it is the cheapest place to find a gate
that one host has and the other does not.

Measured 2026-10-31 (Scribble Maps, `widgets.scribblemaps.com`). Two endpoints existed **only**
in the widget bundle (`/js/core.js`) and nowhere in the main app's route inventory:

```
GET /api/maps/{code}/localLastModified   -> returns the map's content HASH
GET /api/maps/{code}/smjsonLocal         -> returns the map document
```

| map | `smjsonLocal` | `localLastModified` |
|---|---|---|
| public | 200 | 200 |
| **Secure (password)** | 401 | **200 — hash disclosed** |
| **Paid** | 401 | **200 — hash disclosed** |

The content gate held on the widget host too (good — it corroborates the main finding rather than
duplicating it), but the hash endpoint leaked change-detection metadata for both protected classes.
**Metadata-only = an observation, not a finding** — record it, do not report it. The value of the
sweep is the *coverage claim*: "the widget host enforces the content gate" is a sentence a triager
cannot get from the main-app tests alone.

Method (30 seconds once you know the host):
1. `curl https://<widget-host>/js/*.js` and grep for `/api/` — the widget bundle is small (here
   143 KB vs the 6.4 MB editor SDK) and its route list is short.
2. Fire each discovered route at **both** hosts and at **every access class** you hold
   (public / password-protected / paid / tenant-scoped).
3. Embed parameters are not a bypass — `id`, `password`, `pw`, `plan`, `admin`, `secure`, `d`,
   `z`, `l` were all tried against a Secure map: no parameter unlocked content and no map data was
   inlined into the widget HTML. Record it as a negative.

**Corollary — a sibling domain referenced by the JS is not automatically in scope.** The widget
bundle pointed at `scribblemaps.io` (a separate tile server, Cloudflare-fronted) which the program's
published host list does **not** name. It was probed passively only and nothing from it will be
reported. Check the policy's host list against every domain the bundle names before you touch it;
"the product uses it" is not "the program covers it".

### 1o. A rate limit YOU tripped is a disclosure, not a coverage gap

Dry-run probes against the report portal's own submit endpoint tripped a per-IP throttle
(`429 "You've submitted too many reports recently"`) that then blocked the real submission for
~40 minutes. Two obligations follow, and both belong in the deliverable rather than in your notes:

1. **Say the throttle was self-inflicted.** "A handful of deliberately-incomplete dry-run requests
   against POST /api/vulnerability/submit — all rejected by validation, none created a report —
   tripped that endpoint's per-IP rate limit. That is why this report arrived by e-mail rather than
   through the portal." Without that sentence the vendor sees unexplained `429`s from your IP and
   reads it as abuse.
2. **Never dry-run a one-shot submit endpoint to learn its field names.** Read them from the form
   HTML + page JS instead (see `bug-report-delivery` →
   `references/_split/10-portal-submission-discipline.md` §1). One validation failure is enough to
   burn the throttle budget.

Same rule for any state-changing probe that leaves a trace on the vendor's billing or anti-abuse
systems: an orphan Stripe Connect account, an unpaid subscription record, a tripped limiter — each
gets one sentence in the report notes naming it, its state (unverified / inactive / no balance), and
that the vendor may delete it. Failing to disclose reads as sloppy handling of their systems.

## 6. Route map worth remembering

Editor SDK is `https://cdn.scribblemaps.com/api/js/1.613/scripts/main.js` (6.4 MB — grep it for
the full route table). Team app routes live at `team.scribblemaps.com/assets/js/controllers/main.js`
and are reachable only through hash routes (`#/sso`, `#/scim`, `#/s3`, …); the real SSO/SCIM
endpoints are on **api**.scribblemaps.com (`/api/saml/*`, `/api/oidc/*`, `/api/scim/*`).

Map data: `/api/maps/{code}` · `/raw` · `/smjson` · `/smjsonbase64` · `/lzsbase64` · `/format` ·
`/history` · `/lastModified` · `/isPro` · `/kml` · `/geojson` · `/users` · `/users/authority` ·
`/settings` · `/listing` · `/tags` · `/sendToFriend` · `/stream/new` · `/stream/` ·
`/images/{w}/{h}/{code}.{ext}` · `/newCode`.
Account: `/api/account` · `/account/maps` · `/account/settings` · `/account/email` ·
`/account/password` · `/account/card` · `/account/overlays` · `/account/uploadOverlay` ·
`/account/connectors` · `/account/createConnector` · `/account/getGoogleToken` ·
`/api/account/aiLoadSettings` · `/api/account/aiSaveSettings`.
Money: `/api/subscribe/plan-status` · `/subscribe/checkout` · `/subscribe/upgrade` ·
`/subscribe/validateSession` · `/api/credits/purchase/session` · `/api/credits/purchase/validate` ·
`/api/market/defaultPlans/{code}` · `/api/market/is-seller`.
Portal: `/api/vulnerability/submit` · `/api/vulnerability/aisubmit` · `/api/vulnerability/list` ·
`/api/vulnerability/{id}` · `/api/vulnerability/{id}/notes` · `/api/admin/vulnerabilities` (403).

## 7. Operational notes

- **Session cookies expire mid-engagement** (www/api/team share `.scribblemaps.com`). A sudden
  401 on an endpoint that just worked is expiry, not an authz change — refresh via a headed
  Playwright login on the persistent profile, click **YES** on the "logged in elsewhere"
  dialog, then re-verify identity with `GET /api/account`.
- **Camoufox (:9377) and the SeleniumBase MCP were unusable on this host**; Playwright + real
  headed Chrome with a persistent profile was the working path, including for Turnstile.
- **Side effects to disclose**: one unverified Stripe Connect Express account was created for
  the test mailbox while probing `/api/market/create-account`; dry-run probes against
  `/api/vulnerability/submit` tripped a per-IP 429 throttle. Both are written into the
  coverage doc and the report e-mails.
- Clean up after yourself: `DELETE /api/saml/domains/{id}`, `/api/saml/toggle` + `/api/oidc/toggle`
  to false, `GET /api/account/overlays/{id}/remove` for uploaded test files.
