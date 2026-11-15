# FCaptcha empty-signals bypass (self-hosted instances)

Verified live 2026-10-26 on portal.first.org (FIRST bug bounty): 8+ successful token
mints, full account creation and password-recovery e-mail dispatch via the bypass.

## When this applies

Any target that self-hosts **FCaptcha** (open-source, github.com/WebDecoy/FCaptcha,
also mirrored as Mr1Stark/fcaptcha; MIT; server in Python/Node/Go). Detection:

- Page loads `/_fcaptcha/fcaptcha.js`, `/fcaptcha.js`, or a `data-fcaptcha="..."`
  attribute on a hidden form input (value starts as `none`).
- `POST /_fcaptcha/api/score`, `/api/verify`, `/api/token/verify` respond.
- The client JS (`fcaptcha.js`) documents `mode:"invisible"`, `siteKey: <host>`.

## The technique

FCaptcha scores a **client-supplied** bundle of behavioral signals (mouse movement,
timing, fingerprint data) plus a proof of work, and mints a signed token when the
score is below the pass threshold (0.5). The signals are self-reported; the server
has no ground truth except TLS/IP. An empty signal set scores ~0.40 and PASSES:

```
POST /_fcaptcha/api/score
Content-Type: application/json

{"siteKey":"<target-host>","signals":{}}

-> 200 {"success":true,"score":0.4035...,"token":"eyJzaX...",
        "action":"","recommendation":"challenge"}
```

The upstream source itself admits the weakness: a comment in `detection.py` notes a
bare `curl` with no signals "reached 0.1298 against a 0.5 threshold".

Then use the token exactly where the widget would put it: the protected form's
hidden `_utoken` field (initially `none`), submitted with a fresh CSRF token:

```
POST /auth/confirm
email=<address>&wantsurl=<base64>&_utoken=<token-from-score>&__req=<csrf>

-> 200 "Please check for an email sent to <address>..."
```

No browser, no mouse movement, no PoW required.

## Impact and how to frame it

- Anti-automation control ineffective (CWE-799): mass account creation, and
  confirmation/recovery e-mail dispatch to ARBITRARY addresses (phishing amplifier
  on the vendor's mail reputation).
- **Measure the integrating app's quota separately from FCaptcha's own limiter.**
  FCaptcha's in-memory limiter is ~10 mints/min/key; the app may add a soft
  per-address warning (observed: warning at ~4 requests, still sending at 12/15,
  no hard block). Report the measured numbers, not the assumption.
- Severity is typically Low-Medium (abuse/resource impact, no data breach). Say so.

## Pitfalls

- The token is single-use and the integrating backend verifies it server-to-server
  with a secret (`/api/token/verify`, `REQUIRE_VERIFY_SECRET`); you cannot forge
  tokens, only mint legitimate ones via the permissive score path.
- Read the deployed instance's behavior, not the repo defaults: check whether
  `/api/score` enforces PoW on your target (some configs fail closed).
- Same bypass usually covers every FCaptcha-protected endpoint on the host
  (signup, password recovery, contact forms) - enumerate them all.
