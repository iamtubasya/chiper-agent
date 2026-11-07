# Captcha-gated registration, fingerprint anti-fraud, and session-lifecycle testing

Distilled from the djangoeurope engagement (2026-10-19, Django hosting panel: Angular SPA + DRF API
at api.<target>, panel at panel.<target>). Covers four reusable techniques that sit *upstream* of
the IDOR/RCE batteries in `drf-authed-surface-verification.md`: getting an account at all when
signup is captcha + fingerprint gated, driving the authed API from a real browser, and the
session-lifecycle tests that only work once you hold a token.

---

## 1. ALTCHA proof-of-work: reverse the widget, then solve it in Python

ALTCHA (the `<altcha-widget>` custom element, `altcha/altcha.min.js`) is a PBKDF2 proof-of-work
captcha. It is fully client-side and solvable offline once you know the byte layout — do not
brute-force the endpoint, solve the challenge.

**Fetch the challenge** (unauthenticated, scope-gated):
```
GET https://api.<target>/altcha/challenge/?scope=registration
{"parameters":{"algorithm":"PBKDF2/SHA-256","cost":20000,"keyLength":32,
               "keyPrefix":"00","nonce":"<32 hex>","salt":"<32 hex>",
               "expiresAt":<unix>,"data":{"scope":"registration"}},
 "signature":"<hex>"}
```
Scopes are enumerated by the server on a bad value (`Must be one of: registration,
password_reset, contact, test_account`) — probe with a wrong scope to list them.

**The exact construction** (extracted from the minified widget; getting this wrong is the whole
battle — the naive guess fails with "Verification failed"):
- PBKDF2 **salt** = `bytes.fromhex(parameters.salt)`
- PBKDF2 **password** = `bytes.fromhex(parameters.nonce) + struct.pack(">I", counter)` — the
  nonce bytes with a **big-endian uint32 counter** appended (`PasswordBuffer` in the widget;
  `counterMode` is `uint32` unless the challenge carries `_version: 1`, in which case it is the
  decimal counter as a UTF-8 string)
- Find `counter` where `pbkdf2_hmac("sha256", password, salt, cost, keyLength).hex()` starts with
  `keyPrefix` (typically 2-3 tries for prefix "00", ~2 s)
- **Solution payload** = base64 of:
  `{"challenge": {"parameters": <verbatim challenge parameters>, "signature": <sig>},
    "solution": {"counter": <n>, "derivedKey": <hex>, "time": <ms>}}`
- POST it as the `altcha` field of the registration body (base64 string, not a nested dict)

The server then verifies the signature and recomputes the PoW. Solving it proves nothing about
the anti-fraud layer — see §2.

## 2. Fingerprint anti-fraud beats IP rotation — register through a real browser

The registration endpoint accepted a perfectly-solved ALTCHA from raw HTTP and still answered
`{"non_field_errors":["Detected as spam."]}` — on **every** egress IP (verified across a WARP
rotation). The block is browser-fingerprint-based, not IP-based. Repeated attempts then trip a
24 h per-IP throttle on the account-creation endpoints (`429 ... Expected available in 86399
seconds`).

**What worked: drive the real panel form in a real browser.**
- Playwright + the installed Chromium (on this host:
  `~/.local/share/ms-playwright/chromium-1234/chrome-win64/chrome.exe` —
  Playwright's default headless-shell version often does not match the installed browser; pass
  `executable_path` explicitly, and check `ls ~/.cache/ms-playwright/` for the real
  version dir). If the SeleniumBase MCP tool errors out, drop to direct Playwright — same result.
- `--disable-blink-features=AutomationControlled`, a real UA, `locale`, viewport.
- Navigate to the **actual route** — the panel's registration route was `/create-account`, not
  the `/user/create-account` string that appears in bundle link targets; a wrong route silently
  redirects to `/login` and every `fill()` times out.
- Fill by the template's real field ids (`#email_id`, `#first_name_id`, `#password_id`,
  `#password_confirmation_id`), then **wait for the ALTCHA widget to self-solve**
  (`altcha-widget[state=verified]`, up to 30 s) before submitting. The widget's real JS execution
  is what the fingerprint check wants.
