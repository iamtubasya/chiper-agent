# MCP servers behind Cloudflare Access OAuth — audit checklist

Applies to `mcp.<vendor>` deployments built on Cloudflare's remote-MCP template and fronted by Access.
The OAuth server is **Cloudflare Access**, not the app: the metadata's issuer is
`https://<team>.cloudflareaccess.com` and every endpoint lives under `/cdn-cgi/access/oauth/…`.
This class is growing fast (every "MCP portal" launch), so run the checklist rather than improvising.

## Recon (all unauthenticated)

```bash
curl -s https://mcp.<target>/.well-known/oauth-authorization-server          # issuer + endpoints
curl -s https://mcp.<target>/.well-known/oauth-protected-resource/mcp        # RFC 9728 resource
curl -sD - -o /dev/null https://mcp.<target>/mcp | grep -i www-authenticate # 401 + resource_metadata
curl -s https://mcp.<target>/sse ; curl -s https://mcp.<target>/register     # route existence
```

Expect: `/mcp`, `/sse`, `/authorize` → `401 {"error":"invalid_token", … "resource_metadata": …}`;
`/.well-known/openid-configuration` may 404; `/register` on the MCP host may 404 — **the real DCR
endpoint is the one advertised in the metadata** (`registration_endpoint`), not the template path.

## The checks that decide whether it is exploitable

| Test | Probe | Secure result observed |
|---|---|---|
| DCR scope | `POST <registration_endpoint>` with `redirect_uris:["https://evil.example/cb"]`, a wildcard, or `javascript:` | `400 invalid_client_metadata` — "redirect_uri is not allowed by the account configuration" / "Invalid redirect URI" |
| Loopback DCR | same with `http://localhost:3334/callback` or `http://127.0.0.1:8080/callback` | `201 Created` (client_id). **This is deliberate RFC 8252 native-app support — not a bug by itself.** |
| redirect_uri enforcement at authorize | registered client_id + a *different* `redirect_uri` | `400` Access error page, **no redirect** |
| PKCE | omit `code_challenge`; then `code_challenge_method=plain` | `error=invalid_request` (challenge required) / plain rejected; only S256 |
| audience binding | omit `resource=` | `400 invalid_target` "No resource parameter found" |
| client registry | unknown `client_id` at `/authorize` and `/token` | `400` / `401 invalid_client` "Client not found" |
| token forgery | random JWT, `alg:none`, HS256 with "secret", opaque string | `401` for all |
| **identity isolation** | load the Access login page for the MCP host | SAML-only (enterprise IdP) ⇒ an outsider cannot mint a JWT. If a one-time-PIN / social IdP *is* offered, self-enrol with your own address and test the resulting JWT against a **different** Access app on the same team domain (audience confusion) — that is the only remaining high-value path. |
| token endpoint | `POST /token` with each grant type (`authorization_code` + junk code, `refresh_token`, `client_credentials`, `password`, `jwt-bearer`) | `401 invalid_client` / `invalid_grant`; no grant leaks a token without a registered client |

## Reporting discipline

- **Open DCR + arbitrary redirect_uri is a finding; loopback-only DCR is by design.** Do not report the
  loopback registration by itself — a reviewer will close it as intended MCP/native behaviour.
- **Re-verify before reporting a stale lead.** This tenant moved (between two sessions, days apart) from
  a template `/register` that accepted anything to Access-managed OAuth with every control above
  enforced. A lead captured earlier can be dead by the time you write it up; produce a
  control-by-control retest table and close it explicitly ("CLOSED — not exploitable") instead of
  shipping a stale submission.
- **Disclose test side-effects.** When the registration response has no `registration_access_token`
  (no RFC 7592 manage endpoint; `GET`/`DELETE <registration_endpoint>/<id>` → 404), clients you
  registered cannot be self-removed. Log their `client_id`s and the fact that a tenant admin must purge
  them from the Access dashboard.

## Case: mcp.rapyd.org (2026-09)

- Earlier session: `POST /register` → 201 with an arbitrary `redirect_uri`, PKCE `plain` advertised —
  looked like an open-DCR chain.
- Retest: `/register` → Cloudflare 404; the advertised registration endpoint rejects non-loopback
  redirect URIs; redirect_uri validated at `/authorize`; PKCE S256 required; `resource` required; forged
  JWTs rejected; login page = "Rapyd MCP Portal — Sign in with: SAML" only.
- Outcome: **LEAD closed as NOT EXPLOITABLE**, with the retest table kept as evidence. The same file
  recorded the 4 loopback clients registered during testing for the tenant admin to purge.
