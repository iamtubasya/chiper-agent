---
name: spa-authed-api-audit
description: Use when a target's value hides behind an SPA login or WAF.
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [security, bug-bounty, spa, bundle-mining, waf, idor, self-provision, api-recon]
    related_skills: [hunt-spa-api, disposable-auth-identity, api-authz-probe-ordering]
---

# Authed SPA API Audit — recover the contract, self-provision, prove cross-tenant

## When to Use

Use when a bug-bounty target's valuable surface returns 401/403 unauthenticated AND the
frontend is a minified JavaScript SPA (Vue/React/Angular) — so the API contract is hidden
in a bundle and the auth/form flow is validated by the server, not discoverable from the
network alone. Triggers: "recover the API", "WAF blocks curl", "signup returns 422 on a
free-text field", "prove cross-tenant IDOR", "feature is behind a paid tier".

When every valuable endpoint answers 401/403 unauth and the UI is a minified JS SPA,
the finding is gated behind (a) understanding the real API contract and (b) a second
identity. This skill is the end-to-end path: mine the bundle → get past the WAF →
self-provision accounts → run a decisive 2-account cross-tenant battery. It builds on
`hunt-spa-api` (API discovery), `disposable-auth-identity` (account bootstrap), and
`api-authz-probe-ordering` (BOLA matrix). Load those for depth; this carries the glue
and the pitfalls that are easy to miss.

## Step 0 — feudal the bundle for the WHOLE contract, not just routes

`hunt-spa-api` finds route strings. Do more — a minified SPA ships three things worth
grabbing in one pass:

1. **The ENV/JSON config block.** Many apps embed a literal `ENV` object on a single
   line: `M.exports=JSON.parse('{"ENV":"production","SETTINGS_SERVER":"...","API_SERVER":"...","GOOGLE_CLIENT_ID":"...","SEGMENT_WRITE_KEY":"...","MIXPANEL_TOKEN":"...","RECURLY_PUBLIC_KEY":"...","JWT_PUBLIC_KEY":"-----BEGIN PUBLIC KEY-----...","STATSIG_KEY":"...","AWS_WAF_INTEGRATION_SCRIPT":"..."}')`.
   Extract it with one regex `r'JSON\.parse\(\'(\{.*?\})\'\)'` then `json.loads(raw.replace('\\"','"'))`.
   This gives you the **base-URL map** you must hit (often a sub-path like `/settings`,
   not the root — hitting the root returns 404/CloudFront-wrapped 403 and looks like a
   dead end), plus every client secret.
2. **The server enum values for validated forms.** When a signup/register POST rejects a
   hand-written value with `The value you selected is not a valid choice`, the accepted
   enum is an array literal in the bundle (`[{"label":"Marketing Consultant","value":"Marketing Consultant","team":"Marketing"},...]`). Grep for the rejected value, walk back to the
   array `[`, read the exact `value` strings. Same for `audience`, `audience_size`,
   `frequency`, `goal`, `role_team`. This is the fastest path out of a 422 loop.
3. **Client secrets are usually NOT findings.** `SEGMENT_WRITE_KEY`, `MIXPANEL_TOKEN`,
   `RECURLY_PUBLIC_KEY`, `GOOGLE_CLIENT_ID`, OAuth client ids, even a `JWT_PUBLIC_KEY`
   are public-by-design in a browser bundle. The one that matters is a *write* key the
   backend accepts (`cdn.builder.io/api/v1/write` → 401 = correctly scoped) or a private
   key. Probe the write surface; do not report a public key as a secret.

## Step 1 — get past the WAF by driving the SPA, never by guessing tokens

`panel-api`-style hosts often front with AWS WAF JS challenge or CloudFront. Direct
`requests`/curl gets 403, and the WAF token is minted by the browser. Do NOT hand-mint it:

1. Launch **headed persistent Chrome** (Playwright `channel="chrome"`, `headless=False`,
   `--disable-blink-features=AutomationControlled`) and let the JS challenge auto-solve.
   The cookie `aws-waf-token` (or `__cf_bm`) appears in `ctx.cookies()`.
2. Do the auth/signup through the real UI (trusted `fill` + `click`), capturing
   `page.on("response")` for every `panel-api`/`*.json` call — the UI *is* the API
   contract teacher (exact body shape, `X-XSRF-TOKEN` header, `preregister_token` param).
3. When the UI wizard is a React-controlled combobox that won't accept synthetic fills,
   skip it: replay the endpoint **from inside the page** with `page.evaluate` + `fetch()`
   using the enum values from Step 0. Same-origin `fetch('../settings/user/signup.json')`
   carries cookies+CSRF correctly. (A `fetch` to the API's cross-origin `https://...com`
   from the SPA's origin will be CORS-blocked → "ERR"; use the SAME origin or plain
   `requests` + the WAF token cookie + `X-XSRF-TOKEN` header.)
4. Signup success == the response body carrying `user.id`, `first_name`, and a
   `subscription_name`/trial — that's your autopsy of what account got created, and the
   ids you need later (workspace id is usually in the post-login URL `/o/<org>/w/<ws>/`).

## Step 2 — decisive 2-account cross-tenant battery (the only honest IDOR proof)

One account + sequential ids proves nothing: `404` is what BOTH "doesn't exist" and
"belongs to someone else" return. Two accounts sharing one id space give three outcomes:

| request | response | reading |
|---|---|---|
| A reads A's own id | 200 | positive control — harness works |
| A reads B's real id | **403** | scoped correctly (denied at authz layer) |
| A reads nonexistent id | **404** | the route/object doesn't exist |

