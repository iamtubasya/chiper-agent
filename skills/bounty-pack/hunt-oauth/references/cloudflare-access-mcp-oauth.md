# Cloudflare Access OAuth / MCP-server OAuth — audit recipe

Case study: `mcp.rapyd.org` (Rapyd, 2026-09-30). Target was an MCP server protected by
**Cloudflare Access-managed OAuth**. This file is the reusable test matrix, the exact command
shapes, and the verdict discipline (the lead was closed as NOT exploitable — do not submit
without re-running these controls).

Applies to: MCP servers (`/mcp`, `/sse`), any host whose 401 advertises `resource_metadata`,
any `*.cloudflareaccess.com` issuer, and any app that offers **Dynamic Client Registration (DCR)**.

---

## 1. Fingerprint the surface in 3 requests

```bash
UA='Mozilla/5.0'; H=(-s -m 20 -H 'X-Bugcrowd: Bugcrowd-<user>' -A "$UA")
curl "${H[@]}" -D - -o /dev/null https://TARGET/mcp     # 401 + WWW-Authenticate
curl "${H[@]}" https://TARGET/.well-known/oauth-protected-resource/mcp
curl "${H[@]}" https://TARGET/.well-known/oauth-authorization-server
```

Expected shape (Cloudflare Access OAuth):

```json
// 401 challenge (RFC 9728)
WWW-Authenticate: Bearer realm="OAuth", error="invalid_token",
  resource_metadata="https://TARGET/.well-known/oauth-protected-resource/mcp"

// protected-resource
{"resource":"https://TARGET/mcp","authorization_servers":["https://<team>.cloudflareaccess.com"]}

// authorization-server
{"issuer":"https://<team>.cloudflareaccess.com",
 "authorization_endpoint":"…/cdn-cgi/access/oauth/authorization",
 "token_endpoint":"…/cdn-cgi/access/oauth/token",
 "registration_endpoint":"…/cdn-cgi/access/oauth/registration",
 "revocation_endpoint":"…/cdn-cgi/access/oauth/revoke",
 "response_types_supported":["code"], "response_modes_supported":["query"],
 "grant_types_supported":["authorization_code","refresh_token"],
 "token_endpoint_auth_methods_supported":["client_secret_basic","client_secret_post","none"],
 "code_challenge_methods_supported":["S256"]}
```

Read `registration_endpoint` — **that** is where DCR lives, not `/register` on the resource host.
A `POST /register` on the resource host returning Cloudflare's 404 means the app-level DCR from the
original MCP template is gone (the deployment moved to Access-managed OAuth).

## 2. DCR allowlist probe (the decisive test)

Register clients with different redirect classes and diff the responses:

```bash
A='https://<team>.cloudflareaccess.com/cdn-cgi/access/oauth'
dcr(){ curl -s -m 25 -H 'Content-Type: application/json' -X POST -d "$1" "$A/registration"; echo; }
dcr '{"redirect_uris":["https://evil.example/cb"],"token_endpoint_auth_method":"none","client_name":"t1"}'
dcr '{"redirect_uris":["http://localhost:3334/callback"],"token_endpoint_auth_method":"none","client_name":"t2"}'
dcr '{"redirect_uris":["http://127.0.0.1:8080/callback"],"token_endpoint_auth_method":"none","client_name":"t3"}'
dcr '{"redirect_uris":["javascript:alert(1)"],"token_endpoint_auth_method":"none","client_name":"t4"}'
dcr '{"redirect_uris":["https://evil.example/*"],"token_endpoint_auth_method":"none","client_name":"t5"}'
```

Observed on Rapyd:

| redirect_uri class | result |
|---|---|
| public host (`evil.example`, `claude.ai`, `chatgpt.com`, target host) | `400 invalid_client_metadata` "redirect_uri is not allowed by the account configuration" |
| wildcard | same 400 |
| `javascript:` | `400 invalid_client_metadata` "Invalid redirect URI" |
| `http://localhost:<port>/callback`, `http://127.0.0.1:<port>/callback` | **`201 Created`** → client_id issued |

**Interpretation:** open DCR restricted to loopback URIs is the intended OAuth-for-Native-Apps
pattern (RFC 8252) used by desktop MCP clients. It is **not** a finding on its own — the redirect
always lands on the *victim's own* machine, which the attacker cannot read.

## 3. Does `/authorize` actually validate? (this decides the lead)

Register one loopback client, then try redirect URIs that differ from the registered value:

```bash
CID=<client_id from the 201>
RQ="resource=https%3A%2F%2FTARGET%2Fmcp&state=x"
# mismatch
curl -s -D - -o /dev/null "$A/authorization?response_type=code&client_id=$CID&redirect_uri=https%3A%2F%2Fevil.example%2Fcb&code_challenge=<S256>&code_challenge_method=S256&$RQ"
# registered value (control)
curl -s -D - -o /dev/null "$A/authorization?response_type=code&client_id=$CID&redirect_uri=http%3A%2F%2Flocalhost%3A3334%2Fcallback&code_challenge=<S256>&code_challenge_method=S256&$RQ"
```

