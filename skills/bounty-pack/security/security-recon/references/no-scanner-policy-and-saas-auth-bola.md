# "No automated scanners" policy + SaaS auth provisioning + BOLA `/id`-resolver pattern

Worked case: Wallbox (wallbox.com / wall-box.com, EV-charging SaaS) bug bounty, 2026-11.

## 1. The "no automated scanners" policy tier (distinct from "be gentle")

Wallbox's `wallbox.com/.well-known/security-policy.html` says verbatim:

> "No automated scanners. Mass, unauthenticated scanning generates noise for our team and load on
> our infrastructure ... reports generated this way are not eligible, and repeated use may result in
> removal from the program."

This is a **harder** rule than "rate-limits / don't be brutal". Correct response:
- Passive recon only: `subfinder` (CT log / passive DNS — does NOT request the target), `httpx` ONE
  request per *discovered* host for fingerprinting (light, acceptable).
- Do NOT run: nuclei, ffuf, dirsearch, sqlmap, kiterunner, mass wordlist brute. A finding they make
  is ineligible + a removal risk.
- Vulnerability hunting is **manual, targeted, impact-first** — which is exactly what such a program
  rewards anyway (business logic, authz, IDOR on the API).
- Document this decision in the summary so "no scanner artifacts" is a *policy compliance* note, not
  a coverage gap. A later session must not re-derive it and accidentally run nuclei.

## 2. SaaS auth provisioning (JSON:API backend, email-activation flow)

Wallbox stack: `user-api.wall-box.com` (JSON:API, openresty) + `api.wall-box.com` (custom/Slim-like
`/v4/*`). Auth = email+password → RS256 JWT.

**Discover the signup schema by abusing field-by-field validation.** POST a minimal body; the 400
JSON:API error names the exact missing field one at a time. Wallbox returned, in order:
`id is required` → `terms.marketing required` → `terms.profile required` → `type must be in enum`.
Loop until it accepts. Final shape:

```
POST https://user-api.wall-box.com/users
Content-Type: application/vnd.api+json
Headers: Partner: <partner>, Platform: mywallbox
{
  "data": {
    "id": "<ULID>",            # client-supplied! accepted verbatim as user's sub/user_id
    "type": "user",
    "attributes": {
      "name": "...", "email": "...", "password": "...",
      "terms": {"policy": true, "marketing": false, "profile": false},
      "country_code": "ES", "language": "en", "client_type": "com.wallbox"
    }
  }
}
```

**Email-activation flow (the reusable pattern):**
1. Signup → `204` and status becomes `not_confirmed`.
2. Email arrives (Gmail API: search `subject:"new myWallbox account"`). Its "verify" link is
   `https://wallbox-link.wallbox.com/<uuid>` → `302 Location: https://my.wallbox.com/?action=1&email=...&confirmToken=<ULID>`.
3. `POST /users/activate` body `{"data":{"type":"user_activation","attributes":{"email":...,"activation_code":<confirmToken>}}}` → `204`.
4. `GET /users/signin` with **HTTP Basic auth** (`Authorization: Basic base64(email:password)`,
   NOT a JSON body; POST returns `405` here) → `200` with `data.attributes.token` (JWT) + `refresh_token`.

**JWT claim drop:** header `alg:RS256`; payload `{username, uid, session_id, exp, iat, sub}`. No role
claim — role is resolved server-side from `sub` (client-supplied ULID). Short `exp` (~15 min); the
`refresh_token` is long-lived, so re-signin between test rounds.

**Tenant binding:** the `Partner` header is cosmetic — swapping it (`wallbox`→`iberdrola`) still
returns the JWT's own partner. Tenant is bound to the token, not the header. (Cross-tenant header
confusion = NEGATIVE here, don't claim it.)

## 3. The BOLA `/id`-resolver + sequential-integer-ID pattern

`GET https://api.wall-box.com/v4/users/{ulid}/id` → `{"data":{"type":"user_id","attributes":{"value":<int>}}}`.

- It resolves a ULID to the user's INTERNAL numeric id with **no ownership check** (any authenticated
  user can resolve any other user's ULID — reproduces both directions with two accounts).
- Internal ids are **globally sequential integers** (two accounts created minutes apart got 2795918
  and 2795926).
- Analogous `/id` resolvers exist for chargers (`/v4/chargers/{chargerUid}/id`), groups
  (`/v4/groups/{groupUid}/id`), etc. — the same missing-authz pattern.
- Severity ceiling: Low unless you can chain the integer id into an endpoint that returns PII. Here
  the activity/data endpoints (`/v4/groups/{groupId}/charger-charging-sessions`, `/rates`) were either
  operator-gated (`403 "User is not operator"`) or returned empty lists, so no PII leak was provable.

**Probe recipe for the same class** (JSON:API OR custom `/vN/` backend):
1. Find the client `data.id` / primary key the backend accepts (try posting your own ULID).
2. Grep the SPA bundle for `/{entity}/{xUid}/id` and integer-id routes (`/{entity}/{xId}/...`);
   the `/id` resolver that maps ULID→int is the giveaway that int ids are sequential.
3. Create two accounts; from A call `/…/{B's ULID}/id` and vice-versa. 200 with B's value = BOLA.
4. Then hunt for an int-id route that returns data without authz to escalate.