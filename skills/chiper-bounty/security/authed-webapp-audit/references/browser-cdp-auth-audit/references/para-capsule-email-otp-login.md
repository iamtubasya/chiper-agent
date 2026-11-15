# Para/Capsule email-OTP login driven headlessly (case study: app.vana.com, 2026-10)

Concrete recipe for the class "app delegates identity to a third-party embedded auth SDK whose form
lives in a cross-origin iframe". Copy the commands; swap the origins/selectors.

## Environment / prerequisites

- **Browser backend.** `browser_navigate` may route to Camofox (REST on `:9377`). If that server is not
  up, either start it (`cd ~/camofox-browser && node server.js`, then it answers on
  `http://localhost:9377/health`) or launch real Chrome and use `browser_cdp`:
  ```bash
  "/c/Program Files/Google/Chrome/Application/chrome.exe" --remote-debugging-port=9222 \
    --remote-allow-origins=* --user-data-dir="…/Temp/vendor-chrome-profile" \
    --no-first-run --no-default-browser-check --disable-blink-features=AutomationControlled about:blank
  ```
  Verify: `curl -s http://127.0.0.1:9222/json/version`. Then `browser_cdp Target.getTargets` works.
- **Mailbox.** Gmail API refresh-token file at `%LOCALAPPDATA%\hermes\google_token.json`
  (`client_id`, `client_secret`, `refresh_token`). Test identity = plus-alias of the operator's address.

## Step 1 — reach the real login page

`app.vana.com/login` 302s to `/get` ("Download the Vana App … Continue on web"). Click the button whose
text matches `/continue on web/i`, wait ~3 s, and you land on
`/login?callbackUrl=%2F` with a "Login / Signup" button plus an `input#terms` checkbox.

```js
const cb=document.querySelector('input#terms'); if(cb&&!cb.checked) cb.click();
[...document.querySelectorAll('button')].find(x=>/login \/ signup/i.test(x.innerText)).click();
```

The SDK modal renders into **shadow DOM** (`cpsl-text`, `cpsl-code-input`, `cpsl-icon`), so
`document.querySelectorAll('button')` shows almost nothing. Walk shadow roots:

```js
const ins=[]; (function w(r,d){ if(d>10||!r) return;
  try{ r.querySelectorAll('input').forEach(e=>ins.push(e));
       r.querySelectorAll('*').forEach(e=>{ if(e.shadowRoot) w(e.shadowRoot,d+1); }); }catch(e){} })(document,0);
// step 1 shows: input[type=checkbox]#terms
// email step shows: input[placeholder="Enter email"] (later "Enter email or phone")
```

## Step 2 — submit the email, without touching React's tracker

```js
const set=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
set.call(inp,'operator+vendor@gmail.com');
inp.dispatchEvent(new Event('input',{bubbles:true}));
inp.dispatchEvent(new Event('change',{bubbles:true}));
```
Then focus it and send a REAL Enter (`Input.dispatchKeyEvent {type:'keyDown', key:'Enter',
code:'Enter', text:'\r', windowsVirtualKeyCode:13}`). `insertText` alone left the form idle.

## Step 3 — the OTP form is a separate OOPIF target

`Target.getTargets` right after the Enter shows:

```
{"type":"iframe","targetId":"F29F…","url":"https://app.usecapsule.com/auth/otp?apiKey=prod_…&origin=https%3A%2F%2Fapp.vana.com&partnerId=…&portalFont=…&authInfo=…&email=…&userId=490c100d-…&sessionId=…&encryptionKey=<hex of a PEM RSA public key>&pregenIds=%7B%7D&isBasicLoginUpgradeVersion=true"}
```

- `apiKey` / `partnerId` / `encryptionKey` = public client config (they MUST be in the browser). Useful
  for driving the vendor API directly later; never report as a leak.
- Drive the frame with `browser_cdp` and **`target_id = the iframe's targetId`** (this is the routing
  that works without an attached CDP supervisor; `frame_id=` returns
  "No CDP supervisor is attached… call browser_navigate or /browser connect first").
- Inside it: body = `Verify Email / Please enter the code we sent to <email>`, and six
  `input.code-input` elements inside shadow roots (`querySelectorAll('input.code-input')` in the frame's
  top document finds none — that is the tell that they are shadow-scoped).

## Step 4 — pull the code from the mailbox, then type it

```python
q = "from:getpara.com newer_than:30m"          # subject: "445867 is your Verification Code for Vana App"
lst = g(f"messages?maxResults=3&q={urllib.parse.quote(q)}")
full = g(f"messages/{lst['messages'][0]['id']}?format=full")   # walk parts[].body.data, base64url
code = re.search(r"\b(\d{6})\b", decoded_body).group(1)
```

```js
// focus first box, inside the shadow walk
ins[0].focus();
```
```text
Input.dispatchKeyEvent {type:'keyDown', key:'4', code:'Digit4', text:'4', windowsVirtualKeyCode:52}   # ×6, in order
```
Read back after each batch (`ins.map(i=>i.value)`) — focus auto-advances, wrong order = wrong code.

## Step 5 — read the SDK state machine, expect `AWAITING_ACCOUNT`

`localStorage` keys to watch: `@PARA/modalState`, `@PARA/provider-state`, `@CAPSULE/authInfo`,
`@CAPSULE/userId`, `@CAPSULE/sessionCookie`, `@CAPSULE/wallets`.

Observed progression (and what each means):

| modalState.step | meaning | evidence |
|---|---|---|
| `OTP` | code sent, waiting | `authState:{auth:{email},stage:"verify",nextStage:"signup"}` |
| `AWAITING_ACCOUNT` | code accepted, SDK is creating the MPC wallet | UI "Sign Up / Creating your account…", `@CAPSULE/userId` set, `wallets:{}` |
| `AUTH_MAIN` (after reload) | flow restarted, wallet never finished | `@CAPSULE/wallets` still `{}` |

After a successful code submit the iframe target **disappears** and later CDP calls to it fail with
`Target.attachToTarget failed … No target with given id found` — that is success, not an error.

## Step 6 — when the wallet step stalls

A verified identity without a wallet yields **no app session**: `Page.navigate` to `/` redirects back to
`/login`. Re-entering the email only re-sends a code. Options, in order:

1. Operator-assisted: have the operator finish the wallet/onboarding once in a browser profile you can
   read (`--user-data-dir` you can copy, or a profile you already drive), then lift the cookies
   (`Network.getAllCookies` on the browser-level socket) and run the whole authenticated suite from
   curl/python.
2. Vendor API: use the captured `apiKey` + `sessionId` + `@CAPSULE/sessionCookie` to drive
   `app.usecapsule.com`'s own endpoints from a script.
3. Report the blocker honestly: "identity verified (userId …), wallet/onboarding did not complete under
   automation → authenticated surface untested", never as a negative about the target.

## Reusable one-liners

- list frames as targets: `Target.getTargets` → filter `type=='iframe'` (their URL carries the SDK config)
- re-read the modal step: `JSON.parse(localStorage.getItem('@PARA/modalState')).state.step`
- find a shadow input by placeholder: walk shadow roots, match `e.placeholder`
