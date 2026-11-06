# Managed IdP OAuth — Cloudflare Access-fronted MCP/API servers

Case study: `mcp.rapyd.org` (2026-09/10). A month-old lead said "open dynamic client
registration, arbitrary redirect_uri accepted, PKCE `plain` advertised". On retest **none of it
was true any more** — the service had been moved behind Cloudflare Access-managed OAuth, which
closed the chain. The lead was marked `CLOSED — NOT EXPLOITABLE` with the retest evidence.
Use this file as (a) the control matrix to run, and (b) the reminder that proxy/IdP-fronted
OAuth configs change under you.

## 1. Fingerprint what fronts the OAuth server

```bash
curl -s https://TARGET/.well-known/oauth-authorization-server | jq .
curl -s https://TARGET/.well-known/oauth-protected-resource/mcp      # RFC 9728
curl -si https://TARGET/mcp | head -5        # expect: 401 + WWW-Authenticate: Bearer … resource_metadata="…"
```
Real output shape seen:
```json
{ "issuer": "https://<tenant>.cloudflareaccess.com",
  "authorization_endpoint": "https://<tenant>.cloudflareaccess.com/cdn-cgi/access/oauth/authorization",
  "token_endpoint":         "https://<tenant>.cloudflareaccess.com/cdn-cgi/access/oauth/token",
  "registration_endpoint":  "https://<tenant>.cloudflareaccess.com/cdn-cgi/access/oauth/registration",
  "revocation_endpoint":    "https://<tenant>.cloudflareaccess.com/cdn-cgi/access/oauth/revoke",
  "response_types_supported": ["code"], "response_modes_supported": ["query"],
  "grant_types_supported": ["authorization_code","refresh_token"],
  "token_endpoint_auth_methods_supported": ["client_secret_basic","client_secret_post","none"],
  "code_challenge_methods_supported": ["S256"] }
```
Key point: **the endpoints live on the IdP host, not the app host.** `POST /register` on the app
host may 404 (its own template's registration route is gone) while DCR is alive at
`…/cdn-cgi/access/oauth/registration`. Always read the metadata instead of guessing paths.

## 2. Control matrix (run every row; record raw responses)

| # | Test | Vulnerable result | Secure result seen |
|---|---|---|---|
| 1 | DCR with a **public** redirect (`https://evil.example/cb`), a wildcard, `javascript:` | 201 Created | `400 invalid_client_metadata: "redirect_uri is not allowed by the account configuration"` / `"Invalid redirect URI"` |
| 2 | DCR with **loopback** redirects (`http://localhost:3334/callback`, `http://127.0.0.1:8080/cb`) | — | **201 Created** — the deliberate RFC 8252 native-app allowance; keep the `client_id`, it is your test handle |
| 3 | `/authorize` with the registered client + the registered `redirect_uri` | 302 to login = flow starts | 302 → `…/cdn-cgi/access/login/<app-host>?kid=…` |
| 4 | `/authorize` with a **different** `redirect_uri` (same client) | redirect to attacker URI | **400 Cloudflare Access error page, no redirect** = validation present |
| 5 | `/authorize` **without** `code_challenge`, then with `code_challenge_method=plain` | accepted | 302 back to the registered URI with `error=invalid_request` (code_challenge missing) / plain rejected — **S256 required** |
| 6 | `/authorize` **without** `resource=` | token unbound / confused deputy | `400 invalid_target: "No resource parameter found"` (audience binding enforced) |
| 7 | `/authorize` with an **unknown `client_id`** | login page served | 400 Access error page |
| 8 | `POST /token` with an unknown client (any grant) | token issued | `401 invalid_client: "Client not found"`; missing client → `"Client ID is required"` |
| 9 | Forged bearer JWT to the resource: random junk, `alg:none`, HS256 with a guessed secret | 200 / tool access | `401` for all (`invalid_token`, or the app's generic "session expired") |
| 10 | **Which login methods does the tenant offer?** curl the login page from the metadata flow | one-time-PIN for arbitrary emails → *you* can mint an Access JWT | `Sign in with: SAML` only (enterprise IdP) ⇒ an outsider cannot self-authenticate, so token-theft/permission confusion is not reachable |
| 11 | Revocation endpoint without `client_id` | 200 | `401 invalid_client: "Client ID is required"` |
| 12 | Client cleanup (`GET`/`DELETE /registration/<client_id>`, RFC 7592) | delete works | **404** — the good news is you cannot remove the clients you created; disclose them as engagement state and let the vendor's admin purge the list |

## 3. Reporting rules for this class

- **Loopback-only DCR is a design choice, not a finding.** It is the standard native-app pattern;
  without code execution on the victim's machine it cannot be chained to token theft. Saying
  "open DCR" when it is loopback-restricted gets you closed as informational.
- **Register clients sparingly.** Each row-1/2 test leaves a client in the tenant's list; some
  tenants offer no delete. Prefer one registration per engagement, reuse its `client_id` for the
  rest of the matrix, and log the IDs you created.
- Free Win: the retest itself is deliverable. A stale lead that is now mitigated is worth an
  explicit `CLOSED — NOT EXPLOITABLE` entry with the raw 400/401 bodies, so nobody re-reports it.
- Client-controlled `device_fingerprint` / `device_os` / `device_timezone` headers (seen on a
  hosted-verify flow, not Access) are spoofable by definition — only worth noting if some control
  actually depends on them.

## 4. Adjacent bearer-link pattern (same engagement)

Hosted application links (`/verify?token=happ_…&otk=…`) are bearer credentials: the SPA sends the
URL token as a custom header (`kyb_token`), so `curl -H "kyb_token: <token>"` reproduces access
with no browser. Test in a **clean profile** to prove session-independence, then enumerate the
write/OTP surface from the bundle before judging severity. Details and the exact PoC shape live in
`browser-cdp-auth-audit` → "Hosted application link flows are bearer credentials".
