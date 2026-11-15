# Rails + React (MUI / react-hook-form) signup: hydration traps, Turnstile dead-ends, direct-endpoint fallback

Verified live on coderpad.io (2026-10-17), app.coderpad.io — Rails monolith + React SPA
(webpack packs on CloudFront, ~20 vendor chunks), Cognito for authz, Ory Hydra legacy SSO,
Cloudflare in front, Turnstile on the final signup step.

## 1. THE BIGGEST TIME SINK: React hydration is SLOW on pack-heavy apps — typing before it
completes silently does nothing

Symptoms (all hit live, ~10 min burned before the fix):
- `pg.fill('#email', ...)` / `keyboard.type()` → the input's **DOM value updates** (so a naive
  `evaluate(()=>el.value)` says "it worked"), but React state never changes: no XHR fires
  (`networkidle`-style checks show only analytics), the submit button stays `disabled=True`
  forever, and MUI checkbox `check()` reports *"Clicking the checkbox did not change its state"*.
- Playwright `click()` on the input times out with *"element is not stable / not visible"* while
  the page looks fine — that's the hydration re-render replacing nodes under you.

Fix (all four parts needed):
```python
pg.goto(url, wait_until='domcontentloaded', timeout=60000)   # NOT networkidle — analytics/
time.sleep(20)                                                # keepalive requests never idle → timeout
pg.evaluate("() => document.querySelector('#email').focus()") # focus via JS, then TRUSTED events
pg.keyboard.type(EMAIL, delay=45)
pg.keyboard.press('Tab')   # blur — react-hook-form mode:"onTouched" validates on blur; the
                           # EmailDomain-style availability query fires here, THEN the button enables
# poll:  pg.evaluate("() => document.querySelector('button[type=submit]').disabled")
```
After 20 s hydration the same sequence flipped the button disabled→enabled within 2 s.
Rule of thumb: **15–25 s wait for any React SPA whose page HTML references dozens of
`packs/*~vendors~*` chunks**; assert hydration by waiting for an XHR/GraphQL request to
app.coderpad.io in the network log, not by a fixed guess.

## 2. Turnstile (invisible mode) is a dead end in headless — recognise it in one look

- The widget exists only as a hidden input (`input[name=cf-turnstile-response]`,
  id `cf-chl-widget-k4jcb_response`) — no iframe to click, `window.turnstile` never gets a
  token, the submit stays disabled for 60 s of polling. No challenge ever renders.
- Headed mode (`headless=False`) on a **fresh** context can trip a Cloudflare
  "Please enable cookies" error page instead of the app.
- Don't grind. Go straight to §3.

## 3. Direct-endpoint fallback: Rails JSON endpoints + page CSRF meta

The SPA's gates are client-side. Read the endpoint contract out of the webpack packs
(grep `register.json`, `check-email`, `canary`), then call the API with the session CSRF token:

```python
page = op.open('https://app.coderpad.io/register').read()          # seeds session cookies
csrf = re.search(r'name="csrf-token" content="([^"]+)"', page).group(1)
POST /check-email  {"user":{"email":E},"canary":"coalmine"}        # + X-CSRF-Token header → 200
POST /register.json {"user":{"email":E,"name":N,"password":P,"email_opt_in":False},
                     "canary":"coalmine"}                          # → 201 {"urlRedirect":"/unconfirmed"}
```
- **No Turnstile token needed server-side** (201 without it) — that gap is usually
  "client-side faking" and OUT of scope per most VDPs; use it as a means, not a finding.
- Missing `X-CSRF-Token` → generic `422 Unprocessable Entity` (not 403) — the tell that you
  forgot CSRF, not that the route is dead.

## 4. ⛔ Account-created ≠ provisioned: PROVE the confirmation email actually arrives

The 201 above may skip the transactional-email side effect (different code path than the UI).
Live failure: 2 registrations + 2 `/confirmation` resends + 2 `/password.json` resets →
**zero emails in 50+ min** (Gmail API, `includeSpamTrash=true`), while the same inbox verifiably
received 200+ other messages incl. other vendors' plus-alias mail. Pre-confirmation login →
`POST /login.json` 403 "Something went wrong"; `/check-email` returns the same empty
`{"message":""}` for known and unknown addresses (no existence oracle).

Checklist before declaring the target untestable-or-provisioned:
1. Search the inbox via Gmail API for the alias **and** the bare sender (`from:coderpad`),
   `includeSpamTrash=true`, several polls over ≥30 min.
2. Try both alias shapes (`user+tag@` and `user.tag@`) — suppression can be per-address-string.
3. **Triangulate the sender with a THIRD, independent provider before blaming anyone.**
   Alias shapes only rule out per-address suppression; they cannot separate "vendor mailer dead"
   from "Gmail-side blocked". Register a 3rd account on a fresh disposable inbox from a different
   provider entirely (mail.tm via API — see SKILL Step 1) and poll it too. Live result on
   coderpad.io: 3 addresses × 2 independent providers × 6 send attempts (register ×3,
   `/confirmation` resend ×2, `/password.json` reset ×1), ~60 min, spam included → **zero mail
   anywhere** while the Gmail inbox received 200+ unrelated messages. That differential is what
   proves the vendor's transactional-email path is broken rather than your inbox or alias being
   filtered — it turns "I never got the mail" into an evidence-backed blocker statement.
4. If nothing arrives across providers while unrelated mail flows: the vendor's mail path is
   broken — report the engagement state as **BLOCKED at authenticated surface** with the evidence
   trail, never as "0 findings / target clean".

## 5. Mapping aid: window.CoderPad-style inline config

SPA apps often expose `window.<App> = {...}` config in the raw login/register HTML before
hydration (here: `STITCH_URL`, `ASSET_HOST`, `GOOGLE_CLIENT_ID`, FLAGS). Grep the raw page for
`window\.<Name>\s*=` before downloading JS packs — it usually names the third-party pipelines,
asset CDN and OAuth client in one shot.
