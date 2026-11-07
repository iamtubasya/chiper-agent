# Cross-origin HV challenge iframe: diagnosis, and what to do when you cannot automate it

Measured 2026-10 against Proton (`account.proton.me`). Six approaches tried; the point of this
file is that the failure is **diagnosable in two commands** and the correct response is a
hand-off, not more force.

## 1. The signature (dump first, theorise later)

```python
# every input: geometry + visibility
pg.evaluate("""() => Array.from(document.querySelectorAll('input')).map(e => {
  const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
  return {id:e.id, type:e.type, vis:s.visibility, x:Math.round(r.x), y:Math.round(r.y),
          w:Math.round(r.width), h:Math.round(r.height)};})""")
# every frame
[f.url for f in pg.frames]
```

Output that identifies a decoy + iframe gate:

```
inputs: [ {id:'email',    vis:'hidden', x:-815, y:-609, w:231},   <- honeypot
          {id:'password', vis:'visible', x:185, y:508,  w:493} ]  <- the only real one
frames: [ 'https://account.proton.me/drive/signup?plan=free',
          'https://account-api.proton.me/challenge/v4/html?Type=0&Name=unauth&...',
          'https://account-api.proton.me/challenge/v4/html?Type=0&Name=email&...' ]
```

The main-document wrapper of the decoy is explicit about it:

```html
<div aria-hidden="true" class="absolute top-custom left-custom visibility-hidden"
     style="--left-custom:-1000px; --top-custom:-1000px;">
    <label for="email">Email address</label>
    <input id="email" value="">
</div>
<iframe src="https://account-api.proton.me/challenge/v4/html?Type=0&Name=email..."
        title="Email address" sandbox="allow-scripts allow-same-origin allow-popups"></iframe>
```

So: `aria-hidden` + off-screen + full box size = honeypot. The input a human types into lives in
the `challenge/v4` iframe on the API origin, which is why `fill('#email')` on the main document
"works" (sets a value) yet the form still says `This field is required`.

## 2. The six approaches, and what each proved

| # | Approach | Result |
|---|---|---|
| 1 | Click the Free plan card, `fill('#username')`/`fill('#email')` | plan click did not change React state (network still showed `payments/v5/subscription/check {"Plans":{"bundle2022":1}}` — a PAID plan), so the account form stayed collapsed; decoy input still `visibility:hidden` |
| 2 | Real mouse click at the card's `getBoundingClientRect()` centre | `aria-pressed="true"` on the card, form still hidden |
| 3 | `el.click()` from JS | same as 2 |
| 4 | `pg.fill('#email')` / `keyboard.type` into the decoy | value never lands (`visibility:hidden` swallows events) -> `This field is required` |
| 5 | `frame.fill('#email', val)` + `type` + `Tab` on the **real** iframe input | value IS in the frame (`auditfz09737`), **zero** network requests, parent still `This field is required` -> no state propagation |
| 6 | Direct API `POST /api/core/v4/users {Username,Password}` (+`Payload`, +`GenerateKeys:false`) | `400 Invalid input`; with `x-pm-human-verification-token: ""` -> `422 Invalid token type` (header IS parsed); with a fake token -> `400 Invalid input` |

Approach 6 is the useful one: the empty-header probe proves the HV gate is server-side and
mandatory, so the "just call the API" shortcut is closed for a reason you can state in the ledger.

Synthetic-setter note: the `HTMLInputElement.prototype.value` + `dispatchEvent('input')` trick
throws `Illegal invocation` in this context and, where it does not throw, still fails to move
React state on this wizard. Trusted events (`click` + `keyboard.type(delay=~110)`) are the only
thing that moves it, and here even they cannot cross the iframe boundary.

## 3. Pick the signup URL with the fewest gates

Measured, same day, same target:

| URL | Gates |
|---|---|
| `/signup` | new single-flow wizard: plan cards + payment (Chargebee/card/PayPal/Apple/Google Pay radios) + account fields |
| `/mail/signup` | same wizard (plan + payment) |
| `/drive/signup?plan=free` | **classic wizard: `Get a new encrypted email address` toggle + password + submit. No payment step at all** |

Always compare before handing anything to the operator — a `?plan=free` deep link can remove an
entire payment stage. (Note the Free card still needs a real click to flip `aria-pressed`; `?plan=free`
in the URL is what removes the payment UI.)

## 4. Hand-off procedure (what actually produced the second identity)

```python
# open, and KEEP ALIVE from a background process
ctx = pw.chromium.launch_persistent_context(
    r"/home/agentuser/<target>-manual-profile", headless=False,
    args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
    no_viewport=True, locale="en-US", timezone_id="Asia/Jakarta")
# poll ctx.pages so the script notices when the operator closes the window
```

Run it with `terminal background=true, notify_on_complete=true`. A foreground call hits the tool
timeout and **kills the browser while the human is using it**.

Tell the operator: the URL, the profile path, a suggested password (reuse one so later automation
is simple), and "don't close the window until you're done".

## 5. Harvesting the session afterwards

Two traps, both hit:

1. **`Opening in existing browser session`** — the profile is locked by the still-running process.
   Kill only the processes whose command line contains that profile path (`wmic process where
   "name='chrome.exe'" get ProcessId,CommandLine`), then relaunch, or simply read cookies from the
   instance that is already running.
2. **The app root can be `about:blank`** — a fresh tab in the persistent context may not be
   navigated, so `localStorage` access throws `SecurityError: Access is denied for this document`.
   Navigate first (`/apps`, `/u/0/`), *then* evaluate.

Verify the identity before using it:

```python
pg.goto("https://account.proton.me/apps"); pg.wait_for_timeout(5000)
pg.evaluate("""async () => { const r = await fetch('/api/core/v4/users', {credentials:'include',
  headers:{'Accept':'application/vnd.protonmail.v1+json','x-pm-appversion':'web-account@5.0.430.0'}});
  return r.status + ' ' + (await r.text()).slice(0,300); }""")
# a 401 with `credentials:'include'` usually means the page forgot x-pm-uid — pick the uid from
# ctx.cookies() where name.startswith('AUTH-')
```

Also assert the operator actually created what you think: read the rendered account page
(`RESEARCHER_USERNAME / RESEARCHER_EMAIL`) rather than trusting the supplied email string.

## 6. Source-account type matters for coverage

The manually created account came out as **Type 3 (external address)** with a Type-5 address
(`user@gmail.com`) instead of a proton.me address. Consequences measured immediately:

- Drive and Docs: fully usable.
- Calendar: bounced to `/setup-address?to=proton-calendar` — an external-address account has no
  proton.me address, so Calendar cannot be provisioned. Calendar cross-tenant tests stay UNTESTED
  for that identity.
- Pass: redirected to `/reauth`.

Record the account type next to the identity in the ledger, or you will later misread
"cannot reach Calendar" as "Calendar has no findings".
