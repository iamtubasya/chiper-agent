# Turnstile bypass via Playwright (headed Chrome + stealth init script)

Verified end-to-end against Cloudflare Turnstile on Auth0 Universal Login (production tenant behind a
WP-Engine/Cloudflare WAF). The challenge is `challenges.cloudflare.com/.../turnstile/.../<sitekey>/...`,
mode `new/flexible` (invisible/managed). A fresh Playwright profile gets challenged repeatedly ("rch"
challenge token, `input[name=captcha]` stays empty, form submit silently re-renders with no error).

## What actually works

```python
from playwright.async_api import async_playwright

STEALTH = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
window.chrome = window.chrome || { runtime: {} };
"""

ctx = await p.chromium.launch_persistent_context(
    PROFILE, headless=False, channel="chrome",          # headed + real Chrome channel
    viewport={"width":1366,"height":900},
    args=["--disable-blink-features=AutomationControlled"],   # hide the automation flag
    locale="en-US", timezone_id="America/New_York")
await ctx.add_init_script(STEALTH)
```

The four things that flip the verdict (any one missing = still challenged):

1. **Headed + `channel="chrome"` + a persistent profile** — never a fresh ephemeral headless context.
2. **Stealth init script** — `navigator.webdriver` must be `undefined` (NOT `false`), plus fake
   `languages`/`plugins`, plus inject `window.chrome`.
3. **Seed the profile** — navigate the apex domain first (`unito.io`), scroll, wait a few seconds, so the
   profile has cookies/history before hitting the login/signup page.
4. **WAIT, then poll for the token** — do not submit immediately. After filling the form, poll:

```python
for i in range(40):
    await page.wait_for_timeout(1000)
    token = await page.evaluate(
        "() => { const r = document.querySelector('[name=cf-turnstile-response],[name=captcha]'); "
        "return r ? r.value : ''; }")
    if token: break   # typically appears in ~8s once the browser looks human
```

When the token appears, submit. `navigator.webdriver` should read `undefined` by this point — verify it.

## Pitfalls (all hit live)

- **The cookie-consent / OneTrust overlay intercepts `page.click()`** and makes every "click Sign up"
  fail with "intercepts pointer events". Bypass it: use `fill()` (sets value directly, ignores overlays)
  and submit with `page.locator(sel).evaluate("el => el.click()")` (dispatches a JS click, ignores pointer
  interception). Do NOT rely on `page.click()`.
- **Each Auth0 step has its own Turnstile** (identifier, password, signup, login) — re-wait for the token
  on every step before submitting.
- **Prefill only the real visible field** — the login page has a second hidden `input[type=password]`
  (autocomplete). Use `:visible` in the locator or wait for the visible one.
- **Don't navigate straight to `/signup`** — the SPA/Express backend may return "Cannot GET /signup".
  Go to the apex root and let the client-side router redirect to Auth0, then extract the `state` from the
  URL and drive `/u/signup/identifier?state=...` directly.

## Distinguish bot-detection from a missing account

If signing up re-lands on the identifier page and the caption/reset text says "the user already exists",
the account WAS created earlier (turnstile blocked only the password step, or an API signup created it).
Check the disposable-mail inbox for the verification email and complete email verification instead of
re-signing-up. Don't loop re-creating the same email.