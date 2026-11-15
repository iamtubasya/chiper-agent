# Framing protection + postMessage control channels (embedded / checkout surfaces)

Two independent checks that combine into one finding on any page **designed to be embedded**
(hosted checkout/payment pages, SDK iframes, widget portals, OAuth consent screens) or any page that
ships a `window.addEventListener('message', …)` handler.

## Check 1 — can ANY origin frame it?

```bash
curl -s -D - -o /dev/null -H 'X-Bugcrowd: Bugcrowd-<user>' -A '<normal browser UA>' '<url>' \
  | grep -iE '^HTTP/|x-frame-options|frame-ancestors|referrer-policy'
```

**TRAP — only trust headers that came from a genuine `200`.** In this session a first probe showed
`X-Frame-Options: SAMEORIGIN` and the page looked protected; the real 200 had **no** framing header at
all. The `SAMEORIGIN` came from the Cloudflare **429 rate-limit page**, which carries its own headers.
Print the status line and the headers together, and re-check after the rate limit clears (wait, then
retry once). Never report "framing is blocked" from an error response.

Then confirm dynamically: frame the page from a different origin (harness below). A page that renders
inside your iframe is frameable regardless of what you think the headers said.

## Check 2 — does the receive handler validate `event.origin`?

Grep the JS bundle for `addEventListener("message"`, find the handler, and follow it:

- Missing `e.origin` / `event.origin` check → no validation. *(Rapyd's hosted checkout: the handler
  switches on `e.data.type` and never reads `e.origin`.)*
- Catalogue the accepted types — impact lives there. From Rapyd's `g$` handler:
  `PARAMS` → `hideOrderDetails` (hides the amount/order), `hideCartItems`, `hideSubmitButton`,
  `btnText`, `btnColor`, `customStyles` (arbitrary CSS; only the literal `url(` is filtered),
  `mobileView`, `enableRedirect`, `waitOnPaymentRedirect`; and
  **`CHECKOUT_SUBMIT_PAYMENT` → dispatches a payment submission**.
  A sibling preview handler (`S$`) may take `PREVIEW_PARAMS` / `PREVIEW_SET_CARD_DETAILS` — plenty of
  prompt-injection bugs come from testing the wrong message family, so read which handler is installed
  for which page type.
- Outgoing direction is the second signal: `window.parent.postMessage(msg, "*")` lets any parent read
  it, and a widget that *initiates* the exchange (`GET_PARAMS`, `INIT_DIGITAL_PROVIDERS`,
  `PREVIEW_INITIALIZE`) hands you a live channel for free.

## Harness (attacker origin, local) — this is also the PoC

1. Serve **one** page on `http://127.0.0.1:<port>` that (a) iframes the target, (b) logs every
   received message as `e.origin + JSON.stringify(e.data)`, (c) exposes one button per crafted payload
   sent with targetOrigin `'*'`.
2. Need a token you cannot mint? Look in the bundle for a **preview/demo token endpoint**. Rapyd:
   `GET https://sandboxapi.rapyd.net/v1/hosted/config/preview_tokens?type=checkout` → `200` with demo
   checkout tokens and **no access key or signature**, while every other endpoint on that host returns
   `401 UNAUTHORIZED_API_CALL`. A demo token is enough to prove framing + channel; a real payment token
   needs a merchant/KYB account. (Report the auth inconsistency separately, low severity.)
3. Read the frame's DOM through its **OOPIF target** to capture before/after state —
   see `browser-cdp-auth-audit` → "Cross-origin iframes (OOPIF) + screenshots that never return".
4. Trace what the widget *does* with `Network.enable` + `Network.requestWillBeSent` when you need to
   show the attacker page triggered a server-side action.

## Severity, honestly

- Frameable + a message channel that can hide the amount / relabel the CTA / trigger submission =
  **payment-consent manipulation** → argue P3, accept P4. Never claim the attacker can move funds.
- State exactly what you could not prove. Here: a visual before/after on a live payment page was
  impossible without a merchant account (the preview page renders only after the merchant-SDK
  handshake with a real payment context). Evidence was (a) production framing, (b) a live
  bidirectional cross-origin channel, (c) the handler code applying the params — plus a 2-line repro
  snippet for when the triager supplies a test payment link.
- If the page is frameable only on sandbox/preview hosts and **not** on production, the finding is much
  weaker. Prove which host first and say so.

## Case: Rapyd hosted checkout (2026-09) → RAPYD-2026-008

- `checkout.rapyd.net`, `hosted.rapyd.net`, `sandboxcheckout.rapyd.net`,
  `sandboxcheckout-preview.rapyd.net`, `qacheckout.rapyd.net`: all `200` with no `X-Frame-Options` and
  no `frame-ancestors`.
- Attacker-origin page framed `https://sandboxcheckout.rapyd.net/hosted/preview?token=<demo>` and
  received `GET_PARAMS` / `INIT_DIGITAL_PROVIDERS` / `PREVIEW_INITIALIZE` from it (targetOrigin `*`).
- Correct demo path is `/hosted/preview`; `/hosted/checkout` 404s on the sandbox host.
- Verdict: P4 baseline, P3 argued (payment page + consent manipulation).

## Variant — load the widget on YOUR origin when you must OBSERVE the injected effect

The harness above frames the target, so the widget's DOM is cross-origin and you read it
via the OOPIF target. When the widget is a **publicly-loadable JS bundle**
(`SendSafelyDropzone.min.js`, a hosted-checkout SDK, any embeddable widget), skip the
framing and get direct DOM observability:

- Parent page on `http://localhost:<port>` loads the real widget JS and initialises it
  (the public apiKey/dropzoneId ships in the page — it is not a secret). The widget now
  runs in YOUR origin, so you read its DOM/state directly.
- A sibling iframe on `http://127.0.0.1:<port>` — a genuinely different origin from
  `localhost` — injects the spoofed commands with `parent.postMessage(payload, '*')`.
- Read the result straight off the parent: mutated widget state (e.g. `widget.packageCode`),
  injected DOM rows, a `finalize`-callback URL. No OOPIF target, no screenshot guesswork.

`localhost` vs `127.0.0.1` are two distinct origins, so this is a real cross-origin
injection, not a same-origin trick. Drive it in headless Chrome over CDP; when the MCP
browser backend is unavailable, Node v24's built-in global `WebSocket` is a
zero-dependency CDP client — connect to the page target's `webSocketDebuggerUrl` from
`GET /json`, send `{id,method,params}`, match replies by id; `Runtime.evaluate` +
`Page.captureScreenshot` cover validation + evidence. This is exactly how the SendSafely
Dropzone postMessage origin-bypass was validated 3x (2026-10-23): foreign-origin
`file-uploaded` set `widget.packageCode`, and a spoofed `package-link` delivered an
attacker URL to the `finalizePackage` callback that the page forwards as the "secure link".
