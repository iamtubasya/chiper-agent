# Reference: Vulnerability Classes — Web / API (v2)

> Full attack surface coverage. Detection → exploitation → fix for every class.
> Based on: OWASP Top 10, API Security Top 10, real-world research.

## Broken Access Control / IDOR
- **Detection**: objects referenced via ID in URL/body; weak access control; role/tenant boundary transitions. Sequential/predictable IDs are a strong signal.
- **Exploitation**: access/modify resources across authorization boundaries. Enumerate.
- **Impact**: unauthorized data access, privilege escalation, full account takeover.
- **Fix**: per-object server-side authorization check, deny-by-default.

## Broken Authentication / Session
- **Detection**: flawed login/password reset/MFA/session flows; weak tokens; logout doesn't invalidate; weak rate limiting on login.
- **Exploitation**: session token reuse after logout, brute-force weak credentials, MFA bypass, JWT manipulation (alg:none, key confusion, kid injection).
- **Impact**: account takeover (ATO).
- **Fix**: proper session invalidation, strong random tokens, rate limiting + lockout, MFA.

### Account Takeover via Weak Secret / Credential Reuse
- **Detection**: Auth system uses a user-chosen "secret" as sole credential (no password, no MFA, no email verification). Same secret deterministically returns the same account. No complexity requirements on secret. No rate limiting on creation attempts.
- **Exploitation**:
  1. Victim creates account with weak/guessable secret (e.g., "password123", "mysecret")
  2. Attacker calls account creation endpoint with victim's secret: `POST /v1/ownerships/secrets {"secret": "victim_weak_secret"}`
  3. Server returns SAME account_id + SAME player_id as victim
  4. Attacker mints JWT token for the account
  5. Full access: same inventory, same wallet connections, same game progress
  6. Attack scales: dictionary attack on weak secrets creates mass account takeover
- **Root cause**: "Secret" used as sole auth factor + deterministic account resolution + no complexity requirements + no rate limiting = credential stuffing at the account creation layer
- **Severity**: CRITICAL. Full account takeover with zero prior access. In blockchain games: NFT theft, asset draining. In financial apps: fund access. This is WORSE than password brute-force because there's no lockout mechanism — the attacker uses the account creation endpoint, not the login endpoint.
- **Key indicators**: `identity_provider: SECRET` / `origin: SECRET` without verification; `POST /v1/ownerships/secrets` accepts arbitrary strings; same secret → same account_id; no complexity/length requirements; no CAPTCHA; no lockout.
- **Fix**: require email/phone verification on first creation; enforce minimum secret complexity; implement rate limiting + lockout on creation endpoint; use separate creation vs lookup endpoints; add MFA.
- **Distinction from generic broken auth**: This is NOT about password guessing or session fixation. The vulnerability is in the account CREATION flow — the same endpoint that creates accounts also acts as the login mechanism, and it has none of the protections a login endpoint would have.
- **Example (Aurory 2026-08)**: `POST /v1/ownerships/secrets {"secret": "mysecret123"}` → account s-00015150, player p-f297PMHOBqMJDiN. Attacker calls same endpoint with same secret → same account_id, same player_id, same 106 items, same wallet. Deterministic. No lockout. No complexity check. Verified 2x.

### Mass Account Creation / Unauthenticated Registration (API)
- **Detection**: API endpoints that create accounts/ownership/tokens without auth, email verification, KYC, or social login. Look for: `/ownerships`, `/tokens`, `/accounts/create`, `/signup` without auth headers.
- **Exploitation**:
  1. Call unauthenticated account creation endpoint with arbitrary data
  2. Mint JWT/access tokens for the new account (also unauthenticated)
  3. Use tokens to access all authenticated endpoints
  4. Mass-iterate: create N accounts, get N × free items, N × referral codes
- **Impact**: economy manipulation (free items), bot farming, KYC bypass, referral abuse, leaderboard manipulation.
- **Severity**: CRITICAL when combined with economic impact (free items/currency). MEDIUM when limited to account creation without downstream abuse.
- **Key indicators**: `identity_provider: SECRET` / `origin: SECRET` without verification; sequential `account_id` patterns (`s-00020618`); `platform: WEB_UNRESTRICTED` accepted without social login.
- **Fix**: require API key/mTLS for internal endpoints; validate identity_provider against whitelist; implement CAPTCHA/rate limiting; audit existing SECRET-provider accounts.
- **Example (Aurory 2026-08)**: `POST /v1/ownerships/secrets` (no auth, any tenant_id/secret) → `POST /v1/tokens` (no auth) → full API access + 106 free items per account. 7 accounts created in PoC = 742 free items.

## Server-Side Request Forgery (SSRF)
- **Detection**: features that fetch URLs from user input (webhooks, importers, image fetchers, PDF renderers, API proxies).
- **Exploitation**: request internal services, cloud metadata endpoints (169.254.169.254), internal APIs, port scan via timing.
- **Bypass techniques**: URL parser confusion, DNS rebinding, redirect chains, IPv6/IP decimal encoding, 127.0.0.1 variants.
- **Impact**: internal service access, cloud metadata exfiltration, RCE via internal services.
- **Fix**: destination allowlist, block internal/link-local IPs, reject redirects, network isolation.

