---
name: bug-bounty-recon-patterns
description: "Bug bounty recon — scope APIs, SPA JS bundle analysis, CORS validation, IP blocks, target notes."
version: 1.0.0
---

# Bug Bounty Recon Patterns & Target Notes

Support reference for `bug-bounty` skill. Load when starting a hunt.

## Local Payload Reference (2026-08 added)

Clone of `swisskyrepo/PayloadsAllTheThings` (79K⭐) at `/root/scripts/PayloadsAllTheThings/` (22MB). Use for payload crafting per vuln class — see `payloads-all-the-things` skill for category index & lookup commands. Tool arsenal & recon pipeline: `references/tool-arsenal.md`.

## Communication Style (recurring user correction)

User reacted with a blunt "Oyyyy" to a long recon status message — that's a verbosity complaint, treat it as first-class. For this class of task:
- Lead with the verdict in the first line (found something / found nothing exploitable / blocked, need X).
- Then a tight bullet list of what was checked — no re-narration of the tool-call sequence, no repeating policy text the user can already see on the page.
- Don't apologize-then-repeat the same length next turn — actually compress. If report has more than ~8 bullet lines, it's too long for a status update; move detail into the reference file instead of the chat reply.

See also:
- `references/cloudflare-and-bot-bypass-calibration.md` — Cloudflare block classification
- `references/browser-console-api-discovery.md` — browser_console fetch for API discovery when curl is blocked
- `references/github-source-code-recon.md` — clone target repos, mine webpack/CSP/config t
- `references/wayback-machine-api-docs-bypass.md` — Wayback Machine snapshots for bypassing password-protected API docs (pre-dates password gates)
- `references/preconnect-microservice-discovery.md` — `<link rel="preconnect">` in HTML reveals internal microservice architectureo discover internal subdomains, API endpoints, dev/staging environments
- `references/session-target-notes.md` — per-target session artifacts
- `references/ip-and-geo-notes.md` — IP/geo-blocking context
- `references/blocked-target-proxy-bypass.md` — diagnosing and working around a target that blocks the operator's own IP/ASN: hard-block vs JS-challenge detection, unblocker API (Bright Data/Decodo Site Unblocker) usage and failure modes, when to escalate to residential proxy instead. Cloudflare edge (hard block vs JS challenge, proxy/site-unblocker options, retry-then-pivot discipline).
- `references/cors-false-positive-and-hackerone-2fa.md` — how to distinguish a genuine CORS reflect-any-origin bug from a correct suffix/exact-match allowlist (test with 6-8 origin variants, not one at a time); HackerOne 2FA login sessions dropping between codes — don't over-debug, pivot to unauthenticated recon after 2 failed attempts.
- `references/source-map-hunting.md` — production source map exposure: how to find .js.map files on Next.js/Webpack SPAs, extract sourcesContent with Python one-liner, search for secrets/cookie names/internal packages. Found 57 source files + auth code + cookie names on Wolt Drive (Medium, CVSS 5.3, HackerOne precedents: Shopify/NASA/Uber/GitLab).
- `references/qc-validation-workflow.md` — mandatory 5-round QC ladder before submission (Basic → Hard → God Mode → Screenshot → Final); severity calibration rules (don't inflate, be honest about downgrade); evidence rules (real screenshots from actual website, no fabrication); triager rebuttal preparation.
- `references/report-quality-notes.md` — Flutter APK credential extraction pattern, Open Redirect vs ATO inflation pitfall, YWH report status API notes.
- `references/1password-target.md` — 1Password HackerOne program: scope, rewards, real Events API endpoints, confirmed CORS false-positive (proper suffix-match validation, not a bug), $1M CTF challenge notes.

## Scope Retrieval — Platform APIs

| Platform | Method |
|---|---|
| YesWeHack | `curl -s "https://api.yeswehack.com/programs/<slug>" -H "Accept: application/json"` |
| HackerOne | browser_navigate + browser_snapshot + expand Tier A/B/C/Excluded buttons (each `[expanded=false]` after load). GraphQL `structured_scopes` query returns empty for unauthenticated requests — browser required. Alternatively scroll down after page load; table renders after JS hydration. |

YesWeHack slug: lowercase hyphenated from URL. Example: `dossier-medical-partage-program`.

## IP Block Detection (run first, before deep recon)

```bash
curl -s -I --max-time 6 "https://TARGET" 2>/dev/null | head -5
```

| Response | Cause | Fix |
|---|---|---|
| 403 + `server: AkamaiNetStorage` | Akamai WAF | Residential IP / Browserbase |
| 000 timeout | TCP geo-block | Residential proxy in target country |
| 403 + `CF-Ray:` header | Cloudflare | cloudflare-bypass skill |

## Dangling NS Delegation Detection (Subdomain Takeover Recon)

Batch-scan every in-scope domain + common subdomains for NS records with no matching A record — a classic dangling-DNS takeover signal that costs almost nothing to check and many programs accept as a report even without a full compromise PoC.

```python
import subprocess

scope_domains = ["target.com", "other-target.net"]  # from program scope
common_subs = ["www", "mail", "shop", "store", "blog", "app", "cdn", "static", "api", "admin"]

for domain in scope_domains:
    for sub in common_subs:
        fqdn = f"{sub}.{domain}"
        ns = subprocess.run(["dig", "+short", "NS", fqdn], capture_output=True, text=True, timeout=5).stdout.strip()
        if not ns:
            continue
        a = subprocess.run(["dig", "+short", "A", fqdn], capture_output=True, text=True, timeout=5).stdout.strip()
        if not a:
            print(f"[candidate] {fqdn} -> NS={ns.splitlines()} but NO A record")
```

**Verification (before claiming the finding) — query the delegated NS directly, cross-check against public resolvers:**

```bash
dig @ns1.delegated-provider.com www.target.com SOA   # expect NXDOMAIN if zone doesn't exist there
dig @8.8.8.8 www.target.com A                         # confirm from a resolver you don't control
dig @1.1.1.1 www.target.com A
```

If all of them return `NXDOMAIN` for the subdomain (while the delegated NS answers other queries fine — i.e. it's a live nameserver, not a dead IP), the subdomain is genuinely dangling: whoever can register a matching zone on that DNS provider can serve arbitrary content (or receive mail, if it's an MX-style takeover) for the subdomain.

**Pitfall — don't over-claim severity from DNS state alone:** actual compromise requires confirming the DNS provider will let an unrelated party register that exact zone name (sign up + attempt to add the zone). Without that step, report it as "dangling DNS record, subdomain takeover candidate" — many programs (per `can-i-take-over-xyz` community notes) accept this without requiring full takeover proof, but don't claim Critical/High without it.

**Confirmed example (2026-08-03):** `www.gotdrops.com` and `mail.gotdrops.com` (Harman/Roon scope) delegate NS to `ns1/ns2.namebrightdns.com`, but querying that provider directly for either subdomain returns NXDOMAIN, confirmed via 8.8.8.8 and 1.1.1.1 too. Root domain `gotdrops.com` itself is live (Cloudflare-proxied app). NameBright account creation not yet attempted to confirm exploitability — that's the next step before submission.

## Stack Fingerprinting via Wayback (when direct blocked)

```bash
curl -s "https://web.archive.org/cdx/search/cdx?url=*.target.com&output=text&limit=100&fl=original,statuscode,timestamp&collapse=urlkey&filter=statuscode:200"
```

Signals: Liferay (`com_liferay_login_web_portlet`), Keycloak (`/realms/<realm>/`), FHIR (`DocumentReference`), Next.js (`/_next/static/`).

## Wayback CDX → Live Endpoint Discovery

When direct access is blocked or for passive recon, CDX reveals historical API paths:

```bash
# All 200-status endpoints on a subdomain
python3 -c "
import urllib.request, json, ssl
ctx = ssl.create_default_context()
req = urllib.request.Request(
    'https://web.archive.org/cdx/search/cdx?url=seller.TARGET.com/*&output=json&limit=50&fl=original,statuscode&collapse=urlkey',
    headers={'User-Agent': 'Mozilla/5.0'}
)
with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
    data = json.loads(r.read())
for row in data[1:]:
    print(row[0], row[1])
"
```

Filter for: `/api/`, `auth`, `account`, `payment`, `admin`, `token`, `oauth`, `graphql`, `swagger`, `config`, `debug`.

**Temu seller.temu.com endpoints found via Wayback:**
- `/api/bg/pawpaw/abtest/trigger` — A/B test config
- `/api/bg/pawpaw/auth/history_account/query` — account history
- `/api/bg/pawpaw/region/phone_codes` — country codes (public)
- `/api/bg/pawpaw/service/status` — service health
- `/api/server/_stm` — server timestamp
- `/api/phantom/dm/wl/cg` — whitelist domains (Base64-encoded, no auth)
- `/api/phantom/xg/pfb/a3`, `/a4`, `/b`, `/l1` — telemetry beacons

## CORS Validation Pattern

```python
import urllib.request, ssl
ctx = ssl.create_default_context()
ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0"

for origin in ["https://evil.com", "null", "https://target.com.evil.com"]:
    req = urllib.request.Request(
        "https://TARGET/api/endpoint",
        headers={"User-Agent": ua, "Origin": origin}
    )
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=8) as r:
            acao = r.headers.get("access-control-allow-origin","(none)")
            acac = r.headers.get("access-control-allow-credentials","(none)")
            print(f"Origin: {origin} -> ACAO: {acao} ACAC: {acac}")
    except Exception as e:
        print(f"Origin: {origin} -> {e}")
```

**CORS severity depends on data, not config:**
- `ACAO: https://evil.com + ACAC: true` on `/api/server/_stm` (only returns `{"server_time":...}`) = **Low/Informative**
- Same CORS config on `/api/user/profile` or `/api/order/list` = **High/Critical**
- Always probe what data the endpoint returns before claiming severity

**seller.temu.com `/api/server/_stm`:** reflects any Origin + `Access-Control-Allow-Credentials: true`, but response is just server timestamp — Low severity.

---

### Temu — HackerOne

### Temu — HackerOne
- Handle: `temu` — 5 assets, all Critical eligible, max $25,000
- Scope: www.temu.com, seller.temu.com, ads.temu.com (new Jul 9 2026 — 0 resolved), com.einnovation.temu (Android), 1641486558 (iOS)
- Stack: Cloudflare, accessible from VPS (no Akamai block)
- seller.temu.com infra: Azure `20.47.113.46`; ads.temu.com: Azure `20.237.25.25`
- seller.temu.com CORS: `/api/server/_stm` reflects any Origin + `ACAC: true` — but only returns `{"server_time":...}` → Low
- ads.temu.com CSP: `default-src 'unsafe-inline' 'unsafe-eval' blob: data: *.temu.com *.kwcdn.com` — no inline execution protection
- `/api/phantom/dm/wl/cg` (seller): returns base64 domain whitelist unauthenticated: `temu.com, .kwcdn.com, temu.to, cncc.bingj.com, cc.bingj.com, work.xfsupport.com`
- ads.temu.com robots.txt: `Disallow: /` (aggressive crawl block, SPA with heavy JS)
- Attack surface: seller portal IDOR via `/api/bg/pawpaw/` endpoints (need valid seller session to test)

### Dossier Medical Partage (DMP) — YesWeHack
- Slug: `dossier-medical-partage-program`
- Stack: Keycloak 26.x + FHIR R4 (IHE MHD/PDSm)
- Infra: `80.78.12.14/15` (backend), `80.78.12.16` (LPS), `80.78.12.8` (frontend)
- 10 in-scope: www.dmp.fr, www.dmp.gouv.fr, api.dmp.gouv.fr, auth.dmp.gouv.fr, wps-cps.dmp.gouv.fr, wps-cps.cv.dmp.gouv.fr, web-mh.dmp.gouv.fr, lps.dmp.gouv.fr, lps2.dmp.gouv.fr, sip2.dmp.gouv.fr
- Extra subdomains (not in scope): wps-psc.dmp.gouv.fr, visiotrace.dmp.gouv.fr, lps-traitement.dmp.gouv.fr
- Blocker: TCP timeout from non-FR IP. Need residential FR proxy.
- Source: github.com/ansforge — keycloak mapper, IG-FHIR-PDSM4DMP-EEDS, IG-fhir-partage-de-documents-de-sante
- Hypothesis: IDOR via DocumentReference.patch/conditionalUpdate, patient reference search without authz, Binary.read without per-patient access control

### Hilton — HackerOne
- Handle: hilton — Tier A max $10,000
- Scope: hilton.com auth (/en/hilton-honors/join/), iOS id635150066, Android com.hilton.android.hhonors
- Rule: prefix "Test-Hackerone" in First+Last name for test accounts
- Blocker: Akamai WAF blocks VPS IP (403 AkamaiNetStorage)
- Finding: hHonorsNumber member ID exposed in confirmation URL — indexed by Wayback, potential enumeration
- Dynatrace endpoint exposed in source: https://bf08412nhq.bf.dynatrace.com/bf
- 23 total assets in scope

### Thuringer Forderportal — YesWeHack
- URL: https://thueringer-foerderportal.eu | IP: 185.57.24.17
- Stack: Liferay Portal 7.4.3.x, OpenID Connect, theme efreportal2127theme
- Auth: /anmeldung — Liferay LoginPortlet + OIDC
- High-value: /api/jsonws (Liferay JSONWS API)
- Blocker: TCP timeout from VPS. Need DE/EU proxy.

---

## SPA / JS Bundle Recon (Modern DEX / Web3 Targets)

When every path returns `200 text/html` (SPA), all direct endpoint probing is useless.
The real backend is discovered by extracting it from the JS bundle.

```python
import re, urllib.request, ssl, json

ctx = ssl.create_default_context()
ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36"

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
        return r.read().decode("utf-8", "replace")

# Step 1: extract JS bundle URLs from index.html
html = get("https://TARGET/")
js_urls = re.findall(r'src=["\']([^"\']*\.js[^"\']*)["\']', html)

# Step 2: download largest bundle and mine it
js = get("https://TARGET" + js_urls[0])  # usually /assets/index-HASH.js

# Extract real backend domain
backend_urls = re.findall(r'https?://[^\s"\'\`\\]*(?:api|backend)[^\s"\'\`\\]{3,80}', js)
ws_urls      = re.findall(r'wss?://[^\s"\'\`\\]{5,100}', js)
api_paths    = re.findall(r'["\`](/(?:api|v\d|graphql|spot)[/\w\-\.?\{\}]*)["\`]', js)
secrets      = re.findall(r'(?:VITE_|REACT_APP_)[A-Z_]+\s*[=:]\s*["\']([^"\']{5,})["\']', js)
contracts    = re.findall(r'0x[a-fA-F0-9]{40}', js)
```

**Key signal:** `app.monday.trade` → SPA on CloudFront; real backend = `mainnet-api.monday.trade` (AWS ELB, weaker WAF). Found via `https://mainnet-api.monday.trade` URL in JS bundle. Backend had CORS vuln that frontend CloudFront CDN did not.

**Privy App ID pattern:** `VITE_*` env vars in JS often contain `privy-app-id` (client-side ID, not secret). Probe `https://auth.privy.io/api/v1/apps/<APP_ID>` with header `privy-app-id: <APP_ID>` — returns full app config including `allowed_domains`. Not a vuln by itself (Privy marks it `data_classification: public`) but reveals OAuth domains + embedded wallet config.

---

## monday.trade — HackenProof

- URL: `https://app.monday.trade/` | Scope: all assets discovered within domain
- Frontend: AWS CloudFront SPA (Nginx + Vite build) — all paths 200 HTML
- Real backend: `https://mainnet-api.monday.trade` (AWS ELB `monday-mainnet-api-*.ap-southeast-1.elb.amazonaws.com`)
- Auth: Privy (`cm9yz1pg801t5l90na2grx9f0`) — wallet + email + Google/Twitter/Discord/GitHub OAuth
- Stack: SynFutures DEX engine, Cloudflare Turnstile on frontend
- WebSocket: `wss://mainnet-api.monday.trade/v4/public/ws`
- Spot API prefix: `/spot/api/v1/`

**CORS CRITICAL FINDING (2026-08-01):**

`mainnet-api.monday.trade` reflects ANY arbitrary `Origin` with `Access-Control-Allow-Credentials: true` on ALL `/spot/api/v1/*` endpoints including sensitive ones:

```bash
curl -si -X OPTIONS 'https://mainnet-api.monday.trade/spot/api/v1/account/assets' \
  -H 'Origin: https://evil.com' \
  -H 'Access-Control-Request-Method: GET' \
  -H 'Access-Control-Request-Headers: Authorization, Content-Type' \
  | grep -i access-control
# → Access-Control-Allow-Origin: https://evil.com
# → Access-Control-Allow-Credentials: true
# → Access-Control-Allow-Methods: GET
```

All 8 sensitive endpoints vulnerable:
`/spot/api/v1/user/info`, `/user/balance`, `/account/assets`, `/account/orders`, `/account/history`, `/order/create`, `/order/cancel`, `/market/snapshot`

PoC HTML: `/root/.hermes/scripts/temp/monday_cors_poc.html`
Evidence PNG: `/root/.hermes/scripts/temp/monday_cors_evidence.png`

**Auth mechanism determines severity — check before submitting:**

monday.trade uses Privy — auth token stored in `localStorage` (`auth-storage` key, encrypted). NOT cookie-based.

```python
# Check via browser automation:
ls = await page.evaluate("""() => {
    const result = {};
    for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key.toLowerCase().includes('token') || key.toLowerCase().includes('auth') ||
            key.toLowerCase().includes('privy') || key.toLowerCase().includes('session')) {
            result[key] = localStorage.getItem(key)?.substring(0, 80);
        }
    }
    return result;
}""")
```

**CORS severity matrix for localStorage-auth apps:**
- `ACAO: reflect + ACAC: true` + cookie auth → **Critical** (browser auto-sends cookies)
- `ACAO: reflect + ACAC: true` + Bearer token in localStorage → **High** (token not auto-sent, but window.opener attack possible)
- `ACAO: *` + `ACAC: true` → browser refuses (spec), but mobile/Electron may not → **Medium** with caveat

**Upgrade path to Critical:** chain with `window.opener.postMessage` — see section below.

**Missing security headers on `mainnet-api.monday.trade`:** no HSTS, no CSP, no X-Frame-Options, no X-Content-Type-Options (AWS ELB exposed directly, no WAF in front).

## window.opener postMessage Attack Vector (CORS chain to Critical)

When a target uses OAuth popup flow (window.open for OAuth), check if the `message` event listener validates `event.origin`. Missing origin check = auth token exfiltration.

### Detection (JS bundle analysis):
```python
js = get("https://TARGET/assets/index-HASH.js")

# Find postMessage sends — look for auth data
post_msg_sends = re.findall(r'\.postMessage\(([^)]{0,200})\)', js)

# Find message listeners — check for origin validation
listeners = re.findall(r'addEventListener\(["\']message["\'][^)]{0,200}\)', js)

# Critical pattern: PRIVY_OAUTH_RESPONSE sent to window.opener
# Vulnerable: listener accepts message without checking event.origin
for match in re.finditer(r'.{0,300}PRIVY_OAUTH_RESPONSE.{0,300}', js):
    print(match.group()[:600])
```

### Vulnerable pattern (monday.trade):
```js
// SENDER (popup window): checks opener.location.origin
window.opener.location.origin !== window.location.origin
    ? window.opener.postMessage({type: "PRIVY_OAUTH_ERROR", ...})
    : window.opener.postMessage({type: "PRIVY_OAUTH_RESPONSE",
        stateCode: ..., authorizationCode: ...})  // ← sends auth code

// RECEIVER (parent window): NO origin check
window.addEventListener("message", function(o) {
    if (o.data.type === "PRIVY_OAUTH_RESPONSE"
        && o.data.stateCode && o.data.authorizationCode) {
        resolve(o.data);  // ← accepts from ANY origin
    }
})
```

The receiver at `Pqe({url, popup, provider})` listens for `PRIVY_OAUTH_RESPONSE` without `event.origin` check — any origin can send a spoofed message to steal the auth code.

### Severity: High (standalone), Critical (chained with CORS or XSS)

Attack scenario: attacker page → `window.open(target)` → inject message → receive authorizationCode → use with CORS API access.

**Privy redirect_uri:** `https://auth.privy.io/oauth/authorize?client_id=APP_ID&redirect_uri=https://evil.com` stays on privy.io page but shows "Something went wrong" — server validates and rejects evil.com. NOT exploitable standalone.

---

## CORS Validation — Definitive Test Pattern

OPTIONS preflight is the authoritative test, not GET response headers:

```python
import urllib.request, ssl, json

def cors_test(base_url, endpoints, evil_origin="https://evil.com"):
    ctx = ssl.create_default_context()
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0"
    for ep in endpoints:
        req = urllib.request.Request(
            base_url + ep,
            headers={
                "User-Agent": ua,
                "Origin": evil_origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization, Content-Type",
            },
            method="OPTIONS"
        )
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
                acao = r.headers.get("Access-Control-Allow-Origin","")
                acac = r.headers.get("Access-Control-Allow-Credentials","")
                vuln = acao == evil_origin and acac.lower() == "true"
                print(f"{'[VULN]' if vuln else '[safe]'} {ep} | ACAO:{acao} ACAC:{acac}")
        except Exception as e:
            print(f"[ERR] {ep}: {e}")
```

**Severity calibration — CORS wildcard vs reflect:**
- `ACAO: *` (wildcard, no `ACAC`) → browser **refuses** to send credentials → **Low/Informative** on auth endpoints. Browsers enforce: `ACAO: *` + `credentials: include` = CORS error.
- `ACAO: reflect evil.com + ACAC: true` → **High/Critical** if sensitive data endpoint, **Low** if only public/benign data
- `ACAO: *` + `ACAC: true` → **spec violation**, browser refuses — but mobile SDKs/Electron/WebView may not → **Medium** with caveat, still reportable
- `ACAO: <hardcoded-legit-domain>` no matter what `Origin` you send → **not exploitable, false positive**. The server isn't reflecting your Origin at all — it's answering with a fixed allowed value (its own known frontend domain) baked into config. Confirm by sending 3+ different bogus Origins (`evil.com`, `null`, subdomain-confusion variants); if ACAO never changes, stop — it's not a CORS bug. (Seen on `account.roon.app/api/6/webaccountinfo`, hardcoded to `https://pagerunner.roonlabs.net`.)

Always check what data the endpoint returns BEFORE claiming severity. Wildcard CORS on a 401 response = near worthless.

---

## Delegation Pitfall for Recon Tasks — DO NOT OVER-DELEGATE

**Strong user preference: direct Python scripts, not delegation.**

`delegate_task` subagents fail ~60% of the time with tool corruption ("Invalid JSON arguments", "Extra data: line 1 column 3", "expected string, got NoneType"). This wastes API tokens and produces zero results.

**Default: write_file + python3** for ALL recon tasks. Never delegate recon unless it's genuinely multi-hour parallelizable work.

```
# WRONG — wastes tokens, usually fails, frustrates user:
delegate_task(goal="probe endpoints of target.com...")

# RIGHT — fast, reliable, no token waste:
write_file("/root/.hermes/scripts/temp/recon.py", "... full script ...")
terminal("python3 /root/.hermes/scripts/temp/recon.py")
```

When subagent returns "tool corruption" / "no results" / "restart session" — that's a failed delegation. Don't retry delegation; just run it directly.

Only delegate when:
1. Task is >2 independent sub-tasks that can truly run in parallel
2. Each sub-task takes >30min of actual work
3. Tool environment confirmed healthy in parent session

For bug bounty recon: **always direct Python**.

## urllib.request Critical Pitfall

**`urlopen(req, ctx, timeout=N)` FAILS — ctx must be a keyword arg:**

```python
# WRONG — crashes with "message_body should be bytes-like, got SSLContext"
with urllib.request.urlopen(req, ctx, timeout=10) as r: ...

# CORRECT — always use keyword argument
with urllib.request.urlopen(req, context=ctx, timeout=10) as r: ...
```

This bites silently: the call raises `TypeError` deep in `http.client`, not at the urlopen line.

## Gzip-Compressed JS Files

Large JS bundles (e.g. TeamViewer, Vite builds) are served gzip-compressed even without `Accept-Encoding: gzip` in the request. Use `Accept-Encoding: identity` to force plain text, then attempt decompression anyway:

```python
import gzip, urllib.request, ssl

ctx = ssl.create_default_context()
req = urllib.request.Request(url, headers={
    "User-Agent": "Mozilla/5.0 ...",
    "Accept-Encoding": "identity"  # request uncompressed
})
with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
    raw = r.read()

# Attempt decompress regardless
try:
    js = gzip.decompress(raw).decode("utf-8", "replace")
except Exception:
    js = raw.decode("utf-8", "replace")
```

Signs you got compressed data: JS starts with `\x1f\x8b` (gzip magic), regex finds zero matches on what should be a big bundle.

## Python Scripting Pitfalls in Recon

**`terminal` vs `execute_code` for multi-line Python:**

`terminal` with inline Python via `-c "..."` breaks on f-strings that contain parentheses — bash `eval` misparses `(`. Use `write_file` + `python3 /path/to/script.py` instead:

```python
# BAD (breaks in terminal -c):
terminal('python3 -c "print(f\"Total: {len(names)}\")"')

# GOOD:
write_file("/root/.hermes/scripts/temp/recon.py", "... full script ...")
terminal("python3 /root/.hermes/scripts/temp/recon.py")
```

`execute_code` avoids this issue entirely for short throwaway scripts, but has a 50-tool-call cap per script. For long recon pipelines, write_file + terminal is more reliable.

**Multi-line Python with urllib.request:** wrap all URL construction in functions — don't use f-strings inline in `terminal()` calls. Parentheses in f-string expressions confuse bash heredoc parsing.

## Proxy Validation Pattern (test proxy vs Akamai)

```bash
# Get proxy list
curl -s "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=http&timeout=5000&country=US&ssl=all&anonymity=elite" | head -20

# Batch test proxies against target
for proxy in "IP:PORT" ...; do
  result=$(curl -s -x "$proxy" -I --max-time 8 \
    -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36" \
    "https://TARGET" 2>/dev/null | head -3)
  status=$(echo "$result" | grep -oP 'HTTP/[\d\.]+ \K\d+' | head -1)
  echo "$proxy -> $status"
done
```

**Pitfall:** Public free proxies are datacenter IPs — Akamai/Cloudflare Enterprise blocks them just like VPS.
For Akamai: only residential proxy (IPRoyal, BrightData) or user's own browser can bypass.

## Superbank (`super-id.net`) — YesWeHack Target Notes

- Program slug: `superbank-public-bug-bounty-program`
- In-scope: `ecosystem-experience.super-id.net` (webview/onboarding), `api.super-id.net`, `superbank.id`, Android + iOS apps
- Stack: Next.js SSR + Istio-envoy (k8s), AWS ELB ap-southeast-3
- Bounty: max $2,000 (reward_grid all 0 in API — actual range set internally)
- Qualifying: XSS, IDOR, SQLi, RCE, Auth bypass, CORS with real impact, Open Redirect
- Non-qualifying: missing headers, info disclosure without PoC, user enumeration, rate limiting, session management
- Routes from `_buildManifest.js`: `/auth/entrypoint`, `/auth/otp`, `/auth/pin/*`, `/cvp/grab/flexi-loan`, `/cvp/ovo/flexi-loan`, `/loan/auth/*`, `/error/auth/*`
- CSP script-src allows `unpkg.com`, `cdn.jsdelivr.net/npm/*`, `cdnjs.cloudflare.com` — CDN XSS bypass possible if XSS sink exists
- Partner webview flow: URL params `partner=GRAB|OVO`, `safeID`, `action` injected from mobile app
- S3 buckets: `idbank-prd-backend-*` — all 403 (no public listing)
- `api.super-id.net/status` → 200 empty body (health check, no data)

## YesWeHack Browser Login (via browser automation)

When using browser tools to log in to YWH:
- Email field ref: `e16`, Password field ref: `e17`, LOG IN button: `e10` (from annotated screenshot — refs change across page loads, use `browser_vision(annotate=True)` to get stable refs)
- After login, navigate to "MY PROGRAMS" (`e5`/`e6` depending on nav state) to see joined programs
- Tab "Bug bounty 61" / "VDP 1" shows all enrolled programs
- Login sequence: navigate → vision(annotate=True) → type email → type password → click LOG IN → wait for nav to reload

**CRITICAL PITFALL — do NOT use `browser_navigate` after login:**
After successful YWH login, calling `browser_navigate(url=...)` to any URL (even YWH itself) immediately triggers bot detection and invalidates the session. The page reverts to unauthenticated state.

Correct pattern — always use `browser_click` on nav links after login:
```
# WRONG — kills session:
browser_navigate("https://yeswehack.com/hunter/programs")

# CORRECT — stay in-session:
browser_click(ref=e6)  # click "MY PROGRAMS" nav link
```
After login, only use `browser_click`, `browser_snapshot`, `browser_scroll`, `browser_console`. Never `browser_navigate`.

**localStorage token extraction pitfall:**
`browser_console` results truncate the JWT value (e.g. `eyJ0eX...XXXX`) — the full token is not accessible via the Hermes console tool. If you need the token for API calls, ask the user to run `localStorage.getItem('access_token')` in their own browser console and paste the result.

## YesWeHack Authentication Flow (API)

To access bounty amounts and scope URLs, login is required:

```python
import urllib.request, json, ssl

ctx = ssl.create_default_context()
payload = json.dumps({"email": "USER@EMAIL", "password": "PASS"}).encode()
req = urllib.request.Request(
    "https://api.yeswehack.com/login",
    data=payload,
    headers={"Content-Type": "application/json", "Accept": "application/json",
             "User-Agent": "Mozilla/5.0"}
)
with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
    resp = json.loads(r.read())
token = resp["token"]  # JWT, save to /tmp/ywh_token.txt

# Use for subsequent calls:
req = urllib.request.Request(url, headers={
    "Authorization": f"Bearer {token}",
    "Accept": "application/json"
})
```

Token key: `resp["token"]` (not `access_token`). TTL field also present.

## YesWeHack — Check Your Own Submitted Reports Status

```bash
# /reports and /hunter/reports both 404 — the working endpoint is /user/reports
# Use nb= not nb_items= (nb_items is ignored, nb is the correct param)
curl -s "https://api.yeswehack.com/user/reports?page=1&nb=50" \
  -H "Authorization: Bearer $TOKEN" -H "User-Agent: Mozilla/5.0"
```

Returns `pagination` + `items[]`, each with `id`, `local_id` (e.g. `#YWH-PGM3597-873`), `title`, `program.title`, `status.workflow_state` (`under_review`, `accepted`, `resolved`, etc.), `cvss.criticity`/`score`, `reward`, `currency`, `created_at`, `changed_at`, `marked_as` (`R`=read by triager, `NA`=not applicable). Reliable way to check triage status across all programs in one call instead of clicking through the web UI per-program.

**Endpoints that all return 404/401 — do NOT use:**
- `/reports`, `/hunter/reports`, `/hunters/me/reports`, `/researcher/reports`, `/me`, `/user/me`, `/api/v1/reports`

**Token handling pitfall:** `execute_code` redacts long strings in stdout (shows `eyJ0eX...XXXX`). To get the real token for subsequent API calls, save to file via `terminal()`:
```bash
curl -s -X POST 'https://api.yeswehack.com/login' \
  -H 'Content-Type: application/json' \
  -d '{"email":"USER","password":"PASS"}' \
  -o /tmp/ywh_token.json
python3 -c "import json; t=json.load(open('/tmp/ywh_token.json'))['token']; open('/tmp/ywh_token.txt','w').write(t)"
TOKEN=$(cat /tmp/ywh_token.txt)
```
Token key is `token` (not `access_token`). TTL: 14400 seconds (4 hours).

**Browser session pitfall:** YWH login via browser works but cookies do NOT persist across `browser_navigate()` calls. Any call to `browser_navigate` after login resets the session. Use the API approach above for status checks — faster and more reliable.

**`eligible_for_bounty` field unreliable:** Even with auth, `scopes[].eligible_for_bounty` is always `False` on many programs. The bounty grid uses a different structure:

```python
d = get_program_with_auth(slug, token)
# bounty grid per scope tier
g = d.get("reward_grid_low") or {}
# g = {"bounty_low": 200, "bounty_medium": 1000, "bounty_high": 4000, "bounty_critical": 10000}
# NOT reward_grid_low.max_price — that's always 0

# Use stats for rough signal when unauthenticated:
stats = d.get("stats") or {}
avg = stats.get("average_reward")  # populated without auth
```

## YesWeHack API — Public Scope Endpoint

```bash
# Get full scope without login
curl -s "https://api.yeswehack.com/programs/<slug>" -H "Accept: application/json"
# Returns: title, status, scopes[], out_of_scope[], bounty_reward_range
# Scope fields: scope (URL/domain), scope_type (web-application|api|mobile), eligible_for_bounty
```

No auth required for public programs. More reliable than scraping the web UI.

**PITFALL — bounty amounts and scope URLs hidden without auth:**
`reward_grid_medium/high/critical.max_price` always returns `0` for unauthenticated API calls even on public bounty programs. `scopes[].scope` (the actual domain/URL) also comes back empty. Must be logged in to see actual amounts and scope URLs.

Workaround: check `stats.average_reward` and `stats.max_reward` — these ARE populated without auth and give a rough bounty signal.

```python
stats = d.get("stats") or {}
print("avg_reward:", stats.get("average_reward"))  # populated without auth
print("max_reward:", stats.get("max_reward"))       # populated without auth
# reward_grid_* max_price = 0 without auth — ignore
```

**PITFALL — Decathlon program = no bounty (VDP-like):**
All scopes have `eligible_for_bounty: False` despite `bounty: True` flag on program level.
`www.decathlon.com` also resolves to Shopify (`shops.myshopify.com`) — not Decathlon's own infra.
Skip Decathlon unless specifically looking for Shopify-based bugs.

## Platform Cross-Check: monday.trade / SynFutures

`app.monday.trade` + `synfutures.com` — only on **HackenProof** (`/programs/synfutures-dapp`).
Not present on YesWeHack, Immunefi, HackerOne, or Intigriti (confirmed 2026-08-01).

SynFutures bug bounty page: `https://docs.synfutures.com/security/bug-bounty`
Points to: `https://hackenproof.com/programs/synfutures-dapp`

## HackerOne Scope — Browser Interaction Pattern

Navigate to `https://hackerone.com/<handle>/policy_scopes` then:
1. Click `[ref=e12]` "Scope and Rewards" tab
2. Expand each tier button (Tier A/B/C/Excluded) — they start `[expanded=false]`
3. Full snapshot after all expanded

Note: HackerOne GraphQL API returns empty for unauthenticated scope queries. Browser is required.

## HackerOne Login — 2FA Session Reset Pitfall

The `Program guidelines` tab (rules, rewards summary, exclusions) is public — no login needed. Login is only required for `Scope` (actual asset list) and submitting reports.

**Confirmed failure mode (2026-08-05, Agoda program):** after submitting email+password and reaching the "Two-factor authentication" screen, if the page snapshot is taken again before typing the code (or any delay/re-navigation happens), the session can silently reset — `browser_snapshot` returns `(empty page)` and the ref used for the authenticator textbox becomes `Unknown ref`. Re-navigating to the program URL shows the "Log in" button again, i.e. fully logged out, not just back at the 2FA step.

**Fix:** don't pause between password submit and typing the 2FA code — get the code from the user first if possible, or immediately re-snapshot and type without intervening navigation. If the ref goes stale / page goes blank, don't try to recover the same 2FA attempt — restart the whole login flow (navigate to program URL → click Log in → email → password → wait for fresh 2FA prompt → ask user for a **new** code, since the old one will have expired anyway by the time you retype it).

**Confirmed reproducible (2026-08-05, Agoda, 2 back-to-back failures):** even asking the user for the code and getting a fresh reply doesn't reliably save the session, because in a chat-mediated flow the round-trip (agent asks → user reads → user opens authenticator → types digits → sends) routinely eats 20-30+ seconds — long enough for HackerOne's own 2FA session window to expire by the time you act on the reply. Symptom sequence: password submit succeeds → 2FA screen renders → (wait for user's out-of-band reply) → snapshot on the next turn already shows `(empty page)` or `Unknown ref` for the code textbox → re-navigating shows "Log in" again (fully logged out, not just back at 2FA).

**Practical mitigation:** ask the user to have the authenticator app open and ready to read off a code *the moment* you say you're at the 2FA screen, rather than asking cold and waiting. If a second attempt also resets, don't keep retrying blind — tell the user directly it's a session-timing issue on HackerOne's end (2FA window is short) and ask whether they want to try once more or abandon login for this task; each retry costs a full email+password resubmission cycle so don't loop silently more than twice.

**Confirmed a 3rd time (2026-08-05, Agoda, same session):** even after the user supplied 3 different fresh codes in a row (each requested after explicit "butuh kode baru" prompts), every single attempt still hit the same blank-page/Unknown-ref reset. This confirms the failure is NOT about stale/reused codes — it's structural: the chat round-trip latency alone (agent asks → user reads message → opens authenticator → types → sends) exceeds HackerOne's 2FA session window essentially every time in a mid-length conversation. **Stop after 2 failed attempts, do not try a 3rd blind** — pivot to unauthenticated recon (program guidelines are public) and tell the user login via chat-mediated 2FA is unreliable for this platform rather than repeating the ask.

## Agoda — HackerOne Target Notes (public tier data, no login)

- Handle: `agoda-public` (also has a private `agoda` program)
- Managed by HackerOne, Collaboration Enabled, Includes Retesting, fully compliant with Platform Standards, Top Response Efficiency (>90%)
- Rewards (90-day avg): Low $150, Medium $500–700 (avg $576), High $2,000–3,000, Critical $5,000–6,000
- Avg time to triage: 2 days 9 hours. Avg time to bounty: 2 weeks 1 hour. Avg time submission→bounty: 2 weeks 2 days
- Disclosure NOT allowed for any report (no public disclosure permitted outside HackerOne)
- Prohibited: compromising accounts/data, storing sensitive data locally, social engineering, off-platform comms with staff, automated scanning/scanners, high traffic volume
- Test property rule (ycs.agoda.com): location must be `Test City, Comoros` (irreversible field), name must include `Test` and `Do not book`, description must include `For security testing`
- Traffic identifier convention: `hackerone-<username>` in a request param or `User-Agent` header
- Scope (asset list, bounty amounts per asset) requires login — see 2FA pitfall above before attempting.

## HackenProof Platform Notes

- Public programs: hackenproof.com/programs (blocked by Cloudflare Turnstile from VPS — need browser with residential IP to view)
- Program scope often minimal: just a URL with note "all found within this domain is in scope"
- KYC required before withdrawal (not before submitting reports)
- Reputation = valid report submissions; High/Critical reports give most points
- Tier system: Bronze → Silver → Gold → Top (higher = private program access)

---

## Next.js SSR `__NEXT_DATA__` Information Disclosure

Next.js apps expose `runtimeConfig` in the HTML via `<script id="__NEXT_DATA__">`. This is a server-side rendered JSON blob visible to any unauthenticated visitor. Check every page response for sensitive values.

```python
import re, json, urllib.request, ssl

ctx = ssl.create_default_context()
def get_nextdata(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Linux; Android 13) Chrome/125.0"})
    with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
        body = r.read().decode("utf-8", "replace")
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', body, re.DOTALL)
    if not match:
        return {}
    return json.loads(match.group(1))

nd = get_nextdata("https://TARGET/some/page")
rc = nd.get("props", {}).get("runtimeConfig", {})
props = nd.get("props", {})

# Look for:
print("runtimeConfig:", json.dumps(rc, indent=2)[:2000])
print("props keys:", list(props.keys()))
```

**High-value keys to check in `runtimeConfig`:**
- `kafkaBrokers` — internal Kafka cluster hostnames + ports (production infra)
- `kafkaTopics*` — internal topic names
- `*Flag` / `*Version` — feature flags revealing unreleased flows
- `hvAppId`, `insiderSrc` — third-party SDK app IDs
- `cdn` — S3 bucket URL (check for public listing)

**Superbank (`ecosystem-experience.super-id.net`) — 2026-08-01:**
`runtimeConfig.kafkaBrokers` exposed 6 production Kafka broker hostnames:
`b-1..b-6.idbankprdbackendm.2cahrm.c3.kafka.ap-southeast-3.amazonaws.com:9094`
Plus `kafkaTopicsJanus: prd-janus-tracker`.
Stack: Next.js + Istio-envoy (Kubernetes), AWS ELB ap-southeast-3.
Note: `runtimeConfig` only appears on SSR pages (e.g. `/id/error/app/close`), not static paths.

**Severity:** Medium — internal infrastructure names without PoC exploitation = "Disclosure of information". Check if program considers this qualifying (Superbank does for meaningful infra exposure).

**Also check `props` for:**
```js
// These appear in Superbank — webview context injection vectors:
partner: "GRAB"   // or "OVO" — changes which partner SDK loads
safeID: ""        // injected by mobile app, identifies session
action: ""        // flow control
trackerToken: ""  // AppsFlyer tracker token
```

If `partner` param is reflected server-side without validation, test for SSRF or logic bypass by sending `partner=ATTACKER_CONTROLLED`.

---

## HackerOne Self-Hosted Program Recon (hackerone.com)

Target: Ruby + GraphQL backend. All recon done via POST `/graphql`.

### GraphQL public queries (no auth):
```python
import urllib.request, json, ssl
ctx = ssl.create_default_context()
ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0"

def gql(query, variables=None):
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        "https://hackerone.com/graphql",
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": ua}
    )
    with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
        return json.loads(r.read())

# Enumerate users (public profiles) — no auth
gql("{ users(first: 10) { edges { node { id username reputation } } } }")

# Public disclosed reports
gql("{ reports(first: 10) { edges { node { id title state severity { rating } disclosed_at } } } }")

# Programs list
gql("{ teams(first: 5) { edges { node { handle name } } } }")
```

### Key observations (2026-08-01):
- GraphQL introspection enabled but returns 0 types (filtered) — not truly open
- `users` + `reports` + `teams` queries return PUBLIC data only — all reports are disclosed
- Private report IDOR: `node(id: $gid)` for undisclosed reports returns `null` — auth required
- Email/phone/address fields on User: blank for unauthenticated
- Batch queries rejected: `{"errors":[{"message":"Unexpected end of document"}]}`
- Access control solid: no IDOR, no private data leak via GraphQL unauthenticated

### api.hackerone.com:
- All endpoints: 401 without auth (proper)
- `TRACE` → 405 (disabled)
- `OPTIONS` → 401 (CORS not misconfigured)
- `/v1/programs` → 502 (Cloudflare backend error — minor, not exploitable)
- Conclusion: very mature auth enforcement, not a good unauthenticated target

### HackerOne program scope (security handle):
- 33 assets including: hackerone.com (main app), api.hackerone.com, *.vpn.hackerone.net, www.hackerone.com (Drupal), reviewer.pullrequest.com, app.pullrequest.com, S3 bucket
- All Critical eligible
- hackerone.com: 657 resolved (65%) — high competition, well-audited
- VPN scope: OpenVPN, interested in client isolation bypass

---

## Camofox Browser — Cloudflare Bypass for Recon

**Install once, use for all CF-protected targets:**

```bash
git clone https://github.com/jo-inc/camofox-browser.git ~/tools/camofox-browser
cd ~/tools/camofox-browser && npm install
# Start server (background):
node server.js &
# Server runs at http://localhost:9377
```

**REST API (use from Python/curl):**

```python
import urllib.request, json

def camofox_open(url, user="h1", sess="s1"):
    """Returns (tab_id, final_url)"""
    payload = json.dumps({"userId": user, "sessionKey": sess, "url": url}).encode()
    req = urllib.request.Request("http://localhost:9377/tabs",
        data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.loads(r.read())
    return d["tabId"], d.get("url", "")

def camofox_snap(tab_id, user="h1", wait=3):
    """Returns (final_url, snapshot_text)"""
    import time; time.sleep(wait)
    req = urllib.request.Request(f"http://localhost:9377/tabs/{tab_id}/snapshot?userId={user}")
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
    return d.get("url", ""), d.get("snapshot", "")

def camofox_click(tab_id, ref, user="h1"):
    payload = json.dumps({"userId": user, "ref": ref}).encode()
    req = urllib.request.Request(f"http://localhost:9377/tabs/{tab_id}/click",
        data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

def camofox_type(tab_id, ref, text, user="h1"):
    payload = json.dumps({"userId": user, "ref": ref, "text": text}).encode()
    req = urllib.request.Request(f"http://localhost:9377/tabs/{tab_id}/type",
        data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())
```

**Pitfalls:**
- `npm start` pipes to `head -5` and truncates log — use `node server.js` directly
- Snapshots may be empty if page hasn't fully loaded — add `time.sleep(3-5)` before snap
- `snapshot` returns accessibility tree text, not HTML — enough for link extraction + interaction
- Camofox passes Cloudflare Turnstile. Browser engine fingerprints as Firefox (anti-detect)
- `final_url` after `POST /tabs` shows where CF redirected to — useful for spotting 307/302 chains
- **Camofox does NOT bypass hCaptcha interactive challenges** — site registration/login forms with hCaptcha checkbox fail with "Verification failed! Please try again to confirm you're not a robot." Only non-interactive CF Turnstile (invisible challenge) is bypassed. Workaround: use a real browser with manual CAPTCHA completion, or pre-existing account session cookies.
- **Screenshot endpoint returns raw PNG binary** — `GET /tabs/<id>/screenshot?userId=x` returns binary PNG, not JSON. Use `subprocess.run(cmd, capture_output=True)` WITHOUT `text=True`, then check `r.stdout[:4] == b'\x89PNG'`. Using `text=True` will UnicodeDecodeError on the binary response. Some server versions wrap in `{"screenshot": "<base64>"}` JSON — try PNG magic bytes first, fall back to base64 decode.
  ```python
  r = subprocess.run(["curl","-s",f"http://localhost:9377/tabs/{tab_id}/screenshot?userId={user}"], capture_output=True)
  if r.stdout[:4] == b'\\x89PNG':
      open(path, "wb").write(r.stdout)  # raw PNG
  else:
      import base64, json
      d = json.loads(r.stdout)
      open(path, "wb").write(base64.b64decode(d.get("screenshot","") or d.get("data","")))
  ```
- **iframe-heavy pages (e.g. temp-mail.org) cause snapshot timeout** — `buildRefs: total timeout exceeded` after 12s. Retry snapshot once after the timeout clears; second call usually succeeds.
- **Use `execute_code` with subprocess.run for camofox calls** — avoids terminal bash syntax issues with JSON payloads containing special chars.

---

## TeamViewer — YesWeHack Target Notes

- Program slug: `teamviewer-bounty-program`
- Bounty: Low=$200, Med=$1,000, High=$4,000, Crit=$10,000
- Scope: `web.teamviewer.com`, `account.teamviewer.com`, `login.teamviewer.com`, TV desktop app, Android + iOS apps
- CDN: Cloudflare — accessible from VPS
- 871 total reports, 8 new per day (active program)

**Stack (from JS bundle `index.D9eF9ow1.js`, 20MB decompressed):**
- `webapi.teamviewer.com/api/v1/` — public REST API
- Version endpoint (no auth): `GET /api/v1/version` → `{"ReleaseInfo":"(HEAD(Olaf)","VersionInfo":"15.80.2.0"}` — internal codename `Olaf` exposed
- Ping endpoint (no auth): `GET /api/v1/ping` → `{"token_valid":false}`
- All other `webapi` endpoints: 401 without auth (properly protected)
- `webapi.teamviewer.com` CORS: `ACAO: *` (wildcard, no `ACAC: true`) on 401 responses — Low severity

**Staging/RC environments from JS bundle** (all TCP unreachable from VPS, internal only):
`account-playground1`, `account-playground2`, `account-staging`, `account-trunk`, `account-rc0/1/2.teamviewer.com`

**`account.teamviewer.com` internal API paths** (return 200 "BadRequest" without proper payload):
- `/account-token` — token issuance endpoint
- `/account-token/refresh` — token refresh
- `/accountstate` — account state check (GET with `?email=` param)
- `/api/commonasset/v1/labels` — label management
- `/api/ticketing/v1` — helpdesk/ticketing (internal)
- `/api/knowledgebase/v0` — KB API (internal)
- `/api/scaleorchestrator/v0` — orchestration service

**Key API paths from JS** (probe with authenticated session):
`/account-migration-eligibility`, `/api/commonasset/v1/labels/bulk/fetch`, `/api/knowledgebase/v0/article/bulk/delete`, `/api/ticketing/v1/email/send`

**`web.teamviewer.com` CSP:** strict, no external CDN bypass vectors. `script-src 'self'` + specific TeamViewer CDN origins only.

**CORS finding:** `webapi.teamviewer.com/api/v1/*` returns `ACAO: *` (wildcard) on 401 responses. NOT `ACAO: reflect + ACAC: true`. Wildcard on 401-only responses = Low/Informative (browser still enforces credentials restriction with `*`).

**Highest-value unauthenticated finding so far:** version + internal codename leak at `/api/v1/version` — Low/Informative, probably not bounty-eligible.

**Next steps requiring account:** probe `/account-token` POST with grant_type flows, test IDOR on `/api/commonasset/v1/labels` with authenticated user.

**OAuth `redirect_uri` path traversal (Medium — VALIDATED via state decode 2026-08-01):**

`account.teamviewer.com` validates `redirect_uri` domain but NOT path normalization:

```bash
# Rejected (BadRequest):
curl -s 'https://account.teamviewer.com/?redirect_uri=https://evil.com' | grep -c BadRequest  # 1

# Accepted (login page renders normally!):
curl -s 'https://account.teamviewer.com/?redirect_uri=https://web.teamviewer.com/../../evil.com' | grep -c "Sign in"  # 1
```

The login page accepts `redirect_uri` containing `/../` path traversal that resolves to `evil.com`. Server validates `startsWith("https://web.teamviewer.com")` but doesn't normalize the path before redirect. Confirmed with camofox: page renders login form, `redirect_uri` is preserved in all links (Create account, Sign in) throughout the flow.

**Impact:** After successful login, OAuth token may be forwarded to `evil.com` instead of `web.teamviewer.com`.

**VALIDATED:** `state` parameter decode after entering email confirms `"RedirectUri":"https://web.teamviewer.com/../../../evil.com"` is embedded in Google OAuth callback URL. Server does NOT normalize the path before embedding in state. Post-login destination unconfirmed (hCaptcha blocks test account login from VPS — needs manual CAPTCHA or real account session).

**Exact validated payloads:**
```
REJECTED:  https://web.teamviewer.com/../../evil.com          (HTTP 403)
ACCEPTED:  https://web.teamviewer.com/../../../evil.com       (HTTP 200, state confirmed)
ACCEPTED:  https://web.teamviewer.com/authenticate/../../evil.com (HTTP 200)
```

**Pattern applies broadly:** Any OAuth server that validates the redirect_uri domain prefix but not the canonicalized path. Try `https://ALLOWED_DOMAIN.com/../../../evil.com` and `https://ALLOWED_DOMAIN.com/%2F..%2F..%2Fevil.com` (encoded variant). See `oauth-oidc-audit` skill Phase 3 for full redirect_uri bypass battery.

---

## GitHub Source Recon for Web3/dApp Targets

When target is a dApp/NFT project, search GitHub org repos before probing live endpoints — source often has contract addresses, API base URLs, and auth flows that the minified JS doesn't reveal clearly.

```python
import urllib.request, json, ssl, re

ctx = ssl.create_default_context()
ua = "Mozilla/5.0 Chrome/125.0"

def ghget(url):
    req = urllib.request.Request(url, headers={"User-Agent": ua,
          "Accept": "application/vnd.github.v3+json"})
    with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
        return json.loads(r.read())

# 1. Find org repos
repos = ghget("https://api.github.com/orgs/TARGET_ORG/repos?per_page=50&sort=updated")
for r in repos: print(r['name'], r.get('language',''), r['updated_at'][:10])

# 2. Get file tree
tree = ghget("https://api.github.com/repos/ORG/REPO/git/trees/main?recursive=1")
for f in tree['tree']:
    p = f['path']
    if any(k in p.lower() for k in ['contract','config','constant','abi','deploy','.env']):
        print(p)

# 3. Read raw file
import urllib.request
s, b = urllib.request.urlopen(f"https://raw.githubusercontent.com/ORG/REPO/main/{path}",
                               context=ctx, timeout=10).read().decode(), ...
```

**High-value files to look for:**
- `src/constants/contract.ts` / `src/config/contract.ts` — hardcoded contract addresses + ABI
- `src/config/wagmi.ts` — chain IDs, projectId, RPC URLs
- `.env.example` — env var names reveal what keys exist (SUPABASE, XELLAR, GRAPHQL_URL, contract addrs)
- `src/lib/nft.ts` / `src/hooks/useMintTransaction.ts` — server-side auth gating logic
- `src/actions/*.ts` — server actions reveal auth check order + bypass potential

**Encoteki finding (2026-08-01):** `encoteki/encoteki-fe-claim` → `src/lib/nft.ts` hardcodes `baseSepolia` + `arbitrumSepolia` in `SUPPORTED_CHAINS` map. Production server-side NFT ownership gating (`getDeal` action) queries these testnet chains. Attacker mints testnet NFT (0.0001 ETH faucet) → `hasNftOwnership()` returns `true` → full access to partner deal coupon codes. **Pattern to look for:** `import { baseSepolia, arbitrumSepolia } from 'viem/chains'` in any file used for production auth gating.

---

## Blockscout Multi-Chain Contract Discovery

When contract addresses unknown, search by contract name across all chains:

```python
import urllib.request, json, ssl

ctx = ssl.create_default_context()
ua = "Mozilla/5.0 Chrome/125.0"

EXPLORERS = {
    "Base mainnet":   "https://base.blockscout.com",
    "Arbitrum":       "https://arbitrum.blockscout.com",
    "Lisk":           "https://blockscout.lisk.com",
    "Manta":          "https://pacific-explorer.manta.network",
    "Base Sepolia":   "https://base-sepolia.blockscout.com",
    "Arb Sepolia":    "https://sepolia.arbiscan.io",  # no blockscout, use arbiscan
}

def search_contract(name_query):
    for chain, api in EXPLORERS.items():
        url = f"{api}/api/v2/smart-contracts?q={name_query}"
        req = urllib.request.Request(url, headers={"User-Agent": ua})
        try:
            with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=8) as r:
                items = json.loads(r.read()).get("items", [])
                for item in items:
                    addr = item.get("address",{}).get("hash","")
                    name = item.get("name","") or "(unverified)"
                    print(f"  [{chain}] {addr} — {name}")
        except:
            pass

search_contract("EncotekiProject")  # replace with actual name

# Get contract ABI + state
def contract_info(api_base, addr):
    req = urllib.request.Request(f"{api_base}/api/v2/smart-contracts/{addr}",
                                  headers={"User-Agent": ua})
    with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=10) as r:
        d = json.loads(r.read())
    fns = [x["name"] for x in d.get("abi",[]) if x.get("type")=="function"]
    token = d.get("token",{})
    print(f"Name: {d.get('name')} | Token: {token.get('name')} ({token.get('symbol')}) supply={token.get('total_supply')}")
    print(f"Functions: {fns[:15]}")
```

**Basescan API V1 deprecated** → use Blockscout API v2 instead. Free Basescan API returns `"You are using a deprecated V1 endpoint"` and `"Free API access is not supported for this chain"` for many chains.

**Read contract state without API key:**
```python
from web3 import Web3
w3 = Web3(Web3.HTTPProvider("https://mainnet.base.org"))  # or sepolia.base.org
result = w3.eth.call({"to": "0xCONTRACT", "data": "0x18160ddd"}, "latest")  # totalSupply()
# decode: int(result.hex(), 16)
```

---

## Web3/eth-account Python Setup

All major faucets block VPS IPs — use venv to avoid system Python conflicts:

```bash
python3 -m venv /tmp/web3env
/tmp/web3env/bin/pip install web3 eth-account -q
```

Then use `/tmp/web3env/bin/python3` for all Web3 scripts. `pip install --break-system-packages` is unreliable (debian package conflicts with typing_extensions).

Basic wallet + contract interaction pattern:
```python
from eth_account import Account
from web3 import Web3

w3 = Web3(Web3.HTTPProvider("https://sepolia.base.org"))
acct = Account.from_key("0xPRIVATE_KEY")
print(f"Address: {acct.address} | Balance: {w3.eth.get_balance(acct.address)/1e18:.6f} ETH")

CONTRACT = Web3.to_checksum_address("0xCONTRACT_ADDR")
ABI = [{"inputs":[],"name":"mint","outputs":[],"stateMutability":"payable","type":"function"},
       {"inputs":[],"name":"cost","outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function"}]
c = w3.eth.contract(address=CONTRACT, abi=ABI)
cost = c.functions.cost().call()

# Send transaction
tx = c.functions.mint().build_transaction({
    "from": acct.address, "value": cost,
    "gas": 200000, "gasPrice": w3.eth.gas_price,
    "nonce": w3.eth.get_transaction_count(acct.address)
})
signed = acct.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
print(f"Tx: {tx_hash.hex()} | Status: {receipt['status']}")
```

---

## Vercel Security Checkpoint (VPS IP Block)

Vercel-hosted Next.js apps show "Vercel Security Checkpoint" page (Astro-cid security page) from VPS IPs. All paths return HTTP 403 with HTML checkpoint page, not the actual app content.

**Symptoms:**
- Response body: `<title>Vercel Security Checkpoint</title>`
- `<link rel="stylesheet" ...data-astro-cid-nbv56vs3>`
- Only link visible: `"Website owner? Click here to fix"`
- camofox also shows this page — it's IP-based, not UA-based

**Impact on recon:**
- `/graphql`, `/admin`, `/api/*` paths all 403 even if they exist
- Path probe returns 200 for SPA routes but 403 for actual API endpoints
- Camofox bypasses Cloudflare Turnstile but NOT Vercel's IP-based block

**Workaround:**
- Use residential proxy or user's own browser for these endpoints
- GraphQL introspection must be done from non-VPS IP
- Focus on GitHub source code analysis + public API endpoints that don't hit Vercel directly

---

## SwissTransfer Email Verification Flow

SwissTransfer (`www.swisstransfer.com`) requires email verification before creating transfers. The session is established via cookie, NOT a field in the transfer request.

**Correct flow:**
```python
import urllib.request, json, ssl

ctx = ssl.create_default_context()
h = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/125.0"}
BASE = "https://www.swisstransfer.com"

# Step 1: Request OTP
r1 = urllib.request.urlopen(urllib.request.Request(f"{BASE}/api/1/email-validations",
    data=json.dumps({"email":"user@example.com"}).encode(), headers=h, method="POST"), context=ctx)
d1 = json.loads(r1.read())
uuid = d1["data"]["id"]  # save this

# Step 2: User receives OTP in email (6-char code like "EX882B")
# Step 3: Confirm — captures ST_SESSION cookie
import http.cookiejar
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
r2 = opener.open(urllib.request.Request(f"{BASE}/api/1/email-validations/{uuid}/confirm",
    data=json.dumps({"token": "OTP_CODE"}).encode(), headers=h, method="POST"), timeout=10)
# ST_SESSION cookie now in jar

# Step 4: Create transfer WITH cookies (not author_email_token field!)
r3 = opener.open(urllib.request.Request(f"{BASE}/api/1/transfers",
    data=json.dumps({"email":"user@example.com","expires_in_days":7,"language":"en",
                     "max_download":250,"message":"","password":"",
                     "files":[{"path":"test.txt","size":12,"mime_type":"text/plain"}]
                    }).encode(), headers=h, method="POST"), timeout=10)
```

**Pitfalls:**
- `author_email_token` field in body does NOT work — session is cookie-based (`ST_SESSION`)
- OTP expires in ~2-3 minutes (`token_expires_at` Unix timestamp in response)
- Rate limit: 50 confirmations per session, then `email_validation_rate_limit_error` — wait ~5 min
- `confirm` endpoint requires field name `"token"` (not `"code"` or `"otp"`)
- Transfer API field names use `snake_case` (`expires_in_days`, `max_download`, `mime_type`)

---

## Self-Hosted Bug Bounty Programs (non-platform)

Some small/indie projects host their own BB program via Google Docs or Notion — no HackerOne/YWH platform. Key differences:

- **Scope doc**: usually a Google Doc or Notion page with scope, rules, rewards
- **Submit link**: typically a Google Form or bit.ly shortlink (e.g. `https://bit.ly/EncotekiBBReport`)
- **Reward model**: often pool-based (fixed total, split by severity weight at program end)
- **PoC standard**: usually accepts static/code analysis write-ups per program rules, doesn't always require live exploitation
- **No dedup system**: first-come-first-served, no platform-enforced dedup

```bash
# Extract plain text from Google Docs (no login needed for public docs)
DOC_ID="1_0EuBJwDf896J6Fa_siUGtL5fsvK7jKxnznVe1BmeII"
curl -sL "https://docs.google.com/document/d/$DOC_ID/export?format=txt" | head -200
```

**Google Form submission field mapping (self-hosted programs):**
Standard fields and what to fill for common bug types:

| Field | Authentication Bypass | Notes |
|---|---|---|
| Vulnerability Category | Authentication Bypass | Not "Business Logic" — pick the closest technical class |
| Impact Severity | 4 (out of 5) | Complete auth bypass without data exfil = 4, not 5. Critical (5) = funds drained / PII mass exposed |
| Findings Description | Full English write-up | Root cause + affected file + why it happens. User wants COMPREHENSIVE, not short |
| Steps to Reproduce | Numbered, exact | Start from clean state. Every step reproducible without guessing |
| PoC Link | Blockscout TX + GitHub source | Multiple links OK if form allows; otherwise use primary Blockscout TX link |
| User Data Accessed | No | For testnet/source-code-only PoC: always No |
| Data Accessed Explanation | (leave blank) | Only fill if answered Yes above |
| Chained Vuln | No, standalone | Only "Yes" if bug requires another bug to be exploitable |

**Style rule:** Report fields should be in **English**, full detail. User rejected short descriptions — write everything: root cause, code snippet, affected files, full PoC steps, on-chain evidence.

**Pool-based reward math example (Encoteki):**
- Total: $300 IDRX on Base Network
- Critical=$75, High=$45, Medium=$30, Low=$15
- If total calculated > $300 → pro-rata scale down
- If total < $300 → remainder retained (not distributed)
- Value per point = $15 regardless of pool size

---

## Ethereum Sepolia → Base Sepolia Bridge (for Testnet PoC)

When you need Base Sepolia ETH for a testnet PoC mint but only have ETH Sepolia:

```python
from web3 import Web3
from eth_account import Account

pk = "0xPRIVATE_KEY"
acct = Account.from_key(pk)
w3 = Web3(Web3.HTTPProvider("https://ethereum-sepolia-rpc.publicnode.com"))

# OptimismPortal on Ethereum Sepolia (Base's L1 bridge contract)
PORTAL = Web3.to_checksum_address("0x49f53e41452C74589E85cA1677426Ba426459e85")
ABI = [{"inputs":[
    {"internalType":"address","name":"_to","type":"address"},
    {"internalType":"uint256","name":"_value","type":"uint256"},
    {"internalType":"uint64","name":"_gasLimit","type":"uint64"},
    {"internalType":"bool","name":"_isCreation","type":"bool"},
    {"internalType":"bytes","name":"_data","type":"bytes"}],
    "name":"depositTransaction","outputs":[],"stateMutability":"payable","type":"function"}]

portal = w3.eth.contract(address=PORTAL, abi=ABI)
amount = Web3.to_wei(0.005, "ether")  # bridge 0.005 ETH

tx = portal.functions.depositTransaction(
    acct.address,   # same address on L2
    amount, 100000, False, b""
).build_transaction({
    "from": acct.address, "value": amount,
    "gas": 200000, "gasPrice": w3.eth.gas_price,
    "nonce": w3.eth.get_transaction_count(acct.address),
    "chainId": 11155111,  # Ethereum Sepolia
})
signed = acct.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
print(f"Bridge TX: {tx_hash.hex()} | Status: {receipt.status}")
# ETH arrives on Base Sepolia in ~1-2 minutes
```

**Pitfall:** `L1StandardBridge.depositETH()` at `0xfd0Bf71F60660E2f608ed56e1659C450eB113120` fails with status=0 (wrong ABI or outdated address). Use `OptimismPortal.depositTransaction()` at `0x49f53e41452C74589E85cA1677426Ba426459e85` instead — confirmed working 2026-08-01.

---

## ERC721 walletOfOwner Pattern (get token IDs by address)

`balanceOf(address)` returns count only. To get actual token IDs:

```python
ABI = [
    {"inputs":[{"type":"address"}],"name":"balanceOf","outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"type":"address"}],"name":"walletOfOwner","outputs":[{"type":"uint256[]"}],"stateMutability":"view","type":"function"},
]
c = w3.eth.contract(address=CONTRACT, abi=ABI)

bal = c.functions.balanceOf(ADDR).call()        # count
tokens = c.functions.walletOfOwner(ADDR).call() # [tokenId1, tokenId2, ...]
print(f"balanceOf={bal}, tokenIds={tokens}")
```

**ERC1155 vs ERC721:** `balanceOf(address)` (1 arg) = ERC721. `balanceOf(address, uint256)` (2 args) = ERC1155. If you get ABI mismatch errors on balanceOf, check which standard the contract implements — look at ABI file or Blockscout `/api/v2/smart-contracts/{addr}`.

---

## Alasco GmbH — YesWeHack Target Notes

- Slug: `alasco-gmbh-bug-bounty-program`
- Bounty: High, 4 scopes, €50–€1,000, 161 reports, response < 1 day
- Stack: Cloudflare + Django (`{"detail":"Not authenticated"}` on 401), Datadog RUM, Zendesk, Pendo (EU), Sentry

**Scopes:**
- `app.alasco.de` — Web application, Asset=HIGH (CF 302 → `/auth/login/`)
- `api.alasco.de` — API, Asset=HIGH (CF 401, JSON errors)
- `*.alasco.de` — Other, Asset=MEDIUM
- `*.alasco.rocks` — Other, Asset=LOW

**Headers from `app.alasco.de`:**
- `x-alasco-release: master-175efa62e68fdeaa5120905f74ccb40eadf3f02b` — full commit SHA exposed
- CSP `report-uri` → Datadog: `https://csp-report.browser-intake-datadoghq.eu/api/v2/logs?dd-REDACTED_********&...` — Datadog API key exposed in CSP header (public key, not secret, but reveals infra detail)
- `reporting-endpoints: csp-endpoint` — same URL

**`api.alasco.de` — all endpoints 401 from VPS (no unauth surface):**
- `/swagger.json`, `/openapi.json`, `/redoc`, `/docs`, `/schema`, `/api/schema` — all 401 JSON
- API docs protected behind auth — cannot enumerate endpoints without account

**`branding.alasco.de` — S3 bucket on AWS (via Cloudflare):**
- Returns 403 + `x-amz-request-id` + `x-amz-id-2` headers → bucket exists, private
- CF-Ray from WAW (Warsaw) datacenter
- Potential: check bucket name via DNS CNAME → `branding.alasco.de.s3.amazonaws.com` — if CNAME resolves, try listing directly

**`support.alasco.de`** → Zendesk (`support.alasco.de/hc`)
**`files.alasco.de`** → 404, Cloudflare (likely S3 private file storage)

**Blocker:** All meaningful API surface requires account. B2B SaaS — create free trial/demo account at `app.alasco.de` to test IDOR on project/contract endpoints.

---

## Infomaniak — YesWeHack Target Notes

- Slug: `infomaniak`
- Bounty: Med=$1K, High=$3.5K, Crit=$7K | avg_reward $72,868 (highest in program list)
- 2,837 total reports — very active, high competition
- Stack: Swiss cloud provider, Vercel + Next.js on some assets

**In-scope assets:**
- `api.infomaniak.com` — REST API, v1+v2 authenticated endpoints
- `login.infomaniak.com` — OAuth2 PKCE flow
- `*.kdrive.infomaniak.com` — file storage
- `ksuite.infomaniak.com` — office suite
- `*.kchat.infomaniak.com` — chat
- `mail.infomaniak.com`, `calendar.infomaniak.com`, `contacts.infomaniak.com`
- `www.swisstransfer.com` — file transfer
- `kmeet.infomaniak.com` — video meetings
- `kpaste.infomaniak.com` — paste service

**Out of scope:** `api.pub1.infomaniak.cloud`, OpenStack dashboard, `ov-XX.infomaniak.ch`, `*.vps.infomaniak.com`, `*.ftp.infomaniak.com`, Jelastic subdomains

**API patterns (from MCP server source code at github.com/Infomaniak):**
```
GET  /2/drive/{driveId}/files/{fileId}
GET  /2/drive/{driveId}/files/{fileId}/access/invitations
GET  /2/drive/{driveId}/files/{fileId}/download
POST /2/drive/{driveId}/files/{fileId}/rename
GET  /3/drive/{driveId}/files/{fileId}/files   # directory listing
GET  /1/calendar/pim/calendar
GET  /1/calendar/pim/event?{params}
GET  /2/profile
```

**CORS (confirmed):** `login.infomaniak.com` returns `ACAO: *` on `/oauth/token`, `/api/token`, `/fr/login`. No `ACAC: true` → not exploitable (browser refuses credentialed requests with wildcard). Login/token endpoints are HTML pages, not JSON APIs.

**Sentry DSN exposed in SwissTransfer JS bundle:** `https://d46a0f...@sentry-kdrive.infomaniak.com/9` — but store endpoint returns 401. Not exploitable.

**Traffic identification rule:** All requests MUST include `User-Agent: Infomaniak-YWH-Bugbounty` — Infomaniak explicitly requires this and reserves the right to block IPs that don't comply.

**Active challenges (bonus +50% on first valid report):**
- Challenge #6: Node.js Hosting — `https://www.infomaniak.com/en/hosting/nodejs-hosting` — 30-day free trial available
- Challenge #5: Managed Kubernetes — `https://www.infomaniak.com/en/hosting/public-cloud/kubernetes`
- Challenge #4: Email Encryption via kSuite — `ksuite.infomaniak.com`

**Low-competition targets (report count as of 2026-08-02):**
- `admin2.infomaniak.com` — 8 reports, Critical value (max €7,000) — BUT returns 503 from VPS (IP block or internal-only subnet). Skip unless using Swiss residential proxy.
- `kpaste.infomaniak.com` — 7 reports, High value (max €3,500) — SPA dead end (see below)
- `ai-tools.infomaniak.com` — 6 reports, High value (max €3,500) — mobile app + web
- `swiss-backup*.infomaniak.com` — 3 reports, High value
- `vod.infomaniak.com` — 8 reports, High value

**kpaste.infomaniak.com — confirmed dead end (2026-08-02):**
- Pure SPA (React/Vite), all paths return 200 HTML (client-side routing, catch-all)
- `x-version-id: 2.0.12` exposed in response headers
- CSP `frame-ancestors: https://ksuite.infomaniak.com` — can only be embedded in kSuite
- JS bundle (~50KB minified) has no API endpoints, no fetch() calls to backend, no infomaniak URLs
- Only external JS: `web-components.storage.infomaniak.com/current/init.js` (nav/menu component)
- No real backend API exposed unauthenticated — backend logic entirely server-side
- Conclusion: 7 reports likely cover all surface; skip unless doing authenticated testing

**admin2.infomaniak.com — blocked (2026-08-02):**
- All paths return 503 from VPS IP — IP block or internal-only subnet (no CF, bare 503)
- DNS resolves to `185.125.25.30` — Swiss IP range
- crt.sh returns no results — domain not in CT logs (truly internal)
- 8 total reports only because barely accessible externally
- Skip unless using Swiss residential proxy

**www.swisstransfer.com — attack surface notes (2026-08-02):**
- `x-app-version: 0.46.0` exposed in response headers
- CSP is `Content-Security-Policy-Report-Only` (not enforced) — XSS vectors don't get blocked
- S3 backend: `*.s3.swisstransfer1.infomaniak.cloud` (Ceph Object Gateway)
- Download redirect subdomain: `dl-s3cy4u5n.swisstransfer.com` → `Apache/2.4`
- `SWISSTRANSFER-API-XSRF-TOKEN` cookie: NOT httpOnly (accessible via JS)
- Email validation API (no auth needed):
  - `POST /api/1/email-validations` — request OTP to email
  - `GET /api/1/email-validations/{uuid}` — check status
  - `POST /api/1/email-validations/{uuid}/confirm` — verify OTP code (field: `"token"`)
  - `POST /api/1/email-validations/{uuid}/resend` — resend OTP
- Rate limit on confirm: ~50 attempts per session → `email_validation_rate_limit_error`
- OTP format: 6-char alphanumeric (e.g. `EX882B`)
- **Rate limit is tied to validation UUID, NOT IP** — confirmed 2026-08-02: XFF/X-Real-IP/X-Originating-IP/X-Client-IP spoofing on `/resend` all still return 429 `email_validation_rate_limit_error`. Don't bother with IP header bypass on this specific rate limiter; it's session/resource-scoped.
- Transfer creation requires `ST_SESSION` cookie (set after email confirm), NOT `author_email_token` in body
- robots.txt: `Disallow: /d/*` — download links at `/d/{uuid}` pattern

**Attack surface priority:**
1. kdrive IDOR: `GET /2/drive/{A_driveId}/files/...` with token of user B → test cross-user file access
2. Calendar event IDOR via `/1/calendar/pim/event`
3. ai-tools.infomaniak.com — 6 reports, mobile app surface likely under-tested
4. SwissTransfer file transfer flow (requires valid email session cookie for authenticated ops)
5. Node.js Hosting challenge — bonus +50% on first valid report, 30-day free trial available

---

## GoTo Financial (Midtrans + Mokapos) — YesWeHack Target Notes

- Slug: `goto-financial-public-bounty-program`
- Bounty: High=$3K, Crit=$7K
- Stats: 710 total reports

**Accessible scopes from VPS:**
- `gopayapi.com` → 401 all paths (Istio-envoy, internal auth, 403 sandbox)
- `mokapos.com` → 200 (SPA, Nuxt.js)
- `backoffice.mokapos.com` → 200 (micro-frontend React app, redirects `/admin`+`/graphql` to `/login`)
- `findaya.com` / `findaya.co.id` → 200/301 (lending app)
- `gopaymerchant.midtrans.com` → 403 all paths
- `api.midtrans.com` → 401 (requires merchant server_key Basic Auth)
- `api.sandbox.midtrans.com/v2/charge` → 200/401

**mokapos.com JS bundles (found in `/_next/`):**
- Micro-frontend architecture: 9 remote entry files (`BoAuthApp`, `BoPaymentApp`, `BoCustomerApp`, etc.)
- `backoffice.mokapos.com/auth-micro-apps/remote-entry-BoAuthApp.js` — auth shell, 14KB
- Remote entries are shell loaders only — actual API calls in lazy-loaded chunks
- API base URL not hardcoded in remote entries

**backoffice.mokapos.com Vercel block:** `/graphql`, `/admin`, all API paths return 403 Vercel Security Checkpoint from VPS. Needs residential IP or browser.

**Midtrans API pattern (sandbox):**
- `POST /v2/charge` with `Authorization: Basic base64(server_key:)` → full payment API
- `GET /v2/{order_id}/status` → transaction status (requires server_key auth)
- `GET /v1/payment-links` → 401
- No CORS misconfiguration on any tested endpoints

**To go deeper:** Register free merchant account on `dashboard.midtrans.com` for sandbox `server_key`. Test IDOR between merchant IDs on `api.midtrans.com/v2/`.

---

## Harman International — YesWeHack Target Notes

- Slugs: `harman-international-web-applications` and `harman-international-public-bug-bounty`
- Bounty: High=$2,500, Crit=$4,000
- **Not on Cloudflare/Akamai** — most subdomains accessible from VPS directly

**`harman-international-web-applications` scope:**
- `*.jbl.com`, `*.harmankardon.com`, `www.denon.com`, `www.marantz.com`
- `*.roonlabs.com`, `*.roon.app` — Roon music platform
- OOS: `cloud.cloud[1-3].harmanaudio.com`, `jp.jbl.com`, `https://secondchance.jbl.com/module/stripe_official/createIntent`

**`harman-international-public-bug-bounty` scope (IoT API):**
- `https://events.onecloud.harman.com` — 403
- `https://ota.onecloud.harman.com` — **200** (open, no auth on any path)
- `https://apis.onecloud.harman.com` — 403
- `https://edgeapis.onecloud.harman.com` — 403
- `https://tms.onecloud.harman.com` — 404
- `https://bluetooth-events.onecloud.harman.com` — 403
- JBL One mobile app (iOS + Android), JBL Bar devices

**`ota.onecloud.harman.com` — promising unauthenticated API, but stalled at param-guessing (2026-08-02):**

Connectivity confirmed clean: all 7 IoT API endpoints reachable from VPS (no CF/Akamai, no timeout) —
`events`/`apis`/`edgeapis` → CloudFront (403), `tms` → AWS IoT Core direct (404), `quantum-events`/`bluetooth-events` → API Gateway eu-west-1 (403), `ota` → AWS ELB ap-east-1 direct (200). Program verified valid/active/public via YWH API (both slugs, status `V`, not disabled).

All paths on `ota.onecloud.harman.com` return HTTP 200 JSON:
```json
{"result":{"content":""},"code":"-1","message":"appId or projectId not null"}
```

**Confirmed dead-end (20+ combinations tried, all identical -1 response):** path variations (`/v1/check`, `/v1/firmware`, `/v2/check`, `/checkVersion`, `/version`, etc.), param name variations (`appId`, `projectId`, `app_id`, `appid`), param value guesses (`com.jbl.oneapp`, `jbl.oneapp`, `oneapp`, `jbl`, `com.harman.jbl`), IoT-specific params (`deviceId`, `deviceType`, `sn`, `mac`, `productId`, `model`, `sku`), and POST with JSON body. Server gives byte-identical error regardless — this is a single catch-all validator, not path-based routing. **Don't re-try more param-name/value guesses; the blocker is the request FORMAT (likely signed/encrypted payload structure), not the param name.**

**Confirmed mobile app id:** `com.jbl.oneapp` (from YWH scope: `play.google.com/store/apps/details?id=com.jbl.oneapp`). To actually get past the -1 error, need the APK's real request format — mitmproxy-intercept live app traffic, or pull the APK and grep the request-building code. Google/GitHub-code-search-based hunting for the APK stalled 3x in a row this session (APKPure has no direct link on the search page, GitHub code search needs auth, APKCombo wraps download in an encoded redirect) — try an APK-focused download mirror (apkmirror direct version page, not search) or an Android emulator + Frida/mitmproxy capture instead of source-hunting.

**Next step priority:** web-applications scope (27 plain web assets: `*.jbl.com`, Denon, Marantz, Roon) is unauthenticated, no-account, no-APK-needed — likely faster ROI than continuing to chase the IoT API's request format blind.

---

## Harman International (JBL / Denon / Marantz / Roon) — YesWeHack Target Notes — Update

- **Brand storefronts (jbl.com, harmankardon.com, harmanaudio.com, support.jbl.com) run Salesforce Commerce Cloud + DataDome** — fingerprint via response headers `X-SF-CC-*`, `X-DWSID-SAMESITE`, cookie `dwac_*`, and `X-SF-CC-x-datadome: protected`. These are marketing/commerce storefronts, not custom app logic — low ROI for deep probing, skip fast once fingerprinted unless specifically targeting checkout/payment flow.
- **Roon (`roon.app`, `account.roon.app`, `roonlabs.net`, `community.roonlabs.com`) is the real attack surface** in this scope — an actual account/streaming platform, not a storefront, and none of it sits behind Cloudflare/Akamai/DataDome.
  - `account.roon.app` login flow discovered by regexing the page's inline `<script>` block (the whole SPA bundle is inlined, not a separate JS file) for `/api/...` paths: `/api/6/webaccountinfo`, `/api/login/enter-credentials`, `/api/login/enter-tfa`, `/api/login/pick-profile`, `/api/login/setup-token`, `/api/login/status`, `/api/login/confirm-app`, `/api/account/logout`, `/api/6/unassociate`, `/api/6/web_change_billing`.
  - Login uses a device-pairing-style flow keyed by a `?id=<UUID>` query param. **Pitfall:** the UUID looks like a per-session token at first glance but is a static fallback ID baked into the page — confirmed by requesting `/login` fresh 5x with no cookie and getting the identical UUID every time. Don't assume a UUID-in-URL is session-scoped without testing repeatability first.
  - Every mutating endpoint (`enter-credentials`, `pick-profile`, `setup-token`, `enter-tfa`) requires a `recaptcha` field server-side; `confirm-app` requires a custom `roonBI` field that rejects every guessed value — validation is solid, no shortcut found without a real session.
  - `webaccountinfo` CORS is the hardcoded-ACAO false positive documented above (`https://pagerunner.roonlabs.net`, not reflected).
  - **Dangling NS finding:** `www.gotdrops.com` + `mail.gotdrops.com` (Roon's "Drops" music app domain, in-scope via `*.gotdrops.com`) delegate to `namebrightdns.com` NS servers that don't have the zone (NXDOMAIN, cross-verified via 8.8.8.8 + 1.1.1.1). See "Dangling NS Delegation Detection" pattern above. Root `gotdrops.com` is live and Cloudflare-proxied — only these two subdomains are dangling. Exploitability (whether NameBright lets an unrelated party register the same zone name) not yet confirmed — that's the next step before submission.

## YWH Report Quality: Common Rejection Patterns to Avoid\n\n**Open Redirect + OAuth ATO claim (inflated impact):**\nIf you find an open redirect in an OAuth login flow (redirect_uri bypass), claiming \"Account Takeover\" requires proving the authorization code/token reaches the attacker — not just that the user lands on evil.com after login. The critical question: is the *OAuth authorization code* or the *access token* forwarded to the redirect destination? If redirect_uri is a post-auth navigation param (where TeamViewer sends the user after they're already logged in on TeamViewer's side), the ATO claim is wrong — it's plain open redirect. Check: after completing OAuth on the provider side, does the callback URL contain a code/token before hitting your redirect_uri?\n\n**Symptoms of inflated ATO claim:**\n- CVSS you submitted is Medium (5.x) but title says ATO — mismatch is obvious to triagers\n- If it were real ATO: CVSS should be 7.5-9.0+ (C:H, I:H, scope changed)\n- PoC step that says \"attacker exchanges code for access token\" not backed by actual server response showing the token exchange succeeded\n\n**Correct approach:** submit as \"Open Redirect\" with CVSS matching the actual impact (5.4 for phishing-enabling open redirect is correct). Triagers prefer accurate scope reports — inflated claims get downgraded or rejected rather than negotiated up.\n\n**Hard-coded credentials in mobile APK (CWE-798):**\nStrong finding class — almost never rejected if PoC shows token generation works. To maximize acceptance:\n1. Show the extracted credentials (client_id + client_secret)\n2. Show the working `curl` command that generates a valid Bearer token\n3. Decode the JWT payload to show what `scope` the token has\n4. **Critical missing step:** call at least ONE API endpoint with the generated token and show a 200 response (even an empty list). Without this, program may argue the token has no real access. The `client_credentials` M2M flow is sometimes dismissed as \"intended for server-to-server\" — prove it reaches user data or sensitive operations.\n\n## YesWeHack — VPS Accessibility Test (IP Block Triage)\n\nBefore deep recon on any YWH program, batch-test all accessible domains from VPS in one pass. `HTTP 000` or `403` = blocked, skip. `200/301/302/307/308` = accessible.\n\n```bash\n# Quick batch test — all scope domains at once\nfor domain in vendors.paddle.com blablacar.com bitoasis.net; do\n  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 \\\n    -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120' \\\n    \"https://$domain\")\n  echo \"$domain: $code\"\ndone\n```\n\n**Known blockers from Contabo Singapore VPS (AS141995):**\n- Superbank (`superbank.co.id`) — HTTP 000 (DNS/TCP block)\n- GoTo Financial (`gotofinancial.com`) — timeout\n- Moneybox, CoinDCX, Withings, GRW Trading — 403\n- Doctolib, Louis Vuitton — 403\n- Swiss Post E-Voting (`evoting.post.ch`) — HTTP 000\n\n**Accessible from Contabo SG VPS (confirmed 2026-08-03):**\nBlaBlaCar (200), KOMOJU (308), Paddle (200), Gojek (307), DANA (301), Alasco (301), Infomaniak (301), OVHcloud (301), Telenor Sweden (301), MediaMarktSaturn (301), HARMAN (301), Mon Espace Santé (301), Ezviz (301), OTTO.DE (301), ATG (301), BitOasis (301), Decathlon (301), Qwant (302), FDJ United (302), BookBeat (308), Swapcard (301), VINCI (418), Swiss Post (301), Thüringer (301).\n\n## Paddle.com — YesWeHack Target Notes\n\n- Slug: `paddle-com-public-bug-bounty-program`\n- Bounty: med=$300, High=$1,500, Crit=$5,000 | All scopes HIGH asset\n- Stack: Cloudflare + CloudFront behind, React SPA (vendors + sandbox-vendors), Laravel-style session cookie (`paddle_session_vendor`)\n- Reports: 909 total — active but wide scope\n\n**All in-scope domains accessible from VPS:**\n- `vendors.paddle.com` — 200, merchant dashboard\n- `sandbox-vendors.paddle.com` — 200, sandbox merchant dashboard\n- `api.paddle.com` — 404 default, but specific endpoints return 403/error JSON\n- `sandbox-api.paddle.com` — same\n- `sandbox-checkout-service.paddle.com` — 405\n- `sandbox-buy.paddle.com` — 200\n- `paddle.net` — 200\n- `customer-portal.paddle.com` — 200\n- `login.paddle.com` / `sandbox-login.paddle.com` — 200\n\n**API endpoints (no auth — confirmed behavior):**\n\n| Endpoint | No Auth Response | Notes |\n|---|---|---|\n| `/products`, `/prices`, `/customers` | `forbidden` | Endpoint valid, auth required |\n| `/transactions`, `/subscriptions`, `/adjustments`, `/discounts` | `forbidden` | Same |\n| `/events`, `/notifications`, `/notification-settings`, `/event-types` | `authentication_missing` | Different error — possible enforcement gap |\n| `/reports` | `forbidden` | Valid |\n| `/businesses`, `/payment-methods`, `/webhooks` | 404 | Doesn't exist or different path |\n\n**Key finding:** `POST /events` returns framework routing error BEFORE auth check:\n```\n\"The POST method is not supported for route events. Supported methods: GET, HEAD.\"\n```\nMethod validation happens before auth on some endpoints — information leak about routing layer.\n\n**`/events` vs `/products` error difference:**\n- `/products` → `{\"code\": \"forbidden\"}` — auth enforced at middleware level\n- `/events` → `{\"code\": \"authentication_missing\"}` — different code path, auth enforced at handler level\nThis asymmetry is worth investigating: does `/events` handler have weaker auth enforcement for certain conditions?\n\n**Sandbox signup flow (sandbox-login.paddle.com/signup):**\n- React SPA with custom dropdown components — native browser_click on checkboxes is unreliable because React synthetic events don't fire from DOM `.click()`\n- **Workaround:** use `browser_console` JS injection: `document.querySelectorAll('input[type=\"checkbox\"]')[8].click()` to tick TOS checkbox\n- Business type/revenue dropdowns open via `browser_click` on the wrapper div, then click the option. State IS set in React after selection (verified via `[role=\"option\"][aria-selected=\"true\"]`) even when visual display doesn't update\n- Continue button requires React state to have valid values — if validation fails silently (page doesn't advance), check listbox state via: `document.querySelectorAll('[role=\"option\"][aria-selected=\"true\"]')`\n\n**Blocker:** React SPA signup with custom dropdowns hard to complete via browser automation — Cloudflare is NOT the issue (no CF block). The issue is React synthetic event mismatch. **Fastest path: register sandbox account manually in real browser, then use API key for programmatic testing.**\n\n**API key format:** `pdl_sbox_...` (sandbox) / `pdl_live_...` (production). Set via `Authorization: Bearer pdl_sbox_<key>` header.\n\n## Tencent — YesWeHack Target Notes

- Slug: `tencent-bug-bounty-program`
- Bounty: $8–$5,000. Severity at Tencent's sole discretion (no fixed grid)
- Scope: Very broad — Tencent Yuanbao, WeChat, WeCom, QQ, Tencent Video, Tencent Cloud, VooV Meeting, King of Glory, Game for Peace, jiazhang.qq.com, doc.qq.com
- Test accounts: Register at `https://ssl.zc.qq.com/v3/index-en.html?type=0` (QQ) or download WeChat app

**Accessible from Contabo SG VPS (confirmed 2026-08-04):**
- `cloud.tencent.com` — 200 (nginx, CSRF cookie set)
- `mail.qq.com` — 200 (Wwebsvr)
- `exmail.qq.com` — 200 (Wwebsvr)
- `doc.qq.com` → redirects to `docs.qq.com` — 200 (TencentEdgeOne CDN)
- `pay.weixin.qq.com` — 200
- `v.qq.com` — 200
- `voovmeeting.com` — 200
- `work.weixin.qq.com` — 200
- `jiazhang.qq.com` — 200 (but all paths 302, content behind auth)
- `mp.weixin.qq.com` — 200
- `qyapi.weixin.qq.com` — WeCom Open API, all endpoints return structured JSON
- `intl.cloud.tencent.com` — 200, Next.js

**Blocked from VPS:**
- `tencent.com` — HTTP 000 (TCP block)
- `api.tencent.com`, `cam.cloud.tencent.com`, `sts.cloud.tencent.com` — HTTP 000
- `jiazhang.qq.com/*` (all paths) — HTTP 566 (Tencent Cloud EdgeOne WAF block)

**HTTP 566 = Tencent Cloud EdgeOne WAF:** Custom error page served by `waf.tencent.com`. Request ID format: `14-digit-number`. All "interesting" paths on jiazhang.qq.com, *.tencent.com trigger this. Not a real HTTP status code — server-injected by EdgeOne CDN.

**WeCom Open API (qyapi.weixin.qq.com) — structured JSON, accessible, no WAF block:**
All endpoints return `errcode` JSON. IP leaked in every error response: `"from ip: 46.250.227.159"`.

| Endpoint | No-Auth Response |
|---|---|
| `/cgi-bin/user/get`, `/cgi-bin/user/list`, `/cgi-bin/department/list` | `errcode:41001` (access_token missing) |
| `/cgi-bin/checkin/getcheckindata`, `/cgi-bin/agent/get`, `/cgi-bin/media/get` | `errcode:41001` |
| `/cgi-bin/webhook/send` | `errcode:93000` (invalid webhook url) |
| `/cgi-bin/service/get_corp_token`, `/cgi-bin/service/get_auth_info` | `errcode:41022` (suite_access_token missing) |

**SSRF candidate — `/cgi-bin/webhook/send` with `news` type and `picurl`/`url` params timed out (62s)**. News-type webhook instructs server to fetch external URLs for image preview. Needs valid webhook key to test fully. Pattern to verify:
```bash
# Test with invalid key first — if response takes >30s, server is fetching the URL
curl --max-time 70 -X POST 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=WEBHOOK_KEY' \
  -H 'Content-Type: application/json' \
  -d '{"msgtype":"news","news":{"articles":[{"title":"t","url":"http://YOUR_BURP_COLLABORATOR/","picurl":"http://YOUR_BURP_COLLABORATOR/img"}]}}'
# Check Burp Collaborator for incoming HTTP request from Tencent IP
```

**docs.qq.com — Information Disclosure:**
`window.__DWS_INFO__` JavaScript global exposed on all pages to unauthenticated visitors:
```json
{
  "dwsVersion": "2.2.9",
  "releaseVersion": "hotfix/20260514_1756_open_861d7760",
  "imageVersion": "oci-kc8-1jojbmlg0",
  "tkePodName": "tdocs-open-webserver-prod-gz4-5d789bd6fc-8nzc7"
}
```
Kubernetes pod name, OCI image tag, and internal release branch leaked. Low/Informative severity.

**docs.qq.com guest session:** Server auto-assigns `userId: g.<9-digit-number>` to every visitor. Guest userId present in `window.basicClientVars` (base64 encoded). Test: can guest userId access or modify other users' documents?

**docs.qq.com robots.txt:** `Allow: /open, /vip, /mall, /resume. Disallow: /` — `/open` is the only public path.

**voovmeeting.com robots.txt — attack surface hints:**
```
Disallow: /s/   # short meeting links
Disallow: /redirect   # open redirect candidate
Disallow: /google-cb  # Google OAuth callback
Disallow: /reset-password-by-phone, /reset-password-by-email
Disallow: /user-center/
```
`/s/<id>` returns 302 (meeting short links). `/redirect` returns 404 from VPS (WAF/routing). `/google-cb` = 404 (not exposed).

**exmail.qq.com attack surface:**
- `/cgi-bin/loginpage` — login form (200)
- `/cgi-bin/readmail`, `/cgi-bin/compose_send`, `/cgi-bin/mail_list` — all 200 (redirect to login when not authed)
- `/cgi-bin/download`, `/cgi-bin/upload` — 200 (require session for actual operation)
- `/domain/` — 200 (domain management page)
- WAF: Tencent WAF (`waf.tencent.com` 501 page) blocks path traversal/dot-file probes

**intl.cloud.tencent.com (Next.js) — Aegis SDK key exposed:**
`window.Aegis` init in page source exposes `id: 'jUjXEnQXZRgAfQbizh'` and `hostUrl: 'https://rumt-sg.com'`. Aegis = Tencent internal monitoring SDK. Not a bounty-eligible finding on its own.

**Strategy for Tencent hunting:** Unauthenticated surface is well-protected. Most findings will require a valid QQ/WeChat account. Register free account → get access_token → test IDOR on WeCom API endpoints, cross-user docs.qq.com access, and WeChat Pay API flows.

---

## Amazon-Hosted Vendor/Tax Portals (tax.audible.com pattern) — Recon Dead-End Signature

Amazon subsidiary vendor/back-office portals (Audible Tax Portal, likely similar for other
`*.audible.com`, ACX, KDP-adjacent vendor tools) share a recognizable shape:

- Served via CloudFront + `server: Server` header, cookie domain `.audible.com`
- All auth-gated paths (`/login`, `/horizonte/login`, `/accountManager`, `/user_settings`)
  302-redirect cleanly to `https://www.amazon.com/ap/signin?...` — Amazon's central OpenID
  login, not a custom auth stack. No creds/session logic lives on the subdomain itself.
- CSP is `Content-Security-Policy-Report-Only` (not enforced) but HSTS/X-Frame-Options/
  X-Content-Type-Options are all properly set — headers hardened even though CSP isn't blocking.
- Client-side JS bundles (`AudibleTaxPortalJsAssets` etc.) are typically tiny (2-3 lines),
  cookie-preference + form-submit glue only — no API endpoints, secrets, or business logic
  to mine. Don't expect a JS-bundle goldmine on these; that technique pays off on SPAs, not
  server-rendered Amazon vendor tools.
- `openid.return_to` / redirect params get echoed back through the OpenID chain rather than
  used for a direct redirect — not a naive open-redirect target.
- Common probe paths (`.git`, `.env`, swagger, graphql, actuator, path traversal) all clean 404s.

**Verdict pattern:** these portals have near-zero unauthenticated attack surface by design —
the interesting bugs (if any) are all post-login (IDOR on vendor ID, tax form data exposure,
session handling after Amazon SSO). Unauthenticated black-box recon on this class is a fast
`no-findings, need real Amazon vendor account` conclusion — don't burn many turns re-probing
the same handful of path guesses once the OpenID-redirect-everywhere shape is confirmed.

---

## HackerOne Scope Tab — Use the Search Box, Not Manual Scrolling

Large programs (Amazon VRP, 1Password, etc.) list 8-110+ assets in the Scope tab table.
Don't scroll/read the whole paginated table — type into the **Search** field (top of Scope
tab) to filter directly to the relevant row(s). E.g. typing the bare target hostname or a
keyword collapses "1 of 110" down to "1 of 1" instantly.

**Wildcard coverage catches targets not listed by exact name.** A specific subdomain search
(e.g. `alexa`) may return an unrelated app entry while the actual coverage lives under the
apex wildcard (`*.amazon.com`). Always re-search on the apex domain before concluding
"not in scope" — Amazon VRP explicitly notes "All retail marketplaces are Wildcard scoped
(*.amazon)" in Program guidelines, and `*.amazon.com` shows up as its own Critical/Eligible
row in Scope, separate from named subdomains.

Also read the **Bounty eligibility** column per row, not just "In scope" — some rows are
in-scope-but-explicitly-ineligible (e.g. Amazon's "Other Amazon Retail Sites (Please only
actively test explicitly stated scope)" — In scope but Ineligible). Testing those wastes
effort even though the row shows green.

## CORS Reflection — Negative-Control Battery Before Reporting

A single `curl -H "Origin: https://evil.com"` that reflects your origin back in
`Access-Control-Allow-Origin` looks like a bug but is very often a false positive from your
own test, not the target's config. Before writing it up, run a negative-control battery:

1. Pure attacker domains (`evil.com`) — must be rejected. ✅ expected.
2. Origins that merely *contain* the target domain as a substring in a non-authoritative
   position: `evil.com/target.com`, `evil.com?x=target.com`, `target.com-evil.com`,
   `evil.com.target.com` — these must ALSO be rejected by a correctly implemented target.
3. Real subdomains of the target (`sub.target.com`) and the bare apex — these SHOULD reflect
   if the API legitimately serves first-party subdomains. That's proper suffix-matching, not
   a vulnerability, even though it "reflects" in the same way #2 would if the target were
   naive.

Only call it a CORS misconfiguration if an origin that is genuinely NOT a subdomain/apex of
the target (by strict suffix match) gets reflected. If every non-target origin is cleanly
rejected and only #3-style origins reflect, the target's origin validation is doing suffix
matching correctly — stop, it's not a finding. Confirmed clean on `events.1password.com`
(Critical-scoped asset) and `alexa.amazon.com` during 2026-08-05 recon — both reflect only
genuine `*.1password.com` / same-origin, reject every attacker-substring variant tried.

## Mature Enterprise Program Pattern — Amazon / 1Password / Audible-class (2026-08-05)

Ran unauthenticated black-box recon across 5 assets in one session: Agoda (HackerOne),
Audible Tax Portal, 1Password Events API (`events.1password.com/api/` — Critical scope),
`alexa.amazon.com` (Amazon VRP, Critical via `*.amazon.com` wildcard), and
`skills-store.amazon.com`. All five hit the identical wall:

- Every functional endpoint returns clean `401`/`302`-to-login with zero verbose error,
  zero stack trace, zero routing leak (even a **blanket-401 gateway prefix** like
  `skills-store.amazon.com/api/*` returns 401 for both real and nonsense sub-paths alike —
  can't use it for endpoint enumeration).
- CORS validated strictly (suffix-match only, see above) on every asset tested.
- SPA/deeplink shells return `200` on almost any path (e.g. Alexa's `/api/lists`,
  `/api/skills` both 200) — verify the body is the identical React/HTML shell before
  treating a 200 as a real API response; it's client-side routing, not a working endpoint.
- No `.git`/`.env`/swagger/graphql/actuator/debug exposure on any of the five.

**Takeaway:** once this signature is confirmed on one asset in a large well-audited org's
portfolio (Amazon, 1Password, similarly mature programs), don't keep spending turns
unauth-scanning sibling assets in the same org expecting a different outcome — say so
directly and pivot to one of: (a) authenticated testing with a real/trial account (check
Program guidelines first — self-service trial accounts are usually explicitly permitted),
(b) mobile app / APK reverse engineering if a companion app is in scope, (c) diffing
recent changelogs/releases for regressions. Report the pattern to the user plainly instead
of manufacturing a weak finding to have something to show.

## External Repos (~/projects/external-repos/)

| Repo | Stars | Focus |
|---|---|---|
| claude-bug-bounty | 4089 | AI autonomous recon |
| KingOfBugBountyTips | 5486 | Methodology/checklist |
| awesome-oneliner-bugbounty | 3170 | One-liner recon |
| solsec | 885 | Solana security |
| pakala | 343 | EVM scanner, symbolic exec |
| Argus | — | Ethereum attack detection |
| Bitcoin-Sentinel | — | BTC+ETH forensics, MITRE |
| MIESC | 10 | 50 tools, 35 EVM analysis modules |
| scout-audit | 48 | Smart contract audit |
| web3-security-resources | 426 | Web3 security hub |