- `200` on B's id = **cross-tenant IDOR → report now**.
- Uniform 403 for B + 200 for own = authz verified (verified-negative with a denial string).
- Uniform 404 for foreign + 200 for own = scoped, and 404 doesn't even confirm the route
  shape — state it as scoped, not as "data protected at the row level".
- Assert the two sessions differ (different cookie jar / second `launch_persistent_context`
  profile) BEFORE trusting any row — two tabs in one context = A vs A.

## Step 3 — mass-assignment: a 200 is not a mutation

On a settings PUT that returns `200 OK` for an unauthorized-field override, **re-GET the
resource and confirm the field actually changed.** Many backends silently ignore unknown
fields (`subscription_responses_limit=999999` → 200 → re-read shows no change). Correct
verdict: "field is whitelist-filtered" (control works), not a finding. Only a persisted
change (or a reflected change in the victim's own view) is a finding.

## Money-gate / paid-feature discipline (anti "minta akun bayar")

**The billing/payment/monetary namespace is often a SEPARATE service not in the OpenAPI
spec.** A product spec will list VPS/CDN/DNS/kubernetes endpoints but omit the account,
balance, and payment surface (`/balance`, `/payments/cards`, `/payments/methods`,
`/payments/create-payment`, `/payments/paypal/create-order`, `/account/limits`,
`/payments/validate-promotion-code`). Recover it by driving the SPA to the account/billing/
deploy pages with `page.on("request")` capture — that's where the money logic (prepayment,
promo codes, tier limits, card attach) actually lives, and where amount-tampering and
promo-abuse bugs are. Do this before concluding "verification requires payment / can't test".

A feature gated behind payment ($49–$499 tier, add-on, plan boundary) is NOT a reason to
ask the operator for a paid account. It's a reason to attack the gate:

1. **Enum the public estate first.** A paid feature often has live public subdomains
   (`<slug>.target.com`) that expose the same capability anonymously. `subfinder` +
   `assetfinder` + `crt.sh` before concluding "offline / needs purchase".
2. **Replay the entitlement endpoint directly** (the radio/checkbox/`plans[]` form POST),
   with no payment token. A 500/tolak is proof the server enforces it — capture the denial
   string. A 200 that flips the flag = bypass.
3. **Price/tier tampering on checkout** (negative qty, cheapest tier, empty Stripe token)
   is safe: no valid token = no charge, and the response reveals server-side vs
   client-side validation.
4. Only after all three dead-end, record it as a COVERAGE LIMIT ("finalization needs a
   valid payment method"), never as "give me money."

## Output & impact rules (encode the operator's corrections)

- **Results and evidence first, narrative last.** Open each reply with the verdict table +
  coverage KPI; prose comes after, never as a gate that delays the result.
- **OTP/rate-limit without ATO = DROP.** "No rate limit" is not a finding; a missing
  rate limit is Low/Info at best and only becomes a finding when it yields account
  takeover (email-OTP brute → 200). Never report a 6-digit OTP endpoint that has no
  verified ATO path.
- 200/400 empty, self-XSS, missing headers, "admin can X" = drop. Severity must survive
  the "why wouldn't the victim take the easy path" challenge.

## Pitfalls

- Hitting the API root instead of the `/settings` sub-path → 404/CloudFront 403 that reads
  like a dead end. Always take the base from the ENV block's `SETTINGS_SERVER`/`API_SERVER`,
  not from guesswork.
- `fetch()` from the SPA origin to the API's absolute cross-origin URL → CORS "ERR" on every
  call. Use same-origin fetch, or `requests` + the WAF cookie + `X-XSRF-TOKEN`.
- Free-text in a validated enum field → 422 loop. Pull the enum from the bundle array, don't
  permute values by hand (see Step 0.2).
- mail.tm / `fldubai.com` is on disposable-email blocklists; Survicate-style signups silently
  never deliver. Use `tempmail.lol` random-subdomain inboxes (`user@<rand>.<tld>`) — see
  `disposable-auth-identity` for the provider ranking.
- React-controlled combobox won't take `.fill()` — detect it (value stays committed but
  submit still "required"), then replay the endpoint directly instead of fighting the UI.
- A second account must live in its OWN `launch_persistent_context` profile; reusing the
  first profile reuses the first session and turns the matrix into A vs A.
- "200 OK" on an override is not success — re-GET confirms persistence (Step 3).
- **A bare `403 "Forbidden"` on EVERY write (POST/PUT/DELETE) while GET returns 200/401 is
  usually a missing CSRF header, not an authz gate.** FastAPI/React/Next APIs commonly enforce
  `X-Requested-With: XMLHttpRequest` (or `X-XSRF-TOKEN` / `X-CSRFToken`) on state changes and
  return an anonymous `{"detail":"Forbidden"}` when it's absent. That short-circuit fires BEFORE
  per-object authz and field validation, so it masquerades as "everything is locked down" — you
  will wrongly conclude "mass-assignment blocked" and "cross-tenant IDOR denied" when you really
  just forgot the header. Fix: replay the identical write with `X-Requested-With: XMLHttpRequest`
  (+ `Origin: https://<spa-host>`). The real error surfaces (e.g. `Account not verified`,
  `not found`, `Input should be >= 10`). Re-run your mass-assignment and 2-account BOLA matrix
  AFTER adding the header — every 403-based "control holds" verdict from before is void.
- **`X-Requested-With` + strict CORS is a legit CSRF defense — don't report it.** A custom
  header forces a CORS preflight; if the preflight reflects an attacker `Origin` with NO
  `Access-Control-Allow-Origin` (or returns 400), CSRF is already blocked and "missing CSRF
  token" is a false positive. Only flag CSRF when there's neither a header guard nor a strict
  CORS allow-list.