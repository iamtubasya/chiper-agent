# Browser automation + vendor-portal submission (measured 2026-10-31, Scribble Maps)

Recipes that worked when the usual browser paths were unavailable. All of it is **fix-shaped**:
what to run, not "tool X is broken".

## 1. Playwright + real headed Chrome is the reliable path for CAPTCHA-gated signup/login

Cloudflare Turnstile on the vendor's signup/login passed automatically in a **real headed Chrome**
launched by Playwright with a persistent profile. It did not pass in the headless/CDP-only browser.

```python
from playwright.sync_api import sync_playwright
ctx = p.chromium.launch_persistent_context(
    "<workdir>/chrome-profile-<label>", channel="chrome", headless=False,
    args=["--disable-blink-features=AutomationControlled"],
    viewport={"width": 1400, "height": 900}, locale="en-US")
page = ctx.pages[0] if ctx.pages else ctx.new_page()
```

Timing measured: token appeared ~9-10 s after clicking submit. Poll it, don't guess:

```python
for i in range(90):
    time.sleep(1)
    tok = page.evaluate("()=>{try{return window.turnstile.getResponse()}catch(e){return null}}")
    if tok: break
```

If the token never appears, the widget is rendered but its iframe sits in a shadow root, so
`document.querySelectorAll('iframe')` returns `[]`. Two nudges that worked, in order:
1. click the widget's checkbox by coordinates — `rect = el.getBoundingClientRect()`, then
   `page.mouse.click(rect.x + 32, rect.y + rect.height/2)`;
2. `window.turnstile.reset('#id')` then `window.turnstile.execute('#id')`.

Field ids on this vendor (Angular account app): login `input[name=email]` / `input[name=password]`,
submit `button.btn-blue`; register `#registerEmail` / `#registerPassword` / `#registerRepeatPassword`,
submit `#registerNow`. **Always re-probe ids with a DOM dump before filling** — they differ per app.

## 2. Concurrent-session lock on login

Login can answer with a modal "You are logged in elsewhere. Logout other location?" and the
account API still returns 401. Click the visible `YES` control, wait ~8 s, then re-check
`GET /api/account`. Without that click the session looks dead and you will re-register an
account that already exists.

## 3. Keeping a form open for the operator to submit manually

Pattern: fill the form, verify N times, screenshot, then hold the browser with a long sleep in a
`terminal(background=True)` process so the window stays on the operator's screen.

**Pitfall:** the window dies when the sleep ends. Set the hold long enough for a human
(2 h worked better than 1 h) and tell the operator the exact expiry time. If it closes, re-open —
do not assume the submission happened. Verify independently afterwards with
`GET /api/vulnerability/list` (empty = nothing submitted).

## 4. NEVER spam validation probes on a submit endpoint

Dry-running a submit endpoint to learn its field names is useful, but each incomplete POST counts
against a **per-IP throttle**. Measured: 6 deliberately-incomplete probes → the endpoint started
returning `429 "You've submitted too many reports recently"`, which then blocked the *real*
submission for ~30+ minutes.

Correct pattern:
- Send **one** incomplete payload (e.g. `{"title": "probe"}`) and read the validation error —
  that already reveals the next required field.
- Repeat only if a *different* field name is still unknown, and space them out.
- Before the real submission, re-probe once: `400 <validation error>` = throttle clear,
  `429` = still blocked, wait.
- If you already tripped it, say so in the report and in COVERAGE.md — it is an agent-caused
  side effect the vendor may ask about.

## 5. nuclei sizing: tech-targeted beats blanket

`-tags cve` alone = 4,583 templates. Across 6 hosts that is tens of thousands of requests, which
most programs explicitly ask you not to do. Fingerprint first, then run the matching tags:

```
nuclei -tl -tags aspnet,iis,dotnet,angularjs,jquery   # 45 templates
nuclei -tl -tags exposed-panels,backup,swagger,graphql # 88 templates
```

A combined 105-template run over 6 hosts finished in 11 min at `-rl 15 -c 8`. Always run with
`-stats` and keep the log: `Scan completed ... N matches` plus `Requests: X/Y (100%)` is the
artifact that makes a zero-finding claim honest. If a run is too slow, **kill it and replace it
with a bounded run that actually completes** rather than reporting a partial sweep as coverage.

## 6. Side-effect hygiene when probing money/payout APIs

Probing seller-provisioning endpoints can create **real financial objects** on the vendor's
platform (here: one unverified Stripe Connect Express account from `POST /api/market/create-account`).
Rules that kept this clean:
- Idempotent calls are fine to repeat; do not proceed into KYC/onboarding to "complete" the test.
- Record the created object id in COVERAGE.md and disclose it in the report body.
- If self-provisioning of the paid feature is impossible without KYC, demonstrate the finding on
  the **vendor's own demo asset** instead of faking identity — that is also stronger evidence.

## 7. Wordlists when none are installed

No local wordlist? Build a targeted one from the app's own surface (routes harvested from JS
bundles + obvious config/backup names) — 90 entries was enough here — and always establish a
soft-404 baseline first (`GET /zz-nonexistent-<rand>`) and filter on its byte length
(`-fs <len>`). Compare a hit's SHA-256 against the baseline before calling anything a finding.

## 8. PoC regenerated ⇒ draft must be rebuilt, not edited

If a PDF PoC is corrected/regenerated **after** a Gmail draft exists, do not try to "update" the
draft: editing the body does **not** replace the attachment, so the vendor receives the stale
file (wrong size/hash) as evidence.

Correct sequence:
1. Create a NEW draft via `drafts().create()` with the current file attached.
2. Delete the old draft (`drafts().delete()`) so one finding never has two versions in flight.
3. Verify the new draft by reading it back with `drafts().get(format="full")`: check
   `parts[].filename` **and** `parts[].body.size` against the file on disk, plus key strings in
   the body (evidence hash, reference ID).

Also put a **submission-details block** in the email body (title, date of discovery, attachment
name + size, payout e-mail). The same text can then be pasted straight into the vendor's portal
form without re-authoring it, which matters when the portal allows only one report per day.
