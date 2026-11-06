# Cross-origin postMessage channels + framing on embedded/payment pages

Class: a page that is **designed to be embedded** (hosted checkout, payment widget, iframe SDK, embed
chat, consent banner) usually talks to its parent over `postMessage`. Two independent defects are worth
testing there, and they compound:

1. **No framing protection** → any origin can embed the page (`X-Frame-Options` absent AND no CSP
   `frame-ancestors`).
2. **No `event.origin` validation on receive** → the embedding page can drive the widget (change labels,
   hide amounts/order details, prefill fields, trigger the primary action).

Tested on Rapyd Hosted Checkout 2026-09 → filed as a P4 (frameable page + unvalidated control channel
that can hide the order details and dispatch the submit message).

## 1. Static recon: find the handler in the bundle

```bash
grep -o 'addEventListener("message"[^;]\{0,120\}' *.js        # who listens
grep -o '\.origin[^;]\{0,80\}' *.js                           # is event.origin ever read?
grep -o 'postMessage([^)]\{0,80\}' *.js                       # outbound, look for targetOrigin "*"
```

Read the handler body: it is usually a `switch (e.data.type)` that dispatches redux/state updates. Record
the accepted message types and what each one actually does — that table is your impact section. Two traps:

- **Two handler families in one app.** Rapyd's hosted checkout installs `g$` for the real page and `S$`
  for the preview page (`Yp = e => { let n = g$; e === preview && (n = S$); addEventListener("message", n) }`).
  The message *names* differ (`PARAMS` / `CHECKOUT_SUBMIT_PAYMENT` vs `PREVIEW_PARAMS` /
  `PREVIEW_SET_CARD_DETAILS`). Sending the wrong family looks like "the widget ignores me" — pull the
  `INCOMING_MESSAGES` / `OUTGOING_MESSAGES` constants out of the bundle and use the exact strings.
- Look for a *state-changing* message, not just cosmetic ones. Rapyd's `CHECKOUT_SUBMIT_PAYMENT`
  dispatches a submit — that is what upgrades "UI tampering" to "payment-consent manipulation".

## 2. Framing check — and the rate-limit-page trap (important)

```bash
for u in https://target/hosted/checkout?token=x https://target/ ; do
  curl -s -D - -o /dev/null -A "$UA" -H 'X-Bugcrowd: Bugcrowd-<user>' "$u" \
    | grep -iE '^HTTP/|x-frame-options|content-security-policy|referrer-policy'
done
```

**Pitfall that nearly produced a wrong conclusion:** the first probe returned
`X-Frame-Options: SAMEORIGIN` — but that response was a **Cloudflare `429` rate-limit page**, not the app.
After a cooldown the real `200 OK` had **no** XFO and no `frame-ancestors` at all. Rule: when a
header-based claim matters, confirm the status is the real one (200), retry after the rate-limit window,
and keep the raw `-D -` dump as the evidence file. Never conclude "protected" from a WAF/error page.

## 3. Dynamic PoC: local attacker-origin harness

- Serve a page from a **different origin** you control (e.g. `python -m http.server` on
  `http://127.0.0.1:PORT`) that (a) iframes the target URL, (b) logs every `message` it receives, and
  (c) has buttons that post each message type you found in step 1. Localhost is a perfectly valid
  attacker origin for the PoC. Ready-made: **`scripts/postmessage_harness.py`** in this skill —
  `TARGET_URL='https://target/…?token=REPLACE_ME' TOKEN_URL='https://api.target/…preview_tokens?type=checkout' python postmessage_harness.py 8899`
  serves the page, auto-fetches a demo token if you point `TOKEN_URL` at one, and exposes a button per
  payload (`MSGS='[...]'` overrides the default set).
