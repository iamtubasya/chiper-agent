---
name: browser-cdp-auth-audit
description: Use when auditing authenticated web apps via browser CDP.
version: 1.0.0
author: RESEARCHER_NAME
license: MIT
metadata:
  hermes:
    tags: [security, bug-bounty, cdp, browser, auth, idor, csrf, nextjs]
    related_skills: [bb-methodology, hunt-idor, hunt-oauth, bug-bounty]
---

# Browser CDP Authenticated Webapp Audit

Real-browser methodology for auditing auth-heavy web apps where curl/urllib fails or
where access-control must be proven across two accounts. Primary case study: Next.js
App Router with Server Actions (quarterwise.co.uk, 2026-09) — patterns generalize to
any SPA/SSR app with client-populated form state.

## When to use
- Signup/login/forgot/change-password flows that return 500 from plain HTTP clients
- Multi-account cross-tenant IDOR/BOLA proof (need isolated cookie jars)
- OTP/email-verification flows (need temp inbox + code extraction)
- Server-action based state changes (CSRF, object-ID swap, role tamper)
- "No finding" pushback → re-attack with the deep-dive checklist below

## Core setup: two Chrome debug profiles (isolated cookie jars)
One profile per account, each on its own port so HttpOnly sessions never mix:

```bash
chrome.exe --remote-debugging-port=9222 --remote-allow-origins=* \
  --user-data-dir=".../Temp/qw-chrome-debug"  --no-first-run --no-default-browser-check about:blank
chrome.exe --remote-debugging-port=9223 --remote-allow-origins=* \
  --user-data-dir=".../Temp/qw-chrome-debug2" --no-first-run --no-default-browser-check about:blank
```

- `--remote-allow-origins=*` is REQUIRED for external WS clients
  (python `websocket-client`); without it Chrome 131+ rejects handshake 403
  (`WebSocketBadStatusException: Handshake status 403 Forbidden … Rejected an incoming WebSocket
  connection from the http://localhost:9222 origin`). The flag must be on the Chrome YOU launched —
  if you inherited an already-running Chrome you cannot add it; relaunch on a scratch
  `--user-data-dir`.
- **`GET /json/new?<url>` returns `405 Method Not Allowed` on Chrome 131+ — open a tab with `PUT`.**
  Every other `/json/*` endpoint (`/json`, `/json/list`, `/json/version`) is GET; `/json/new` is the
  odd one out, so a helper written the obvious way dies before it does any work:
  ```python
  def http(path, method="GET"):
      req = urllib.request.Request("http://localhost:9222" + path, method=method)
      return json.load(urllib.request.urlopen(req))
  tab = http("/json/new?" + urllib.parse.quote(url, safe=""), method="PUT")
  ```
  Sanity-check the port first with `curl -s localhost:9222/json/version`: an *empty* `/json/list`
  alongside a live `/json/version` means Chrome is up but has no page target yet — and a port that
  answers neither means the CDP Chrome has exited (it is not a target problem, relaunch it).
- Kill stale debug Chrome with `powershell Stop-Process -Id <pid> -Force` — MSYS
  does NOT convert `taskkill //F` here; wmic/taskkill `//F` forms fail.
- **The debug Chrome can self-terminate mid-engagement** with
  `crashpad_client_win.cc(188) crash server did not respond, self-terminating` (observed twice on a
  long Tripadvisor session; the CDP port then refuses connections while other Chrome processes still
  run). Relaunch with `--disable-crash-reporter --disable-breakpad --noerrdialogs` added to the normal
  flags. Two consequences to handle: the profile dir keeps cookies so you do NOT need to re-login, but
  **the page `targetId` changes on every relaunch** — always re-run `Target.getTargets` and take the
  fresh id instead of reusing the one from earlier in the session (a stale id fails with
  `Target.attachToTarget failed … No target with given id found`).
- Cookies persist in the profile dir across restarts; a browser restart does NOT
  lose the session (only tab state). Relogin only when redirected to /login.
- **Need a logged-OUT view without a second Chrome process? `Target.createBrowserContext` + `Target.createTarget`.**
  A fresh browser context has its own cookie jar inside the SAME Chrome, so the main profile stays
  authenticated while you exercise login/forgot-password/reset as an anonymous visitor:
  ```
  Target.createBrowserContext {}                        → {browserContextId: "A641…"}
  Target.createTarget {browserContextId, url:"about:blank"} → {targetId: "EE0E…"}
  Page.navigate {url:"…/RegistrationController?flow=sign_up_and_save"}   (target_id = the NEW id)
  ```
  Two things that bite: (1) the new targetId is what you must pass to every later `Page.*`/`Runtime.*`
  call — the old (logged-in) target is untouched and still holds the session; (2) if you are already
  logged in on the main profile, hitting a login/registration URL there just 302s you to `/`, which
  looks like "the page is gone". It isn't — you were authenticated. Drop to the isolated context.
  (Cheaper than the two-profile setup when you only need a throwaway anonymous jar; use two profiles
  when you need two *authenticated* identities at once.)
- **Driving from Hermes: reach for the built-in `browser_cdp` tool when it is present.** If the
  built-in `browser_navigate`/`browser_*` tools route to a *different* backend (e.g. Camofox) while
  `browser.cdp_url` is set to your debug Chrome (`ws://localhost:9222`), don't fight them — call the
  CDP methods yourself: `Target.getTargets` → take the `page` targetId → then `Page.navigate`,
  `Runtime.evaluate`, `Input.insertText`, `Input.dispatchMouseEvent` all accept that `target_id`.
  No python websocket needed for one-off steps; drop to `scripts/cdp.py` for long multi-step flows.