- Email verification: the link is `panel.<target>/create-account-confirmation/<uuid>/validate/<code>`;
  the API call behind it is `GET /email/<uuid>/validate/<code>/` (uniform "Invalid validation
  code." on garbage — no oracle, no low-volume rate limit).

**Recovery path when the password is unknown:** the reset flow is
`POST /password_reset/ {username, altcha(scope=password_reset)}` → email carries
`panel.<target>/password_reset/<uuid>` → `POST /password_reset/<uuid>/ {password}`. Reset tokens
are single-use (reuse → "Password reset expired."). Login is enumeration-safe (uniform "Unable to
log in with provided credentials.") and rate-limited (10 attempts → 429, ~5-15 min window).

## 3. Rotating-token auth: cookie + header together, and a request budget

The DRF API authenticated with **both** a cross-origin cookie jar and an Authorization header:
- Header: `Authorization: Token <token>` where `<token>` is the value of the `token` cookie
  (40-char hex, set from the login response; the panel's interceptor only refreshes the cookie
  *expiry* from the `X-Token-Expires-At` response header — the value itself is stable)
- `credentials: 'include'` on every fetch — without the cookies the same token answers
  `401 Invalid API token` / `API token has expired`, which reads like rotation but is the missing
  cross-origin credential binding
- **Request budget:** after roughly ~10 rapid authenticated requests the token starts answering
  401 until a fresh login. Batch probes, add delays, or re-login per batch. Multi-step sequences
  (list → delete each) must re-read the cookie or re-login between steps.
- Practical pattern: do authenticated probing **from inside the logged-in browser page**
  (`page.evaluate` with a fetch helper that reads `document.cookie` and sets the header), so the
  session, rotation, and cookies are all handled by the real client.

### 3b. v2 refinement (2026-10-24): the `webkey` cookie is the real authenticator; token rotates PER LOGIN; drive it from a cookie-jar opener

The MFA login path sharpens §3 in three ways that each cost a full round:

- **The session authenticates via the `webkey` HttpOnly cookie, NOT the JSON token.** `POST /login/mfa/` sets `Set-Cookie: webkey=<40-hex>; HttpOnly; SameSite=Lax; Secure` AND returns a JSON body `{token, id, expires_at}` where `token` is a DIFFERENT 40-hex value. The DRF endpoints accept the **cookie** (sent automatically by a cookie-jar opener) and reject the bare `Authorization: Token <json_token>` header with `401 Invalid API token` / `API token has expired`. So: build `opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookiejar))` and route EVERY authed call through that opener — bare `urllib.request.urlopen` (no cookie) fails. Adding the header too (to mimic the panel) is harmless; the cookie is what actually works.
- **The token/cookie ROTATES on every login — only the most-recent login is valid.** A fresh `/login/`+`/login/mfa/` invalidates the previous token (it then answers `expired`/`invalid`). This CORRECTS the §3 "value itself is stable" note: stable within one live session, but a new login rotates it. Practical rule: **do the login and ALL authenticated tests inside ONE script/process**; never persist the token to a file and reuse it in a later run (guaranteed 401). A cross-run "expired token" is almost always a rotation artifact, not a bug.
- **Email-OTP MFA login automation** (MFA gates LOGIN here, not just signup): `POST /login/ {username,password}` → `{mfa_required:true, mfa_token, devices:[{id, otype:"email", name:"E-mail"}], email_sent:true}` → a 6-digit code arrives by email from `info@<target>`, subject "Your login verification code" → poll it with imap_tools (newest matching message, `re.findall(r'\b(\d{6})\b', text)`) → `POST /login/mfa/ {mfa_token, otp_device_id, otp}` → `{token, id, expires_at}`. Codes expire ~10 min and are single-use; the `mfa_token` is short-lived, so fetch the OTP promptly and submit immediately. Wrap the whole login in a retry loop (OTP/mfa timing is flaky across runs — a run that returns no token just needs a retry, not a different approach).

## 4. Session-lifecycle battery (run once you hold a token)

Add these to any authed audit — they are cheap and the second one paid out on djangoeurope:

1. **Does a password change invalidate existing sessions?** Capture token A → change the password
   (`PATCH /user/<id>/ {current_password, password: new}` — verify the change is real: old
   password → 400, new → 200) → replay token A. If it still returns 200, **sessions survive the
   password change**: an attacker holding a stolen token keeps access for the token's full
   lifetime (here 7 days) even after the victim's standard remediation. Eviction requires manual
   `DELETE /token/<id>/`, which is not part of the password-change flow. Reportable (Medium for
   panels whose accounts carry infrastructure access).
2. **Are reset tokens single-use?** Replay a consumed reset UUID → "expired" = good.
3. **Login rate limit / enumeration** — 10 attempts → 429 and uniform error bodies = good.
4. **MFA endpoints** may accept unauthenticated POSTs but must validate the server-issued
   `mfa_token` before touching devices/OTPs ("This login challenge has expired." on garbage) —
   correct design, record the negative.

## 5. Lazy-chunk harvesting for the paywalled surface

When creation endpoints fail with "requires an active product" (paywall), the panel's lazy-loaded
chunks still contain the exact payload contracts. Visit every feature route in the browser
(`/ssh`, `/domain`, `/website`, `/payment`, `/installer`, ...), capture the `*.js` chunk responses,
download them, and grep for `post("<resource>"` / `patch("<resource>"` call sites plus the
payload construction (`let t={name:...}; t.server=...; t.planprice=...`). This yields the field
names and shapes needed to (a) reach deeper validation errors and (b) test ownership overrides on
nested creation — even before a paid product exists.

## Pitfalls (this engagement)

- **`execute_code` runs NATIVE Windows Python — MSYS paths are invisible to it.** The git-bash
  `terminal` tool understands `/d/data hermes/...` and `/c/Users/...`, but `execute_code`'s Python
  does NOT: `open('/d/data hermes/x/evidence.txt','w')` → FileNotFoundError. Inside `execute_code`
  always use native paths (`D:/data hermes/...` or `/home/agentuser`); reserve MSYS `/d/...`,`/c/...`
  for the `terminal` tool. (Generalises the old '/tmp is invisible' note — it is ALL MSYS paths, not
  just /tmp.) A path mistake here silently wastes a whole login cycle when the write is the last step
  of an expensive MFA-authenticated capture.
- **The output redactor masks secrets in DISPLAY only** — a captured request body showing
  `"password": "cekChr...aB1!"` was the full 20-char password on the wire; the file on disk is
  intact. Don't "fix" a redacted-looking value.
- **Playwright `page.evaluate` with backticks in payloads** — a name like `` detest`id` ``
  inside a JS template literal is a SyntaxError. Pass test vectors as an argument array, never
  inline them in the evaluated JS.
- **Truncated `slice(0, N)` response bodies** break `json.loads` mid-test — slice generously
  (20 k+) or parse in-page and return only the fields you need.
- **A 500 on creation is not injection-reachable** — if every payload (including a benign one)
  500s, the failure is backend state (no subscription), and name/command injection cannot be
  tested until a valid product exists. Record it as a robustness note, not an RCE.
- **Login throttles are IP-wide and long** — budget login attempts; after a rate-limit test, wait
  out the window or expect every later login in the session to 429.
