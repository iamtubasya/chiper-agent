# Turnstile / Auth0 bot-detection bypass via Playwright stealth

Tested and working 2026-11 against a Cloudflare-Turnstile-gated Auth0 universal-login signup
(`unito.io` → `login.unito.io`). Fresh persistent profile, no manual solve, no external captcha service.

## The recipe that worked (Turnstile token obtained in ~8 s)

```python
STEALTH = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
window.chrome = window.chrome || { runtime: {} };
"""

ctx = await p.chromium.launch_persistent_context(
    PROFILE_DIR, headless=False, channel="chrome",
    viewport={"width":1366,"height":900},
    args=["--disable-blink-features=AutomationControlled"],
    locale="en-US", timezone_id="America/New_York")
await ctx.add_init_script(STEALTH)
```

Critical details that make or break it:

1. **`webdriver` → `undefined`, NOT `false`.** `navigator.webdriver === false` is a self-reported
   bot tell; `undefined` matches a clean browser. Self-check with
   `page.evaluate("() => navigator.webdriver")` — must print `None`, else the challenge will not
   auto-pass.
2. **`--disable-blink-features=AutomationControlled` alone is NOT enough** — without the init script
   the Turnstile `rch` (challenge) frame never auto-passes.
3. **Seed the profile first** — load the target's marketing/landing site, scroll, move the mouse,
   wait a few seconds — before the auth page. A fresh profile with zero history gets challenged harder.
4. **Poll for the token before you submit.** After filling the form, loop every 1 s reading
   `document.querySelector('[name=cf-turnstile-response],[name=captcha]').value`. Auth0 universal
   login stores the solved token in a hidden `input[name=captcha]` (Turnstile managed mode). Only
   click Continue once the token is non-empty — otherwise the form silently re-renders with no error.
5. **Submit via JS `el.click()`, not `page.click()`** — the OneTrust/cookie-consent overlay
   (`onetrust-pc-dark-filter`) intercepts pointer events and makes every click time out. `fill()` also
   bypasses the overlay (it does not use pointer events).

## Auth0 tenant recon — find extra tenants + detect open signup

A target often runs **multiple Auth0 tenants**. The production tenant is bot-detected; a separate
dev/staging tenant used for a "developer program" or admin portal may be wide open.

1. **Read the `Sign in` link href** on the login/docs page: it carries
   `https://<tenant>.auth0.com/authorize?client_id=<id>&...&redirect_uri=<callback>` — tenant +
   client_id + downstream app for free.
2. **Discovery:** `GET https://<tenant>.auth0.com/.well-known/openid-configuration` → issuer,
   endpoints, `mfa_challenge_endpoint`.
3. **Open-signup oracle — `POST /dbconnections/signup`** (`{client_id, connection, email, password}`):
   - `200` + created-user object → **open self-registration, no bot detection**. (`unito-dev.us.auth0.com`
     did this; prod `login.unito.io` never did.)
   - `401 {"name":"requires_verification"}` → Auth0 Bot Detection is ON (signup needs a
     Turnstile/hCaptcha token). The user may still be created before the 401 — check for a verify mail.
   - `404 {"error":"connection not found"}` → wrong `connection` name. This is a connection-name oracle:
     iterate `Username-Password-Authentication`, the tenant short name, the product name. The non-404
     names the real DB connection.
4. **Login API is not ROPC-friendly.** `POST /usernamepassword/login` returns
   `403 {"name":"AnomalyDetected"}` for a freshly-API-signed-up user. Use the full authorize flow
   instead: `GET /authorize` → POST identifier (`username` + fresh `state`) → POST password
   (`password` + fresh `state`) → follow to callback. Re-read the `state` hidden field from EVERY HTML
   response — it changes each hop.
5. **The callback may be dead.** A decommissioned admin portal returns
   `?error=server_error&error_description=...`. Open signup then leads nowhere useful — record it as
   Low/Info (likely out-of-scope "third party / no impact"), not account-level access.

## Severity framing

Open signup on a dev tenant is **Low/Info at best**, often out-of-scope (third-party Auth0 SaaS, no
impact on the vendor's service) when the downstream app that would grant privileges is broken. Report
it as a supporting observation — the real value of this recipe is usually *getting a session* to test
the actual product, not the signup itself.