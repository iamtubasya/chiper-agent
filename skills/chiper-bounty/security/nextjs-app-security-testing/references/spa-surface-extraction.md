# Extracting a Next.js SPA's surface: inline config, chunk grep, framework fingerprints

Transferable recipe for mapping a Next.js App Router target from public assets only (no auth).
Verified 2026-10 on a multi-host clinical SaaS (burna.ai / app.burna.ai / api. / agent.).

## 1. Inline config object leaks keys + redirect URIs + API base
Next.js apps often dump a server-rendered config blob into the HTML as a global, e.g.
```html
<script>window.<appname> = { config: { api_url: '', recaptcha_site_key: '6L...',
   google_map_api_key: 'AIza...', stripePublishableKey: 'pk_live_...',
   google_auth_client_id: 'NNN-....apps.googleusercontent.com',
   google_login_redirect_uri: 'https://app.<host>/login/2fa', ... } }</script>
```
Extract it by brace-matching from `window.<app> = {` (don't regex the whole thing). Classify each key:
- **Public by design** (do NOT report): reCAPTCHA site key, Stripe *publishable* key (`pk_*`),
  Google OAuth *client_id*, PostHog project key (`phc_*`), analytics/pixel IDs, `NEXT_PUBLIC_*`.
- **Worth noting** (real but often low): a Maps API key that should be referrer-restricted,
  and any *commercial license string* shipped to the client (e.g. an MUI Pro `mui_license_key`) —
  reusable by third parties.
- **Never** test/use any extracted key against the vendor's backend — using their credentials/quota
  is unauthorized use, not testing. Read-and-report only.

## 2. Chunk grep — get the endpoints, and the *real* auth mount prefix
```bash
grep -oE '/_next/static/chunks/[^"\\]+\.js' page.html | sort -u   # collect bundle urls
# download a handful, then:
grep -ohiE '["`'"'"'](/api/[a-z0-9_/.:$-]+)' chunks/*.js | sort -u
grep -ohiE '["`'"'"'](/[a-z0-9-]*(auth|sign|session|token|enroll|invite|verify|otp|org|project)[a-z0-9_/.-]*)' chunks/*.js
grep -ohiE 'https?://[a-z0-9._-]+' chunks/*.js | grep -v 'react|nextjs|vercel|w3.org|schema'
```
**Pitfall — don't assume the auth API is at `/api/auth`.** Grep for a *prefix constant* in the bundle
(e.g. `"CP_AUTH_PREFIX","/cp-api/auth"`). Here `/api/auth/*` returned Next.js **404 HTML** while the
real better-auth was mounted at **`/cp-api/auth`** and returned **307 → /auth/sign-in** (middleware-gated).
A 404 vs 307 difference is exactly how you tell "wrong path" from "gated path".
Also surface: leaked dev hosts (`https://smart.<brand>.localhost`), internal ports (`localhost:4111`),
`NEXT_PUBLIC_*` envs, and third-party ingest hosts (Axiom, PostHog, imagedelivery/CDN).

## 3. Framework fingerprints (name the stack from responses alone)
- **better-auth** — client bundle strings `/api/auth` + endpoint names `get-session`,
  `revoke-session`, `revoke-other-sessions`, `delete-anonymous-user`, `update-session`, `sign-in/anonymous`.
  Anonymous-user + "Try as X, no sign-up" ⇒ an ephemeral-session demo flow; test org/study boundary there.
- **Mastra** (AI agent server) — bundle constants `/mastra`, `/agents-playground`; the host returns
  `{"name":"<...>-agents-api","status":"ok","message":"Hello, World! 👋"}` at `/`, and `/api/agents`,
  `/api/workflows`, `/api/agents/<id>` return `401 {"success":false,"message":"AUTH_REQUIRED"}`.
- **ts-rest / typed client** — bundle shows a client like `r.cpClient["cp-api"].users["request-deletion"].$post()`;
  the dotted path is the API contract — mine it for route names.
- **Redocly / Caddy / CloudFront** on a docs subdomain ⇒ docs are third-party-hosted (supply-chain trust note).

## 4. Cheap verified checks worth recording (good or bad)
- **Source maps**: `GET <chunk>.js.map` → `404` (text/plain, tiny body) is the expected/secure result.
  Record it as a verified negative; a 200 with JSON `version/sources` = full source disclosure.
- **`/health`** (and `/`, `/api`, `/status`) on each origin host: those on **direct-origin hosts not
  behind the CDN** (Railway/Render/Fly give you `x-railway-*/x-*` headers + a real IP) frequently leak
  internal runtime config, e.g. `{"status":"ok","issuer":"http://localhost:4111","remoteAddress":"::ffff:100.64.0.8"}`
  — internal service port + overlay address (`100.64.0.0/10`). Concrete info-disclosure PoC = the raw body.
- **Middleware posture**: request an app route unauthenticated and note `307 → /auth/sign-in?redirect_uri=…`.
  Repeat the enumerated API paths with ALL verbs — a GET-only matrix can't prove the boundary.
- **Reflection**: `?q=<script>`-style probes — check the RAW response for `&lt;script&gt;` (escaped = safe)
  vs literal `<script>` before claiming XSS.

## 5. Out-of-scope discipline (policy-driven)
If the VDP excludes "best-practice recommendations without a specific vulnerability" and "scanner findings
without a working PoC", then missing HSTS/CSP/other headers are **observations, not findings** — do not
report them as vulns. Say so explicitly so a clean pass isn't padded. See `recon-scope-triage`.
