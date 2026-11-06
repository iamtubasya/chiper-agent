# Finding the unauthenticated surface: drive the pre-auth SPA, don't guess paths

## Why this beats fuzzing and crawling

On an SPA webmail/portal product the login page must fetch branding, locale and password policy
**before any user authenticates**. Every request it makes is therefore, by definition, a reachable
unauthenticated endpoint. Wordlists miss these because the paths are product-specific
(`/auth`, `/auth/spa/config?app=webmail`, `/api/.well-known/jmap-settings?cachebust=<epoch>`,
`/config.json`); `katana -jc` under-covers because the SPA routes are client-side and many calls
fire after a click. The browser is the oracle.

## Recipe 1 — record every pre-auth request (Playwright, sync API)

```python
from playwright.sync_api import sync_playwright
HDR = {"X-Bug-Bounty": "you@example.com"}

recs = []
with sync_playwright() as pw:
    br = pw.chromium.launch(headless=True, args=["--ignore-certificate-errors"])
    for label, url in TARGETS:                     # webmail root, login host, account/portal host
        ctx = br.new_context(ignore_https_errors=True, extra_http_headers=HDR)
        page = ctx.new_page()
        page.on("request",  lambda r: recs.append((label, r.method, r.url, r.resource_type,
                                                   (r.post_data or "")[:300])))
        page.on("response", lambda r: recs.append((label, r.request.method, r.url, "RESPONSE",
                                                   r.status, r.headers.get("content-type", ""))))
        page.goto(url, wait_until="networkidle", timeout=45_000)
        page.wait_for_timeout(4000)
        page.mouse.wheel(0, 1200)                   # lazy chunks
        page.wait_for_timeout(3000)
        ctx.close()
    br.close()
```

Then keep only `resource_type in ("xhr", "fetch")` or a path containing `/api/` or `/auth/`, drop
`/assets/`, and print unique `(method, path)` with status — that list *is* your target surface.

Key detail: set the identity header on the **context** (`extra_http_headers`), not per-request, so
navigation and subresources all carry it.

## Recipe 2 — mine the bundles for path literals

```bash
grep -ohE '"/[a-zA-Z0-9_/{}.:-]{3,70}"' *.js | sort -u \
  | grep -Ei 'api|auth|jmap|config|setting|sso|oidc|token|register|portal|redirect'
```

Then grep for how a path is *built* — the interesting ones are template literals:

```bash
grep -ohE '.{120}(feature-flags|signupapi|billing/v1|accountapi)[^"]{0,40}' portal.js
```

This is where `/api/accountapi/v1/redirect/cookie?code=`, `/api/billing/v1`, `/api/signupapi/v2`
turned up — none of which any wordlist run had produced.

## Worked case (email platform, 2026-09)

Captured pre-auth calls, per host family:

| path | what it returned unauthenticated | verdict |
|---|---|---|
| `/api/settings` | the full tenant config object | the finding |
| `/api/.well-known/jmap-settings?cachebust=<epoch>` | `301 -> /api/settings` (the SPA's own alias) | second path to the same payload — list it in the report |
| `/auth` | `{"methods":[password,require2FA,forgottenPassword,otp,passcode,reissue]}` | 200 unauth, but byte-identical on every host -> capability only, NOT a finding |
| `/auth/spa/config?app=webmail` | `{"authorizeUrl":"https://login.…/auth/authorize","clientId":"webmail-…","enable":true}` | 200 unauth, per-tenant SSO config -> fold into the same finding |
| `/config.json` | 404 on app hosts, but the **SPA shell** on portal hosts (200 `text/html`) | false positive — check the content-type before calling it a leak |
| `/api/accountapi/v1/redirect/cookie?code=` | 404 SCIM-style error on prod | route present in the bundle, gone server-side — always probe, don't trust the bundle |

Census result: `/api/settings` 137/176 hosts, `/auth` 143/176, `/auth/spa/config` 52/176.

## Pitfalls that cost time here

1. **A reflected parameter inside a relative `Location` is not an open redirect.** The OIDC
   `/auth/authorize` answered `302 -> /ui/auth/signin?client_id=…&redirect_uri=https%3A%2F%2Fevil.example%2F…`
   for *every* redirect_uri tried. A naive "Location contains evil.example" check flags this as an
   open redirect on 23/23 variants. It is not: the target is the relative signin path and the
   attacker string is a **URL-encoded parameter value**. Before calling open redirect, assert the
   Location host differs from the application host.
2. **Bundle endpoints may not exist.** Probe every literal you extract; several 404'd on production.
3. **Don't trust a `<script>`-built URL you never fetched.** The capture only proves the *client*
   calls it; the server may 404 (as `/api/accountapi/v1/redirect/cookie` did).
4. **A second host family exposes a different surface.** The API-gateway host served
   `/api/settings`; the login host served `/auth/authorize` + `/auth/spa/config`; the account portal
   served `/auth/spa/config?app=account-portal`. Capture all of them.
5. Static PWA files (`/manifest.json`, `/serviceWorker.js`) return 200 and are *not* findings —
   check the body before writing anything up.
