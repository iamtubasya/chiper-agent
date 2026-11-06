# Multi-app suite, round 2 (Proton, 2026-10-25): session recovery from a stale browser profile,
# the scope-differential matrix, and "leaked-looking secret" crypto triage

Continuation of `proton-e2e-audit-2026-10.md`. That file covers *getting in* and the E2E surface map.
This one covers three things that cost the most time and generalise to **any suite that issues a
per-app session token** (Proton / Google-style cookie families, any `AUTH-<uid>` + `REFRESH-<uid>` pair).

---

## 1. Recovering the test account from a persistent Playwright profile

Setup: an old run left an authenticated Chromium profile (`proton-test-profile`) plus a plaintext
`testuser.txt` / `testpw.txt`. Both the stored refresh **cookies** and the recorded password were
stale-but-not-dead. What actually worked, in order:

```
# a) enumerate every AUTH-<uid>/REFRESH-<uid> PAIR in the profile (do NOT assume the first one works)
ctx = p.chromium.launch_persistent_context(PROFILE, headless=True); ck = ctx.cookies(); ctx.close()
pairs[uid] = {'AUTH': …, 'REFRESH': …}     # one uid per app (mail/calendar/drive/pass/account…)

# b) probe each pair; most are dead. Success shape:
POST https://<host>/api/auth/v4/refresh
  {ResponseType:"token", GrantType:"refresh_token", RefreshToken:<rt>, RedirectURI:"https://…"}
  cookies: AUTH-<uid>, REFRESH-<uid>
  → 200 {"Code":1000,"UID":…,"LocalID":…,"RefreshCounter":…}   (token often comes back in Set-Cookie,
                                                                 sometimes in the JSON body — read BOTH)
  → 422 {"Error":"Invalid refresh token","Code":10013}          (dead pair, move on)

# c) classify what the class of token can do — don't guess, ask the server:
GET /api/core/v4/auth/scopes  → {"Scopes":["full","locked","self","payments","keys","parent",
                                "user","loggedin","nondelinquent","mail","calendar","drive",
                                "pass","verified","settings","wallet","lumo","meet"]}
```

Three facts that matter:

- **`REFRESH-*` cookie values are sometimes URL-encoded JSON blobs** (`%7B%22ResponseType%22…`), not
  raw tokens. A helper that assumes a raw token sends garbage and every call 401s while looking like
  "the account is gone". Decode first (`urllib.parse.unquote`) or re-mint from the password.
- **Only the newest pair per app is live.** Old ones linger in the profile forever and answer 422.
  Iterate all of them; the working uid is usually the one NOT present in the older state dumps.
- **A `locked`-scope session is the one that can revoke/step-up.** Fork-derived and child-app tokens
  lack it, so scope-work must be done from the SRP-login session (see §2).

Browser route when the profile itself is logged out (it was, twice): drive the login form by **id**,
not by CSS class — `#username`, `#password`, `button[type=submit]`, typed with `type(..., delay=50)`
so React's controlled inputs register. A synthetic `fill()` on a React 18 input can silently leave
the field empty and the form re-renders "This field is required". After submit, wait for the
`authorize?app=…&reason=session-expired` hop to finish, then read cookies (not `page.url`, which
stays on the authorize page while loading).

## 2. The scope-differential matrix — how to test scope enforcement without a second account

Proton mints one token per app via fork. The fork token and the SRP-login token differ **only in
scope**, which makes a free, high-signal differential: send the same privileged call with both and
compare. Read `MissingScopes` out of the 403 body — it names the exact scope the server wanted.

| call | fork token (no `password`/`locked`) | SRP-login token (`locked`) |
|---|---|---|
| `PUT /api/core/v4/settings/email` | 403 `9102` `MissingScopes:["password"]` | (needs step-up) |
| `DELETE /api/auth/v4/sessions/{uid}` | 403 `9101` `MissingScopes:["locked"]` | 200 |
| `PUT /api/core/v4/keys/user` | 403 `9101` `MissingScopes:["locked"]` | — |
| `GET /api/core/v4/users` | 200 | 200 |

