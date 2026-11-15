# Auth0 Universal Login signup + managed Cloudflare Turnstile auto-solve

Proven recipe (Unito, 2026-11). Applies to any target fronted by Auth0 Universal Login
(`login.<target>.com/u/signup/identifier`) with a **managed** Cloudflare Turnstile on the
identifier step.

## The symptom that costs the most time

`POST /u/signup/identifier` returns **HTTP 400 with an empty body** and the hidden
`captcha` field is `""`. That reads as "rejected" — it is NOT. It means the Turnstile
token was not ready when you clicked submit. Do not fight the 400; wait for the token.

## Why headless / Playwright-launched Chrome fails

With a Playwright `launch_persistent_context(... executable_path=chrome)` (even with
`--disable-blink-features=AutomationControlled` + `navigator.webdriver` stripped), the
Turnstile iframe (`challenges.cloudflare.com/cdn-cgi/challenge-platform/.../turnstile/...`)
stays **empty (body len 0)** — the managed widget never renders. Cloudflare still flags the
automation. Stop chasing stealth flags here.

## The fix: real Chrome over CDP, then WAIT

1. Launch the real Chrome binary with a fresh persistent profile (NOT Playwright's launch):
   ```
   chrome.exe --remote-debugging-port=9225 --remote-allow-origins=* \
     --user-data-dir=C:\...\<profile> --no-first-run about:blank
   ```
2. Drive it with Playwright:
   ```python
   browser = p.chromium.connect_over_cdp("http://127.0.0.1:9225")
   ctx = browser.contexts[0]           # connect_over_cdp -> Browser, NOT pages
   pg = ctx.new_page()                  # or ctx.pages[0]
   ```
3. `goto(app signup)`, `wait_for_url("**login.<target>**")`, dismiss the cookie banner
   (OneTrust "Accept All" overlays the social buttons and blocks clicks).
4. **Poll the captcha field until it auto-fills** (managed Turnstile self-solves ~10-15 s):
   ```python
   for _ in range(14):
       n = pg.evaluate("()=>{const c=document.querySelector('input[name=captcha]');return c?c.value.length:0}")
       if n > 0: break        # ~730 chars
       time.sleep(2)
   ```
5. Only then fill email/name/company and submit.

## Auth0 signup / login flow shape (for reuse)

- signup identifier: `POST /u/signup/identifier` body `state, email, name, company_name,
  captcha, js-available, webauthn-available, is-brave, webauthn-platform-available`
- → `POST /u/signup/password {password}` → app `/api/v2/auth0/callback?code=...`
- email verification link (in "Welcome" / verify email): `https://login.<target>/u/email-verification?ticket=<token>`
- login: `/u/login/identifier` → `/u/login/password` (captcha auto-solves again)

## Pitfalls

- `connect_over_cdp` returns a `Browser`; `.pages` lives on `browser.contexts[0]`, not on the browser object.
- One Chrome profile per account (A vs B) for IDOR differential — separate `--user-data-dir` each; a second
  port alone does NOT isolate the cookie jar.
- The hidden `js-available`/`webauthn-available` fields default `false`; the 400 is captcha, not those.
- `email-verification?ticket=` token is short-lived but the signature is validated; tampering → 404.