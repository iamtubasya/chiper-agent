# JSON:API signup → email-activation short-link → HTTP-Basic GET signin → JWT

Verified on wallbox.com (myWallbox, 2026-11): a Laminas/API-Platform-style JSON:API backend where
signup, activation and signin are three separate REST calls and the "login" is a **GET** with **HTTP
Basic** auth, not a POST. This is a common shape for `.jsonapi`-style SaaS — worth knowing cold so you
don't burn 20 minutes probing a `405` on `POST /users/signin`.

## The three-call flow (all on the user-api host, e.g. `user-api.<target>`)

1. **Signup** — `POST /users`, `Content-Type: application/vnd.api+json`, body:
   ```json
   {"data":{"id":"<CLIENT-SUPPLIED-ULID>","type":"user","attributes":{
     "name":"...","email":"...","password":"...",
     "terms":{"policy":true,"marketing":false,"profile":false},
     "country_code":"ES","language":"en","client_type":"com.<target>"}}}
   ```
   Returns **204 No Content** (accepted, no body). **`data.id` is caller-chosen** — the backend uses it
   verbatim as the user primary key (the JWT `sub` and `/users/me` `id` both echo it). Same pattern on
   create-org. Note it as a weak-ID signal, not a finding (ULIDs are 128-bit).
   - The schema rejects loudly: dropping a required field returns a JSON:API `errors[]` array naming each
     `property` (`data`, `data.attributes.terms.marketing`, …) — send the union of errors once to learn the
     exact required-fields shape instead of guessing.

2. **Activation** — the confirmation email carries a **short-link** (`https://link.<target>/<uuid>`), NOT a
   code. That link `302 Location: https://app.<target>/?action=1&email=<e>&confirmToken=<ULID>`.
   Extract the token from the **redirect Location**, not from the email body text:
   ```python
   loc = requests.get(link, allow_redirects=False).headers["Location"]
   ct  = re.search(r"confirmToken=([A-Za-z0-9]+)", loc).group(1)
   ```
   Then `POST /users/activate` `{"data":{"type":"user_activation","attributes":{"email":E,"activation_code":ct}}}` → 204.
   The account is `not_confirmed` until this fires; signin before it returns **`403 Insufficient rights`**
   (not 401) — a useful discriminator.

3. **Signin** — `GET /users/signin` with **HTTP Basic** (`Authorization: Basic base64(email:pass)`) plus
   `Partner: <brand>` + `X-Request-ID: <ulid>` headers → `200` with
   `{"data":{"attributes":{"token":"<JWT>","refresh_token":"…","user_id":"…"}}}`.
   - It is a **GET**, not POST — `POST /users/signin` → `405`. Method-locked, don't re-derive.
   - The returned JWT is **RS256** (`alg/typ` header), claims `{username, uid, session_id, sub, exp, iat}`,
     **no role claim** — role is looked up server-side per-request. Don't waste time on `alg:none`/weak-secret
     forgery against a well-formed RS256 token.
   - Access token TTL is short (~15 min); `ttl`/`exp` in the response/claims are absolute epoch timestamps.
     Refresh the session before cross-account harness runs or the "second" token silently 401s mid-diff.

## What it unlocked (IDOR/BOLA check that paid off)

After provisioning two accounts (A, B), the cross-tenant resolver was open:

- `GET https://api.<target>/v4/users/{ULID}/id` (Bearer JWT) returns the user's **internal sequential
  numeric id** with **no ownership check** — account A resolved B's ULID → B's id, and vice versa.
- Internal ids are **globally sequential integers** (two accounts minutes apart = ids 8 apart). A public-ULID
  → sequential-internal-id converter that skips ownership is a classic **BOLA**, and the same `/{x}/{...}/id`
  pattern repeated for chargers/groups. When you see a `/{ulid}/id` endpoint on a ULID-hiding SaaS, test
  cross-user resolution first — it is cheap and frequently missing the ownership check.
- Severity is usually **Low** (leaks the identifier, not PII) and can overlap a "disclosure of non-sensitive
  identifiers" exclusion — so chase the *data-access* IDOR (chargers/sessions/invoices) the same pattern
  might unlock rather than stopping at the id-resolution BOLA.

## Note: "no automated scanners" programs

wallbox.com's policy is the strong form of the scanner rule: *"No automated scanners … reports generated
this way are not eligible, and repeated use may result in removal."* Details + the scanner-budget
decision rule live in `security-recon` Step 6. The takeaway for provisioning: everything here is
**manual + targeted** (3–5 REST calls), which is exactly what such programs reward.