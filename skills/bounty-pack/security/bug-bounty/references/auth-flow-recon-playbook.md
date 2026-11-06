# Auth-Flow Recon Playbook (signup / login / recovery)

Derived from Luno staging engagement. Class-level: applies to any target's unauthenticated auth surface.

## Flow probing order (unauthenticated)

1. **Signup:** fill form → submit → capture the app's own POST (hook before triggering — see camoufox skill for main-world fetch+XHR hooking). Do NOT guess param names; capture the real request. Real param may differ from intuition (`g-recaptcha-response`, not `captchaToken`).
2. **Login with the just-submitted creds** — this is the ONLY reliable "did the account actually get created" check. Server 500/2xx on signup proves nothing.
3. **Recovery:** request recovery for an email you control, note the URL/token shape, then test token semantics (below).

## Email enumeration FALSE POSITIVE

Some apps always advance to the password step regardless of whether the email exists (Luno did). "It showed me the password field" ≠ account exists. The reliable negative signal is submitting a wrong password and getting "email or password is not correct".

## Pre-issued recovery token pattern

Some login pages generate a recovery token for ANY typed email before the user requests recovery — visible as `/recover?token=...` inside the "Forgot password" href before any POST.

Test ladder (each step = higher severity; stop honestly where gated):
1. Does the token vary per email? (two emails → two tokens = email-specific generation, not a static bootstrap token.)
2. Does the token load a "create new password" page without email access?
3. Is the page merely a shell gated by a verification step (email 6-digit / SMS code / personal-info challenge)?
4. Exhaust the "Try another way" chain (email code → SMS code → generic rejection) BEFORE judging.

**Honest verdict rule:** if any gate requires access to the victim's email/phone, the chain is DEAD — report INFO/LOW (pre-auth token issuance is still reportable as unnecessary attack surface), never claim ATO. Blocked chain = INFO (standing user rule: severity inflation = omong kosong).

## Signup 500 on valid submission

A 500 with a trace ID on a fully-valid POST (correct csrf + fresh captcha token) is a server-side unhandled exception. Report with: trace ID, exact captured request, and the login-probe result proving whether a side effect occurred (account created or not).

## reCAPTCHA during auth testing

See camoufox skill (keyboard Tab+Space solve, coordinate-click image challenges, escalation-to-image-challenge on repeated solves). Budget for the challenge rotating per attempt; keep sessions warm to reduce re-solves.

## Evidence hygiene

- Capture the app's real request via hook; guessed-param replays produce misleading 400s and wasted cycles.
- Login-probe result is ground truth for "did signup succeed".
- Every severity claim must survive the chain-gate test above.
