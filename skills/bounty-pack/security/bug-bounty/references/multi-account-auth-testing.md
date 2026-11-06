# Multi-account auth testing — session pinning & clean-room reproduction

Class: testing auth / IDOR / JWT across **2+ live accounts in one long session**.
Covers the failure mode that fabricates cross-account findings, the mandatory
clean-room rule, short-TTL token handling, OTP-code extraction, and the JWT
forgery battery shape. Worked case: Fintual 2026-10 (CL+MX, 4 accounts).

## ⚠️ THE TRAP: auto-reauth silently switches accounts (fabricated ATO)

A session helper resolved the target account from a **module-global** `CREDS`
dict chosen by env var at import, and auto-relogged on 401. Mid-session I
observed `/api/me` returning **account B's data while holding account A's
cookies**, and it stayed on B after "restoring" the cookie — a textbook
unsigned-cookie account-confusion ATO. It was 100% self-inflicted:

1. The JWT TTL was 300 s; the token expired mid-analysis → helper got a 401.
2. The helper's `refresh()` called `login()` which read the **module-global**
   `CREDS`.
3. The module had been `importlib.reload()`-ed for account B earlier, so
   `CREDS` now pointed at B → the 401-refresh logged in as B inside A's jar.
   Cookie domain `email` even showed B's address.

**A clean-room reproduction killed it in one shot** (fresh process, fresh
login, only the uid cookie varied → no effect). Cost of NOT doing the
clean-room: a fabricated Critical ATO shipped to a vendor.

### Hard rules
- **Pin creds per instance at construction**: `self.creds = dict(CREDS)`;
  every `login()`/`refresh()` reads `self.creds`, never a module global.
- After ANY `importlib.reload()` of the helper module, **rebuild every
  session object** — old instances share the mutated module dict.
- After ANY unexplained 401/identity shift, **re-login explicitly** and
  re-check `/api/me` identity before trusting the next observation.
- **Clean-room reproduction is mandatory for any identity/authorization
  finding**: fresh process + fresh login + exactly one variable changed.
  A one-shot "wow" signal is never evidence. (Bug-bounty stop-rule 20.)

## Short-TTL tokens (300 s JWTs are common)

Long analysis cells routinely outlive the token. Expect silent expiry; the
symptom is a sudden 401 on a call that worked 5 minutes ago. Re-login is
cheap — do it before believing any negative result ("404/401 might just be
my dead session").

### Emailed step-up code extraction (Gmail API, own test accounts)
- Query `subject:"<subject>" to:<address>`, sort hits by `internalDate`
  DESC, take the newest message only — older mails carry stale codes that
  still regex out cleanly.
- **Decoy numbers are normal**: tracking-pixel fragments, year strings
  (`2026`), template constants (`404040`). Strip `<style>/<script>` before
  digit-regexing, then filter a decoy set; prefer the candidate that is NOT
  in the decoy set and appears in the visible-text region.
- Codes are single-use and re-initiate invalidates them: fetch the code
  AFTER `initiate_login`, use it once, never retry a stale code (the
  `401 Wrong verification code` vs `403 Checks limit reached` split tells
  you stale-code vs lockout).

## JWT forgery battery (ATO-of-any-account attempt)

Prerequisite: **prove the baseline first** — real token in the live session
jar must return 200 with your `sub`. Then swap forgeries into the SAME jar
in place, restoring the real token after every probe. Fetch the JWKS from
`/.well-known/jwks.json` for the key material.

Battery (all rejected on Fintual: RS256 + kid `_VOfSTIugek`):
1. `alg:none` — with kid, without kid, case variants (`None`).
2. HS256 key-confusion — HMAC signed with the RSA public key in all four
   encodings: SPKI/PKCS1 × PEM/DER.
3. kid injection — path traversal (`/../../dev/null`), SQLi
   (`' OR '1'='1`), comment (`'--`), unknown kid.
4. Tampered signature with a VALID kid (sub=victim).
5. Expired-token replay (exp/nbf in the past).

Pitfalls:
- A cookie-only API returns 401 for `Authorization: Bearer <real token>` —
  that is NOT a forgery failure, it is the auth model. Establish the cookie
  baseline before drawing any conclusion.
- Any 401 during the battery is only meaningful if the real-token control
  still 200s **in the same minute** (mind the TTL).

## Cross-account IDOR test shape
- Create state on account A (a resource with a real ID), then read/write it
  from account B: `Not found` from BOTH = no oracle; data from B = finding;
  data only from A = positive control (scoping proven).
- Without a funded/real object, uniform "not found" from both sides is
  **UNPROVEN-BENIGN, not verified-negative** — say so in the ledger.
- Error differentials are oracles: probe 4-6 IDs and check the error text is
  byte-identical; a single differing message = existence oracle = finding.
