---
name: browser-session-daemon
description: "Use when a browser session must survive across many steps."
version: 1.0.0
author: Hermes curator (from TeamViewer portal auth session, 2026-09-11)
license: MIT
metadata:
  hermes:
    tags: [browser, playwright, cloakbrowser, auth, captcha, bug-bounty]
    related_skills: [bug-bounty]
---

# Browser Session Daemon

Persistent, file-driven browser daemon for multi-step auth flows (login → captcha → verify →
cookie export).

## When to Use

- A Playwright/CloakBrowser flow needs **≥3 sequential browser steps** (navigate, dismiss banner,
  fill, solve captcha, submit, export cookies).
- CloakBrowser **free tier caps concurrent sessions at 1** — throwaway script launches burn the
  slot and lose the warm profile each time.
- A prior browser died and `connect_over_cdp` can't recover: that only works when the original
  launch set `--remote-debugging-port` — a plain `launch()` never exposes one. File-IPC avoids CDP
  entirely.
- Captcha trust / fingerprint continuity matters — re-launching re-triggers risk challenges.

**Why:** every `launch()` is a new session — warm profile state, captcha trust, and cookies die
when the script exits, so each retry re-triggers risk challenges. One daemon launched once,
driven per step, keeps everything alive.

## Ready-made scripts

`scripts/bd.py` (daemon) + `scripts/bctl.py` (controller) — copy both into the session work dir,
edit WORK/PROFILE paths, run `python bd.py > bd.log 2>&1` in a background terminal, then
`python bctl.py '{"cmd":"dump"}'` per step. bctl auto-adds a `_n` timestamp so identical
commands aren't dedup-skipped. Kill the daemon (`process(kill)`) when done to free the session slot.

## Architecture

```
step script ──cmd.json──▶ daemon (launch_persistent_context, poll loop)
step script ◀─res.json──  daemon executes Playwright action, writes result
```

**Controller** `bctl.py '<json-cmd>'`: deletes res.json, writes cmd.json, polls res.json, prints result.

## Daemon (bd.py) — working pattern

```python
import json, os, time
from cloakbrowser import launch_persistent_context

WORK = "<session dir>"; CMD = WORK+"/cmd.json"; RES = WORK+"/res.json"
PROFILE = WORK+"/profile_tv"  # persistent → cookies survive daemon restarts

os.remove(CMD) if os.path.exists(CMD) else None
os.remove(RES) if os.path.exists(RES) else None
ctx = launch_persistent_context(PROFILE, headless=False, humanize=True,
                                viewport={"width": 1366, "height": 900})
deadline = time.time() + 1200; last = None
while time.time() < deadline:
    try: cmd = json.load(open(CMD))
    except Exception: time.sleep(0.4); continue
    key = json.dumps(cmd, sort_keys=True)
    if key == last: time.sleep(0.4); continue  # dedup
    last = key
    pg = ctx.pages[cmd.get("page", 0)]
    c = cmd.get("cmd"); out = {"ok": False}
    if c == "goto":
        pg.goto(cmd["url"], wait_until="domcontentloaded", timeout=90000)
        time.sleep(cmd.get("wait", 4)); out = {"ok": True, "url": pg.url, "title": pg.title()}
    elif c == "fill":
        el = pg.query_selector(cmd["sel"])
        if el: el.click(); el.fill(cmd["val"]); out = {"ok": True}
        else:  out = {"ok": False, "err": "no such selector"}
    elif c == "click":
        if "sel" in cmd:
            el = pg.query_selector(cmd["sel"])
            el.click() if el else None; out = {"ok": bool(el)}
        else:
            pg.mouse.click(cmd["x"], cmd["y"]); out = {"ok": True}
    elif c == "eval":
        out = {"ok": True, "result": pg.evaluate(cmd["js"])}
    elif c == "dump":  # map the form FIRST — visible inputs/buttons + frame URLs
        out = {"ok": True, "url": pg.url, "title": pg.title(),
               "els": pg.evaluate("""() => Array.from(document.querySelectorAll('input,button'))
                   .map(e=>({t:e.tagName,ty:e.type||'',id:e.id||'',nm:e.name||'',
                             ph:e.placeholder||'',tx:(e.innerText||'').slice(0,30).trim(),
                             v:!!(e.offsetWidth||e.offsetHeight)})).filter(o=>o.v)"""),
               "frames": [f.url[:90] for f in pg.frames]}
    elif c == "body":
        out = {"ok": True, "text": pg.evaluate("() => document.body.innerText.slice(0,2500)")}
    elif c == "shot":
        p = WORK + f"/s_{cmd.get('tag','x')}.png"; pg.screenshot(path=p)
        out = {"ok": True, "path": p}
    elif c == "cookies":
        cs = ctx.cookies(); json.dump(cs, open(WORK+"/cookies_auth.json","w"), indent=2)
        out = {"ok": True, "n": len(cs), "names": sorted(set(x["name"] for x in cs))}
    elif c == "exit":
        out = {"ok": True}
    json.dump(out, open(RES, "w"), indent=2, default=str)
    if c == "exit": break
ctx.close()
```

