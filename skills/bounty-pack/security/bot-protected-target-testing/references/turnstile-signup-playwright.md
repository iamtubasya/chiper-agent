# Solving Cloudflare Turnstile on a signup form (headed Playwright)

Tested against a Rails SaaS (Rootly) with Turnstile on its `/users/sign_up` form
(sitekey `0x4AAAAAAA...`). The challenge stayed stuck at "Checking your Browser…"
with an empty `cf-turnstile-response` until one change was made.

## The unlock: a stealth init script, not just the blink flag

`--disable-blink-features=AutomationControlled` alone is NOT enough. Playwright/CDP
still sets `navigator.webdriver=true`, and Turnstile reads it and refuses to issue a
token. The override below is the part that matters — observered token length went
0 → 752 in ~3s ("TOKEN iter 1 len 752"):

```python
ctx = p.chromium.launch_persistent_context(
    PROFILE, headless=False, channel="chrome",
    args=["--disable-blink-features=AutomationControlled"],
    viewport={"width": 1280, "height": 900},
)
ctx.add_init_script(
    "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
    "window.chrome=window.chrome||{runtime:{}};"
)
```

Headless mode does NOT render Turnstile — the `challenges.cloudflare.com` iframe never
appears in `page.frames`. Always `headless=False` for Turnstile, and use a persistent
profile (reuses `__cf_bm`/`cf_clearance` across runs).

## Poll for the token; do not guess the checkbox

Turnstile implicit mode injects a hidden input into the PARENT form when solved:

```python
def token(page):
    return page.evaluate(
        "(document.querySelector('#new_user input[name=cf-turnstile-response]')||{}).value || null"
    )
```

Poll every ~3s up to ~60s; a non-empty value >10 chars = solved. The checkbox lives
inside the `challenges.cloudflare.com` iframe behind a shadow DOM:
`frame.query_selector()` does NOT pierce it, but `frame.locator(sel)` does. Recurse
`page.frames` and match on `'challenges.cloudflare.com' in f.url`, then click
`f.locator('input[type=checkbox]')` / `.ctp-checkbox-label` / `[role=checkbox]`.

## After solving, the signup POST can STILL fail — read the placeholder first

A B2B SaaS with a "Work email" placeholder on signup is very likely rejecting
free-email domains (gmail/outlook/…). The tell: `POST /users` returns **404**
(Content-Type text/html, no Location header) even with a VALID Turnstile token —
they obfuscate the rejection as 404 instead of a 422 validation error, so it reads
like a routing bug. Do not burn time debugging a "route"; check the email-domain
filter. Rootly (rootly.com) 2026-11: Turnstile solved, `POST /users` → 404. Next
move is a non-free-email test account (or a disposable domain not on their blocklist),
not more browser work.

Also note: turnstile + email-rejection are TWO independent gates. Solving the captcha
does not mean the account will be created; the account/registrability wall (free-email,
domain allowlist, B2B sales-led signup) is the next thing to probe — see target-pool's
REGISTRABILITY GATE.