## Injection (SQL / NoSQL / Command / Template)
- **SQLi**: 
  - Detection: error-based (`'`, `"`, `\`), boolean-based (AND 1=1 vs 1=2), time-based (SLEEP/WAITFOR), UNION-based (ORDER BY column count).
  - Exploitation: data extraction via UNION, blind exfiltration, file read/write (INTO OUTFILE, LOAD_FILE), RCE via xp_cmdshell/UDF.
  - Fix: parameterized queries/prepared statements, ORM, stored procedures.
- **NoSQLi**: MongoDB $where/$regex injection, operator injection ($gt, $ne), JS injection in $where.
- **Command injection**: `;`, `|`, `&&`, `||`, backticks, `$(...)`, newline injection. Exploit: reverse shell, data exfil.
  - Fix: avoid shell execution, use execFile/spawn without shell, input sanitization.
- **SSTI (Server-Side Template Injection)**: detect via `{{7*7}}`, `${7*7}`, `<%=7*7%>`. Exploit: RCE via framework-specific gadgets.
  - Fix: sandboxed templates, avoid user input in templates.

## Cross-Site Scripting (XSS)
- **Detection**: reflected/stored/DOM-based. Input echoed without encoding; dangerous DOM sinks (innerHTML, document.write, eval, setTimeout with string).
- **Exploitation**: session theft, keylogging, phishing overlays, CSRF via XSS, crypto wallet drainer UI.
- **Bypass**: encoding tricks, mutation XSS (mXSS), dangling markup, CSP bypass via JSONP/script gadgets.
- **Fix**: contextual output encoding, CSP, HTML sanitization, avoid dangerous sinks.

## Cross-Site Request Forgery (CSRF)
- **Detection**: state-changing actions without anti-CSRF tokens, no origin/referer check, SameSite=None cookies.
- **Exploitation**: forged form submission, XHR/fetch from attacker origin, chained with XSS.
- **Fix**: anti-CSRF tokens, SameSite=Lax/Strict cookies, origin/referer verification.

## Insecure Deserialization
- **Detection**: serialized data from user input (cookies, params, uploads). PHP (unserialize), Java (ObjectInputStream), Python (pickle), Node (node-serialize, js-yaml), .NET (BinaryFormatter).
- **Exploitation**: gadget chains for RCE. ysoserial (Java), PHPGGC (PHP), node-specific gadgets.
- **Fix**: avoid deserializing untrusted data, use safe formats (JSON), type allowlisting, signing.

## XXE (XML External Entity)
- **Detection**: XML parser accepting user input (upload, SOAP, SAML, RSS).
- **Exploitation**: file read via SYSTEM entity, SSRF via external DTD, DoS via billion laughs.
- **Bypass**: parameter entities, external DTD, XInclude, UTF-7 encoding.
- **Fix**: disable external entity resolution, use safe parsers (defusedxml).

## File Upload & Path Traversal
- **Upload**: bypass extension filters (double extension .php.jpg, null byte, case variants), content-type manipulation, polyglot files, image with embedded PHP.
- **Path Traversal**: `../`, `..\`, URL-encoded variants, absolute paths, symlinks, zip slip.
- **Impact**: RCE (web shell), arbitrary file read, source code disclosure.
- **Fix**: validate type/content, store outside webroot, normalize paths, extension deny-list.

## Business Logic Flaws
- **Detection**: race conditions (concurrent requests), negative prices, skipped steps, coupon reuse, quota bypass.
- **Exploitation**: race with Turbo Intruder, parameter pollution, workflow bypass, integer overflow.
- **Impact**: financial loss, feature abuse, inventory manipulation.
- **Fix**: server-side validation, atomic operations/locking, state machine enforcement.

## API-Specific (REST / GraphQL)
- **REST**: BOLA (IDOR for APIs), mass assignment, excessive data exposure, deprecated API versions without auth.
- **GraphQL**: open introspection, nested query/aliasing for DoS, excessive data exposure per field, weak per-resolver auth.
- **Exploitation**: BOLA via ID enumeration, mass assignment via additional params, GraphQL query depth attacks.
- **Fix**: per-object & per-field authorization, disable introspection in production, query cost limiting, field allowlists.

## Misconfiguration & Info Disclosure
- **Detection**: missing security headers, directory listing, debug/stack trace exposure, exposed backups (.bak, .swp, ~), public S3/GCS buckets, default credentials.
- **Exploitation**: dump exposed data, use leaked credentials, access debug endpoints.
- **Fix**: config hardening, disable debug in production, rotate leaked secrets.

## Known Vulnerable Components
- **Detection**: outdated library/framework/CMS versions with public CVEs. Wappalyzer + version scanning.
- **Exploitation**: Metasploit, public PoCs, custom adaptation. Check exact version compatibility.
- **Fix**: patch/upgrade, SCA in CI/CD, monitor advisories.

## WebSocket & Real-time
- **Detection**: ws:// or wss:// endpoints, missing auth handshake, CSWSH (Cross-Site WebSocket Hijacking).
- **Exploitation**: hijack connections, inject messages, auth bypass, DoS.
- **Fix**: origin check, auth tokens in connection, rate limiting.

## OAuth 2.0 / OpenID Connect Attacks
- **Detection**: redirect_uri validation, state parameter missing, PKCE absence, scope confusion, CSRF on authorization endpoint.
- **Exploitation**: redirect_uri bypass (open redirect, path traversal, subdomain takeover), CSRF linking attacker account, scope upgrade.
- **Fix**: strict redirect_uri validation, PKCE, state parameter, CSRF protection.

## JWT Attacks
- **Detection**: JWT in Authorization header, weak/absent signature verification.
- **Exploitation**: alg:none, HMAC key confusion (public key as HMAC secret), kid injection (path traversal, SQLi), JWK header injection, expired token reuse.
- **Fix**: enforce algorithm, validate claims, use strong keys.
