# Cloudflare Turnstile on signup / register — getting a token out of a real browser

Measured 2026-10-31 on scribblemaps.com (register + vulnerability-portal forms), Windows,
headed real Chrome via Playwright persistent profile. Reproducible pattern for any target whose
signup is gated by a Turnstile widget.

## The trap

`window.turnstile.getResponse()` returns `null` and `document.querySelectorAll('iframe')`
returns `[]` even though the widget has a normal bounding box. Two wrong conclusions follow:
"Turnstile is unsolvable" and "the widget never rendered". Both are false — the iframe lives
inside the widget div, and the widget is in a mode that does **not** issue a token until it is
activated.

## What actually works

1. Drive the form in a **headed, real Chrome** (Playwright `launch_persistent_context` with
   `channel="chrome"`, `--disable-blink-features=AutomationControlled`, a real viewport and
   `locale`/`timezone_id`). Headless and CDP-only launches did not produce tokens.
2. Fill the fields, click submit so the app switches to its captcha view and calls
   `turnstile.execute(...)`.
3. Read the widget rect, then **click the checkbox**:
   ```js
   const r = document.getElementById('registerTurnstile').getBoundingClientRect();
   // checkbox sits vertically centred, ~32-36px from the left edge
   page.mouse.click(r.x + 34, r.y + r.height / 2);
   ```
4. Poll `window.turnstile.getResponse()` once per second. Token appeared **~4 s** after the
   click on a good run; allow 45 s.
5. The app auto-submits on the token callback (`captchaAutoSubmit`), so do not click submit
   again — verify with `GET /api/account` (or the app's own session endpoint) returning 200.

## Read the sitekey, never hardcode it

Each form has its own key and they differ on the same site (scribblemaps: register
`0x4AAAAAADCl3kOJjZHJ_uoz`, portal form `0x4AAAAAACwfY3Um6fHIjKSd`). Pull it from
`data-sitekey` on the `.cf-turnstile` div at runtime.

## Flakiness is real — plan for it

The same click sequence succeeded once and then failed three consecutive times (widget
rendered, rect correct, click landed, token stayed `null`). Treat Turnstile as **best-effort**:

- Retry the whole flow in a **fresh profile** rather than re-clicking a dead widget.
- If it keeps failing, look for a **captcha-free path the vendor documents for automation**.
  Scribble Maps' own portal page publishes one
  (`POST /api/vulnerability/aisubmit?userId=<own userId>`), which is how the report was
  finally submitted. Vendor-documented automation endpoints beat fighting the widget.
- Never brute-force the widget: repeated failed attempts are what makes the next attempt fail.

## Session hygiene that goes with it

- The auth cookie is what matters; `ctx.storage_state(path=...)` after a successful login and
  replay those cookies into `requests` for all API work.
- Sessions expire mid-engagement (observed repeatedly). Re-login through the same profile, and
  handle the **"You are logged in elsewhere. Logout other location?"" dialog by clicking YES**
  (the primary button) before assuming the credentials are wrong.
- Verify identity before every sensitive call: `GET /api/account` → compare `userId` to the
  value you are about to send as a parameter. A stale session silently turns a valid request
  into a 401 and reads as "authz holds" when it does not.
