# SPA API and Model Context Protocol (MCP) Reconnaissance

## 1. Cloudflare Email Protection Decoding
When public policy or security contact emails are obfuscated using Cloudflare's `data-cfemail` attribute:
```python
def decode_cf_email(cf_hex: str) -> str:
    r = int(cf_hex[:2], 16)
    return ''.join(chr(int(cf_hex[i:i+2], 16) ^ r) for i in range(2, len(cf_hex), 2))
```

## 2. Certificate Transparency & SAN Correlation
- **Failover**: When `crt.sh` (`https://crt.sh/?q=%25.domain&output=json`) times out, query CertSpotter:
  `https://api.certspotter.com/v1/issuances?domain=example.com&include_subdomains=true&expand=dns_names`
- **TLS SAN Extraction**: For origin servers, extract shared Subject Alternative Names:
  `openssl s_client -connect host:443 -servername host 2>/dev/null | openssl x509 -noout -ext subjectAltName`

## 3. SPA JavaScript Bundle Endpoint Mining
Single-Page Applications (React/Vue/Vite/Next.js) bundle API route maps in `/assets/index-*.js`:
- Extract versioned REST endpoints (`/api/v[0-9]+/`):
  `grep -oE "['\"\`]/api/v[0-9]+/[^'\"\` ]+['\"\`]" index.js | tr -d "'\"\`" | sort -u`
- Identify parameterized routes containing `${id}` or `:id` for BOLA/IDOR testing.

### 3a. Vite lazy-chunk route mining (docs sites / API references)
Vite/React "docs" SPAs (e.g. Mintlify-style) split each endpoint into a lazy-loaded chunk. The main `index-*.js` often only carries route *names*, not the real HTTP paths — grep returns nothing for `/api/vN/`. Two-step extraction:

1. **Grab the real bundle, not the SPA-fallback HTML.** The main HTML references `/assets/index-<hash>.js`, but Cloudflare/SPA fallback may 301 that asset back to `/` and serve HTML (size == HTML size, not JS). Serve the asset from a host that isn't behind the SPA-rewrite, or use `curl -sL` and check `%{size_download}` vs the HTML size. If you got HTML, the redirect `location:` header tells you the canonical host (e.g. `a-docs` vs `docs`).
2. **Enumerate chunk names from the main bundle**, download each, and extract the real paths:
   ```python
   import re, subprocess, os
   b = open('bundle.js', encoding='utf-8', errors='replace').read()
   chunks = sorted(set(re.findall(r'assets/[a-zA-Z0-9_.-]+\.js', b)))  # skip the main index-*.js
   routes = {}
   for c in chunks:
       p = os.path.join('chunks', os.path.basename(c))
       if not os.path.exists(p):
           subprocess.run(['curl','-sL','-A','Mozilla/5.0',f'https://{host}/{c}','-o',p])
       d = open(p, encoding='utf-8', errors='replace').read()
       for m in re.finditer(r'path:"(/[^"]+)"', d):
           seg = d[max(0, m.start()-200):m.start()]
           meth = re.findall(r'method:"([A-Z]+)"', seg)[-1:]
           ver  = re.findall(r'version:"([0-9]+)"', seg)[-1:]
           routes[(meth[0] if meth else '?', m.group(1), ver[0] if ver else '?')] = c
   ```
   Each chunk carries `method:"GET"`, `version:"1"`, `path:"/api/v1/merchant/wallets/:id/addresses/:aId"` — the full surface in one pass. This yields the *complete* endpoint map (110+ routes on CoinPayments) far faster than crawling the rendered docs.

### 3b. Relative `api/vN/...` paths (app bundles)
App bundles call their API via **relative** paths (`api/v1/wallets/${id}/...`), not absolute `/api/vN/` — grep for `/api/vN/` misses them. Mine both:
```bash
grep -oE "api/v[0-9]+/[a-zA-Z0-9/_{}\$.:-]{2,70}" bundle.js | sort -u
```
Relative paths reveal app-only endpoints absent from the public docs (e.g. `api/v1/wallets/two-fa-unlock-vault`, `api/v1/esims/${t}/spend/${n}/broadcast`, `api/v1/referral-codes`) that are prime IDOR/business-logic targets.