## Python CDP driver essentials (websocket-client)
```python
d = json.load(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json', timeout=10))
pages = [t for t in d if t['type']=='page' and 'quarterwise' in t.get('url','')]
ws = websocket.create_connection(pages[0]['webSocketDebuggerUrl'], timeout=40,
                                 header=["Origin: http://localhost"])
# cmd(): send {id,method,params}, loop recv until id matches, buffer Network.requestWillBeSent
# js():  Runtime.evaluate {expression, returnByValue:True, awaitPromise:True}
```
Key calls:
- `Network.getAllCookies` → HttpOnly cookie values (document.cookie can't see them) →
  cookie header for curl-based API checks. **Browser-scoped: send it on the browser-level
  websocket (`/json/version`), not on a page target** — and filter the returned list by
  `domain` yourself, since it spans every profile host. Dump it to a JSON file in the
  engagement dir and replay the cookie with `urllib`/`requests` (add a plausible
  `User-Agent`: some apps answer 307 to a header-less client). This is the fast loop —
  export the session once, then do all API probing in Python instead of driving the UI.
  Note the flip side seen this session: a cookie value pulled out of the *cookie database*
  (rather than the live browser) can come back as non-printable bytes even though the GCM
  tag validated — read cookies from the running browser, never from the encrypted store.
- `Network.getRequestPostData` with requestId → **full multipart/JSON body**
  (postData inside requestWillBeSent is TRUNCATED in Chrome)
- `Page.navigate` / `Page.reload` + sleep, then `Runtime.evaluate` DOM reads
- `Network.clearBrowserCookies` before a fresh-login verification test

## CAPTCHA / Turnstile-gated flows: route to real Chrome
Signal: the submit button stays `disabled` and there is a hidden
`input[name="cf-turnstile-response"]` (or a `challenges.cloudflare.com/turnstile/v0/api.js` script).
Diagnose in one evaluate:
```js
JSON.stringify({t: typeof window.turnstile, tok:(document.querySelector('input[name=cf-turnstile-response]')||{}).value,
                iframe:[...document.querySelectorAll('iframe')].map(f=>f.src.slice(0,60)),
                btn:[...document.querySelectorAll('button')].find(b=>/Continue/i.test(b.innerText))?.disabled})
```
- `window.turnstile === "object"` + a ~700-char token + button enabled ⇒ the widget solved (real Chrome).
- `typeof window.turnstile === "undefined"`, no challenge iframe, button stuck disabled ⇒ this browser
  backend will never pass the gate. **Do not fight it — run real Chrome over CDP** (the two-profile
  setup above). Managed Turnstile issues its token silently in real Chrome for a normal profile;
  no clicking required.
- Re-check the token before submitting: it expires. Read it right before the click.
- **A Turnstile/reCAPTCHA token is ONE-SHOT PER PAGE INSTANCE — reload between attempts.** After the
  first submit, the widget's token is spent, but the token value sitting in the hidden input still
  looks fresh. Re-reading it and submitting again fails with
  `ERROR_CLOUDFLARE_CAPTCHA_VALIDATION_FAILED` even though the value is only seconds old, which reads
  like a credential/proxy problem and sends you chasing the wrong thing. Reliable loop:
  `Network.setCacheDisabled {cacheDisabled:true}` → `Page.navigate` to the login page → poll
  `input[name="cf-turnstile-response"].value.length > 20` → submit **once**. One page load = one attempt.
- **Read the token through the widget's field, but send it under the app's field name.** On Rapyd the
  DOM field is `cf-turnstile-response` / `g-recaptcha-response` while the API body field is
  `recaptcha_token` — a replay that uses the DOM name silently fails validation. Get the wire name
  from `Network.requestWillBeSent.postData` on the app's own submit (see "Capturing the app's own
  API calls" below) instead of guessing.
- **Testing the gate itself (anti-automation finding class).** Once you can drive the widget, grab one
  real token and POST the same request twice/thrice: identical token accepted repeatedly (while a
  garbage token and no token still fail) = the server does not enforce single-use → captcha replay.
  Also try the same token against a *different* endpoint (bound-to-endpoint = not reusable there).
  Only claim what you proved: a replayable token still requires one valid solve, so pair it with the
  server's lockout behaviour before proposing severity. If a per-IP/per-account lockout still caps the
  attempts (watch for a `…MAX_LOGIN_ATTEMPTS` style error), the honest rating is P4/P5
  "insufficient anti-automation" — not credential-stuffing bypass. Say which half you verified and
  which you could not (e.g. no second egress to test IP-binding).

## Signup forms with a server-side time token: the "valid timestamp" wall

Observed on lecturio.com registration (2026-10). The form looks fully replayable — visible
`firstName`/`lastName`, per-render hashed names for email/password, a `registration[_csrf_token]`,
and **empty** hidden `authorization`/`user` fields (empty = NOT an invite gate, despite the shape
suggesting one) — yet every submit re-renders the form with `Please provide a valid timestamp!` and
**no confirmation email is ever sent** (verify that: an absent expected mail is a signal, and the
whole registration is a no-op without it).

Diagnostic order that settles it in three steps:

1. **`Network.enable` + submit, then read what actually went out.** If **no POST to the registration
   URL appears at all**, the submit button is client-validated and never fired — the only captured
   traffic will be pixels/analytics (`analytics.tiktok.com`, `tr.snapchat.com`,
   `pagead2.googlesyndication.com`, vendor telemetry). Do not read that as "the POST failed"; the
   request was never made.
2. **POST the form yourself from inside the page** (cookies + CSRF come along):
   `fetch(f.action,{method:'POST',body:new URLSearchParams(fd),credentials:'include'})`. A `200` that
   echoes the form **plus** the error string is the server rejecting a value the real client injects.
3. **Confirm the token is not derivable.** Grep the DOM *and* the site's shipped JS bundle for
   `timestamp` — jQuery's `event.timeStamp` hits are noise. If nothing signs a time value anywhere
   you can read, the token is minted in code you cannot see and form replay is a dead end.

**Rule:** a signed/opaque anti-bot value absent from both the DOM and the bundle means the form path
cannot be driven from outside the real UI. Stop replaying it and pivot to the **SSO buttons on the
same page** (`CONTINUE WITH GOOGLE / APPLE / FACEBOOK`) — OAuth/SSO completes on different endpoints
that do not carry the form's anti-bot fields. If SSO is unavailable too, that authenticated surface
is an **untested area** — say exactly that; never report the wall itself as a finding.

**Hashed field names rotate per page load.** Resolve them from the live DOM in the *same* call that
fills and submits (`[...f.querySelectorAll('input')].filter(i=>i.type==='email')[0].name`), never
hardcode a name read from an earlier render — a stale hashed name posts a field the server ignores,
and the symptom is a silently re-rendered form. Same trap for the CSRF/LUD values.

## The SAME anti-bot shape, but DEFEATABLE: Laravel/Livewire honeypot + self-contained signed field

Do **not** generalize the lecturio wall into "signed anti-bot fields are unbeatable". A very common
Laravel pattern (observed on ohdear.app `/register`, 2026-10) looks identical — a per-render hashed
field, a hidden signed-looking token, a CSRF — and is trivially open, because the signature ships
**inside the field value** and the server only checks `now - issued_at < N minutes`.

Read the three fields and decide in ONE evaluate:

```js
[...f.querySelectorAll('input')].map(i=>({n:i.name,t:i.type,v:(i.value||'').slice(0,60)}))
// ohdear /register →
//   _token                              hidden  "sJbIeI2W…"              <- Laravel CSRF (reusable as-is)
//   my_name_DnsbCFbbfg4tjs6c            text    ""                       <- HONEYPOT (random suffix, must stay EMPTY)
//   valid_from                          text    "eyJpdi...djUw"          <- signed token, ALREADY IN THE DOM
//   name / email / password            ...
```

Decision rule — the discriminator is **who fills the value**, not what the field looks like:

| observation | verdict |
|---|---|
| hidden/signed value already **populated in the DOM** at render | **send it back verbatim** — it is a form-time attestation, not a challenge |
| value is **empty** and nothing in the DOM or the shipped JS bundle writes it (`grep timestamp|valid_from` → only `event.timeStamp` noise) | lecturio case: minted out-of-band → wall, pivot to SSO |
| a field whose name carries a **random suffix** (`my_name_<rand>`) AND is absent from `body.innerText` | **honeypot — leave it empty.** Any value marks you a bot |

Fill + submit in ONE expression so a re-render cannot invalidate the token, and skip the honeypot
explicitly (`if (/^my_name_/.test(i.name)) return;`). Reuse the React-native-setter recipe above for
the value (it works on plain forms too, and fires the listeners Livewire binds to):

```js
const set=(el,v)=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el,v);
  ['input','change','keyup','blur'].forEach(t=>el.dispatchEvent(new Event(t,{bubbles:true})));};
[...f.querySelectorAll('input')].forEach(i=>{ const n=i.name||'';
  if(/^my_name_/.test(n)) return;                     // honeypot: never touch
  if(n==='name') set(i,'Test User');
  else if(i.type==='email') set(i,EMAIL);
  else if(i.type==='password') set(i,PW); });
[...document.querySelectorAll('button')].find(b=>/create account/i.test(b.innerText)).click();
```

Success signal = **a redirect away from the form** (`/email/verify`, `/app`, `/onboarding`) — NOT the
presence of a success banner. A re-rendered form with a validation string means the wall is real after
all; fall back to the SSO buttons (previous section).

Then finish the loop: verification mail usually **does** arrive here (unlike lecturio), so pull the
signed link from the operator's Gmail and `Page.navigate` it:

```python
# q='to:<operator>+<tag>@gmail.com newer_than:1h' → messages/{id}?format=full
real=[c for c in re.findall(r'https://<host>/[^\s"<>\'\)\]]+', body)
      if not re.search(r'\.(woff2?|css|js|png|jpg|svg|ico)(\?|$)', c) and '/assets/' not in c]
# → /email/verify/<uid>/<hash>?expires=&signature=…   ← navigate THAT, then re-check location.href
```

## Livewire apps: state lives in the component, not in the <form>

Laravel + Livewire renders **no useful form** for actions — the `<form>` carries `wire:submit="<method>"`
and `method="get"`, so scraping `form.action` tells you nothing. Two consequences:

1. **Enumerate the components to learn the real action surface:**
   ```js
   [...document.querySelectorAll('[wire\\:id]')]
     .map(e=>({id:e.getAttribute('wire:id'),
               name:JSON.parse(e.getAttribute('wire:snapshot')).memo.name,
               submit:[...e.querySelectorAll('[wire\\:submit]')].map(x=>x.getAttribute('wire:submit'))}))
   ```
   On ohdear `/user/api-tokens` this yielded `api-token-manager`, `delete-monitor`, `delete-status-page`,
   `rate-us-at` — the real operations, none of which had a URL.
2. **Drive them with the native-setter + `click()`, not with a form POST.** Setting `wire:model`-bound
   inputs and clicking the submit button works because Livewire round-trips over its own
   `/livewire/update` XHR; a hand-built `fetch(form.action, …)` will not. Then read the mutation's
   result from the DOM (a modal/toast), because there is no HTTP response body to inspect.

**Self-service API-token creation is the cheapest way onto a JSON API surface.** Creating one costs
three DOM actions (`set name → click CREATE → read the revealed value`) and immediately converts an
HTML-only engagement into a scriptable one. Grab the revealed value from the textbox and note that it
is **shown once**:
```js
[...document.querySelectorAll('input,textarea')].map(i=>({n:i.name,v:(i.value||'').slice(0,60)}))
// → [{name:'name',…},{name:'can_use_entire_api',v:'1'},{v:'C9nFTadn…d8'}]  <- the token
```
Scope flag to record: `can_use_entire_api` — note the token's blast radius in the engagement log.
Do this **before** any read/write API probing: without a token every `/api/*` route answers
`401 {"error":"Unauthenticated."}` (cookie sessions are NOT accepted on the API — see the reference).

## Attribute a blocked request to the right LAYER before concluding anything

`www.<target>` refused **every** POST with a CDN error page while `app.<target>` (different hostname,
nginx) accepted POST and answered a JSON `404`. One app, two layers, opposite-looking conclusions.
The response body names the layer that spoke:

- `This distribution is not configured to allow the HTTP request method that was used … supports only
  cachable requests` = **CDN method policy** (CloudFront). The CDN is not the origin and says nothing
  about it. Find the real app host from the login page's own references — `<script src>` paths, an
  `assets-cdnN.` host, or an API path echoed in the page HTML (`/api/<lang>/latest/html5/…`).
- A `403`/`405` **carrying the app's own JSON envelope** (`{"error":{"code":"404","message":"Not
  Found"}}`) = the ORIGIN answered; the path is just wrong. Path enumeration against this host is how
  you map the API surface.

**Classify the block with ONE egress test, not a loop.** Re-run the exact blocked request after
switching egress (e.g. `warp-cli connect`, then confirm with an IP echo). Identical result ⇒ the block
is method/header-based, **not** IP-based, so changing IPs will never help — stop and change *path or
host* instead. Different result ⇒ it was IP reputation and the egress change was the fix. Either way
you now hold a verified control, and you have spent one request instead of an afternoon.

## IdP SSO widgets that never initialise (Okta SIW) — take the session from the operator

Program portals often delegate login to a hosted IdP. Case: `bugcrowd.com/user/sign_in` →
`login.hackers.bugcrowd.com/oauth2/default/v1/authorize?...client_id=…&redirect_uri=…` (Okta OAuth).

Observed 2026-10: `okta-sign-in-widget/7.49.0` **loaded**, `document.readyState` was `complete`, body
HTML was ~26 KB — and `#okta-login-container` still had **0 children** with `innerText` empty. No form,
no error, no captcha iframe. The same URL renders normally in the operator's own Chrome.

One-line probe (costs nothing, run it before deciding):

```js
document.title + '::' + (document.getElementById('okta-login-container')||{}).children.length
// → "Bugcrowd - Sign In::0"  ⇒ never initialised
```

Rules so this cannot eat a session:

- **Budget ONE reload, then stop.** Retry once with a longer wait; if the container is still empty, treat
  it as an environment/rendering problem. It is **not** a finding about the target and **not** evidence
  that the app is broken — do not write it up as anything.
- **Fallback that always works: operator-assisted login.** Ask the operator to sign in by hand **in the
  same `--user-data-dir` profile you are driving**, then take over. Cookies persist in the profile dir,
  so the session survives your `Target.getTargets` → `Page.navigate` and you never need the credential.
  This is the same "don't fight the gate" call the Turnstile section makes above.
- **Ask once, early — for the DATA, not just the login.** If what you actually need is program-scoped
  material (test-entity links, the brief's scope clause), having the operator paste it is faster than any
  login automation and it unblocks the audit immediately. A whole planning cycle went into trying to
  reach a scope detail that a one-line paste would have settled.
- Keep the distinction explicit in your reporting: "could not authenticate (IdP widget does not render
  under automation)" is an *untested* area, never a negative result about the target.

## Third-party auth widgets in cross-origin iframes (Para/Capsule, email-OTP SDKs)

Some apps delegate the whole identity layer to an embedded SDK (Para/Capsule `app.usecapsule.com`,
Privy, Dynamic). Case: `app.vana.com` login → Para/Capsule email OTP (2026-10). The form is NOT in the
parent DOM — it is a cross-origin **OOPIF**, so the parent page cannot read or fill it.

1. **Find the widget as its own target.** `Target.getTargets` lists it as
   `{"type":"iframe","url":"https://app.usecapsule.com/auth/otp?apiKey=prod_…&partnerId=…&userId=…&sessionId=…&encryptionKey=…"}`.
   The query string is the SDK's whole config (apiKey/partnerId/encryptionKey are PUBLIC client values —
   useful intel, never a credential finding). Page content is not a finding either.
