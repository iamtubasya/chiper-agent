# OAuth popup signup + invisible reCAPTCHA + React zero-request wizard

Session detail, verified 2026-10-21 on CodeRabbit and Cloudsmith. These three traps cost ~2 hours
across the two engagements; each has a cheap diagnostic.

## 1. OAuth popup flow (CodeRabbit, app.coderabbit.ai/login)

Shape: login page offers "GitHub Cloud / GitLab Cloud / Bitbucket Cloud / Azure DevOps Cloud /
Single Sign-On". Clicking a provider button runs `window.open(...)` — the GitHub authorize page
opens in a POPUP and `pg.url` stays on the app origin.

What failed first: headless click, then `pg.url` polling — "no redirect", concluded "click didn't
register", burned 4 attempts. The popup was there the whole time.

Working sequence (headed):

```python
popups = []
ctx.on("page", lambda pg: (popups.append(pg), pg.bring_to_front()))
pg = ctx.new_page(); pg.bring_to_front()
pg.goto("https://app.<target>/login", ...)
pg.wait_for_timeout(10000)
box = pg.evaluate("()=> { /* getBoundingClientRect of the provider button */ }")
pg.mouse.click(box["x"], box["y"])          # real click; JS click also works
# operator completes GitHub login + Authorize in the popup
for i in range(170):                        # poll ~8 min
    time.sleep(3)
    main = pg.url
    if "github.com" not in main and "/login" not in main:
        break                               # main page left /login = done
ctx.storage_state(path=PROFILE + r"\state.json")   # save on URL change, crash-safe
```

After the first manual authorization the GitHub app keeps the grant, so subsequent automated runs
redirect instantly (headless OK). The OAuth authorize URL exposes `client_id`, `redirect_uri`,
`scope`, and a `state` param — record them; state presence is the design, absence would be the bug.

Crash-safety lesson from the same run: the final `pg.evaluate` after a navigation throws
"Execution context was destroyed" — wrap every post-navigation evaluate in try/except and save
storage_state immediately on URL change, not after the loop.

## 2. Invisible reCAPTCHA (Cloudsmith, app.cloudsmith.com/signup)

Signup wizard: email → (username/firstName/lastName/password/acceptTerms) → Continue. No captcha
widget visible at any point. On Continue, the ONLY network traffic is:

```
GET https://www.google.com/recaptcha/api2/anchor?ar=1&k=<sitekey>&co=...
GET https://www.google.com/recaptcha/api2/bframe?hl=en&v=...&k=<sitekey>
```

Zero app XHRs → the form never submitted. This is NOT the React-state failure (that also fires
zero requests, but no recaptcha iframes either). The discriminator: filter requests during the
click excluding datadogh/sentry/vercel/assets — if you see the recaptcha pair, it's the captcha.

reCAPTCHA v3 scores the session, so headless, headed-automated, AND a human drag inside the
automated window can all fail. Verdict after 3 attempts (headless typed, headed typed+manual):
BLOCKED at authenticated surface.

Pivot that still produced value: the unauthenticated plane was fully reachable —
`/v1/packages/{owner}/{repo}/` (public repo metadata), `/v1/formats/` (incl. a new "AI Skills"
zip format), `/v1/openapi/` (Swagger 2.0 YAML, 11 public paths), `/v1/status/check/basic/`
(version disclosure), `/v1/rates/limits/` (caller usage), `/v1/user/self/`. Only the bare API apex
was CloudFront-WAF'd from the datacenter IP; the versioned paths answered fine.

## 3. React wizard: terms label + zero-request diagnostic (Cloudsmith)

- `input[name=acceptTerms].click()` and a real mouse click at the checkbox's bounding-box centre
  both left `checked=false` (the box is visually hidden; the label is the hit target). Clicking
  `label:has-text('service terms')` worked. Assert `cb.checked` after.
- Username field auto-fills from the email local-part (incl. the `+tag`) — try to overwrite it;
  if `locator.click` times out on it, it may be derived/read-only.
- Even with every field showing a correct `el.value` and terms checked, Continue fired zero app
  requests → React state empty. Only trusted keyboard input
  (`locator.click()` → `pg.keyboard.type(val, delay=40)`) registered. Combined with the recaptcha
  pair in the traffic, the block was confirmed as captcha, not state.

## Generalised checklist for "signup won't submit"

1. Filter network during the submit click (exclude analytics/assets).
   - App XHR fires → server-side rejection; read the response body.
   - Only recaptcha anchor/bframe → invisible captcha; log BLOCKED, pivot unauth.
   - Nothing at all → React state; re-fill with trusted keyboard typing.
2. Terms: click the label, assert `.checked`, re-read the error text.
3. OAuth buttons: assume popup; `ctx.on("page")` + headed; poll main + popups.
4. Save storage_state on every URL change (crash-safe), never after the loop.