### 3c. Environment → host mapping leak
Bundles with multi-env config embed a `window.location.hostname → env` map. Extract it and probe the internal hosts it names — they are often non-production (sandbox/staging) hosts never caught by subfinder/crt.sh/DNS:
```bash
grep -oE '"api\.[a-z0-9.-]+":"(sandbox|b|c|staging|prod)"[^}]{0,400}' bundle.js
```
(CoinPayments: `api.coinpayments.net`=sandbox, `b-api`/`c-api`=internal stages — not in any CT/DNS source.) These hosts are in-scope (same parent domain) and frequently have weaker auth or debug features.

## 4. MCP (Model Context Protocol) Endpoint Probing
Exposed LLM agent connectors or developer tool endpoints often mount at `/mcp`:
- If `GET /mcp` returns `405 Method Not Allowed`, test read-only JSON-RPC:
  ```bash
  # Step 1: Initialize handshake
  curl -s -X POST https://target/mcp \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"auditor","version":"1.0"}}}'

  # Step 2: List exposed tool definitions
  curl -s -X POST https://target/mcp \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
  ```
- **Triaging MCP Findings**:
  * If `tools/list` returns schema, inspect parameters for sensitive backend operations.
  * If all `tools/call` invocations return `403 Forbidden` or `disabled`, document as informational unless execution can be triggered without credentials.

## 5. OAuth2 / OIDC Discovery and redirect_uri Validation Triage
Auth subdomains (`auth.`, `login.`, `id.`, `sso.`) running IdentityServer4 / Duende / Keycloak / Auth0 leak config through the discovery document:
```bash
curl -s https://auth.target/.well-known/openid-configuration | jq .
curl -s https://auth.target/.well-known/openid-configuration/jwks
```
Extract `authorization_endpoint`, `token_endpoint`, `code_challenge_methods_supported`, `id_token_signing_alg_values_supported`.

**Find the real `client_id` in the app bundle** — never guess. Grep for the authorize call:
```bash
grep -oE 'client_id:[$a-zA-Z0-9_"'"'"'. -]{0,40}' bundle.js
grep -oE 'const \\\$w="[^"]+"' bundle.js        # minified alias for client_id
grep -oE 'client_id=\$\{?[A-Za-z0-9_$]+\}?' bundle.js
```
(CoinPayments: `client_id="coinpayments-aphrodite-pkce"`, scope `openid profile orion offline_access`, redirect `https://a-dashboard.coinpayments.net/callback`.) Then probe that real client_id with a candidate redirect.

**Interpreting the authorize response — three distinct shapes:**
| Response | Meaning | Action |
|---|---|---|
| `400` + `invalid_redirect_uri` / `unauthorized_client` | Strict allow-list check *before* login | Not exploitable |
| `302 → /connect/authorize/callback` or `302 → login page` with a *session cookie already set* | **redirect_uri validated AFTER login** — classic auth-code injection precondition | **High→Critical candidate** — needs an authenticated session to prove whether `code` lands on attacker redirect |
| `302 → /Error?errorId=<opaque>` for *every* redirect_uri including legitimate ones | Error indirection (IdentityServer error middleware) — inconclusive, validation result hidden | Test with a real session; do not claim a finding |

**Two confirmation requirements before reporting:**
1. `redirect_uri=https://evil.com/cb` on the *real* client_id returns a redirect that is **not** a generic error page.
2. With a self-registered account authenticated, the returned `302 Location` actually points at `evil.com` and carries `?code=`. An error page alone is not proof.
Also test PKCE downgrade (`code_challenge_method=plain` is advertised here — confirm the server rejects missing PKCE for public clients) and `response_type=token` (implicit) on a client declared code-only.

### 5b. Obtaining an authenticated session (OIDC + PKCE via browser)
When redirect_uri triage is inconclusive and IDOR/BOLA testing needs a real session, drive the code flow yourself instead of waiting on the user:

1. Generate PKCE + state/nonce:
   ```python
   import secrets, hashlib, base64
   verifier = secrets.token_urlsafe(64)
   challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
   state = secrets.token_urlsafe(16); nonce = secrets.token_urlsafe(16)
   ```