## Controller (bctl.py)

```python
import json, os, sys, time
CMD = "<session dir>/cmd.json"; RES = "<session dir>/res.json"
cmd = json.loads(sys.argv[1])
if os.path.exists(RES): os.remove(RES)
json.dump(cmd, open(CMD, "w"))
t0 = time.time()
while time.time() - t0 < cmd.get("timeout", 100):
    if os.path.exists(RES):
        try: print(json.dumps(json.load(open(RES)), indent=2)[:3000]); break
        except Exception: time.sleep(0.3)
    time.sleep(0.3)
else:
    print(json.dumps({"ok": False, "err": "daemon timeout"}))
```

Run daemon via `terminal(background=true)`: `python bd.py > bd.log 2>&1`; tail bd.log for liveness.

## Auth-flow playbook (learned on TeamViewer login, 2026-09-11)

1. `goto` login → **`dump` first**. Real field IDs are often NOT the guesses
   (`#email`/`input[type=email]` failed; actual was `#UserName`/`#Password`, submit `#btn-sign-in`).
   Never hardcode guessed selectors.
2. **Kill the cookie-consent banner BEFORE touching fields** — OneTrust overlay causes
   `Element failed pointer_events check: element is covered by <DIV>` on every fill/click.
   Click `#onetrust-reject-all-handler` (or equivalent); ids show up in `dump`.
3. reCAPTCHA **silent block**: submit appears to do nothing — no URL change, no error text in `body`.
   Diagnose with eval: `#g-recaptcha-response` value length `0` = challenge unsolved, submit swallowed.
   Check `frames` / iframe bounding rects: visible bframe ~400×580 = image-grid challenge rendered.
4. Captcha inspection: `shot` → PIL crop the iframe rect (page coords == viewport coords when
   viewport fixed) → `vision_analyze` the crop for instruction text; enumerate tiles via eval of
   `div[class*="tile"]` getBoundingClientRect; click tiles via `{"cmd":"click","x":..,"y":..}`.
5. On success: `cookies` → export `cookies_auth.json` → authenticated API testing via curl/requests.
6. Second account (A×B IDOR): a SECOND PROFILE DIR — but free tier caps concurrent sessions at 1,
   so serialize daemons (exit A → start B with `profile_tv2`), not simultaneous.

## Pitfalls

- `launch(user_data_dir=...)` → TypeError (not a supported kwarg). Persistent profile ONLY via
  `launch_persistent_context(dir, ...)`.
- Passwords via env vars (`TV_PW=...`), never argv/logs. Operator passwords pasted in chat →
  remind them to rotate after the session.
- If the daemon dies mid-flow the cookies stay in the profile dir — restart the daemon, don't
  re-login from scratch.
- The daemon is a long-lived background process: always `process(kill)` it when done, or it
  holds the CloakBrowser session slot and blocks the next launch.
- Login pages served via curl often return a ~2KB JS shell with no form — go straight to the
  browser daemon rather than burning HTTP attempts.

## Parallel multi-account CDP (Chrome + Next.js Server Actions)

Proven recipe for cross-tenant (A×B×C) testing on Next.js apps — see
`references/nextjs-server-actions-cdp-testing.md` for the full workup
(quarterwise.co.uk VDP, 2026-09-26: 3 accounts, server-action capture/replay,
invite-token binding, export-injection verification).