2. **Drive it by passing that iframe's `targetId` as `target_id`** to `browser_cdp` — plain
   `Runtime.evaluate` / `Input.*` work inside the frame even though the parent is cross-origin.
   `frame_id` routing needs an attached CDP supervisor; `target_id` does not. Cheap discovery loop:
   `Runtime.evaluate` inside the frame → `{url, body, inputs, buttons}`; the OTP page text reads
   "Verify Email / Please enter the code we sent to <email>".
3. **`document.querySelectorAll('input')` returns nothing — walk shadow roots.** Widget UIs use
   `cpsl-*` custom elements with per-digit inputs inside shadow DOM:
   ```js
   const ins=[]; (function w(r,d){ if(d>10||!r) return;
     try{ r.querySelectorAll('input').forEach(e=>ins.push(e));
          r.querySelectorAll('*').forEach(e=>{ if(e.shadowRoot) w(e.shadowRoot,d+1); }); }catch(e){} })(document,0);
   ins[0].focus();
   ```
4. **Type the code with real per-digit key events** — the widget advances focus per box, so one
   `insertText` does not work. One call per digit:
   `Input.dispatchKeyEvent {type:'keyDown', key:'4', code:'Digit4', text:'4', windowsVirtualKeyCode:52}`
   then read back `ins.map(i=>i.value)` to confirm. **Get the digit order right** — an OTP box is not
   forgiving and a re-send burns the old code.
5. **Reading the OTP without a temp-inbox service.** If the operator's own mailbox is the recipient,
   use a Gmail API token (`%LOCALAPPDATA%\hermes\google_token.json`, refresh-token flow) — no third-party
   inbox needed:
   `GET /gmail/v1/users/me/messages?q=from:getpara.com newer_than:30m` → `messages/{id}?format=full` →
   base64url-decode `payload.parts[].body.data` → `re.search(r"\b(\d{6})\b", body)`. Use a **plus-alias**
   of the operator's address (`operator+vendor@gmail.com`) as the test identity: it lands in a mailbox
   you can read, it is obviously a test tag, and it is not a fabricated identity or KYC data.
6. **Read the SDK's own step machine from localStorage before guessing at the UI.**
   `@PARA/modalState` carries `{step, authState:{auth:{email}, stage, userId, nextStage}}`;
   observed sequence `OTP` → `AWAITING_ACCOUNT` → (reload) `AUTH_MAIN`. Also useful:
   `@CAPSULE/userId`, `@CAPSULE/sessionCookie`, `@CAPSULE/wallets`.
7. **A vanished iframe target is GOOD news.** After submitting the code, the next CDP call can fail with
   `Target.attachToTarget failed … No target with given id found` — the widget closed because verification
   succeeded and the flow advanced. Re-check the parent page instead of retrying the frame.
8. **PITFALL — identity created is not a session.** On this flow the Para identity existed
   (userId + Capsule session cookie) and the email was verified, yet the app issued NO session because the
   **wallet/onboarding step** (`step:"AWAITING_ACCOUNT"`, UI stuck on "Creating your account…", `wallets:{}`)
   never completed; a reload restarted the whole flow at `AUTH_MAIN`. Re-running the email step re-sends a
   code and does not fix an unfinished wallet. Do not burn an hour on it: fall back to the operator-assisted
   path (they finish the wallet in their own browser with the same test identity, then you take the cookies
   from that profile — see the "operator-assisted login" rule above) or drive the SDK's API directly with
   the apiKey + session you already captured.

## OAuth provider buttons that open a POPUP (not a redirect) — headed + popup listener

Observed on app.coderabbit.ai "Continue with GitHub" (2026-10). The button calls
`window.open` — the OAuth flow runs in a **popup window**, the main page never navigates.
Two failure modes that look like "the button is broken":

1. **Headless + JS `.click()`: nothing happens.** The popup is blocked/never opens, the main
   page stays on `/login`, and re-clicking changes nothing. There is no error — just no
   redirect.
2. **Headed + JS `.click()`: flaky.** Sometimes it redirects full-page, sometimes not.

Working recipe (Playwright, headed):
```python
popups = []
ctx.on("page", lambda pg: (popups.append(pg), pg.bring_to_front()))
# real mouse click on the button's viewport coordinates (scrollIntoView first)
box = pg.evaluate("()=>{const t=[...document.querySelectorAll('button,a')]
        .find(b=>/GitHub Cloud|Continue with/i.test(b.textContent||''));
        t.scrollIntoView({block:'center'});const r=t.getBoundingClientRect();
        return {x:r.x+r.width/2,y:r.y+r.height/2};}")
pg.mouse.click(int(box["x"]), int(box["y"]))
# then poll BOTH the main page and popups for the callback:
#   success = main page leaves /login and is not on the IdP host
```
Completion signal: the popup lands on `<app>/login?code=...&iss=...` (the OAuth callback),
the main page redirects to the authenticated app (`/wizard`, `/dashboard`). Save
`ctx.storage_state()` the moment the URL changes — a later `page.evaluate` after navigation
can throw "Execution context was destroyed" and kill the script *before* the save.

**After the provider authorization is granted once, a second click completes instantly**
(GitHub remembers the approved OAuth app) — so a lost session is recoverable by re-clicking
the provider button with the same profile, no re-login. Scope requested here was
`user:email read:org` (read-only).

Corollaries:
- The provider `state` parameter IS present and per-attempt (good practice; note it in the
  report as a control).
- If the OAuth handoff must be done by the operator, give the exact click path (button
  label → provider login → Authorize) and poll for the URL change rather than asking "done?".
- A leftover Chrome process holding the profile lock makes the next launch die with
  "Opening in existing browser session" — `taskkill //IM chrome.exe //F` and relaunch before
  debugging anything else.