Result: enforcement correct → **negative, and a *measured* negative** ("we drove the token to its
boundary and the server named the scope it refused"), which is what makes the sibling positive
credible. Always run this before claiming "full-scope token".

**Revocation test (do this every time, it is cheap):** mint a fork in both modes
(`Independent:0` and `Independent:1`), then `DELETE /api/auth/v4/sessions` from the locked session and
re-probe. Here both fork tokens died (401) and their refresh tokens were invalidated (422) → revocation
covers fork sessions. If they had survived, that would have been the High (session persists past
"log out of all devices").

## 3. "Unauthenticated endpoint" ≠ missing authorization — read the CHILD's caller code

`GET /api/auth/v4/sessions/forks/{selector}` with **no cookies, no Authorization, no secret** returns a
full-scope AccessToken+RefreshToken. That reads like a critical authz bypass. It is not:

```js
// pass-2.js / drive / wallet bundles — the CHILD app's own hand-off, unauthenticated by design
e.pullFork ?? (e => { let {selector:t}=e, a={method:'get', url:`auth/v4/sessions/forks/${t}`};
                     return a.url = n?`${n}/${a.url}`:a.url, r({...a, unauthenticated:!0}) })(t)
```

The selector **is** the bearer credential for the hand-off; the parent creates it and hands it over
out-of-band. So: **before reporting an unauthenticated endpoint as a missing-authz bug, grep the
client bundle for the call site.** `unauthenticated:!0` / `credentials:'omit'` in the app's own code is
the by-design signature. Also check child-client enumeration: only `web-mail` could claim its own
selector; `web-account`/`web-drive`/`web-pass`/`web-calendar`/`web-wallet`/`web-docs` all answered
`422 Invalid selector` when claimed by a mail-client caller → the selector is client-bound.

## 4. Leaked-looking secret fields: prove the consumer before you write "data exposure"

`GET /api/core/v4/users` returns, to *any* session token, per-key `RecoverySecret` (44 B b64) +
`RecoverySecretSignature`, and `PrivateKey` (armored). Looks like key material disclosure. It is not:

```js
// auth chunk (module 67803) — how the secret is actually used
h = async e => { let t = crypto.getRandomValues(new Uint8Array(32)).toBase64();
                 return { signature: await signMessage({textData:t, …detached:true}),
                          recoverySecret:t } }
x = async e => { … exportPrivateKey({passphrase:null, format:'binary'}) … encryptMessage(… t …) }
// ⇒ recovery FILE = the decrypted private keys, PGP-encrypted with that random 32-byte secret.
//   Server stores only {RecoverySecret, Signature}. The secret alone decrypts nothing.
```

Rule: **a secret-shaped field is not a finding until you find its consumer and prove the blast
radius.** Grep the bundle for the field name, read whether it is a *key* or a *pointer/label*, and
state explicitly what it does not unlock.

### Sub-pitfall: verifying a PGP passphrase — `--import` success proves NOTHING

```bash
# WRONG: import succeeds regardless of passphrase; "secret key imported" appears for any value,
#        and `grep -c 'BEGIN PGP SIGNED MESSAGE'` counts 1 even when signing FAILED (clearsign
#        writes the armor to stdout before the error).
gpg --pinentry-mode loopback --passphrase "$PW" --import key.asc

# RIGHT: actually use the key and read STDERR for "Bad passphrase"
echo t | gpg --batch --yes --pinentry-mode loopback --passphrase "$PW" \
       --local-user <KEYID> --clearsign >/dev/null
# → stderr "signing failed: Bad passphrase"   vs   silence = passphrase correct
```

Also: MSYS gpg chokes when `GNUPGHOME` is a Windows-style absolute path (`C:\Users\…`) — it builds
`<cwd>/C:\Users\…` and reports "no writable keyring found". Use a relative dir (`GNUPGHOME=./gpgtest`)
or a `/c/...` path. And a *bare* `--import` of a Proton private key without the matching public key
fails with "No public key" — fetch the public half (`/api/core/v4/keys/all?Email=`) and concatenate.

## 5. Payments: price tampering is gated BEFORE price evaluation

```
POST /api/payments/v4/subscription {Plans:{…}, Currency, Cycle}
  body field is `Plans` (not `PlanIDs`) → wrong name gives 400 "Missing required attribute Plans"
  → with a correct plan: 400 2001 "No valid payment method available"
```
So the server refuses to even compute an invoice without a stored payment method: no proration /
coupon / amount-tamper surface is reachable from a card-less free account. Do not use real or
throwaway test cards against a live PSP to get past it — record it as **not tested (needs a stored
method)**, not as "no pricing bugs". Read-only plan/entitlement endpoints are still worth harvesting:
`/payments/v4/plans?Currency=USD`, `/payments/v5/subscription?no-redirect=1`, `/core/v5/entitlements`,
`/payments/v6/plans/entitlements` (feature flags per plan = the entitlement oracle for later).
Referral surface (`/core/v4/referrals`, `/referrals/info`, `/referrals/status`) is live and returns
reward 2000¢ each side, cap 100000¢ — self-referral needs a second identity, so it inherits the
second-account blocker.

## 6. Second-account blocker (unchanged, and it caps the whole engagement)

Free-tier signup silently blocks after the first account on the same IP (no captcha shown, form never
submits). Consequences to state in the report rather than paper over: all cross-tenant BOLA (Drive /
Docs / Pass / Calendar / Wallet shares), org-role escalation, referral abuse and payment-with-method
tests stay **UNTESTED**, not negative. Mint account #2 in the FIRST session of an engagement — do not
leave it for later, because the block is per-IP-fingerprint and outlives the session.