Key rules that cost real time when missed:

1. **curl/urllib CANNOT submit Next.js Server Action forms.** The multipart POST
   needs hidden fields `$ACTION_REF_1`/`$ACTION_1:0`/`$ACTION_KEY`; `$ACTION_REF_1`
   is empty in server-rendered HTML and only the framework fills it during a real
   submit. Raw POST → HTTP 500 error page. Always drive the real browser:
   set input values via JS (`value` + `dispatchEvent(new Event('input',{bubbles:true}))`)
   then `form.requestSubmit()`.
2. **One Chrome profile per account = true isolation.** Launch separately per
   account, each with its own port AND user-data-dir:
   `chrome.exe --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=<dir1>` and
   `--remote-debugging-port=9223 --user-data-dir=<dir2>`. A second port alone is
   NOT enough — tabs share the cookie jar unless the profile dir differs.
   Stale Chrome holding a profile dir silently ignores the new flags: find it with
   `netstat -ano | grep :9222` → PID, kill via `powershell Stop-Process -Id <pid> -Force`
   (wmic/taskkill from git-bash mangles flags), then relaunch.
3. **HttpOnly cookies only via CDP**, not `document.cookie`: `Network.getAllCookies`
   from a websocket to the page's `webSocketDebuggerUrl` with header
   `["Origin: http://localhost"]` (requires `--remote-allow-origins=*`, else 403).
4. **`Network.requestWillBeSent` truncates multipart postData.** Get the FULL body
   with `Network.getRequestPostData {requestId}` and save a replay manifest
   {url, headers, postData}.
5. **Cross-tenant write-scope test** — do NOT replay A's captured action with B's
   cookie (you get `Server action not found`; actions bind to the session). Correct
   test: in B's OWN context open the form (valid action ids), then swap the hidden
   object id field (e.g. `propertyId`) to A's uuid and submit. Server saying
   `That property could not be found` / `Only the owner can...` proves write-scope
   is enforced server-side; `We can't find that page` on direct URL access proves
   page-level authz.

## Cloudflare Turnstile "managed" on Auth0 Universal Login (learned unito.io, 2026-11-03)

Auth0 Universal Login email+password signup guarded by a Cloudflare Turnstile widget:

- Signup sequence: `#/signup` → redirect to `login.<tenant>/u/signup/identifier` → enter email/name/company → `POST /u/signup/identifier` → `/u/signup/password` → set password → email verification (`/u/email-verification?ticket=<t>`).
- The identifier AND password steps embed a **Turnstile "managed" widget** (`render=explicit`, sitekey `0x4AAAA...`) whose token silently populates a hidden `input[name=captcha]`.
- The widget **auto-solves after ~10-15s** for a normal headed Chrome. Poll `document.querySelector('input[name=captcha]').value.length` every 2s until >0 (token ≈730 chars), THEN fill + submit.
- **Pitfall:** clicking submit before the token is ready returns HTTP 400 with an empty body and the page silently stays put — no inline error, easy to misread as a validation bug. The earlier "400" flip to success was purely a timing fix.
- The POST carries hidden fields `state`, `captcha`, `js-available`, `webauthn-available`, `is-brave` — leave them as the page set them; only `captcha` matters for the Turnstile token.
- Playwright `launch_persistent_context` (even with `--disable-blink-features=AutomationControlled` + `navigator.webdriver`=undefined) leaves the Turnstile iframe EMPTY = bot-detected. Real Chrome launched with `--remote-debugging-port --user-data-dir` then driven via `connect_over_cdp` is the path that actually renders and auto-passes.
- Self-hosted connector "Connect account" buttons open a **separate page** (`#/connect/{provider}?windowOpenerId=<uuid>`), not a modal in the same page — iterate `ctx.pages` to find it.

## Related

- **bug-bounty** skill's `references/cloakbrowser-stealth-browser.md` — install, launch API, anti-bot pass matrix.
- **bug-bounty** skill's `references/account-first-exploitation.md` — why 2 authenticated accounts, cookie capture, captcha escalation ladder.
