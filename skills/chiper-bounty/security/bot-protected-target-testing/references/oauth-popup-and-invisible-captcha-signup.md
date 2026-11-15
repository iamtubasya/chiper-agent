# OAuth popup flows, invisible reCAPTCHA signup gates, and React wizard automation

Verified 2026-10-21 across three engagements (Proton signup, CodeRabbit OAuth, Cloudsmith
signup). All three failed the same way before the diagnosis below.

## 1. OAuth popup flow (Playwright) — the silent auth failure

CodeRabbit (`app.coderabbit.ai`): "Sign in with GitHub" opens the provider authorize URL
in a **popup** (`window.open`), not a full-page redirect. A script that only watches the
main page sees "URL never changed" and wrongly concludes the button is broken — the auth
actually completed in the popup window.

Fix:
```python
popups = []
ctx.on("page", lambda pg: (popups.append(pg), pg.bring_to_front()))
# click the provider button, then poll BOTH pg.url and [p.url for p in popups]
# success = main page leaves /login (popup carries ?code=...&iss=github.com/login/oauth)
```

Notes:
- Headless sometimes drops the popup click entirely (needs a trusted gesture). Headed +
  real mouse click on the button (`pg.mouse.click` at the button's bounding-box center)
  is the reliable combo.
- The OAuth authorize URL itself is worth capturing: `client_id`, `redirect_uri`,
  `scope`, and `state` (presence of state = good practice; note it in the report).
- Session save: `ctx.storage_state(path=...)` right when the URL change is detected —
  a crash before the save loses the whole handoff (one full CodeRabbit round was lost
  this way).

## 2. Invisible reCAPTCHA signup gate — diagnosis via network capture

Cloudsmith (`app.cloudsmith.com`): the multi-step signup wizard's final Continue is gated
by **invisible reCAPTCHA v3**. When the score fails, the app blocks SILENTLY: the button
label flips to a processing state ("Verification") and **no request leaves the browser**.
Symptom is identical to "React state didn't register" (§3) — the two are distinguished by
network capture.

Diagnostic sequence:
1. Fill the form, click submit with a REAL mouse click (`locator.click`, not JS click).
2. Capture ALL non-telemetry requests during the submit window (filter out datadogh /
   sentry / vercel / static assets).
3. If only telemetry fires and zero app API or Server-Action requests → the gate is
   client-side (captcha or React validation), NOT the backend rejecting you.
4. The reCAPTCHA iframe appears during submit:
   `google.com/recaptcha/api2/anchor?ar=1&k=<SITEKEY>` — record the sitekey for the report.

Headless AND headed-automated both fail the score (no mouse movement, no typing cadence,
no cookie history). A human driving the same headed window can pass. Do not grind
automated retries against it — that burns the session clock; hand off to the user.

## 3. React wizard automation — what actually works

Rules learned the hard way, in order of reliability:

- **Synthetic value setters do NOT register.**
  `Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el,val)` +
  dispatched `input`/`change` events sets the DOM value but React's controlled-component
  state stays empty → submit does nothing. `locator.click()` + `keyboard.type(value,
  delay=40-70)` (trusted events) works for most inputs.
- **Terms checkboxes are custom components**: `input.click()` via JS or via raw mouse
  coordinates often no-ops. Clicking the associated `<label>` text works (verified
  Cloudsmith: `pg.locator("label:has-text('service terms')").first.click()`).
- **Auto-filled fields**: a username field may auto-populate from the email local-part
  (Cloudsmith did this). Clear it (`Ctrl+A`) and retype if a clean value is needed; also
  note the auto-fill value in the report if it leaks the email into the username.
- **Wizard state is fragile**: a page reload mid-flow resets the wizard to step 1. Run
  the whole flow in one page session; never reload to "check state" — inspect the DOM
  instead.
- **Off-screen inputs**: some wizard steps render inputs at negative x (off-viewport;
  Proton signup username). `scrollIntoView({block:'center',inline:'center'})` before
  interacting, or the keystrokes land nowhere.
- **Field-name casing matters on tRPC-ish backends**: Proton's invite endpoint wanted
  `InviterAddressID` (capital ID) while its own error message said `InviterAddressId` —
  probe both casings before concluding a field is "missing".
- **When all of the above fails**: hand off to a headed window and let the user type.
  Trusted input defeats both the React-state issue and the captcha score at once. Keep a
  polling loop watching for the URL to leave `/signup` / `/login`, save
  `storage_state` immediately on change, and keep the window open for a few minutes
  after as buffer.

## 4. Signup-gate report language

When a target's authenticated surface is unreachable because of an anti-automation
signup gate, the honest close is: "account creation gated by invisible reCAPTCHA
(sitekey <key>); automated and manual attempts both failed the score; authenticated
testing (entitlements/custom-domains/api-key-rules) requires an account" — plus the
unauthenticated surface that WAS mapped. Do not claim the authenticated surface is clean;
it is untested.
