# Testing redirect_uri validation when the code flow is entitlement-gated

Verified live 2026-10-26 on portal.first.org (FIRST bug bounty): authorization
endpoint validated client_id but not redirect_uri; 302 to arbitrary external URIs.

## The problem this solves

You suspect an OAuth 2.0 authorization endpoint does not validate `redirect_uri`,
but the authorization-code flow (the one that actually leaks a code) is gated:
your test account is not entitled to the client's service, so `response_type=code`
returns a generic 401/error page BEFORE any redirect. You cannot observe a code
leaving the server, and you must not claim one.

## The method: use the error path

Non-code response types still exercise the redirect machinery. Request
`response_type=token` (or `id_token`, `id_token token`, `code id_token`) with an
ARBITRARY `redirect_uri`. If the server answers `302 Location: <your-uri>?error=...`,
the redirect target is attacker-controlled and redirect_uri validation is absent:

```
GET /oauth/authorize?response_type=token
    &redirect_uri=https://evil.example.com/cb
    &client_id=<real-client-id>&scope=openid&state=st123

-> 302 Location: https://evil.example.com/cb?error=unsupported_response_type
                 &error_description=implicit+grant+type+not+supported&state=st123
```

Get the real `client_id` by starting a legitimate SSO login on a dependent service
(e.g. open the JupyterHub/GitLab-style login and read the redirect to the
authorize endpoint). A bogus client_id gets `400 invalid_client`, so client_id
validation is usually present and must be acknowledged in the report.

## Variant matrix (run all; record each outcome)

| redirect_uri value | Expected if unvalidated |
|---|---|
| `https://evil.example.com/cb` | 302 to attacker domain |
| `https://legitimate@evil.example.com/cb` | 302 (userinfo trick) |
| `//evil.example.com/cb` | 302 protocol-relative |
| `https://legitimate/pathX` (suffix) | 302 (path suffix accepted) |
| `http://legitimate/path` | 302 over plain HTTP (downgrade) |
| `javascript:alert(1)` | typically 406/400 (scheme check exists) |
| `https://legitimate/path/../../x` | typically 406/400 (traversal check) |

## Honest framing (proved vs argued)

- **Proved:** arbitrary external redirect from the authorize endpoint (open
  redirect on a trusted domain + OAuth flow manipulation primitive).
- **Argued, not proven:** authorization-code interception leading to account
  takeover on SSO-linked services, for entitled victims. If the code flow 401s
  for your unentitled test account before any redirect, say exactly that.
- Rate the report on the proven impact (open redirect, typically Medium with
  UI:R), and state the escalation condition ("would rate High if the code-theft
  chain is confirmed on an entitled account").
- Also check the error path reflects nothing injectable, and probe
  `/.well-known/openid-configuration` for the endpoint map (issuer, token,
  userinfo, supported grant types) before writing the report.

## Adjacent checks worth one request each

- `POST /oauth/token` with `grant_type=user_credentials` / `password` (advertised
  but often disabled) and with no client credentials (expect `invalid_client`).
- Dynamic client registration (`POST /oauth/register`) - usually 404; if open,
  that is a separate, larger finding.
- `GET /oauth/userinfo` with a garbage bearer (expect clean 401, note any
  verbose error as an info-leak minor).
