# Para / Capsule email-OTP login — shadow DOM + OOPIF driving (Vana case, 2026-10)

Provider class: **wallet-as-a-service embedded login** (Para / Capsule; `app.usecapsule.com` portal +
`api.getpara.com` user-management API). The app (e.g. `app.vana.com`) embeds it as a custom-element
widget. No password is involved: email → 6-digit OTP → wallet creation → app session.

## Why it is not a normal login page

| Layer | Reality |
|---|---|
| Email field | inside a **shadow root** (`cpsl-*` custom elements); `document.querySelector('input')` shows only the cookie/terms checkbox |
| OTP step | renders in a **cross-origin OOPIF** (`app.usecapsule.com/auth/otp?...`) — not readable from the top page |
| Submit | no `<form>`, no button inside the input's root; it is a small icon button beside the field |
| State | authoritative state lives in **localStorage**, not in the DOM text |

## Step 0 — launch your own Chrome and drive it with raw CDP

If `browser_navigate`/the managed browser cannot reach the target (or Camofox is down), launch a real
(not headless) Chrome on the CDP port and use `browser_cdp` — but see the session-scoping trap below:

```bash
chrome.exe --remote-debugging-port=9222 --remote-allow-origins=* \
  --user-data-dir="/tmp/<eng>-chrome-profile" \
  --no-first-run --no-default-browser-check --disable-blink-features=AutomationControlled about:blank
curl -s http://127.0.0.1:9222/json/version     # verify, then drive via browser_cdp / CDP client
```

**Keep the profile you launch**: whatever session the operator completes in that window is readable by
you afterwards (cookies via `Network.getAllCookies`, storage via `Runtime.evaluate`). That is what makes a
human-handoff recoverable instead of a dead end.

## Step 1 — reveal the widget, then find the email input through shadow roots

`/login` may first bounce to a "download the app" page; click **Continue on web** to reach the real form.
Open the widget, then walk shadow roots (the field is 1 level deep):

```js
// find input by placeholder, walking shadow roots
let inp=null; (function f(r,d){ if(d>12||!r) return;
  try{ r.querySelectorAll('*').forEach(e=>{ if(inp) return;
    if(e.shadowRoot) f(e.shadowRoot,d+1);
    if(/^input$/i.test(e.tagName) && /email/i.test(e.placeholder||'')) inp=e; }); }catch(e){} })(document,0);
```

Fill it with the **native value setter** (React-controlled inputs ignore `el.value = x`):

```js
const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
set.call(inp, 'user+tag@gmail.com');
inp.dispatchEvent(new Event('input',{bubbles:true})); inp.dispatchEvent(new Event('change',{bubbles:true}));
```

## Step 2 — submit by COORDINATE, not by selector

There is no `<form>` and no button in the input's shadow root. Enumerate visible buttons with their
bounding boxes and click the small one immediately to the right of the field:

```js
// collect {x,y,w,h} for every visible button + the email input's own rect, then pick the 32x32
// icon button whose y overlaps the field and whose x is just past (field.x + field.width)
```

```jsonc
// then: browser_cdp Input.dispatchMouseEvent mousePressed + mouseReleased at the button centre
{"type":"mousePressed","button":"left","clickCount":1,"x":793,"y":220}
```

An `Enter` keyDown on the field sometimes works and sometimes silently does nothing — do not conclude the
flow is broken from one attempt; use the arrow click.

## Step 3 — read the OTP from the mailbox (operator mailbox case)

When the operator supplies their own address, use a **plus-alias** (`user+vana@gmail.com`): it tags the
account, lands in their inbox, and needs no disposable-inbox dance. With a stored OAuth token:

```python
TOK = pathlib.Path(os.path.expandvars(r"%LOCALAPPDATA%\hermes\google_token.json"))
d = urllib.parse.urlencode({"client_id":t["client_id"],"client_secret":t["client_secret"],
                            "refresh_token":t["refresh_token"],"grant_type":"refresh_token"}).encode()
at = json.load(urllib.request.urlopen(urllib.request.Request(
        "https://oauth2.googleapis.com/token", data=d), timeout=25))["access_token"]
lst = gmail("messages?maxResults=3&q=" + urllib.parse.quote('from:getpara.com newer_than:30m'))
```

Sender is `no-reply@getpara.com`, subject `NNNNNN is your Verification Code for <App>` — still **extract
the code by context**, not by the first 6 digits you see. Codes are single-use and short-lived
(~10 min); a second email step issues a NEW code and the old one dies.

## Step 4 — type the code into the OOPIF

The OTP iframe appears as its own CDP **target** (`Target.getTargets` → `type:"iframe"`, url contains
`auth/otp`). Route page-level CDP calls to it by passing that **iframe targetId as `target_id`** in
`browser_cdp` (the documented `frame_id` route needs the CDP *supervisor*, i.e. `browser_navigate`; it is
not available for a hand-launched Chrome).

```py
# per digit: one real key event; the widget auto-advances to the next box
cmd("Input.dispatchKeyEvent", {"type":"keyDown","key":"4","code":"Digit4","text":"4","windowsVirtualKeyCode":52},
    target_id=otp_iframe_target)
```

Traps:
- the iframe body can be **empty on first attach** and only render seconds later — poll
  (`count inputs every 3 s, up to ~30 s`) before declaring it broken;
- the 6 boxes are `input.code-input` inside **shadow roots**, so `querySelectorAll('input.code-input')`
  on the frame's document returns nothing — walk shadow roots;
- when the frame target **disappears**, the code was accepted (the flow advanced). Verify in
  localStorage instead of hunting for a success banner.

## Step 5 — read the authoritative state, not the UI

