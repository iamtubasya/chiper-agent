# Test-Account Provisioning — probe the backend before climbing the UI ladder

Use when a returning engagement needs an account to reach the surface that is still novel.
The point is to answer **"can an account be created at all"** in three requests, *before*
spending an hour on UI-level signup walls.

Measured 2026-10-27 on Flux (`manager.runonflux.io`, Firebase project `fluxnode-manager`).

---

## 1. Recover the identity-provider config from the bundle

Provider keys are public by design in any SPA — they ship to the browser.

```python
import re, urllib.request
js = "".join(open(f, encoding="utf-8", errors="ignore").read() for f in bundle_files)

keys  = set(re.findall(r'AIza[0-9A-Za-z_\-]{30,45}', js))                    # Firebase apiKey
hosts = set(re.findall(r'([a-z0-9\-]+\.firebaseapp\.com)', js))              # project id
sb    = set(re.findall(r'([a-z0-9\-]+\.supabase\.co)', js))                  # Supabase
for fld in ("apiKey", "authDomain", "projectId", "appId"):
    m = re.findall(rf'{fld}\s*:\s*"([^"]{{6,80}})"', js)
    if m: print(fld, list(dict.fromkeys(m))[:2])
```

A 39-char `AIza…` value is a normal Firebase web apiKey. Seeing it is **not** a finding —
it is project-identifying, not a secret, and it only permits the auth operations the project
has enabled. Do not report it.

## 2. Three probes answer "is signup possible"

Firebase Identity Toolkit, key from step 1:

```python
KEY = "..."                              # from bundle
BASE = "https://identitytoolkit.googleapis.com/v1"

# a) password signup
POST {BASE}/accounts:signUp?key={KEY}
     {"email": e, "password": p, "returnSecureToken": true}
#   -> OPERATION_NOT_ALLOWED  = email/password disabled on this project

# b) email magic-link
POST {BASE}/accounts:sendOobCode?key={KEY}
     {"requestType": "EMAIL_SIGNIN", "email": e, "continueUrl": "<target>/"}
#   -> OPERATION_NOT_ALLOWED  = magic link disabled

# c) password reset
POST {BASE}/accounts:sendOobCode?key={KEY}
     {"requestType": "PASSWORD_RESET", "email": e}
#   -> 200 = reset mail sent (NOT proof that signup is open)
```

Outcome matrix:

| signUp | EMAIL_SIGNIN | Meaning |
|---|---|---|
| OK | — | self-provisioning works, mint accounts now |
| `OPERATION_NOT_ALLOWED` | OK | magic-link only, use your own mailbox |
| `OPERATION_NOT_ALLOWED` | `OPERATION_NOT_ALLOWED` | **only OAuth remains → surface is closed** |

Both disabled means the authenticated surface is genuinely unreachable without an existing
OAuth identity. That is an honest coverage limit with a named unlock ("requires an owned
account"), **not** a bug and **not** a reason to keep pushing UI buttons.

## 3. Control every enumeration claim

A reset/OOB endpoint that answers `200` for your own address proves nothing. Send the same
request for an address that cannot exist, and compare the **body**:

```
control  nonexistent-<random>@example.invalid  -> 200  {"kind":"...GetOobConfirmationCodeResponse","email":"nonexistent-..."}
real     your own address                      -> 200  identical shape
=> NO ORACLE. Do not report user enumeration.
```

Measured on Flux: identical 200s for both. Reporting that as enumeration would have been a
fabricated finding.

## 4. When an account does exist but routes 404

If a bundle references `/api/profile`, `/api/user-nodes` etc. but every one returns
`404 {"error":"Route not found"}` — **with and without** an `Authorization` header — the
routes are not deployed, not protected.

```
no header            /api/profile -> 404 Route not found
Bearer notatoken     /api/profile -> 404 Route not found
Bearer alg:none JWT  /api/profile -> 404 Route not found
```

A 404 that does not change with auth means auth never ran; the handler is absent. Do not
record this as "authz bypass" or "route hides behind auth". It is an absent feature.

Contrast: a route that flips `404 → 401` when you add a header **is** deployed and gated —
that one is worth testing.

## 5. What to write when provisioning fails

```
Authenticated surface not tested: <product> has no self-service signup on this deployment
(Firebase signUp and EMAIL_SIGNIN both OPERATION_NOT_ALLOWED; PASSWORD_RESET returns an
identical 200 for a nonexistent control address, so no enumeration oracle). Only OAuth
remains, which requires an owned account. Testing therefore stayed on the unauthenticated
surface.
```

That is coverage evidence. "Blocked" alone reads as surrender; the three request results make
it a measurement.

## Pitfalls

- **Do not report the web apiKey** as a leaked secret. It is public, and its scope is exactly
  the auth operations the project enabled.
- **`OPERATION_NOT_ALLOWED` is a project setting, not a per-user rate limit.** Retrying will
  not help.
- **Deleting/recreating an account to "reset" state** is not possible here and is a ToS risk
  on most programs — do not try.
- **If the program requires testing on your own accounts and you cannot mint one**, the
  correct move is to change surface, not to borrow someone else's identity or read other
  users' objects. Several vendors state this explicitly in their rejection letters.
