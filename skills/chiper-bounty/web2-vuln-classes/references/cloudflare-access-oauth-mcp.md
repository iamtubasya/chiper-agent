# Cloudflare Access-managed OAuth + MCP servers — assessment matrix

Applies when a host (often `<brand>.mcp.<domain>` or a "portal" subdomain) is protected by
**Cloudflare Access with its built-in OAuth** rather than the vendor's own auth server, and exposes an
MCP endpoint. Verified 2026-09 against a Rapyd MCP server; re-verify before reporting (see the
"leads rot" pitfall in `browser-cdp-auth-audit`).

## Fingerprinting in 3 requests

```bash
curl -sD - -o /dev/null https://<host>/mcp        # expect 401 + WWW-Authenticate: Bearer realm="OAuth",
                                                  # error="invalid_token", resource_metadata="…/oauth-protected-resource/mcp"
curl -s https://<host>/.well-known/oauth-protected-resource/mcp
curl -s https://<host>/.well-known/oauth-authorization-server
```

A metadata document whose `issuer` is `https://<team>.cloudflareaccess.com` and whose endpoints live
under `/cdn-cgi/access/oauth/…` means everything below is Cloudflare's implementation driven by the
tenant's policy — so the interesting question is always *what the tenant allowed*, not a code bug in
Cloudflare's OAuth.

Typical metadata (Access-managed):
`authorization_endpoint …/cdn-cgi/access/oauth/authorization`, `token_endpoint …/oauth/token`,
`registration_endpoint …/oauth/registration`, `revocation_endpoint …/oauth/revoke`,
`response_types_supported:["code"]`, `response_modes_supported:["query"]`,
`grant_types_supported:["authorization_code","refresh_token"]`,
`token_endpoint_auth_methods_supported:["client_secret_basic","client_secret_post","none"]`,
`code_challenge_methods_supported:["S256"]`.

Note: a vendor may migrate onto this layer between sessions — an older note saying the same host had a
self-hosted `/register` returning `201` is a different deployment, not a duplicate finding.

## Control matrix — run all of these, they are cheap

| # | Test | Request | Secure result observed |
|---|---|---|---|
| 1 | DCR with a public redirect | `POST …/oauth/registration {"redirect_uris":["https://evil.example/cb"],"token_endpoint_auth_method":"none"}` | `400 invalid_client_metadata` — *"redirect_uri is not allowed by the account configuration"* |
| 2 | DCR with `javascript:` / wildcard | same, `["javascript:alert(1)"]` / `["https://evil.example/*"]` | `400` — "Invalid redirect URI" / not allowed |
| 3 | DCR with **loopback** | `["http://localhost:3334/callback"]`, `["http://127.0.0.1:8080/callback"]` | **`201 Created` + `client_id`** — this is RFC 8252 native-app support and is usually intentional |
| 4 | `redirect_uri` validation at authorize | register loopback, then call `/authorize` with a *different* URI (`localhost:9999`, `https://evil.example/cb`) | `400` Cloudflare Access error page, **no redirect** |
| 5 | `resource` binding | `/authorize` without `resource=` | `400 invalid_target` — *"No resource parameter found"* |
| 6 | PKCE required | `/authorize` without `code_challenge`, and with `code_challenge_method=plain` | `error=invalid_request` redirected to the registered URI; `plain` rejected → S256 mandatory |
| 7 | Unknown client | `/authorize?client_id=nonexistent` | `400` Access error page |
| 8 | Token endpoint client check | `POST /token` with a random `client_id` (authorization_code **and** refresh_token **and** client_credentials) | `401 invalid_client` "Client not found" |
| 9 | Forged bearer | `Authorization: Bearer` with a random JWT, an `alg:none` JWT, an `HS256 secret` JWT, and an opaque string, against `/mcp` | `401` for all ("Session expired, please reauthenticate") |
| 10 | Identity source | GET `<host>` → follow the `302` to `/cdn-cgi/access/login/<host>?kid=…&meta=…` | if the page offers **SAML only** (no one-time PIN / social), external parties cannot mint an Access JWT |
| 11 | Worker paths | `/env /debug /config /.env /metrics /health /robots.txt` | `404` (edge may `403` `/.env`) |

## What a "closed" verdict looks like

Loopback-only DCR + redirect_uri validated at authorize + PKCE S256 + `resource` binding + SAML-only
login + forged JWTs rejected = **not exploitable**; the remaining anonymous `client_id` creation is the
intended native-app pattern. Write that in the findings file as `CLOSED — NOT EXPLOITABLE` with the
matrix above, so a future session does not re-run it.

The one test you *cannot* run without an authorised identity is **cross-app audience confusion**
(mint an Access JWT for another app on the same `<team>.cloudflareaccess.com` team domain and see if the
MCP resource accepts it). Record it as `not verified — no authorised identity available`, do not imply
it passed or failed.

## Housekeeping you owe the operator

DCR on this layer is **create-only**: the 201 response carries no `registration_access_token` and
`GET`/`DELETE /cdn-cgi/access/oauth/registration/<client_id>` both return `404`. Any client you register
for testing cannot be removed by you. List the created `client_id`s (all of them, with their
redirect_uris) in the engagement log and tell the operator that an Access admin has to purge them from
the tenant client list.

## Adjacent pattern worth checking on any API bundle: unauthenticated helper endpoints

While mapping the JS bundle for OAuth plumbing, look for internal *config/preview* endpoints that skip
the platform's normal auth. Example: `GET https://<sandbox-api-host>/v1/hosted/config/preview_tokens?type=checkout`
returned `200` with demo checkout tokens **without an access key or signature**, while every sibling
endpoint on that host returned `401 UNAUTHORIZED_API_CALL` (the production host returned an empty list).
Such endpoints are usually "by design" for a merchant dashboard preview panel, but they are (a) a real
authorisation inconsistency to note at low severity and (b) the cheapest way to obtain a valid UI object
when the real creation path is blocked by KYB/onboarding — e.g. a demo checkout token renders the
vendor's checkout page for framing/`postMessage` testing. Say which tokens are `is_demo:true`.