2. Navigate to `https://auth.target/connect/authorize?client_id=<real_id>&response_type=code&scope=openid%20profile%20...&redirect_uri=<real_redirect>&code_challenge=<challenge>&code_challenge_method=S256&state=<state>&nonce=<nonce>&prompt=login`.
3. IdentityServer login is **multi-stage** (email → password → 2FA). `browser_snapshot` after each submit tells you which stage you're on: "Welcome" + the typed email = **account exists**; "Enter password" = email accepted; "2-Step Verification" = **password correct**. This is itself an account-validity oracle — note it, don't brute-force it.

**Client-side password hashing (IdentityServer + CryptoJS).** Some deployments do NOT post the plaintext password — the submit handler hashes it client-side into a hidden `Input.PasswordHash` field and posts that instead. Submitting the raw password via `form.submit()` (or a headless driver) bounces with `The PasswordHash field is required`. The scheme is visible in the login page's inline script or `/js/site.js`:
   ```js
   // key = email.toUpperCase(), msg = raw password (CryptoJS.HmacSHA256)
   function hmacSha256Async(key, msg) { return CryptoJS.HmacSHA256(msg, key).toString(CryptoJS.enc.Hex); }
   ```
   Reproduce in-page before submit:
   ```js
   const f = [...document.forms].find(x => x.action.includes('Account/Login'));
   f.querySelector('input[name="Input.PasswordHash"]').value = await hmacSha256Async(email.toUpperCase(), pw);
   f.querySelector('input[name="Input.Password"]').value = '';   // hash is what validates
   f.submit();
   ```
   Note: `HMAC(email, password)` client-side is weak — the hash *is* the credential (replayable, email is the key). That's a finding-worthy observation separate from the automation detail. The password form fields are `Input.Email`, `Input.Password`, `Input.PasswordHash` (+ `__RequestVerificationToken`, `__Invariant`).
4. Capture `code` from the final redirect, then exchange at `/connect/token` with the stored `code_verifier`.

**Cheap password-grant probe (before touching the browser):**
```bash
curl -s -X POST https://auth.target/connect/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=password&client_id=<id>&username=<u>&password=<p>&scope=openid'
```
- `unauthorized_client` → client is public / PKCE-only, ROPC disabled (expected — proves code+PKCE flow, NOT a vuln).
- `invalid_grant` → wrong credentials (or client allows ROPC and rejected creds).
- `invalid_client` → wrong client_id / missing client secret.

**Stop at 2FA — do not guess the OTP.** Reaching the prompt already confirms email+password validity; attempting codes is "brute force" (forbidden by most program policies, forfeits safe harbor). Ask the user for the code, or have them log in and hand over the session cookie / API key instead.

**Retrieving the emailed OTP (when the user authorises it).** For email-OTP flows the code lands in the account mailbox. If the user has handed over mailbox access (app password) and asked you to complete verification:
   ```bash
   himalaya envelope list --page 1 --page-size 5       # find "Your 2FA Code" / "verification"
   himalaya message read <ID> --raw | python3 -c "
   import sys,re,html
   d=sys.stdin.read(); b=re.sub(r'<(script|style)[^>]*>.*?</\1>','',d,flags=re.S|re.I)
   b=html.unescape(re.sub(r'<[^>]+>',' ',b)); m=re.search(r'Code:\s*(\d{6})',b)
   print(m.group(1) if m else 'NOT FOUND')"
   ```
   Check the email `Date:` header against `date -u` before submitting — codes are typically valid ~10 min. If a code was already consumed, request a *fresh* one (re-trigger the login) rather than reusing it. Two distinct OTP behaviours to expect: (a) IdentityServer **re-sends a new code on each fresh password submit** (old code invalidated), and (b) within a 15-min window it may instead say *"You already started a login within the last 15 minutes … enter that code"* and require the **original** code. Handle both.