**Related finding class — claimant-secret binding on code/fork grants (Proton, 2026-10).**
App-internal "session fork" flows (`POST /api/auth/v4/sessions/forks` → selector →
`GET /api/auth/v4/sessions/forks/{selector}` → tokens) are authorization-code flows in
disguise. Test whether the secret the flow transmits (`sk` in the URL fragment, the
PKCE-verifier analogue) is actually REQUIRED for the grant: claim a fresh fork from an
unauthenticated client with only the selector. If full-scope AccessToken+RefreshToken come
back, the sk is decorative and any selector leak equals account API access. Then measure
what the token can really do (read endpoints 200 vs password-change/session-revoke blocked
by missing scopes) before arguing severity — the honest write-up was "sensitive data
disclosure, not takeover". Forks were single-use with 24h expiry; replay after claim returns
`Invalid selector` (record it as a control).

## Passkeys in automation + the "login worked, app still closed" class (invite/onboarding gates)

Three separate lessons from an app.vana.com session (2026-10), each of which cost real time.

1. **`/json` lists targets with `id`; `Target.getTargets` calls it `targetId`.** Mixing them kills the
   script with `KeyError: 'targetId'` *just before* the step you cared about. Always
   `tid = t.get("targetId") or t.get("id")`.
2. **Passkey/WebAuthn steps: install a virtual authenticator, and do it in ONE session.**
   ```
   WebAuthn.enable            {enableUI:true}          # must be same connection as the add
   WebAuthn.addVirtualAuthenticator {options:{protocol:"ctap2", transport:"internal",
        hasResidentKey:true, hasUserVerification:true, isUserVerified:true,
        automaticPresenceSimulation:true}}             → {authenticatorId:"…"}
   ```
   The virtual-authenticator environment is **session-scoped**. With Hermes' stateless `browser_cdp`
   calls, `enable` on one call and `add` on the next fails with
   `The Virtual Authenticator Environment has not been enabled for this session` — and calling
   `WebAuthn.*` without `target_id` fails with `wasn't found`. Run **both in the same persistent
   WebSocket session** (`scripts/cdp.py` style driver) and leave it open for the whole flow.
3. **Read the page before declaring auth broken — the wall may be product onboarding, not login.**
   The same case study looked like "wallet creation hung" for an hour; the real state after OTP was
   `app.vana.com/referral-code` rendering **"Vana is invite only (for now)"**. Evidence that the
   identity layer was fine: the SDK minted a JWT (`POST /auth/jwt {"keyIndex":0}`) and read a wallet
   (`POST /assets/balances {"wallets":[{"type":"EVM","address":"0x…"}]}`), while the app issued **no
   session cookie** (only `cf_clearance`). Rules: (a) dump `location.href` + `body.innerText` after
   every login step, not just the SDK's own state keys; (b) a hosted SDK session (Capsule/Para
   `@CAPSULE/sessionCookie`, `@CAPSULE/userId`) is **not** an app session; (c) "invite-only /
   waitlist / pending-approval" is an **untested area**, never a finding and never "auth is broken".

**Invite/referral codes are a testable surface in their own right** (do this before giving up on the
authenticated half):

- **Read the code's shape from the input, not from guesses** —
  `[...document.querySelectorAll('input')].map(i=>({max:i.maxLength, pattern:i.pattern, ph:i.placeholder}))`.
  Here: `maxlength=6` + `pattern=^[a-zA-Z0-9]+$` ⇒ keyspace 62⁶ ≈ 5.7e10. That number is what decides
  whether "no rate limit" is a real risk or noise.
- **Probe validation with RANDOM strings, never guessed real codes**, and compare answers:
  uniform `404 {"valid":false,"reason":"not_found"}` for random/empty/missing = **no oracle** (good
  design — record it as a verified negative). A different status for a valid code is the enumeration
  primitive; say which half you observed.
- **Rate-limit evidence = statuses + latency + headers over a bounded burst** (e.g. 30 probes at 1 rps
  + 10 back-to-back), then report the numbers: all 404, no `429`/`Retry-After`, median latency flat
  (0.46 s → 0.41 s). Flag it explicitly as *rate-limit testing only* — it is a hardening finding at
  low severity unless you also show the codes are low-entropy/live, and it is never brute force.
- Then park it: the honest report line is "authenticated surface untested — gated behind a
  community-issued invite code", plus the list of what you did test around the gate.

## Auth0 universal login (auth.<target>): signup works even when /u/ is edge-blocked

If the target's IdP is Auth0 (`auth.<target>/u/login/identifier`, connection like
`<App>-DB`), and POSTs to `/u/login/password` or `/u/signup` come back
**403 "Access Denied"** from `errors.edgesuite.net` (Akamai) while GETs work:

1. **Get `client_id`** by capturing the app's own redirect: enable CDP `Network`, navigate
   the app's login entry point (`/account/redirect-login/?iss=https://auth.<target>/`), and
   grab the `Network.requestWillBeSent` URL containing
   `auth.<target>/authorize?...client_id=…&redirect_uri=…&scope=…`. The sealed `state`
   hides it; the request URL does not.
2. **Create the account on the sibling path** — Auth0 still exposes the legacy
   `POST https://auth.<target>/dbconnections/signup` with JSON
   `{client_id, email, password, connection}`. Ran from the auth origin as an in-page fetch
   (real browser fingerprint, cookies, no CORS problem) it returned 200 + the user object
   (`_id`, `app_metadata.ct_uuid`, `email_verified:false`) while the ULP signup POST stayed
   blocked. Error `Connection must be enabled for this client…` on the second attempt is
   how you confirm the right `connection` name.
3. **Verify the blocker before burning hours.** Read `_abck` for the domain via CDP
   `Network.getAllCookies`: a value containing `-1~-1~` = Bot Manager never validated this
   session, which is what turns credential POSTs into 403s. Human-like input replay
   (randomised mouse paths + per-key typing) does **not** clear it, and neither does
   timezone/locale alignment. `/co/authenticate` (`Cross origin login not allowed`) and
   `/oauth/token` (`Redirection is not available on /oauth/token endpoint`) are the other
   two routes and both are usually closed on modern tenants. Practical conclusion: you need
   a residential egress in the target's country, or the operator logs in and hands you the
   cookies/localStorage.
4. Path-variant tricks (`/u/login/password/`, `//u/`, `?x=1`, `/./`) do not help here — the
   rule is behaviour/risk based, not a literal path match.