- You need a URL that actually renders. Find the right route/path from the bundle — the obvious one may
  404 (`/hosted/checkout` 404'd on the sandbox host; `/hosted/preview` rendered). Grep for the URL maps
  (`URLS`, `getUrlByEnv`, `jM[...]`) instead of guessing.
- Looking for a token so you can test without a merchant account? Hunt for **preview/demo token
  endpoints** (`grep -i preview_tokens`). Rapyd's sandbox mints demo checkout tokens unauthenticated:
  `GET https://sandboxapi.rapyd.net/v1/hosted/config/preview_tokens?type=checkout` → 200 while every
  other call on that host is `401 UNAUTHORIZED_API_CALL`. That is both a PoC enabler and a reportable
  auth inconsistency (demo-scoped, so Low/Info).

## 4. Observing the effect inside a cross-origin iframe (CDP)

- `Page.captureScreenshot` can stall (websocket timeout) on a tab whose iframe is a heavy cross-origin
  SPA. Fallbacks, in order: (a) read the iframe's DOM directly instead, (b) OS-level capture
  (`PIL.ImageGrab` on the visible desktop), (c) screenshot with a fresh CDP connection and no
  `Network.enable` subscription draining the socket.
- **Attach straight to the out-of-process iframe target** — `GET /json/list` shows it as
  `type: "iframe"` with its own `webSocketDebuggerUrl`; connect and run `Runtime.evaluate` to read the
  checkout DOM (`document.body.innerText`, button labels, computed styles) with no cross-origin barrier.
  This is the cleanest evidence channel for "the widget really changed".
- Also worth recording: the widget **initiates** the conversation (`GET_PARAMS`,
  `INIT_DIGITAL_PROVIDERS`, `PREVIEW_INITIALIZE`) and does so with `targetOrigin: "*"` — that alone
  proves the channel is cross-origin-live before you send anything.

## 5. Honest scoping when the funded page is unreachable

The receive-path defect is provable without a real payment: framing is absent (headers), the channel is
live (observed messages), and the handler code applies the parameters with no origin check (bundle).
What you usually **cannot** capture is a visual before/after on a live funded page — creating a payment
link often requires completed merchant onboarding:

```
POST /payment-link        -> 400 ..._GENERATE_HOSTED_CATEGORY_NOT_SUPPORTED   (no enabled categories / KYB)
POST /checkout-payment    -> same
UI: payment-method checkboxes rendered `disabled`, so "Create" never enables
```

When you hit that: file at **P4**, add an explicit "verification status — proved / not proved" section,
paste the blocker error verbatim, and hand the triager the two-line PoC they can run with one valid
link:

```js
const f = document.getElementById('f');
f.contentWindow.postMessage({type:'PARAMS', data:{hideOrderDetails:true, btnText:'Confirm'}}, '*');
f.contentWindow.postMessage({type:'CHECKOUT_SUBMIT_PAYMENT', data:{}}, '*');
```

Do not silently upgrade to P3 on static analysis alone.

## 6. Re-test before you submit (state drifts between sessions)

An earlier pass on the same target recorded "open OAuth DCR, arbitrary redirect_uri accepted, PKCE
`plain` allowed" as a lead. A later session re-tested the same endpoints and found the opposite: DCR now
rejects every non-loopback redirect (`redirect_uri is not allowed by the account configuration`),
`/authorize` validates the redirect against the registration, PKCE is S256-only, and the login page
offers only enterprise SAML. The lead was closed as **not exploitable** and would have been an
embarrassing submission. Rule: re-run the core assertions of any lead in the session where you plan to
submit, and log the new state with a date. Provider config (Cloudflare Access, WAF rules, feature flags)
changes quietly.

## 7. Sibling class — outbound `postMessage(data, "*")` from a POPUP auth helper (WebAuthn / OAuth)

Distinct from the embedded-iframe channel above: here the defect is the **outbound target
origin**, the page is a **popup helper** (not an iframe), and the leaked payload is
**authentication material**, not UI parameters. Worked case: RunOnFlux
`passkey.runonflux.com` (2026-10, F1 Medium — see
`references/runonflux-2026-10-engagement.md`).

Shape to look for — a small helper page opened via `window.open` that runs a ceremony
driven by **URL query params** and returns the credential to its opener:

```js
window.opener.postMessage({ type: action, success: true, data: result }, "*");
// result = WebAuthn { id, rawId, response:{ authenticatorData|attestationObject,
//          clientDataJSON, signature, userHandle } }
```

- **Detection is deterministic and cheap.** `curl -s "<helper>?action=Login&challenge=x&rpId=<domain>"`
  then `grep -c '"\*"'` → the number of wildcard call sites (RunOnFlux served 3: success,
  error, and a `beforeunload` close-notify). A pure sender has no `event.origin` to
  validate, so "no origin check on receive" is expected — the bug is the `"*"` target.
- **Separate the sensitive call from the noise.** The `{type:"close"}` beforeunload
  postMessage is harmless; the credential-bearing success handler is the finding. Quote
  the exact call site in the report.
- **Impact framing (honest Medium, not auto-High).** The assertion reaches any origin
  that opened the popup. Attack: an attacker page opens the *legitimate* helper URL with
  a challenge from a login flow it initiated; the user completes the prompt (the domain
  is authentic, so the phishing is convincing); the assertion lands on the attacker, who
  finishes the login as the user. Caveats that keep it out of "critical": it needs user
  interaction, and the browser validates `rpId` against the page's registrable domain so
  the RP cannot be swapped — the leak stands, the RP-forgery does not.
- **Also grep the params.** `challenge`/`rpId`/`user`/`rp` read straight from
  `URLSearchParams` means the ceremony is driven by attacker-supplied values; note it,
  but the browser's rpId rule is what actually bounds the blast radius.
- **Chain hook:** if the same product has a signature-replay primitive (e.g. a
  self-issued/stateless login phrase valid until its timestamp ages out), a captured
  assertion or signature upgrades from "leak" to "replay" — say so explicitly rather
  than leaving the chain implied.