```js
localStorage.getItem('@PARA/modalState')     // {"state":{"step":"OTP" | "AUTH_MAIN" | "AWAITING_ACCOUNT", ...}}
localStorage.getItem('@CAPSULE/userId')      // Para/Capsule user id (uuid)
localStorage.getItem('@CAPSULE/sessionCookie')// capsule.sid=... (also mirrored into httpOnly cookie)
localStorage.getItem('@CAPSULE/wallets')     // {} until the wallet exists
```

`step:"AWAITING_ACCOUNT"` + `wallets:{}` = verified but **no wallet yet**; the app session is not issued.

## Step 6 — passkey steps: virtual authenticator, and the session-scoping trap

```py
cmd("WebAuthn.enable", {"enableUI": True}, target_id=page)
cmd("WebAuthn.addVirtualAuthenticator", {"options":{"protocol":"ctap2","transport":"internal",
    "hasResidentKey":True,"hasUserVerification":True,"isUserVerified":True,
    "automaticPresenceSimulation":True}}, target_id=page)
```

⚠️ `addVirtualAuthenticator` fails with *"The Virtual Authenticator Environment has not been enabled for
this session"* when `WebAuthn.enable` was sent in a **different** call — stateless per-call CDP loses the
virtual environment. Both commands must run inside **one persistent session**: connect a WebSocket to the
target's `webSocketDebuggerUrl` (from `http://127.0.0.1:9222/json`) and keep it open
(`websocket-client` is installed on this rig). Same connection lets you subscribe to
`Network.requestWillBeSent` and log the SDK's real calls.

## Step 7 — do NOT try to finish via the IdP's API (scope + 403)

Direct calls fail and are the wrong lane:

```
POST https://api.usecapsule.com/login/verify-email  -> 403 Forbidden   (needs portal-scoped flow headers)
POST https://api.getpara.com/v2/login/otp           -> 404 (v2 paths are not on this host)
POST https://api.getpara.com/login/verify-email     -> 403
```

The SDK does call `POST https://api.getpara.com/touch` — i.e. the user-management base is
`api.getpara.com` for this SDK version (`window.__paraApiBase` / `window.__paraOAuthBase` are readable
inside the iframe). Client config that lives in the iframe URL is **public by design**: `apiKey`
(`prod_…`), `partnerId`, per-session `encryptionKey` (RSA public key), and the header name the SDK sends
is `X-External-API-Key` (+ `x-partner-id`, `x-para-client-type`). Record it as intel, never as a finding.

**The IdP is a third party, not the target.** Restart your efforts on the app's own client flow rather
than probing `api.getpara.com`; if the wallet/MPC step still stalls, hand off (below).

## Step 8 — "STALLED" IS USUALLY NOT THE WALLET. CHECK FOR AN APPLICATION GATE FIRST.

**Correction from the same engagement (2026-10-12, found after this file was first written):** the flow was
NOT blocked at wallet creation. The wallet existed the whole time — the blocker was the application's own
**invite-only gate**. Do this diagnostic before any handoff or "blocked" report:

1. **Watch the SDK's own calls** (`Network.requestWillBeSent` on the persistent session). If you see:
   - `POST https://api.getpara.com/assets/balances {"wallets":[{"type":"EVM","address":"0x…"}]}` → **a wallet exists**
   - `POST https://api.getpara.com/auth/jwt {"keyIndex":0}` → **a JWT was minted**
   - `GET  https://api.getpara.com/users/supported-auth-methods/v2?email=…` → identity recognised
   then provisioning is **DONE**. `wallets:{}` in `@CAPSULE/wallets` only means the SDK has not refreshed
   that key in *this* tab — it is not evidence of failure.
2. **Read the app's post-login page text** (`document.body.innerText`). On app.vana.com it said, plainly:
   *"Vana is invite only (for now) — Enter your code or join the waitlist"* (their launch blog confirms
   invite-only onboarding with codes distributed via the community/Discord). Gates like this are **plain
   text**, not errors — nothing in the SDK logs will say "invite required".
3. **Dump cookies** (`Network.getAllCookies`). Only `cf_clearance` and no app session cookie = the app
   refused to issue a session because the gate was not passed. That — not the passkey/MPC step — is the wall.
4. Only after those three come back clean should you consider passkey/MPC, and only then hand off.

**Map the gate as its own surface while you are there** (it is in scope and cheap): on Vana the invite
validator answered a **uniform** `404 {"valid":false,"reason":"not_found"}` for random, empty and missing
codes → no validity oracle (good design, nothing to report). Five gentle probes showed no rate-limit
headers, which is **not** proof of absence — a rate-limit claim needs a bounded burst and must be labelled
as a rate-limit test, never as code guessing. Keep the request count tiny and say exactly what you did.

### Handing off when the wall is a gate (not a wallet)

The handoff below is still right when a gate stalls you — but name the blocker correctly, ask for the thing
that actually unblocks it (**a legitimately obtained invite code**), and do not report "wallet creation
blocked" as if it were a finding. If no code is available, record the authenticated plane as an explicit
coverage gap instead of shipping tests built on a half-session.

Hand off **in the Chrome YOU launched** — 30 seconds of clicks for the operator, and the resulting
session lands in a profile you can still read:

1. tell the operator which window/profile to use and the exact address to type;
2. they complete the wallet/passkey prompt (or paste the invite code) (you may still inject the OTP);
3. you harvest `Network.getAllCookies` + `localStorage` and run the authenticated suite.

Do not report the stall as a target finding, and do not silently burn another hour: state plainly
"verified at the IdP, blocked at <gate name>, handing <that step> to the operator".
