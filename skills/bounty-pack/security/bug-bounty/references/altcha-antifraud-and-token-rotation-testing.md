# ALTCHA PoW solving, fingerprint anti-fraud triage, and rotating-token API testing

Worked case: djangoeurope.com hosting panel (2026-10-19). All three techniques are target-agnostic —
any SPA with a proof-of-work signup gate, application-level anti-fraud, or short-lived rotating
session tokens.

## 1. ALTCHA proof-of-work CAPTCHA — reverse-engineer and solve it

ALTCHA (`altcha-widget`, `altcha/altcha.min.js`) is a client-side PoW anti-bot. It is fully
solvable offline once you read the widget source. **Do not pay a solver service and do not give up
on the endpoint.**

### Challenge endpoint
`GET {api}/altcha/challenge/?scope=<scope>` → JSON:
```json
{"parameters": {"algorithm": "PBKDF2/SHA-256", "cost": 20000, "keyLength": 32,
                "keyPrefix": "00", "nonce": "<32 hex>", "salt": "<32 hex>",
                "expiresAt": 1792372784, "data": {"scope": "registration"}},
 "signature": "<64 hex>"}
```
The `scope` enum is discoverable by sending an invalid scope — the 400 lists the valid ones
(`registration, password_reset, contact, test_account` on djangoeurope) and maps the auth flows.

### The exact solve (from the minified widget — verify against the target's own build)
The worker's `solveChallenge` does:
```js
const { nonce, keyPrefix, salt } = challenge.parameters;
const nonceBuf = hexToBuffer(nonce);   // hex-DECODE the nonce
const saltBuf  = hexToBuffer(salt);    // hex-DECODE the salt
const password = new PasswordBuffer(nonceBuf, counterMode); // nonce_bytes || counter
// PBKDF2(password, saltBuf, cost, keyLength); hex must start with keyPrefix
```
`PasswordBuffer` (uint32 mode, used when the challenge has no `_version: 1`):
`password = nonce_bytes + struct.pack(">I", counter)` — **big-endian uint32 appended to the
nonce bytes**. In `string` mode it is `nonce_bytes + str(counter).encode()`.

Python solver:
```python
nonce_b = bytes.fromhex(p["nonce"]); salt_b = bytes.fromhex(p["salt"])
counter = 0
while True:
    pwd = nonce_b + struct.pack(">I", counter)
    dk = hashlib.pbkdf2_hmac("sha256", pwd, salt_b, cost, klen)
    if dk.hex().startswith(prefix): break
    counter += 1
```

### The payload format (two variants — pick by the `_version` flag)
`s = "_version" in challenge && challenge["_version"] == 1`
- **v1**: base64(JSON of `{algorithm, challenge: keyPrefix, number: counter, salt: nonce, signature, took}`)
- **legacy**: base64(JSON of `{challenge: {parameters, signature}, solution: {counter, derivedKey, time}}`)

The solution goes in the request body field the server names in its error — djangoeurope used
`{"altcha": "<base64>"}`. Debugging ladder: empty body → "Complete the verification challenge"
(field present, unparsed) · wrong base64 shape → "Verification failed" (parsed, check
nonce/salt roles) · wrong PoW input → same "Verification failed" (you have password/salt swapped
or the counter encoding wrong) · success → the next validation error (e.g. "Detected as spam").

## 2. "Detected as spam" on every IP = fingerprint anti-fraud, not an IP block

Symptom: registration (or another write endpoint) returns `{"non_field_errors": ["Detected as
spam."]}` **after** a correctly solved ALTCHA, on the original egress AND on a rotated egress
(WARP), while GET endpoints and other POSTs (login, password_reset, contact) work fine.

Triage:
1. **Rotate egress once** (`warp-cli connect` → verify via api.ipify.org). If the verdict is
   identical, it is NOT IP reputation — stop rotating.
2. **It is a browser-fingerprint / behavioral check.** Raw HTTP clients (Python requests/urllib,
   curl) lack JS execution, canvas/WebGL, and the real widget's solving behavior. Escalate to a
   real browser session — Playwright with the **full Chromium executable** (see host note below),
   drive the actual form, let the real ALTCHA widget solve itself, submit.
3. The browser session passed where every raw-HTTP attempt failed. Afterwards the API-level
   testing can continue from raw clients using the issued session (see §3).

Related but different: an IP **throttle** (`429 {"detail":"Request was throttled. Expected
available in N seconds."}`) IS per-IP — rotation clears it. Distinguish: throttle = 429 with
Retry-After; anti-fraud = 400 "Detected as spam". Both can be active at once (throttle first,
then spam on the new IP).

## 3. Rotating-token APIs — test from inside the browser page context

Pattern seen on djangoeurope (DRF + custom token auth): login returns
`{token, id, expires_at}`; the panel stores them as cookies and sends
`Authorization: Token <cookie-token>` **plus** `withCredentials` (cross-origin cookies). Two
traps:

- **A raw fetch with only the Authorization header gets `401 Invalid API token`** even with the
  correct token — the server also binds the request to the cross-origin session cookies. The
  working raw call needs `credentials: 'include'` AND the header.
- **The token invalidates after ~10 rapid requests** (rate mechanism). A saved session's token
  goes stale; multi-request scripts (list → delete loop) start 401-ing partway.

Working method for authenticated API testing:
1. Log in via the browser (Playwright), land on the dashboard.
2. Run probes **inside the page context** with `page.evaluate`, reading the token fresh from
   `document.cookie` each call and using `credentials: 'include'`:
   ```js
   const token = document.cookie.split('; ').find(c => c.startsWith('token=')).slice(6);
   fetch(url, {credentials:'include', headers: {'Authorization': 'Token ' + token, 'Accept': 'application/json'}})
   ```
3. Keep batches ≤ ~8 requests per login; re-login (fresh browser context) when 401s start.
4. For sequential dependent calls (list → delete), do the whole loop inside ONE `page.evaluate`
   and accept that later calls may 401 after ~10 — re-login and finish the remainder.

## Host notes (Windows + Playwright, this machine)
- `playwright` ships but its **headless_shell is missing**; `chromium.launch(headless=True)`
  fails with "Executable doesn't exist ... chrome-headless-shell". Fix: pass
  `executable_path="~/.local/share/ms-playwright/chromium-1234/chrome-win64/chrome.exe"`
  (check `ls ~/.cache/ms-playwright/` for the installed version dir — it drifts).
- **Backticks inside `page.evaluate` JS template literals break the eval** (a payload like
  `` detest`id` `` closes the template). Pass such strings as Python-side arguments
  (`page.evaluate(js, [data, names])`), never inline.
- MSYS `/tmp/...` paths are invisible to the Windows Python interpreter — write artifacts to
  workspace-relative paths (`ssh-keygen -f detest_key` inside the engagement dir).
- Terminal heredocs > ~10 KB get truncated in transit; big generator scripts via
  `python3 << 'PYEOF'` in chunks, `ast.parse` after each.
- Angular SPA route gotcha: a link like `/user/create-account` may not be a route — the real
  route can be `/create-account` (the wrong one silently redirects to /login). Dump the router
  paths from the bundle (`path:"..."` regex) before driving.
