# ALTCHA proof-of-work, fingerprint anti-fraud, and rotating-token sessions

Session-proven techniques (djangoeurope hosting panel, 2026-10-19) for targets that gate
registration/contact forms behind ALTCHA PoW and behavioral anti-fraud.

## 1. Solving ALTCHA from the widget bundle

Fetch the widget JS (commonly `/altcha/altcha.min.js`) and locate three things:

- the challenge parser (maps the server response into `{algorithm, cost, keyLength,
  keyPrefix, nonce, salt, expiresAt, data}` under `parameters`)
- the solve loop (`solveChallenge` / `PasswordBuffer`)
- the payload emission (grep `number:` and `btoa(JSON.stringify`)

**PoW computation (challenge response has NO `_version` field):**

```
salt_for_pbkdf2 = bytes.fromhex(parameters.salt)
password        = bytes.fromhex(parameters.nonce) + struct.pack(">I", counter)  # 4-byte BE counter appended
derived         = pbkdf2_hmac("sha256", password, salt_for_pbkdf2, parameters.cost, parameters.keyLength)
solved when     : derived.hex().startswith(parameters.keyPrefix)
```

**Payload (base64 of JSON, sent in the field the server's error names, usually `altcha`):**

```json
{"challenge": {"parameters": <full parameters object verbatim>, "signature": "<sig>"},
 "solution": {"counter": <n>, "derivedKey": "<hex>", "time": <ms>}}
```

**Version-1 challenges (`_version: 1` present in the response)** use a flat payload where the
field names are swapped relative to intuition:

```json
{"algorithm": "...", "challenge": "<keyPrefix>", "number": <n>, "salt": "<nonce>", "signature": "...", "took": <ms>}
```

Diagnostic ladder when verification fails: `Complete the verification challenge` = payload not
parsed (wrong field/format); `Verification failed` = parsed but wrong (wrong salt/counter
encoding or stale challenge); success moves the error to the next validator.

## 2. Fingerprint-based vs IP-based anti-fraud

Symptom: form submission returns a generic anti-spam error (e.g. `Detected as spam`) even with
a perfectly solved CAPTCHA, on every egress.

- Rotate egress once (WARP: `warp-cli connect`, verify with api.ipify.org) and retry. If the
  error is unchanged, it is **fingerprint/behavior-based**, not IP-based — stop rotating IPs.
- Fix: drive the real form with Playwright/Chromium. Real JS execution plus the widget solving
  itself passes. Fill by rendered selectors (`input[name=...]`, `#id`), submit, read the result
  from the page (success modal text, redirect URL).
- Egress rotation is still worth doing first: per-IP throttles (DRF throttling, 24h windows on
  `/user/` and `/test/`-style endpoints) reset with a new IP even when the anti-fraud does not.

## 3. Rotating-token + cross-origin-cookie API sessions

Some DRF APIs require BOTH `Authorization: Token <key>` AND the cross-origin session cookies:

- Header-only clients get `Invalid API token` / `API token has expired` even with a valid,
  unexpired token. The missing piece is `withCredentials` / fetch `credentials: 'include'`.
- Test from inside the page origin: `fetch(api_url, {credentials: 'include', headers:
  {'Authorization': 'Token ' + <token from document.cookie>}})`.
- Watch for a per-token request budget (~10 rapid requests, then 401). Space requests
  (~500ms+) or re-login when 401s start mid-sequence.
- Angular SPAs redirect unknown routes to /login: enumerate real routes from the bundle
  (`path:"..."` regex over main.js) before navigating.

## 4. Playwright launch pitfalls on this host

- The headless shell may be absent while full chromium exists. Launch with an explicit
  `executable_path` pointing at the INSTALLED version:
  `C:/Users/<user>/AppData/Local/ms-playwright/chromium-<N>/chrome-win64/chrome.exe`
  (`ls ~/AppData/Local/ms-playwright/` first — playwright's default expected version often
  does not match what is installed).
- Long browser flows exceed the 60s foreground tool limit: run them with
  `terminal(background=true, notify_on_complete=true)` and poll.