**One debug browser per engagement.** A tab can be navigated out from under you by a
sibling automation process on the same machine using the same CDP port (observed: a Kmart
signup tab ending up on another project's app). Launch Chrome with a dedicated
`--user-data-dir` **and a dedicated port**, then verify the port is yours — a brand-new
profile that already shows another project's tabs means that port belongs to someone
else's Chrome (check `wmic process ... CommandLine | grep remote-debugging-port`).

## authentik IdP: drive the flow-executor API with NO browser (and the pyautogui fallback)

When the IdP is authentik (`auth.<target>`, `x-powered-by: authentik`, flows under
`/if/flow/<slug>/`), the sign-in flow is plain HTTP — try this BEFORE any browser work:

```python
s = requests.Session(); s.headers["User-Agent"] = "<browser UA>"
r  = s.get("https://apex/sign-in", allow_redirects=False)       # 302 -> /outpost.goauthentik.io/start
r2 = s.get(r.headers["Location"], allow_redirects=False)        # 302 -> /application/o/authorize/...
r3 = s.get(r2.headers["Location"], allow_redirects=False)       # 302 -> /if/flow/default-authentication-flow/?...
q  = urllib.parse.urlparse(r3.headers["Location"]).query
ex = s.get("https://auth.host/api/v3/flows/executor/default-authentication-flow/",
           params={"query": q}).json()
m  = re.search(r"/if/flow/([^/?]+)/\?(.*)$", ex["to"])          # xak-flow-redirect -> real slug
slug, query = m.group(1), m.group(2)
s.get(f"https://auth.host/api/v3/flows/executor/{slug}/", params={"query": query})   # challenge JSON
s.post(f"https://auth.host/api/v3/flows/executor/{slug}/", params={"query": query},
       data={"uidField": "test@example.com"})                   # FORM-ENCODED, field = uidField
```

Three things that waste an hour if unknown: (1) the POST body must be
`application/x-www-form-urlencoded` — JSON in any shape fails with
`"No identification data provided."`; (2) the identification field on the wire is **`uidField`**
(the challenge's `user_fields: ["email"]` describes the widget, not the body — confirm via a
shadow-DOM dump or the stage chunk `/static/dist/src/flow/stages/identification/chunks/*.js`);
(3) a systematic `ak-stage-flow-error` carrying only a `request_id` means YOUR request shape is
wrong, not a platform 500. Success = the challenge advances to the email-sent stage. Full recipe
(allowlist mapping, OAuth redirect_uri + MCP DCR matrices): `unauth-surface-discovery` →
`skills/security/unauth-surface-discovery/references/authentik-outpost-flow-testing.md`.

If a browser IS required (magic-link click-through), the authentik flow UI is a Lit app whose
form lives in a shadow root, and the usual tricks fail in a specific order: WebDriver CSS
selectors do not pierce shadow roots at all; the native-setter + synthetic-events recipe sets
the DOM value but the framework's submit handler reads empty state, so the Continue click
silently does nothing; CDP `Input.insertText` types successfully but **breaks every subsequent
`Runtime.evaluate` (they return null)**. What works: **headed SeleniumBase + pyautogui** — get
the input's viewport coordinates from a shadow-piercing `getBoundingClientRect`, then
`pyautogui.click(x,y)` → `pyautogui.typewrite(...)` → `pyautogui.press("enter")`. Real OS input
events satisfy the framework every time. Do all read-back verification BEFORE typing, or via a
different channel after.

## Recovering an authenticated identity from the operator's own Chrome profile

Before you ask the operator for a password (or give up on a Pro/paid surface), look on the box.
Two independent things are recoverable from any Chrome/Edge `--user-data-dir`:

1. **Saved passwords** — `<profile>/Default/Login Data` (SQLite). `password_value` is AES-256-GCM
   (`v10` prefix = 3 bytes + 12-byte nonce + ciphertext+tag). The key is in
   **`<user-data-dir>/Local State`** → `os_crypt.encrypted_key`, base64, **strip the leading 5-byte
   `DPAPI` marker**, then `win32crypt.CryptUnprotectData`. This returns clean ASCII and is the path
   that actually works: on quarterwise it yielded the Pro account password and unblocked the whole
   engagement. Enumerate **all** rows whose `origin_url` matches the target — `username_value` is
   often a DISPLAY NAME (`"Mr Fz"`), not the email, so filtering on the email finds nothing.
2. **A still-live session** — copy the whole profile dir (`cp -r`), delete `lockfile`,
   `SingletonLock`, `Default/Network/Cookies-journal` in the copy, launch headless Chrome on the
   copy with `--remote-debugging-port` + `--remote-allow-origins=*`, then `Page.navigate` the app.
   Cookies live in the profile dir, so a copied profile is still logged in. Verify the identity by
   reading the landing page (plan string / account email), not by assuming.

**Do NOT try to decrypt the session cookie out of the DB — go to the live profile instead.** Chrome
`v10` cookie values decrypt with GCM auth *passing* yet come back as non-ASCII bytes that requests
rejects as a header (`'latin-1' codec can't encode characters`). A passing tag is not evidence you
got a usable value, and HTTP header values are latin-1 by definition, so a "cookie" with bytes >127
was never sent by a browser. Recognise it early and spend the time on the copied profile.

**PITFALL — `Local State` is in the profile ROOT, `Login Data` / `Network/Cookies` are under
`Default/`.** Mixing these up is a `FileNotFoundError` on a path that looks correct.

**Enumerating several candidate profiles to find which identity is which:** loop copy → launch on a
distinct port → navigate the app → assert a *specific* marker string. A short slice of `innerText`
is not enough — a free-plan page only reveals `"Upgrade to Pro"` / `"You're on the free plan"`
further down, so a naive `text.slice(0,500)` misclassified a free account as Pro. Read a longer
slice, or grep for the plan string directly.

```bash
python scripts/chrome_profile_creds.py --profile-dir "~/.local/share/Google/Chrome/User Data" --match target.com
python scripts/chrome_profile_creds.py --profile-dir "$HOME/qw_chrome_cdp_b3" --cookie-name qw_session
```

## MFA stage: check which cookies exist, then try the protected route with them

Cheap, decisive 2FA-bypass test on any password → MFA handoff. After submitting the password, dump
the cookie jar *before* entering the code, then hit a protected route with exactly those cookies:

```text
step2 url: /login/mfa
cookies at MFA stage: {'qw_mfa': '4d511de7-…'}     # pending cookie only, no session cookie
navigate /app with them -> redirect back to /login
```

That is a **verified negative** ("no 2FA bypass"), and it is far better evidence than "the app asks
for a code". Record the cookie names and the redirect. If a *session* cookie is present at that
stage and `/app` renders, you have the real thing — escalate immediately.

## Multi-tab, real clicks, and input fallbacks (three silent-failure traps)
1. **`Input.*` events only land on the ACTIVE tab.** With two tabs open (e.g. target + IdP signup),
   `Input.insertText` / `dispatchKeyEvent` against a background tab returns `{}` and the field stays
   empty — no error, no exception. Select the tab explicitly and activate it first:
   `GET http://localhost:9222/json/list` → pick the target id → `Target.activateTarget {targetId}`.
   The driver exposes this as `CDP_TARGET_ID=<id>` env or a `targets` subcommand.
2. **Real-mouse coordinates are VIEWPORT-relative, not page-relative.** A button below the fold
   (`getBoundingClientRect().y == 1406`) produces a click that hits whatever is at that viewport
   offset — the click "succeeds" and nothing happens. Always
   `el.scrollIntoView({block:'center'})`, re-measure, then dispatch. `click(sel, real=True)` in
   `scripts/cdp.py` does this for you.
3. **`Input.insertText` can silently no-op on some React forms** (observed on an Okta signup form:
   focus succeeded, value stayed `""`). Fallback that always works for React-controlled inputs:
```js
const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
const e = document.querySelector(SEL); set.call(e, VAL);
e.dispatchEvent(new Event('input',{bubbles:true}));
e.dispatchEvent(new Event('change',{bubbles:true}));
```
   Reach for `setval` after `type` verified-empty — and always re-read the value to confirm.
4. **File-upload fields silently accept a broken path.** For cert/document pickers use CDP DOM APIs —
   `DOM.getDocument` → `DOM.querySelector {selector:'input[type=file]'}` → `DOM.setFileInputFiles
   {nodeId, files:[...]}` — and **verify the file actually loaded**:
   `f.files.length`, `f.files[0].name`, `f.files[0].size`. A malformed path (e.g. built by string
   surgery, or MSYS-mangled) yields `size: 0` with no error; the server then rejects the whole form with
   a generic message ("Invalid parameters or file structure") that sends you hunting the wrong field.
   Clear with `files: []` first when re-uploading, and prefer forward slashes (`D:/dir/file.crt`).
5. **Self-signed TLS interstitial blocks the whole flow.** Navigating to a local HTTPS lab host shows
   `NET::ERR_CERT_AUTHORITY_INVALID` and `location` becomes `chrome-error://chromewebdata/`. Pass it by
   focusing the page (a mouse click on the body) and typing **`thisisunsafe`** as real key events
   (keyDown+keyUp per char). Then re-read `location.href` to confirm you are back on the app.
6. **SPA deep links bounce; in-app nav clicks work.** `Page.navigate` to an authenticated route
   (`/settings/users/sso`) redirected back to the dashboard home, while clicking the same route through
   the UI's own nav (with a substring/`maxlen`-bounded text match on `a,button,div,span,li`) navigated
   correctly. For authenticated multi-step sections, drive the nav instead of guessing URLs — and
   exact-text matches fail on whitespace, so match with `includes()` plus a length guard.
7. **A submit that "does nothing" is usually a hidden required field, not a broken click.** After one
   submit attempt, read the page's error surface
   (`[...document.querySelectorAll('[class*=error],[class*=error-msg],[role=alert]')].map(e=>e.innerText)`)
   — that is how a required captcha field and a server-side validation message actually surfaced in this
   session. Only then decide between "needs a human", "wrong value", and "real bug".
8. **Legacy form libs (MooTools/jQuery) reject synthetic events AND repeat the field id — two coupled
   traps.** Both hit on TripAdvisor's `RegistrationController` signup (2026-10):
   - **Duplicate ids.** The container `<div>` and the real `<input>` share the SAME id
     (`regSignUp.password`), so `getElementById('regSignUp.password')` returns the **HTMLDivElement**.
     `.focus()` and `.value=` then silently no-op — `document.activeElement` never leaves the previous
     field and the div just grows an expando. Always target by tag+id:
     `document.querySelector('input[id="regSignUp.password"]')`, and when a set "looks like it worked"
     but the field is empty, check `Object.getPrototypeOf(el).constructor.name` (a `DIV` tells you why).
   - **Synthetic events throw.** The React-style native-setter + `new Event('input'/'change')` recipe
     (trap #3) *throws inside* the site's bundled MooTools
     (`Cannot read properties of undefined (reading 'indexOf')`) and resets the other fields. Here the
     fix is the OPPOSITE of trap #3: focus the real `<input>`, then send **real** `Input.insertText`
     (CDP) — legacy `onkeyup` handlers and the server read both see it.
   - **A visible reCAPTCHA Enterprise checkbox may not block submission.** Clicking the 256x60 anchor
     via CDP left the token empty, yet the form still submitted and the account was created. Fire ONE
     submit and read the outcome (URL change / error surface) before hunting a captcha solver.

## React-controlled inputs (SPA signup/login forms)
- Plain inputs: `.focus()` then `Input.insertText` is enough — React's onChange fires and state updates.
  (When it doesn't, see trap #3 above: native setter + input/change events.)
- **react-select / combobox controls need REAL per-character key events.** `insertText` sets the value
  but does not filter the option list (you get "No options"), and a fresh page load clears the filter.
```python
for ch in "ID":                      # one keyDown + one keyUp per char
    p = {"type":"keyDown","key":ch,"code":"Key"+ch,"text":ch,"unmodifiedText":ch,
         "windowsVirtualKeyCode":ord(ch),"nativeVirtualKeyCode":ord(ch)}
    c.send("Input.dispatchKeyEvent", p); c.send("Input.dispatchKeyEvent", {**p,"type":"keyUp"})
```
- **Filter by the LABEL, not the display name.** Phone-country selects are usually labelled
  `"<ISO> +<dialcode>"` (e.g. `ID +62`), so typing "Indonesia" matches nothing — type `ID` and then
  click the option:
  `document.querySelectorAll('div[id^=react-select-2-option]')` → pick by `innerText`.
- The menu is virtualized: query options only while the menu is open (a real mouse click on
  `[class*="-control"]` opens it); a closed menu returns an empty list.
- Custom checkboxes are React inputs — a plain `element.click()` in the page context toggles state and
  satisfies "required" validation (verify the `checked` flag afterwards).

## Capturing secrets from the app's own API (better than decoding images)
For TOTP/OTP enrollment the page may only *draw* a QR on a `<canvas>`. Decoding that raster is fragile
(OpenCV failed on a 128x128 canvas even upscaled 8x). Instead, capture the API response that carries
the secret with a **main-world fetch/XHR hook installed BEFORE the request fires**:
```js
(() => { if (window.__capInstalled) return 'already';
  window.__cap = [];
  const of = window.fetch;
  window.fetch = async (...a) => { const r = await of.apply(this, a);
    try { const u = (typeof a[0]==='string') ? a[0] : (a[0]&&a[0].url)||'';
          const t = await r.clone().text();
          window.__cap.push({t:'fetch', u, s:r.status, body:t.slice(0,6000)}); } catch(e){}
    return r; };
  const oo = XMLHttpRequest.prototype.open, os = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function(m,u,...r){ this.__u = u; return oo.call(this,m,u,...r); };
  XMLHttpRequest.prototype.send = function(...a){
    this.addEventListener('load', ()=>{ try { window.__cap.push({t:'xhr', u:this.__u, s:this.status,
      body:(this.responseText||'').slice(0,6000)}); } catch(e){} });
    return os.apply(this, a); };
  window.__capInstalled = true; return 'installed'; })()
```
- Install the hook, THEN trigger the action (e.g. toggle "use authenticator app" so the app re-issues
  the secret), then read `window.__cap` and regex for `otpauth://…`, `"secret"`, `"provisioning_uri"`.
- **PITFALL: a page reload / SPA route reset wipes `window.__cap`.** Read the buffer before navigating
  anywhere. In one session a captured `change-mfa-type` response was lost this way and the flow then hit
  a 1-hour signup lock — capture first, navigate later.
- With the secret in hand, generate codes locally (`pyotp.parse_uri(uri).now()`) so the flow needs no
  SMS from the account owner.

## Pitfalls (each cost real time this session)
0. **`Runtime.evaluate` + `awaitPromise` on a non-invoked async arrow returns `{}`.** If the
   harness prints empty objects instead of response JSON, the first thing to check is a
   missing trailing `()` on the IIFE (`(async () => { ... })` evaluates to a function, which
   serialises as an empty object — no error, no timeout). Also remember `cdp.py eval` from the
   CLI does NOT pass `awaitPromise`; only the Python API's `ev(expr, await_promise=True)` does.
   Two other silent traps in the same family: calling `c.ev(js, args)` where `ev`'s second
   positional parameter is `await_promise` (the args land in the wrong slot), and assuming
   `fetch()` is native — a site can replace `window.fetch` with a wrapper whose return value
   has no `.text()` (`TypeError: r.text is not a function`); fall back to `XMLHttpRequest`.
1. **Next.js Server Actions: curl POST → 500.** `$ACTION_REF_*` / `$ACTION_ID_*` hidden
   fields are empty in static HTML and populated client-side. Never hand-replay
   signup/login via urllib/curl — drive a real browser: fill + `form.requestSubmit()`.
2. **urllib HTTP 500 during "login check" ≠ vulnerability evidence.** An incomplete
   server-action replay (missing header/state) 500s regardless of password state.
   Verify authz/password claims with a REAL browser login on a fresh cookie jar:
   old-pw → /app (SUCCESS) + new-pw → "do not match" (FAIL) = change was rejected.
3. **Temp inbox**: mail.tm API (`POST /accounts`, `POST /token`, `GET /messages`,
   `GET /messages/{id}` for text body; regex `\d{6}` for the OTP). Create the mailbox
   that receives a reset/"unregistered" probe to confirm what the server actually sent.
4. **Server-action binding is per-session**: replaying account A's captured action with
   account B's cookie → 500 "Server action not found" (expected, NOT a finding).
5. **Accept-invite token binding**: accept with a DIFFERENT signed-in user than the
   invited address → server refuses ("sign in with the invited address") = token bound.
6. **Windows `curl -o /tmp/x.json` silently fails.** The bash shell is MSYS but `curl.exe` is native
   Windows, so a POSIX path in `-o` errors with "No such file or directory" while still reporting an
   HTTP code. Always pass Windows-style output paths (`-o resp.json` in the cwd, or `-o "D:/.../f.json"`).
7. **A drop-in CDP helper beats one-off CDP calls.** Long flows (signup → OTP → password → onboarding)
   cost dozens of round-trips when each step is its own tool call. Keep a small subcommand driver
   (`eval|text|form|click|clicktext|type|key|goto|shot|cookies`) and script the flow end-to-end;
   it also makes the flow repeatable after a rate-limit/lock reset. See `scripts/cdp.py`.
8. **Provider signup locks are normal, not a bug.** "Sign-up using this email will be available again
   in one hour" = plain anti-abuse. Do not retry-pump it. Park the flow and schedule a one-shot resume
   (cron with a self-contained prompt + the driver script) so the engagement keeps moving; capture
   state (cookie jar / profile dir) must stay alive in between.
   **Waiting on an out-of-band email that may never arrive? Don't block — install a silent watchdog.**
   Trigger a flow (password reset, invite) and then sit on an inbox poll is dead time. Instead write a
   `no_agent` cron whose script prints NOTHING until the mail lands, then prints the subject + the
   extracted link/token: `{no_agent:true, script:'watch_x.py', schedule:'*/5 * * * *', deliver:'all'}`
   — empty stdout = silent, so the operator is pinged only on the real event (default `deliver` is
   `local`, which never reaches them; set `all` or a channel). The script itself must live under the
   Hermes scripts dir — cron REJECTS absolute paths (`Script path must be relative to
   ~/.hermes/scripts/`). Before trusting its silence, run it once by hand and echo the status
   (`python watch_x.py; echo exit=$?`) so a wiring bug can't masquerade as "no mail yet". Real case
   (2026-10): a Tripadvisor reset mail never arrived; the watchdog ran every 5 min without spamming
   while other work continued. Also treat a *missing* expected mail as a signal in itself (delivery
   path blocked vs the flow silently failing) — but only chase it after the watchdog has had a few
   cycles.
9. **`grep PATTERN file | head && echo FOUND` prints FOUND even when nothing matched — a pipe reports
   the LAST command's exit status, and `head` exits 0 on empty input.** This manufactured a false
   "stored XSS / HTML injection" conclusion on TripAdvisor's profile page (2026-10): the command
   `grep -o '<b>BOLD</b>' prof.html | head -3 && echo "!! RAW tag PRESENT"` fired the banner while the
   injected marker had in fact been stripped, and the claim had to be retracted a few turns later.
   Never let a shell exit status be your evidence. Rules:
   - Assert on a **count**: `n=$(grep -c PATTERN file)` then branch on `$n` — `grep -c` exits 1 and
     prints `0` when there is no match, so it cannot lie.
   - Always dump the **matched context** before concluding:
     `grep -o '.\{80\}PATTERN.\{80\}' file | head` — an empty result is the answer, and the window
     shows you which context (HTML body vs JSON blob) the match sits in.
   - **Count the raw form and the escaped form separately.** A reflected payload
     `BGC<svg/onload=alert(1)>"x` leaves the literal substring `onload=alert(1)` in an escaped
     document (`&lt;svg/onload=alert(1)&gt;`), so a naive count "proves" injection that isn't there.
     Pin it down with two counters — `grep -c '<svg'` (raw opener) vs `grep -c '&lt;svg'` (escaped):
     escaped-only = safe, and that is the honest finding. Same for JS/JSON contexts, where the escape
     is `\u003c…\u003e` (Next.js RSC flight data) rather than `&lt;`.
   - Corollary for any "the payload is present" claim: presence of a substring ≠ execution context.
     The finding is the DOM element / the unescaped HTML, not the byte.

## Verification discipline (golden rules from this session)
- **CSRF on server actions**: capture a legit POST (page + action state fresh), replay
  byte-identical body + SAME session cookie but `Origin: https://evil.example.com`,
  `Referer: https://evil.example.com/…`. Legit=2xx, evil=500 = Origin check present.
  Cross-check NO state change via the data export endpoint (count objects/rows).
- **BOLA write (cross-tenant)**: in account B's session, open a form scoped to B's own
  object (so the action binds to B), then swap the object `id` to account A's object.
  Reject message ("property could not be found") = write scope enforced. Page-level
  404s are NOT enough — server actions are the real authz surface.
- **Stored XSS**: after saving a payload, confirm whether a DOM ELEMENT was created
  (`document.querySelectorAll('img')` with payload src) and re-check after reload.
  Escaped text (`&lt;img...&gt;` in a `<p>`) = safe, not XSS. InnerHTML escaping on
  Next.js RSC is usually total.
- **XLSX formula injection**: unzip, read `xl/sharedStrings.xml`. Values in
  `<si><t>` are string cells → Excel does NOT execute them (safe). Real formula cells
  appear as `<f>` elements. A name `=SUM(A1:C1)` in sharedStrings = NOT exploitable.
- **CSV formula injection**: client name `=2+2` in exported CSV. Server prepending
  `'` → `'=2+2` = mitigation present.
- **Numeric business logic** (ownership percent etc.): submit 101 / -10 / 0, then
  READ THE INPUT VALUE BACK. Server reverting to 100 = server-side validation.
- **OTP rate limit**: the UI URL can leak the cap (`reset?codeLimit=12&why=cooldown`)
  = protection exists; don't brute-force past it in a no-volume-testing VDP.
- **A pre-MFA token is NOT a session — test it, don't assume it.** `/users/login` can return
  `200 {data:{token:…, is_otp_verified:false, is_first_login:true}}` and that token is refused by every
  protected endpoint (`MERCHANTS_PORTAL_INVALID_SESSION` / `MISSING_TOKEN`). That is MFA enforced
  server-side, i.e. a **verified negative for MFA-bypass** — say so explicitly rather than reporting
  "got a session token without MFA". It also means a fresh invitee cannot be used for RBAC testing
  until the first-login OTP step completes (usually a phone number you may not have).
- **A "forgot password" request can invalidate the password you are actively using.** Observed on
  Rapyd: requesting a reset made every subsequent login return the generic credential error, with no
  session expiry involved — the account sat in a pending-reset state until a reset link was actually
  used. Rules: never fire a reset on an account mid-engagement; if you must, complete the reset
  immediately (pull the link from the mailbox and set a new password) and record the new credential in
  the engagement log, because the old one is dead. A login failure right after you touched a
  reset/OTP flow is far more likely that than a wrong password — check the flow you drove before
  concluding "the password changed".
- **Cheapest way to get a second, lower-privileged identity is the app's own invite flow, not signup.**
  Invite a `you+tag@yourmail` address with the lowest role, open the invite link in a *separate*
  Chrome profile, set the password, and you have an RBAC probe account with no SMS/CAPTCHA signup
  gauntlet. It also gives you the invite/notification email templates as test input for
  HTML-injection work (see `bug-bounty` → `skills/security/bug-bounty/references/email-template-injection.md`).
- **Do not fabricate regulatory identity data to unlock a gated flow — inspect the gate instead.** When
  an audit is blocked behind onboarding/KYC/KYB (or a plan/entitlement gate), the operator may say "just
  fill it in, we'll delete it later". Inventing a business name, registration number, tax id or documents
  for a *KYC pipeline* is a false declaration to a regulated entity — it risks the operator's account
  being banned and their platform standing revoked, and it is not the same thing as a disposable test
  account. Offer the honest alternatives instead: (a) the operator hands you their REAL entity data and
  you complete the form with it; (b) ask the program to enable the sandbox capability — a normal request
  for payment/fintech programs; (c) ship the finding at its honest lower severity with an explicit
  "verification status" section naming the blocker (exact server error code, e.g.
  `…_HOSTED_CATEGORY_NOT_SUPPORTED`, plus the disabled control, e.g. payment-method checkboxes rendered
  `disabled` so the submit button never enables). Triagers accept a precise blocker; they do not accept
  an invented PoC.
  Payoff observed: inspecting the blocked gate rather than faking past it produced a real finding — the
  hosted KYC "application link" (`verify.<host>/verify?token=happ_…&otk=…`) turned out to be a pure
  bearer credential whose token alone returned the applicant's email and internal entity token, and whose
  bundle exposed write/submit plus an SMS-OTP-trigger endpoint. Read the gate's own flow, its iframe URL
  and its JS bundle before deciding the only way through is to lie to it.

## Driving React/react-select UIs (this is where the hours go)

Modern portals are full of `react-select`-style comboboxes (country pickers, role pickers, table
filters). Two hard rules learned the slow way:

1. **Do the whole interaction in ONE process.** A react-select menu closes/blurs when the CDP
   websocket disconnects, and every new script run is a new connection. `click → wait → inspect`
   split across separate invocations always sees an empty option list. One script: focus, open,
   choose, verify, submit.
2. **JS-dispatched `KeyboardEvent` beats synthetic mouse events.** `Input.dispatchMouseEvent` on the
   control does not always open the list, and `Input.insertText` into the combobox input closes it
   (React's value tracker never sees a filtered term). What works reliably:
   ```js
   // tag the target input once, then:
   const o={key:'ArrowDown',code:'ArrowDown',keyCode:40,which:40,bubbles:true,cancelable:true};
   i.dispatchEvent(new KeyboardEvent('keydown',o));
   i.dispatchEvent(new KeyboardEvent('keyup',o));
   // ArrowDown opens the menu (first press focuses option 1), then n presses, then Enter (13).
   ```
   To locate the right combobox, do not guess ids (`react-select-2-input` may be the *language*
   selector, not the country one). Anchor on the sibling hidden input that carries the real value:
   `document.querySelector('input[name="country.phone"]').closest('.css-1ocyjpi-container')
   .querySelector('input[role=combobox]')`, and tag it with a data attribute.
3. **Read progress from the a11y live region, not the DOM.** Long lists are virtualised — only ~7
   `[class*=dropdown__option]` nodes exist at a time, so "is my target in the list?" is always
   false. The `aria-live` spans announce the truth:
   `"option ID +62 focused, 100 of 247"`. Loop ArrowDown until the wanted label appears, then Enter.
   Short lists (<10) can be read directly from `[class*=dropdown__option]`.

**Typing: verify every field's value before submitting.** CDP has two input paths and neither is
universally right: `Input.insertText` can silently drop characters (observed: a 19-char password
arriving as 17), while per-character `Input.dispatchKeyEvent` needs the right `code` for punctuation
(`Period`, `Minus`) or it drops `.`/`-`/`!`. Recipe: fill, then `el.value` read-back and check
`length`; if it is short, switch method for that field. A "credentials incorrect" response is far
more often a mangled field than a changed password — read the value back BEFORE concluding anything.

**Capturing the app's own API calls: `Network.enable`, not JS hooks.** `fetch`/`XHR` monkey-patches
miss requests made by frameworks that captured their own reference (Next.js app router, pre-bound
axios instances). This session's login/invite POSTs were invisible to a JS hook but obvious via
`Network.enable` + `Network.requestWillBeSent` (`postData` gives you the exact body + field names)
and `Network.getResponseBody` for the response. Wrap drain loops with a 1s socket timeout so you can
collect events and still issue commands.

**GraphQL persisted-query apps: harvest the query ids, then read the response to the control probe.**
Worked case: Tripadvisor `POST /data/graphql/ids`. Three findings that generalise:
1. The body is a **JSON array** of `{"variables":{…},"extensions":{"preRegisteredQueryId":"<16 hex>"}}`.
   The id is what the server matches on — a bare `{"query":"…"}` gets
   `"Arbitrary operations not available to untrusted clients"` (HTTP 200). **That response is a control
   working correctly; it is a negative, not a finding.** Record it as a verified-negative.
2. Harvest ids with `Network.requestWillBeSent` on a single data-heavy page load. A JS `fetch`/`XHR`
   hook AND `Page.addScriptToEvaluateOnNewDocument` both **missed** the calls here (urql +
   `batchFetchExchange`), so the Network domain is the only reliable capture.
3. Once you have an id whose variables contain an object id (`{"userId":"<hex>"}`), replay it with the
   SAME session and a different id — but **two empty results prove nothing.** In this session your own
   id and a random format-valid id both returned `{"trips":[]}`, which cannot distinguish "server
   ignores the id" from "server honours any id"; an invalid-format id erroring proves only format
   validation. To claim BOLA you need a **populated victim object** coming back to you. Otherwise write
   it up as inconclusive and move on.

**Header-token SPAs: cookies are not the session.** Some portals authenticate with a token held in
`localStorage` and sent as a custom header (`token:`), so a cookie-only replay returns
`INVALID_SESSION` and every unauthenticated-looking endpoint looks dead. Before declaring an endpoint
unauthenticated/blocked, diff the app's real request headers and replay them
(`{'token': localStorage.token, 'fingerprint': localStorage.fp}` + `credentials:'include'`).

**Two identities at once = two browser profiles, not two tabs.** Launch each identity with its own
`--user-data-dir` and its own `--remote-debugging-port`, and make the CDP helper read the port from
the environment (`CDP_PORT`) so the same script can drive either. Also unset any pinned
`CDP_TARGET_ID` — a stale target id makes the helper attach to the wrong browser (or fail outright)
when a second instance is up.

## Cross-origin iframes (OOPIF) + screenshots that never return

Symptoms seen on pages that host a heavy third-party iframe (checkout/payment widgets, SDK embeds,
vendor dashboards): `Page.captureScreenshot` simply never answers — the websocket raises
`WebSocketTimeoutException` after the socket timeout, and a longer `settimeout` / a bigger logical
timeout does not help. Commands issued after it look broken too. This is the page, not your driver.

1. **Diagnose**: `GET /json/list` shows the frame as its own target —
   `{"type":"iframe","url":"https://…/hosted/preview?token=…"}` alongside the `page` target.
2. **Fix — attach to the iframe target directly.** Open a second CDP client on that target's
   `webSocketDebuggerUrl` and use plain `Runtime.evaluate` there. You get full DOM access *inside* the
   frame even though the parent page is cross-origin and cannot read it:
   ```python
   t = [x for x in json.load(urlopen(f"http://localhost:{PORT}/json/list")) if x["type"]=="iframe"][0]
   n = Raw(t["webSocketDebuggerUrl"])            # send {id,method,params} yourself
   n.ev("JSON.stringify({btns:document.querySelectorAll('button').length, txt:document.body.innerText.slice(0,200)})")
   ```
   This is also the only practical way to *observe the effect* of a cross-origin postMessage payload
   when the parent cannot read the frame's DOM — far better evidence than a screenshot.
3. **Keep sessions short-lived.** Do not call `Page.enable` in a connection you also want to
   screenshot from (the event stream starves the reply), and prefer one fresh connection per action on
   heavy pages. If you truly need pixels, `Page.bringToFront` then an OS-level grab
   (Pillow `ImageGrab`) sidesteps CDP compositing entirely.
4. **Watching a widget's own messages** requires *your* page to be the parent: serve a page on
   `http://127.0.0.1:<port>` that frames the widget and logs
   `window.addEventListener('message', e => log(e.origin + ' ' + JSON.stringify(e.data)))`.
   See `modern-web-framework-attacks` → `skills/security/modern-web-framework-attacks/references/framing-and-postmessage-audit.md`.

## Deep-dive checklist when the user pushes for medium+ ("deepdive lagi")
Re-attack in this order — these are the Medium/High vectors that are easy to skip:
1. Child-object IDOR (transactions/notes/documents by ID, NOT just page-level)
2. Gated features (Pro-only upload/AI/API) — direct endpoint call from free plan
3. CSRF on state-changing actions via same-session evil-Origin replay
4. Invite/share/co-owner flows: token binding, role tamper, accessId manipulation
5. Password/email change re-auth requirement (verify via real login!)
6. Export endpoints (xlsx/pdf/csv): IDOR on format/taxYear params + formula injection
7. Notes/description stored XSS (check DOM, not raw HTML)
8. Numeric bounds on financial fields
9. Session cookie format (64-hex random = server-side, not predictable; NOT a finding)
10. Reset/signup OTP flows for user-enum (identical responses = anti-enum = good)

## Never let an error/rate-limit page become your evidence

Two ways this bit hard, both cheap to avoid:

1. **Response headers from a non-200 response are the error page's headers.** Probing
   `checkout.<target>/?token=…` returned `X-Frame-Options: SAMEORIGIN` + `Referrer-Policy` and looked
   like framing protection; it was actually the **Cloudflare/edge 429 rate-limit page** (status line
   was `429 Too Many Requests`, easy to skim past when you only grep for the header you want). The real
   `200 OK` response had **no** framing headers at all — i.e. the opposite conclusion, and the whole
   finding depended on it. Rules: print the status line in the same grep as the headers, always
   re-request after the rate-limit cooldown before believing anything, and treat `429/503/403 + HTML`
   bodies as "no data", not as configuration evidence.
2. **Re-test a lead before you submit it — findings rot.** A month-old note said
   `POST /register` on the target's MCP host returned `201` (open dynamic client registration). On
   retest the same host returned a Cloudflare `404` and the real DCR endpoint rejected every
   non-loopback `redirect_uri` (`invalid_client_metadata`) while enforcing PKCE S256 — the vendor had
   moved the service behind a managed OAuth layer, which closed the lead. Cheapest possible action:
   re-run the exact request from the old note, then mark the item `CLOSED — NOT EXPLOITABLE` with the
   reason and the date in the findings file. Reporting a stale lead burns credibility with the triager
   and wastes the operator's submission slot. (Corollary: retest can also *upgrade* an old lead —
   header/origin checks that were absent in an earlier observation may still be absent and now provable.)

## Hosted "application link" flows are bearer credentials — test them as such

KYC/KYB/onboarding/e-signature/support-portal flows often hand the user a link like
`https://<verify-host>/verify?token=happ_<hex>&otk=<long>` embedded in an iframe of the main portal.
Test the link as a credential in its own right:

1. **Pull the iframe src** from the authenticated portal page, then open it in a *clean* browser
   profile (no cookies, no session) and see whether the flow renders. If it does, the link alone is the
   credential.
2. **Find what authorises the API calls.** Capture `Network.requestWillBeSent` for the app's own XHR and
   read the custom headers; here the SPA sent the URL token as a `kyb_token:` header
   (`zt.kyb_token || (zt.kyb_token = getSearchParam("token"))`), alongside client-controlled
   `device_fingerprint` / `device_os` / `device_timezone` values. That means a plain
   `curl -H "<that header>: <token-from-link>"` reproduces the access with **no browser at all** — the
   cleanest PoC you can write, and a control pair (`no header → 401`, `token+1 char → 401`) proves the
   token is the sole credential.
3. **Enumerate the whole surface from the bundle before judging severity** — grep the verify/hosted
   bundle for `api.get(`/`api.post(`/`api.put(` and the message maps. Typical shape: reads
   (`/applications/hosted/<token>`) plus *writes* (`…/hosted/update`, `…/<app>/save`, `…/submit`,
   `…/documents*`) and, notably, **`POST …/hosted/otp {action:'resend'}` = a third party holding the
   link can trigger SMS OTP to the applicant's phone.** Do not actually fire the OTP during testing —
   noting "reachable, not exercised (would SMS the account owner)" is the honest, operator-friendly
   claim. Bearer-link designs are often intentional, so lead with the PII actually returned (here
   `authorized_user_email` + internal `rapyd_entity_token`) and with the collateral write/SMS surface,
   and expect a "by design / informational" triage.
4. Cross-check for BOLA by swapping the path token for another object id **only after** confirming the
   path actually reaches the API — in this session `/v1/verify/applications/<token>` silently returned
   the **SPA HTML** (200/400/500 + `<!DOCTYPE html>`), which is "route not found", not a finding.

## Evidence & reporting
- Write every tool output to disk under the workspace; claims must map to a file.
- In the report, include the exact capture→replay commands (cookie header + body file).
- Distinguish "verified safe (blocked)" from "untested (needs Pro/real HMRC/izins)" —
  never blur a skipped area into a negative.
- **Keep a verified-control ledger for any repeat engagement** (same target, second pass, or a program
  that rewards one root cause once): one row per control probed, with the exact status/code and the
  probe that produced it. Start the next session by reading it, so you attack the unsaturated surface
  instead of re-deriving yesterday's negatives. It also makes the "no finding" answer defensible —
  see `references/quarterwise-2026-10-verified-controls.md` for the shape.

## Reference
- `scripts/cdp.py` — drop-in CDP driver (subcommands: eval/text/form/click/clicktext/type/key/goto/
  shot/cookies). Attach to a debug Chrome on `:9222` and drive the whole auth flow from bash/python.
  Make the port env-overridable (`CDP_PORT`) so the same script drives either identity's profile.
- `scripts/chrome_profile_creds.py` — recover the operator's own saved logins (and dump cookies)
  from any Chrome/Edge `--user-data-dir`, for when the credential is lost. See
  "Recovering an authenticated identity from the operator's own Chrome profile".
- `references/quarterwise-2026-09-playbook.md` — full session recipe: CDP driver
  snippets, mail.tm OTP flow, server-action capture/replay, verification table.
- `references/para-capsule-email-otp-login.md` — **third-party auth SDK in a cross-origin OOPIF**
  (Para/Capsule email OTP on app.vana.com): finding and driving the widget frame by `target_id`,
  shadow-DOM input walking, per-digit `Input.dispatchKeyEvent` into OTP boxes, reading the code from the
  operator's Gmail via API, and the `OTP → AWAITING_ACCOUNT → AUTH_MAIN` state machine to diagnose a
  stalled wallet/onboarding step.
- `references/quarterwise-2026-10-verified-controls.md` — **verified-control ledger** for a
  repeat engagement: every control already proven to hold (BOLA, MFA gate, CSRF origin check, API
  validation/cap battery, mail tag-strip), the policy's not-rewarded list, and the still-unsaturated
  surface. On a program that rewards one root cause once, read the ledger before re-probing anything.

- `references/playwright-state-and-mocking.md` — **browser state, mocking, and PoC capture.** Storage-state
  export/reuse per identity (log in once, reuse for the whole audit), request mocking/interception to test
  *client-side* trust (does the server enforce what the UI gates?), tracing, and video/screenshot capture
  for the PoC artefact. Includes the discipline rules: always record the unmocked exchange next to the
  mocked one, never leave a mock running into a later phase, evidence ≠ proof of impact.
  *Clean-room re-expression of technique from ARTEX `playwright-cli` (AGPL-3.0); our own text.*
