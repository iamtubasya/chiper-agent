# Multi-step wizard registration (PHP/LAMP style) — mapping, capture, and gate diagnosis

Verified on microkeeper.com.au (2026-10-17). Applies to any classic server-rendered app whose
signup is a multi-step wizard driven by one big inline `<script>` posting `action=<step>` to a
single PHP endpoint. This is the *other* half of the provisioning problem from the SPA/React
recipes: no framework, no source maps — the whole contract is in the page's inline JS.

## 1. Map the state machine from the inline JS before sending anything

The wizard's steps, field list, and AJAX contract are all in the page source:

```python
import re
h = open('register.html', encoding='utf-8', errors='ignore').read()
scripts = re.findall(r'<script(?![^>]+src)[^>]*>(.*?)</script>', h, re.S)
big = max(scripts, key=len)                      # the wizard script is the biggest inline block
print(re.findall(r"set_reg_data\('([^']+)'", big))          # every field the wizard collects
print(re.findall(r"action\s*=\s*'([^']+)'", big))           # every server-side step
print(re.findall(r'xmlhttp\.open\("POST", "([^"]+)"', big)) # the single endpoint
```

On Microkeeper this gave: steps `email_pin → verify_email_pin → abn → [ref_method,
your_details: client-side only] → sms_send → verify_sms_pin → create_account`, all POSTed to
`register.php` as `action=<step>&<params>&val=nul`. Two steps were **client-side only**
(`next_step()` with no XHR) — knowing which steps hit the server is what tells you where the
server-side gates actually are.

All steps live in ONE DOM (shown/hidden via CSS) — `document.querySelectorAll('.reg_step')`
plus `offsetParent !== null` finds the visible one; `next_step()` (a global fn) advances
without clicking.

## 2. Email PIN: read it from the operator's mailbox, extract by context

- Use a **plus-alias** (`operator+mktest1@gmail.com`) — it tags the account and lands in the
  real inbox. A Gmail **dot-variant** (`mk.redteam.test@gmail.com`) is a *different mailbox*
  (dots are only ignored for the base address, and `mkredteamtest@` ≠ `RESEARCHER_USERNAME@`) — the PIN
  silently goes somewhere you cannot read. Plus-alias, always.
- Read with the Gmail API token (`%LOCALAPPDATA%\hermes\google_token.json`), poll
  `newer_than:1h`, and extract the PIN **by context** (`PIN is:\s*(\d+)`), never "first 6-digit
  run" — the same email carries CSS colours that look like codes.
- The verification email also contains a **signed link**
  (`?reg_email=…&hash=<64-hex>&exp=<unix>`): SHA256, ~24 h expiry. Phase-2 requests carry
  `hash` + `email` + `exp` (note: the POST param is `email`, the URL param is `reg_email`).

## 3. When curl archaeology fails, hook XHR in the browser and capture the real request

Symptom: you replay what the JS *appears* to send and the server answers a generic error
("Email address missing") for every param-name variant you try. Stop guessing names — capture
the wire format the real client sends:

```javascript
// via browser_cdp Runtime.evaluate on the page
window.__xhrLog = [];
const oOpen = XMLHttpRequest.prototype.open, oSend = XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.open = function(m, u) { this.__m = m; this.__u = u; return oOpen.apply(this, arguments) };
XMLHttpRequest.prototype.send = function(b) {
  if (this.__u && this.__u.includes('register.php')) window.__xhrLog.push({m: this.__m, u: this.__u, body: b});
  return oSend.apply(this, arguments);
};
```

Then drive the wizard (fill inputs with the native setter + `input`/`change` events; selects
need their **option values**, not display text — dump `[...el.options].map(o => o.value)` first)
and read `window.__xhrLog`. On Microkeeper this exposed what curl archaeology could not:
`dial=61` (no `+`), `phoneno` with leading `0`, `busname` echoed from the ABR lookup, and the
exact param order. Differences this small are exactly what a hand-built request gets wrong.

## 4. Diagnose gates from behaviour, not from the error string

- **No cookies ≠ no state.** `document.cookie` showed only analytics tags; the server tracked
  registration state server-side keyed by email + the signed hash. Don't hunt for a session
  that doesn't exist.
- **A generic error on a LATE step usually means an EARLIER step's server-side gate.**
  `create_account` kept answering "Email verification parameters missing" with
  byte-identical correct params — the real gate was the unverified **SMS PIN** step. The
  message names the wrong thing. Test enforcement by *forcing the client-side flag*
  (`sms_pin_verified = true` in the page, then click through) and watching whether the server
  still refuses — that separates client-side gating from server-side gating.
- **Steps that return empty bodies are usually successes** on these wizards (`ref_method`,
  `your_details` returned HTTP 200 with no body). Don't read "no JSON" as failure.

## 5. The SMS-PIN wall — and what it is NOT

Login-details-via-SMS is a hard gate: the PIN goes to a phone you don't control. Do **not**
fire SMS at arbitrary numbers (a stranger receives the vendor's welcome mail). Options in
order: operator's own number → operator-approved VoIP → park the authenticated plane and
report the blocker with the full mapped state machine (it is still deliverable intel: the
wizard, the signed-link scheme, the PIN length, and the enforced gate). Brute-forcing the
6-digit SMS PIN is rate-limited anyway (Cloudflare 1015 on register.php was observed within
~50 requests) — measure before claiming.

## 6. Rate limits compound across your own session

Sustained manual probing + the audit pipeline's traffic together tripped Cloudflare
(`429` / error `1015`) mid-session. When it fires: stop manual requests, let the pipeline
finish its phase, and resume after a cool-down. A 429 on a probe is not a finding about the
endpoint — re-verify after backoff before recording anything.