| probe | observed | meaning |
|---|---|---|
| mismatched redirect_uri | `400` Cloudflare Access error page, **no redirect** | redirect_uri validated at authorize ✅ |
| registered redirect_uri | `302` → `…/cdn-cgi/access/login/TARGET?kid=…` | flow proceeds |
| missing `resource` | `400 invalid_target` "No resource parameter found" | tokens are audience-bound ✅ |
| unknown `client_id` | `400` Access error page | client must be registered ✅ |

If a mismatched redirect_uri **redirects** instead of erroring, that is a real auth-code-theft bug —
stop and pursue it. Otherwise the DCR capability is not chainable and the lead closes.

## 4. PKCE enforcement

```bash
# no code_challenge
…/authorization?...&redirect_uri=<registered>&$RQ
# → 302 to the REGISTERED uri with ?error=invalid_request&error_description=code_chal… (required)
# code_challenge_method=plain
…&code_challenge=abc123&code_challenge_method=plain
# → 302 … error=invalid_request (S256 only)
```

PKCE enforced = note it in the closure evidence. PKCE *optional* would be a genuine downgrade
finding (code interception), so this test matters in both directions.

## 5. Token endpoint + JWT forgery battery

```bash
# unknown client → 401 invalid_client "Client not found"  (client registry is real)
curl -s -X POST -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=authorization_code&code=test&client_id=abc&redirect_uri=https://evil.example/cb' \
  "$A/token"
# unsupported grants (client_credentials / password / jwt-bearer) → invalid_client, never a token
```

Then hammer the resource with forged bearer tokens — cheap and worth doing on any MCP/JWT endpoint:

| token | observed |
|---|---|
| random 3-part string | 401 |
| `alg:none` with `aud=https://TARGET/mcp`, correct-looking `iss` | 401 |
| HS256 signed with `secret` | 401 |
| opaque string | 401 |

All 401 ⇒ no algorithm confusion / no signature skipping. Record it as a **verified negative**.

## 6. Can an outsider even complete the login? (gate on the IdP, not the OAuth config)

Fetch the Access login page the authorize call redirects to and inventory the offered methods:

```bash
L=$(curl -s -D - -o /dev/null "$A/authorization?…&$RQ" | grep -i '^location:' | tr -d '\r' | sed 's/^[Ll]ocation: //')
curl -s "$L" | grep -oiE '(one-time pin|send me a code|saml|okta|google|github)' | sort -u
```

Observed: `"Log in to Rapyd MCP Portal — Sign in with: SAML"` only — no one-time-PIN, no social IdP.
⇒ an external party cannot self-authenticate, therefore cannot mint an Access JWT for that team
domain, therefore cross-app/`aud`-confusion tests are **not possible** (you cannot obtain any valid
JWT for the tenant). If OTP *is* offered for arbitrary addresses, that changes everything: obtain your
own JWT for a sibling Access app on the same team domain and try it against the MCP resource to test
`aud`/`iss` validation. Absence of a self-service IdP is itself a closure argument — write it down.

## 7. Verdict + hygiene

- Write the closure as a **control-by-control table** (as above) into the engagement log and
  `findings.json` (`status: "CLOSED — NOT EXPLOITABLE (retested <date>)"` with a
  `retest_<date>` evidence object). A closed lead with evidence is worth as much as a finding.
- **DCR is create-only on Cloudflare Access:** the 201 body has `client_id` +
  `registration_client_uri` but **no `registration_access_token`**, and `GET/DELETE
  /registration/<id>` → 404. You cannot remove the clients you created. Record every issued
  `client_id` (+ the redirect_uri used) in the engagement log so the program can purge them from the
  Access dashboard, and disclose the list if you ever contact them.

## Meta-lessons (learned the expensive way)

1. **Leads rot — re-test before submitting.** The same target's earlier observation ("open DCR,
   arbitrary `redirect_uri` accepted, PKCE `plain` advertised") was **unreproducible** a day later
   because the vendor moved the MCP server behind Access-managed OAuth, which enforces exactly the
   missing controls. Never submit a lead from a previous session without re-running the matrix; the
   closure evidence is what protects your reputation.
2. **Vendor-implemented OAuth = look at the tenant config, not the code.** With Cloudflare Access
   (or Auth0/Okta) the *implementation* is not the target; the misconfiguration is. Probe the tenant
   (allowlist, PKCE, login methods) rather than reverse-engineering the vendor's AS.
3. **"Anonymous client registration exists" is not a finding.** State the redirect class it is
   restricted to and the concrete path to token theft; if that path needs code execution on the
   victim's machine, the honest rating is informational at best.
