# SPA API discovery & gated-flow testing (worked case: Byte Federal KYC, 2026-10-20)

For Astro/SvelteKit/Next.js SPA frontends whose API surface is not documented. Goal: extract the
real API contract, then either walk the flow or prove the gate holds.

## 1. Find the real backend from the browser, not from guesses

Drive the SPA with Playwright and log `response` events filtered to non-static hosts:

```python
pg.on("response", lambda r: REQS.append(r) if "api-" in r.url and "telemetry" not in r.url else None)
```

One page load + one click exposed the true backend (`api-register.<target>/telemetry`) that
black-box path guessing (api.register / api.verify / register host) never found — all those
returned nginx 405 because the API lives on a DIFFERENT subdomain. Lesson: **one instrumented
browser run beats twenty curl guesses**; the SPA's own XHR tells you the base host.

## 2. Extract the API contract from the bundles

- The main bundle (hundreds of KB) contains wrapped client calls: search for
  `Ct.post("kyc/site-token...")` style strings and for the `baseUrl` computation — a common Astro
  pattern is `window.location.origin + window.location.pathname` (so relative paths resolve on the
  serving host — and 405 there means the API is elsewhere, see §1).
- Lazy chunks: katana the SPA, then fetch every `/_astro/*.js` / `/_app/immutable/*.js` chunk and
  grep for `"/api/..."`, `fetch(`, `XMLHttpRequest`, `X-*-Session-Token` headers. The chunk that
  matters often loads only after a step you can't reach — read it statically anyway.
- SvelteKit: `/route/__data.json?<params>` serves the server data for a route (guest-visible where
  the page is public). The response's `uses.search_params` lists accepted params — feed those to
  sqlmap/dalfox rather than guessing.
- Look for hardcoded third-party keys near endpoints (FaceTec device key, Turnstile site key,
  Plaid refs) — usually public-by-design; only report if the key is a secret-class credential.

## 3. Entry-credential schemes (KYC/onboarding journeys)

Byte Federal's KYC accepted these URL/hash credentials (parsed by `byteverify-host.js`):
`token, invite, handoff, pending, pendingId, tablet, phone, launch`; journey IDs are **sequential
positive integers** (`wk_pending_journey_id` in sessionStorage).

Test before the wall: load `#/verify?pendingId=1..N`, `?tablet=1&launch=1`, `?token=1` etc. and
watch for ANY API call before the captcha step. If the app renders only the welcome screen with
zero XHRs → no pre-auth IDOR surface (verified negative). The IDOR question only becomes live if
an API fetches journey state by ID pre-auth — prove that call exists first.

## 4. Proving a gate holds (verification, not assumption)

- **Turnstile**: POST the endpoint with `{}` / dummy token / token-shaped garbage and diff the
  responses. Observed ladder on `phone/otp-challenge`: no body → 400; dummy token → 403
  "bot verification required"; token-shaped + extra field → different 400. That differential proves
  server-side siteverify — report as a control that works, not a finding.
- **OTP endpoints**: the 422 body leaks the schema (`{phone, code}`) — useful for the writeup of
  what's gated, not a finding itself.
- **Headless/headed Chromium will not pass managed Turnstile** (observed both). Don't burn the
  session retrying widget clicks; record as coverage limit and ask the operator for the one
  concrete unblock (test phone number). If a stealth browser server (camoufox) is running, its REST
  API is documented at `http://localhost:9377/openapi.json` — drive it directly when the Hermes
  browser client times out.

## 5. Registration mass-assignment (cheap, often forgotten)

POST the register form with extra fields (`is_admin`, `role`, `bytename`, `balance`,
`email_verified_at`, `id`). If the response doesn't change (e.g. still the same 500 as clean
registration) there's no differential — the crash is pre-persistence or unrelated. A differential
(validation error naming your field, or a created account with the attribute) is the finding; no
differential = negative, one line in the ledger.
