# OAuth/OIDC control-verification battery (DCR + PKCE + client_credentials)

Concrete tests that separate "this OAuth IdP is vulnerable" from "the controls hold". Run right after OIDC discovery, whenever `POST /oauth/register` (or `/oauth/reg`) returns 201 to an anonymous caller. Produced on Rootly (rootly.com, 2026-11) where every control held except the redirect_uri policy. Complements `oauth-dcr-impersonation.md` (which covers the minted-client proof + metadata impersonation); this file is the negative-control side — proving which OAuth controls are actually enforced.

## 1. redirect_uri ACCEPTANCE matrix at DCR

POST /oauth/register with each redirect_uri value; record accepted (201) vs rejected (400):

| redirect_uri | result |
|---|---|
| `https://<target>/callback` (same domain) | accepted |
| `https://evil.com/callback` (external HTTPS) | accepted — no domain allowlist |
| `http://evil.com/callback` (external plain HTTP) | 400 (rejected) |
| `http://localhost:8080/callback` (localhost HTTP) | accepted |
| `https://<target>.evil.com/callback` (suffix confusable) | accepted |
| `https://<target>@evil.com/callback` (userinfo trick) | 400 |
| `https://attacker.<target>/callback` (arbitrary subdomain) | accepted |
| `https://*.<target>/callback` (wildcard) | accepted — most notable item |
| empty array / no field | 400 |

**Framing (honest severity).** Accepted external/wildcard redirect_uri is Low/Medium, not Critical. It needs either (a) a victim authorizing the attacker's client (phishing → usually out of scope under "no social engineering") or (b) content-control on a `*.target` subdomain (customer status pages, custom domains) to escalate into authorization-code interception. The token endpoint DID check redirect_uri-consistency (error "does not match the redirection URI used in the authorization request"), so a flow-time mismatch is caught. The wildcard `*.<target>` acceptance is the most defensible item because the product hosts thousands of customer-controlled subdomains. Report as hardening, add one sentence inviting reassessment, do not inflate.

## 2. PKCE enforcement test (public client)

Register a public client (`token_endpoint_auth_method:"none"`, grant `authorization_code`). Then hit the token endpoint with a random code:

```bash
curl -X POST <token_endpoint> -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "grant_type=authorization_code" \
  --data-urlencode "code=<random>" \
  --data-urlencode "client_id=<public_client_id>" \
  --data-urlencode "redirect_uri=<registered>"      # NO code_verifier
```

- `400 {"error":"invalid_request","error_description":"Missing required parameter: code_verifier."}` → **PKCE enforced** (control holds).
- Proceeding to `invalid_grant`/`invalid code` with no code_verifier complaint → PKCE optional = real finding (code interception without PKCE).

Use an already-registered public client_id rather than re-registering — DCR rate-limits and a fresh registration can come back empty, which defeats the test (the token endpoint then returns `invalid_client` for the empty id, not the PKCE verdict you wanted).

## 3. client_credentials grant stripping (self-registered confidential client)

DCR a confidential client with `grant_types:["authorization_code","client_credentials"]`:

1. The response's `grant_types` comes back `["authorization_code"]` only → server strips client_credentials.
2. Confirm at the token endpooint: `grant_type=client_credentials` + client_id + client_secret → `401 {"error":"unauthorized_client","error_description":"The client is not authorized to perform this request using this method."}`.

A 200/access_token here would be Critical: client_credentials is user-independent, so a self-minted server-to-server token is org/team-wide access without any user consent. The strip is the control; verify it is enforced at the token endpoint (the strip could be cosmetic in the registration response only).

## 4. introspect / revoke authorization

- `POST /oauth/introspect` (no client auth, no token) → `400 "Request needs to be authorized..."` = requires caller auth (control holds). An open introspect = token-enumeration oracle.
- `POST /oauth/revoke token=<fake> client_id=<valid>` (no secret) → `403 "You are not authorized to revoke this token"`.

## 5. CORS allowlist on token/API hosts

```bash
curl -D - -o /dev/null -H "Origin: https://evil.com" <api_endpoint>
```

No reflected `Access-Control-Allow-Origin` = allowlist (good). With `Origin: https://<target>` returning `Access-Control-Allow-Origin: https://<target>` (explicit, no wildcard, no `Allow-Credentials: true`) = correct. A reflected arbitrary origin + credentials = separate CORS finding.

## 6. DCR rate limiting

~12 registrations then `429 {"error":"too_many_requests"}` = rate-limited (control holds). Absence of 429 across a burst is separately reportable (see `oauth-dcr-impersonation.md`).

## 7. Uniform API auth = global auth middleware (not per-endpoint)

Sweep ALL GET endpoints no-token → uniform `401 "Invalid token"`. Then ONE probe each of POST/PUT/PATCH/DELETE (empty body `{}`, non-existent id like `999999999`) → same `401 "Invalid token"`, because the Bearer check runs before routing and before any resource is touched. This is the safe way to prove non-GET endpoints are auth-gated without risking a write: empty body + non-existent id means even a hypothetical unauthenticated endpoint 404s/422s before creating/updating real data.

Watch the error-shape differential: `401 "Invalid token"` (auth middleware ran) vs `404 "Not found or unauthorized"` (a per-endpoint existence+authz check that deliberately conflates the two — heartbeat `ping` style). A split signals per-endpoint auth models to investigate individually.