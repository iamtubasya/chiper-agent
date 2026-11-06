# Cloudflare Turnstile "flexible" bypass — Playwright stealth recipe

Turnstile in **flexible/new** mode (`.../challenges.cloudflare.com/.../new/flexible`) auto-passes for
clean human browsers but challenges fresh/automated profiles silently: there is no visible checkbox in
the DOM, the challenge iframe's child frames are all `about:blank`, and clicking "submit" just re-renders
the form with no error. The captcha token never materialises.

What actually got a token (Auth0 signup behind Turnstile, 2026-11):

1. **Stealth init script** (this made `navigator.webdriver` read `undefined` — the tell that broke it):
   ```js
   Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
   Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});
   Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
   window.chrome = window.chrome || { runtime: {} };
   ```
2. **Headed persistent Chrome**, not headless:
   ```python
   ctx = await p.chromium.launch_persistent_context(PROFILE, headless=False, channel="chrome",
       args=["--disable-blink-features=AutomationControlled"], locale="en-US")
   await ctx.add_init_script(STEALTH)
   ```
3. **Poll for the token before submitting** — Turnstile drops the response into a hidden input after ~8s:
   ```python
   token = ""
   for i in range(40):
       await page.wait_for_timeout(1000)
       token = await page.evaluate("() => { const r=document.querySelector('[name=cf-turnstile-response],[name=captcha]'); return r?r.value:''; }")
       if token: break
   ```
   Only submit once `token` is non-empty.

4. **Submit via JS click, not `page.click`.** A cookie-consent overlay (OneTrust) intercepts pointer events
   (`...subtree intercepts pointer events` spam). `fill()` is unaffected (no pointer event); only `click()`
   is. Use `page.locator(sel).first.evaluate("el=>el.click()")` to dispatch the click directly.

5. Success also minted a `cf_clearance` cookie (domain `.unito.io`) that softened later Cloudflare checks.

## Auth0-specific twists (separate "dev" tenant with OPEN signup)

Some programs run a **separate Auth0 tenant** for the developer program (e.g. `unito-dev.us.auth0.com`)
with **open signup and no bot detection** — `POST /dbconnections/signup` returns 200 and creates the user
unconditionally. Two oracles:

- **Connection-name oracle:** `POST /dbconnections/signup` with the wrong connection returns
  `404 {"error":"connection not found"}`; the *right* connection returns
  `401 {"name":"requires_verification", ...}` — that 401 is confirmation the connection name is correct,
  not a hard block.
- **`requires_verification` can still create the user.** Even though the signup response is 401
  "Suspicious request requires verification", the user *is* created and the welcome/verification email
  *is* sent. Check the mailbox for the verification link instead of assuming failure. A later interactive
  signup then says "The user already exists" — which is actually good news.

## Pitfall: the manual `dbconnections/signup` → interactive flow

After an API signup created the user, the interactive signup form rejects with "The user already exists"
on the password step because the account already exists — go straight to *login* (username/password),
don't fight the signup form again.