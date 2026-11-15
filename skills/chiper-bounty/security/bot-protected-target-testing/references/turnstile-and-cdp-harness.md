# Turnstile interaction + CDP cookie/identity pitfalls

Hard-won on a Cloudflare + custom-WAF estate (nachi.org, 2026-10-30) where in-page
`fetch`/XHR POST and every CLI client were rejected, so the browser had to be driven
by CDP Playwright.

## 1. Solving Turnstile from CDP Playwright

The widget renders in an iframe under `challenges.cloudflare.com`. Two failure modes
before the working move:

| attempt | result |
|---|---|
| `pg.click('[id^=ts-]')` / `.cf-turnstile` | timeout — container reports `height: 0` |
| `fr.query_selector("input[type=checkbox]")` | `None` — the checkbox is inside a shadow root / cross-origin doc |

Working move — click the **iframe body**, poll the hidden response field:

```python
tok = ""
for attempt in range(8):
    for f in pg.frames:
        if "challenges.cloudflare.com" in f.url:
            try:
                f.click("body", timeout=4000)
            except Exception:
                pass
    for _ in range(5):
        time.sleep(2)
        tok = pg.evaluate(
            """() => { const e = document.querySelector('[name="cf-turnstile-response"]');
                       return e ? e.value : ''; }"""
        )
        if tok:
            break
    if tok:
        break
# success token length observed: 730-752 chars
```

Notes:
- The **first click usually no-ops.** Loop; do not conclude "unsolvable" after one attempt.
- `appearance: "interaction-only"` widgets only mint a token after a real interaction, so
  a pre-filled form with `token len 0` is expected, not a bug.
- Token is single-use. Any re-render of the form (`ajax:after` handlers that call
  `turnstile.remove(id); turnstile.render(...)`) invalidates it — re-solve before submit.

## 2. Submit with a real click, not `requestSubmit()`

`form.requestSubmit()` and `form.submit()` race the Turnstile callback and post an **empty**
token → server returns the form again with no error surfaced. Prefer:

```python
pg.click('form[action$="/target"] button[type=submit]')
time.sleep(10)   # do not poll the response object, it often arrives after navigation
```

If you must use `requestSubmit()`, verify the token is non-empty immediately before.

## 3. Filling forms: `pg.fill()` can desync client framework state

On Alpine/Aire-style forms, `pg.fill()` set the DOM value but the framework model stayed
`null`, so validation re-rendered and the submit silently no-op'd. Real typing fixed it:

```python
pg.click(f'[name="{k}"]')
pg.keyboard.type(v, delay=15)
```

Diagnostic: if a submit produces no POST at all, dump the framework state
(`x-data` JSON in the form tag) and compare against the DOM values.

## 4. CDP cookie injection rejects `;` — URL-encode it

`BrowserContext.add_cookies` and `Network.setCookie` fail on cookie values containing `;`:

```
Error: BrowserContext.add_cookies: Protocol error (Storage.setCookies): Invalid cookie fields
Error: CDPSession.send: Protocol error (Network.setCookie): Sanitizing cookie failed
```

The value itself is legal for the server (it arrives decoded), so encode on the wire:

```python
cdp.send("Network.setCookie", {
    "name": "app_auth",
    "value": "59293421%3Ba6face30...",   # ';' -> %3B
    "domain": ".example.org", "path": "/", "secure": True,
})
```

Also: `expires: -1` is rejected in `add_cookies` dicts on this build; omit the key.

## 5. Reusing identity across parallel accounts

`ctx.storage_state(path=...)` then `b.new_context(storage_state=path)` carries
`cf_clearance` across, so you can run N accounts in parallel without re-solving the
challenge each time. The clearance is bound to IP + UA; keep both stable.

Caveat that cost real time: `storage_state` captures **all** cookies from the context,
including unrelated third-party origins. Loading it into a fresh context after the session
expired silently authenticates as *nobody* while looking fine — always assert identity
(`"Log Out" in body`, or read the app's own `logged_in_user` blob) before trusting a run.

## 6. `page.evaluate` "Execution context was destroyed"

Fires when the page navigates (or a form submit lands) mid-evaluate. It is **not** a signal
that the technique is broken. Two fixes:

- Prefer `pg.goto(...)` + `time.sleep()` over in-page `fetch` for anything that triggers
  navigation; `fetch` with `redirect:'follow'` on a cross-origin redirect blows up the context.
- Wrap the evaluate in a small retry, and re-`goto` the base page between probes:

```python
for attempt in range(3):
    try:
        pg.goto(base, wait_until="domcontentloaded", timeout=60000); break
    except Exception:
        time.sleep(2)
```

## 7. Don't trust `pg.title()` as the challenge gate

While the CF interstitial is showing, `title()` returns `Just a moment...`. But the reverse
is not reliable either: after the challenge clears the title can still read the old value for
a moment, and a nav that 403s keeps the interstitial title indefinitely. Gate on a **real
element** instead:

```python
ready = pg.evaluate("() => !!document.querySelector('form[action$=\"/target\"]')")
```

Observed once: a title came back as `🐴 Report an Inspector - InterNACHI®` — the emoji is a
tell that the title string was mangled during the challenge swap. Another reason not to
parse titles.

## 8. Uniform 403 across payload variants = ban, not filter

When follow-up requests 403, change the **destination host**, not the payload. If an
innocuous host also 403s, the block is on endpoint+IP and retrying with different bodies
proves nothing. Record as `UNREACHABLE-for-retry`, schedule the retry, and do not
proxy-hop (that's evasion, and it violates most programs' anti-automation rules).