**Driving the form when `browser_click`/refs are stale.** After each POST the page re-renders and prior `@eN` refs die (`Unknown ref`, or the click silently no-ops leaving the field populated but unsubmitted). Reliable fallback — set the value and submit programmatically, then read the resulting URL/body:
   ```js
   const i = document.querySelector('input[name="Input.TwoFactorCode"]');
   i.value = '792164'; i.closest('form').submit();
   ```
   Confirm progress by reading state, not the screenshot: `JSON.stringify({url:location.href.slice(0,200), body:document.body.innerText.slice(0,300)})`. A successful post-2FA lands on `https://a-dashboard.<host>/<lang>/app/...` with an empty SPA body — that's success, not a failure.

**Extracting the API bearer token after login.** The SPA keeps tokens in `sessionStorage` (look for `oidc_token`, `oidc_idtoken`, `oidc_refreshtoken`, `oidc_expiration`, and a `pkce_code_verifier`):
   ```js
   JSON.stringify({token: sessionStorage.oidc_token, exp: sessionStorage.oidc_expiration})
   ```
   Then authenticate API calls with `Authorization: Bearer <oidc_token>` and confirm against a known-good endpoint (`/api/v1/features`, `/api/v1/wallets`) — a `404` means the *endpoint path* is wrong (e.g. `/user/profile` doesn't exist), not that the token is bad. Verify the header shape empirically across `Bearer`, bare token, `X-Api-Key`, `X-Token` and pick whichever returns `200`.

**Cross-tenant (IDOR/BOLA) testing needs TWO identities.** A single authenticated session can only confirm your *own* objects render; proving BOLA requires account A requesting account B's resource id. If the user has only one test account, say so plainly and ask for a second (a Gmail `+`-alias usually suffices) before claiming any IDOR surface. Anchors to capture from your own session: wallet/invoice UUIDs, `LinkedSubstanceId`-style linkage ids from `/settings/all`, team ids — then replay them from the other account.


## 6. Auth-posture triage: 401 vs 404 vs 405 as a signal map
Before declaring an API "secure", sweep each discovered route with all methods and compare status codes — the *difference* between them is the finding surface.

| Status | Meaning | What it tells you |
|---|---|---|
| `401` / `403` | Auth middleware rejects first | Route is protected at the edge — low yield |
| `404` | Route/auth both ran and object absent | Route exists; the object lookup happened pre-auth or pivot is ID/format based |
| `405` | **Method binding resolved before auth** | Route + method table exposed. Sweep every method: another verb may return `401` (protected) where the documented one returns `405`, or vice versa |
| `400` validation body | Model binding reached | Leaks the expected ID format (e.g. `InvoiceId has wrong format` → probe GUID vs int vs 32-hex). The format hint is your IDOR entry point |

**Method sweep snippet:**
```bash
for m in GET POST PUT PATCH DELETE OPTIONS HEAD; do
  printf '%-7s' "$m"
  curl -s -X "$m" -o /dev/null -w '%{http_code}\n' -A 'Mozilla/5.0' \
       -H 'Content-Type: application/json' -d '{}' "https://api.target/api/v1/resource"
done
```
Do not treat a 405-vs-401 split as a bypass by itself — it proves route existence and method binding order, which escalates to a finding only if a non-protected method actually returns data.

## 7. Public buyer-facing endpoints (invoice / checkout surface)
Payment platforms expose some endpoints unauthenticated by design (invoice status, payment currencies, rates, refund lookups by secret). These are the highest-yield IDOR/BOLA surface because they are reachable without an account.
- Mine the docs bundle for `/invoices/:id/...`, `/refunds/:refundid/:tag`, `/refunds/:secret` and test with a **valid-format but nonexistent** ID first — the error message tells you whether the lookup ran.
- Distinguish "not found" (`404 Invoice not found` → lookup ran, ID format accepted) from "wrong format" (`400 InvoiceId has wrong format` → model binding rejected, keep probing formats).
- Test the **same path against every backend host you discovered** (e.g. `a-api` vs `api`) — they can be different envs with different validation, and one may leak where the other doesn't.

## 8. Triage Order: Low-to-High Severity
1. Unauthenticated surface sweep (info disclosure, env variables, debug routes, CORS headers).
2. Authenticated testing on self-owned accounts (IDOR/BOLA, session handling, 2FA bypass).
3. Business logic & race conditions (concurrency on coupon, transfer, withdrawal endpoints).
