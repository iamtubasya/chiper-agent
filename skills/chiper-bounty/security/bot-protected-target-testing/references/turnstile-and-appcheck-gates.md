# Turnstile 400020, honeypot short-circuits, and App Check gates

Measured 2026-10-29 on `www.ngrave.io` (Next.js + Payload CMS) and `*.api.cloud.ngrave.io`
(Firebase App Check + Firebase Auth). Every item below was reproduced ≥3× unless marked.

## 1. Turnstile error 400020 = "invalid widget size" — the token never exists

Symptom set (all four together is diagnostic):

- `window.turnstile` is present, `Object.keys(window.turnstile)` = execute/getResponse/
  isExpired/ready/remove/render/reset.
- `document.querySelectorAll('iframe').length === 0` — the widget iframe was never created.
- A hidden `input[name=cf-turnstile-response]` exists with `value=""` forever.
- Console: `[Cloudflare Turnstile] Error: 400020.` plus `Failed to load resource: … 400 ()`
  and a `postMessage` origin-mismatch warning against `challenges.cloudflare.com`.

Root cause: the render container has **no layout box**. On SPAs the widget host is often a
`<div data-testid="…-turnstile">` inside a section that never laid out (hidden tab, `display:none`
ancestor, zero-height flex child, CSS chunk not applied). Turnstile rejects the zero-size render
and emits 400020 instead of `110100` (invalid sitekey).

Fix — force a box before rendering, and do NOT re-render into the same collapsed container
(re-rendering reproduces 400020, which is the trap when you retry blindly):

```python
pg.evaluate("""(sitekey) => {
  try { window.turnstile.remove(); } catch(e){}
  const el = document.querySelector('[data-testid="cdd-turnstile"]');
  el.innerHTML = '';
  el.style.width = '320px'; el.style.height = '80px'; el.style.display = 'block';
  window.__tok = null;
  window.turnstile.render(el, {sitekey, theme:'dark',
    callback: t => { window.__tok = t; },
    'error-callback': e => { window.__err = String(e); }});
}""", SITEKEY)
# then poll window.__tok and read window.__err when it stays null
```

Reading `__err` is what turns "token is always null" into a 30-second diagnosis instead of an
hour of clicking iframes that don't exist.

**Rule:** a widget that cannot issue a token is *not* a finding. It only means the happy path is
unavailable to you. The finding — if any — is whether the **server** still honours the request
without a valid token. Test that directly (next section).

## 2. Honeypot field short-circuits the anti-bot check (real logic flaw pattern)

The form carried a hidden `honeypot` input. Behaviour matrix (each 3×):

| payload | result |
|---|---|
| valid fields, `honeypot: ""` | `{"ok":false,"reason":"robot"}` |
| valid fields, `honeypot: "bot"` | `{"ok":true,"requestId":"CDD-XXXX-2026-1029"}` |
| `email:"bad"`, `honeypot:"bot"` | `{"ok":false,"reason":"invalid"}` |
| `confirmWord:"NOPE"`, `honeypot:"bot"` | `{"ok":false,"reason":"invalid"}` |
| `order:""`, `honeypot:"bot"` | `{"ok":false,"reason":"invalid"}` |

Interpretation: the honeypot is wired as an **allow** signal, not a deny signal — a non-empty
honeypot makes the handler return early *success* and skip Turnstile verification entirely.
Field validation still runs first, which is why `invalid` wins when a required field is bad.

Ordering is therefore: schema validation → honeypot branch (bypass) → Turnstile (skipped).

**Discipline — the expensive mistake here.** `{"ok":true,"requestId":"…"}` is NOT proof that a
record was created. A requestId can be generated and returned without any write. Before claiming
impact you need a read-back: a confirmation email arriving in a mailbox you control, an admin
listing that shows the row, or a follow-up endpoint that returns it. Absent read-back the honest
statement is *"the anti-bot control is not enforced for requests carrying a non-empty honeypot"*
— never *"arbitrary deletion requests are written"*. Reporting the latter without read-back is
the fastest way to get a triager to distrust the whole report.

## 3. Firebase App Check — use the error envelope to decide if spoofing is worth trying

Two different 401 envelopes on the same host, different byte lengths:

- no App Check header → `{"errors":[{"id":…,"status":401,"code":"MISSING_HEADERS","title":"Missing headers","detail":"Missing headers"}]}` (149 B)
- bogus `X-Firebase-AppCheck: test` → `{"errors":[{"id":…,"status":401,"code":"UNAUTHORIZED","title":"Unauthorized","detail":"Unauthorized"}]}`

The **envelope change** is the signal: the header is parsed and its value is actually verified
against Firebase attestation. If a bogus value still returned `MISSING_HEADERS` the guard would be
presence-only and worth attacking; flipping to `UNAUTHORIZED` means real verification and header
spoofing is dead — stop spending time there.

Harvest the header name from the app bundle, not from guesses. Hermes/React-Native bundles keep
it as a literal next to the interceptor name:

```
…n_ai.request.top_parseCookieHeaderswap.to_coinBalanceStretchOutX-Firebase-AppCheck uw Link by Stripe…
```

## 4. Firebase Auth posture enumeration without any credentials

The apiKey embedded in the APK/bundle is **public by design** — treat it as a discovery tool, never
as a finding. With it you can read the auth posture in four calls:

| call | response | meaning |
|---|---|---|
| `accounts:signUp` with email+password | `OPERATION_NOT_ALLOWED` | email/password provider disabled |
| `accounts:signUp` with no email | `ADMIN_ONLY_OPERATION` | anonymous provider disabled |
| `accounts:sendOobCode` `EMAIL_SIGNIN` | `OPERATION_NOT_ALLOWED` | magic-link disabled |
| `accounts:createAuthUri` `providerId=google.com` | 200 + `authUri` containing `client_id=<num>-…apps.googleusercontent.com` | **only** login path is Google SSO |

That last row is the important one: it tells you the entire auth surface is federated Google, so
there is no password-reset/registration flow to attack and no credential to spray. `sendOobCode`
with `requestType=PASSWORD_RESET` returning 200 for an arbitrary address confirms a reset path
exists but does not tell you whether the account exists (no enumeration oracle).

Consequence for planning: to reach anything behind App Check + Google-only auth you need a real
device that passes Play Integrity plus a Google account. That is a scoped decision for the
operator, not something to brute-force from a workstation.

## 5. Don't confuse "gated" with "absent" — guards are per-route

On the same host, in one sweep:

- `/api/v1/info` → `200` `{"version_zero":"1.8.0","version_app":"2.10.5","server_version":"5.1.2",…}`
- `/api/v1/health` → `200` `Hello NGrave!`
- `/api/v1/{currencies,nfts,portfolio,support}` → `401 MISSING_HEADERS` (App Check)
- `/docs` → nginx basic auth, 172 B HTML (a *third* gate family)

Three guard families, all answering 401-ish. Bucket results by **body**, not status, or the
ungated `/info` sibling hides inside the "everything is 401" pile. See
`fuzzing-false-negative-pitfalls` §Pitfall 1b for the sweep-level version of this.
