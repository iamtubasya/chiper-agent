# ALTCHA proof-of-work CAPTCHA — full reversal and solver

ALTCHA is a PoW-based anti-bot widget (`altcha-widget`, `altcha/altcha.min.js`). Seen live on
djangoeurope.com registration/contact/password-reset (2026-10-19). The PoW is trivially solvable
client-side; the work is getting the payload byte-format right.

## Recon: find the pieces

1. Challenge endpoint (from the bundle): `${api_url}altcha/challenge/?scope=<scope>`.
   Valid scopes are enumerated by the server error: `Must be one of: registration,
   password_reset, contact, test_account.` - probing scopes maps the auth flows for free.
2. Challenge response shape:

```json
{"parameters": {"algorithm": "PBKDF2/SHA-256", "cost": 20000, "keyLength": 32,
                "keyPrefix": "00", "nonce": "<32 hex>", "salt": "<32 hex>",
                "expiresAt": 1792373271, "data": {"scope": "registration"}},
 "signature": "<64 hex>"}
```

## The PoW (extracted from altcha.min.js - do not guess this)

`PasswordBuffer` in the widget builds the PBKDF2 **password** as:

```
password = bytes.fromhex(parameters.nonce) || struct.pack(">I", counter)   # big-endian uint32
salt     = bytes.fromhex(parameters.salt)
hash     = PBKDF2-SHA256(password, salt, iterations=cost, dklen=keyLength)
```

Loop `counter` from 0 until `hash.hex().startswith(keyPrefix)`. (An earlier guess using
`str(counter)` as password fails - the counter is appended to the nonce bytes as a BE u32.)

## Payload format (version-dependent - check the challenge for `_version`)

The widget emits `btoa(JSON.stringify(payload))` into the form field named `altcha`:

- If challenge has `_version == 1`:
  `{algorithm, challenge: keyPrefix, number: counter, salt: nonce, signature, took}`
- Otherwise (the common case):
  `{"challenge": {"parameters": <full parameters object>, "signature": <sig>},
    "solution": {"counter": <n>, "derivedKey": "<hash hex>", "time": <ms>}}`

Server-side verification order (learned from error progression): parse base64 -> verify PoW ->
verify signature -> then business logic. A wrong format yields
`{"altcha": ["Complete the verification challenge and try again."]}`; a parsed-but-wrong PoW
yields `"Verification failed. Please reload the page and try again."`; a correct solve moves the
error to the next field.

## Python solver skeleton

```python
import json, urllib.request, hashlib, base64, struct

def altcha_solve(scope):
    ch = json.load(urllib.request.urlopen(
        f"https://<host>/altcha/challenge/?scope={scope}", timeout=15))
    p = ch["parameters"]
    nonce_b, salt_b = bytes.fromhex(p["nonce"]), bytes.fromhex(p["salt"])
    counter = 0
    while True:
        pwd = nonce_b + struct.pack(">I", counter)
        dk = hashlib.pbkdf2_hmac("sha256", pwd, salt_b, p["cost"], p["keyLength"])
        if dk.hex().startswith(p["keyPrefix"]):
            break
        counter += 1
    obj = {"challenge": {"parameters": p, "signature": ch["signature"]},
           "solution": {"counter": counter, "derivedKey": dk.hex(), "time": 5.0}}
    return base64.b64encode(json.dumps(obj).encode()).decode()
# POST the registration/contact body with "altcha": altcha_solve("registration")
```

## Pitfalls

- **Solving the PoW != bypassing anti-fraud.** djangoeurope accepted the solved ALTCHA and then
  rejected registration with `{"non_field_errors": ["Detected as spam."]}` followed by a 24-hour
  IP throttle (`429 Retry-After: 86399`). The PoW is one layer; IP reputation / fraud scoring is
  another. Budget for the throttle and pivot to the unauthenticated surface.
- Fetch a FRESH challenge per attempt - they carry `expiresAt`.
- The widget's `counterMode` is `"uint32"` unless the challenge carries `_version: 1` (then
  `"string"`, i.e. `str(counter)` appended as UTF-8). Read the flag, don't assume.
- Reuse the same solver for every scope; only the `scope` query param changes.
