# Turnstile-gated signup — headed Chrome + persistent profile

Working script shape, measured 2026-10-31 (Scribble Maps, explicit-render Turnstile, Angular form).
Minted two accounts (`+sm1`, `+sm2`) in ~15 s each. No captcha service, no solver.

## Why headed + real Chrome

The Turnstile widget is rendered explicitly (`api.js?onload=onTurnstileLoaded&render=explicit`) and
executed on submit. Headless Chromium gets a challenge that never resolves. `channel="chrome"` in a
`launch_persistent_context` with `headless=False` behaves like a normal browser and solves
non-interactively in ~9–10 s.

## Skeleton

```python
import time, os
from playwright.sync_api import sync_playwright

D      = r"$HOME/bounty\<target>"
EMAIL  = "RESEARCHER_USERNAME+sm1@gmail.com"      # plus-alias = a real inbox, one per identity
PWD    = "Zq7vLm2Kx9pR4t!a"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        os.path.join(D, "chrome-profile"),          # one dir per identity
        channel="chrome", headless=False,
        args=["--disable-blink-features=AutomationControlled"],
        viewport={"width":1366, "height":900}, locale="en-US", timezone_id="Asia/Jakarta")
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://<host>/account/login", wait_until="domcontentloaded", timeout=60000)
    time.sleep(3)

    # 1) switch to the register TAB (class, not id)
    page.click("button.btn.btn-orange")
    time.sleep(2)

    # 2) fill by input ID — the name= attributes differ from the ids
    page.fill("#registerEmail", EMAIL)
    page.fill("#registerPassword", PWD)
    page.fill("#registerRepeatPassword", PWD)

    # 3) submit by the real button id
    page.click("#registerNow")

    # 4) poll the token, not the DOM
    tok = None
    for i in range(90):
        time.sleep(1)
        try:
            tok = page.evaluate("()=>{try{return window.turnstile.getResponse()}catch(e){return null}}")
        except Exception:
            tok = None
        if tok:
            print("token after", i, "s:", str(tok)[:24]); break

    time.sleep(10)

    # 5) judge success from the account API, not page text
    print(page.evaluate("async()=>{const r=await fetch('/api/account',{credentials:'include'})"
                        ";return [r.status,(await r.text()).slice(0,200)]}"))
    ctx.storage_state(path=os.path.join(D, "state.json"))
    ctx.close()
```

## Gotchas that cost a full round

| symptom | real cause |
|---|---|
| `page.fill("input[name=rEmail]")` → "waiting for locator" timeout | ids are `registerEmail/registerPassword/registerRepeatPassword`; `name=` is `rEmail/rPass/rPass2` |
| `page.click("button.btn-orange")` → timeout, form still open | two elements carry that class; the tab is `btn-orange`, the submit is `#registerNow` |
| `turnstile.getResponse()` → "Could not find widget" | widget is not rendered until submit; container is `0×0` with no iframe |
| body still shows the onboarding wizard after submit | signup **succeeded**; verify with `GET /api/account` → `200 {userId,…}` |
| widget never solves | headless mode — must be `headless=False` + `channel="chrome"` |

## Harness details

- **Two identities = two profile dirs** (`chrome-profile`, `chrome-profile2`) and two
  `storage_state` files. Never reuse one profile for both; never `clear_cookies()` on a working one.
- **Harvest the session cookie for `requests`** from the saved state, allowing only cookies whose
  domain contains the apex (`"scribblemaps" in c["domain"]`) — that carries `ScribbleMaps_Auth`
  (752 B) plus `cf_clearance`. Per-host cookies (`team.scribblemaps.com`) belong to another app.
- **A separate host = a separate session.** A cookie valid on `www.` did not authenticate the `team.`
  subdomain; `team.` needed its own visit (`state2.json` came back with no `ScribbleMaps_Auth` and
  every `team/api/*` call returned the login HTML). When an app is split across subdomains, re-visit
  each one in the same profile before harvesting.
- **Captcha enforcement check:** `POST /api/account/` with any body → `{"error":"Captcha required"}`.
  That confirms the token is server-validated (correct behaviour) rather than client-trusted.
- Clean up: the accounts are disposable aliases; keep `creds.json` (0600) in the engagement dir.
