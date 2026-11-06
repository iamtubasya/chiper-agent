# Turnstile-gated SPA signup → reusable authenticated session (2026-10-31)

Target: a marketing/SPA app (Angular login micro-app) whose register form is protected by Cloudflare
Turnstile in `render=explicit` mode. Result: two working test identities provisioned end-to-end with
zero operator interaction, then all API testing done from `requests` (no browser).

## What was observed before the working path

| attempt | result |
|---|---|
| `POST /api/account/ {"email":"","password":""}` from Python | `200 {"error":"Captcha required"}` — gate fires, endpoint itself is fine |
| clicking the register submit by CSS class `button.btn-orange` | timeout 10 s on the *second* click — that class is the panel-opening button, not submit |
| poll `window.turnstile.getResponse()` before submitting | throws `[Cloudflare Turnstile] Could not find widget.` — widget not executed yet |
| `page.screenshot()` in the save/signup flow | timeout 30 s ("waiting for fonts to load") — drop it, it is not gate-related |

Diagnosis that unblocked it: dump inputs and buttons by id/class, then click the element whose **id** is
the app's register submit.

## The recipe

```python
import time, os
from playwright.sync_api import sync_playwright

EMAIL = "yourname+alias1@gmail.com"          # alias you can read
PWD   = "Zq7vLm2Kx9pR4t!a"                   # random, per-target, stored in the workdir
profile = os.path.join(WORK, "chrome-profile")

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        profile, channel="chrome", headless=False,            # real Chrome, headed
        args=["--disable-blink-features=AutomationControlled"],
        viewport={"width": 1366, "height": 900},
        locale="en-US", timezone_id="Asia/Jakarta")
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://target/account/login", wait_until="domcontentloaded", timeout=60000)
    time.sleep(3)

    # 1. open the register panel (correct selector for this app)
    page.click("button.btn.btn-orange"); time.sleep(2)

    # 2. confirm the real field ids instead of guessing names
    ids = page.evaluate("()=>[...document.querySelectorAll('input')].map(i=>i.id)")
    #  -> ['registerEmail','registerPassword','registerRepeatPassword']

    page.fill("#registerEmail", EMAIL)
    page.fill("#registerPassword", PWD)
    page.fill("#registerRepeatPassword", PWD)

    # 3. submit with the app's real submit button
    page.click("#registerNow")

    # 4. poll the token (do NOT sleep blindly)
    tok = None
    for i in range(90):
        time.sleep(1)
        try:
            tok = page.evaluate("()=>{try{return window.turnstile.getResponse()}catch(e){return null}}")
        except Exception:
            tok = None
        if tok:
            print("token at", i, "s", tok[:24]); break
    time.sleep(8)   # let the app finish the post-token onboarding step

    # 5. verify the session is real before harvesting
    print(page.evaluate("async()=>{const r=await fetch('/api/account',{credentials:'include'});"
                        "return [r.status, (await r.text()).slice(0,200)]}"))

    ctx.storage_state(path=os.path.join(WORK, "state.json"))
    ctx.close()
```

Then, from plain Python (no browser):

```python
st = json.load(open("state.json"))
S = requests.Session()
S.headers.update({"User-Agent": "...Chrome/131...", "Accept": "application/json"})
for c in st["cookies"]:
    if "targetdomain" in c["domain"]:
        S.cookies.set(c["name"], c["value"], domain=c["domain"])
assert S.get("https://target/api/account").status_code == 200
```

Persist `state.json` per identity (`state.json`, `state2.json`) — a second identity is just the same script
with a different alias and a different `chrome-profile` dir. Keep the profile dirs separate: one profile per
process, or the second launch refuses with "Opening in existing browser session".

## Details worth reusing

- Token appeared ~9 s after submit. Turnstile token is bound to the page/session; do not try to replay it
  from `requests` — replay the **cookies** (`storage_state`) instead.
- The post-signup screen was an onboarding questionnaire ("Your Industry/Purpose"), not an error. `GET
  /api/account` returning `200` with a `userId` is the proof the account exists; a `401` there means the
  flow did not complete.
- `window.turnstileSiteKey` is a fast way to confirm what you are fighting without parsing the HTML.
- Alias mailboxes: `user+sm1@gmail.com` / `user+sm2@gmail.com` both worked for two independent identities
  on this target (no plus-address normalisation). Where the app *does* normalise, use the alternate-domain
  trick in §1b of the parent skill.
- Run the browser script through `terminal` with a generous timeout (or `background=true`), never inside
  `execute_code` — headed Chrome plus a 90 s poll loop will outlive a short tool budget.

## Honest-reporting notes

- Two accounts were created by the researcher on a free plan; no PII was fabricated.
- The signup gate itself (Turnstile) is a **working control**, not a finding. What it protects — the
  authenticated API — is where the audit starts.
