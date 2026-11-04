# Web3 Frontend Recon & DeFi Logic Auditing

## 1. Next.js Manifest & Route Harvesting
Modern Web3 dApps heavily utilize Next.js. Rather than blind fuzzing, recover the entire client-side architecture directly:
* **Build Manifest:** Locate `/_next/static/<buildId>/_buildManifest.js` or `/_ssgManifest.js` in the HTML source to dump all client routes and dynamic parameter patterns (e.g., `/audit/[id]`, `/dao/createproposal`).
* **API Client Discovery:** Grep chunks for `axios.create({baseURL: ...})` to reveal internal microservices (e.g., separating web API, pad API, chat/AI API).
* **Auth Pattern Inspection:** Inspect interceptors to identify header generation and storage conventions (e.g., `localStorage.getItem("access_token:" + walletAddress)` or Web3 wallet signature login flows via `ethereum.signMessage`).

## 2. Web3 & DeFi Client-Side Logic Flaws
* **Decimal Truncation & Parsing Pitfalls:**
  * EVM tokens predominantly use 18 decimals, whereas tokens like USDC/USDT may use 6, and WBTC uses 8.
  * Developers frequently hardcode decimal regexes (e.g., `.replace(/(\.\d{6})\d+/, '$1')`) instead of dynamic decimal limits (`${decimals}`).
  * Verify whether this leads to precision loss, unexpected dust amounts, or transaction revert/slippage failure in swap/bridge widgets.
* **Launchpad & IDO Data Leakage:**
  * Endpoints like `/pools` and `/pool/:id` often return verbose internal models.
  * Audit response fields for leaked administrative details: `campaign_hash`, `registed_by`, `multiplier_salt`, `kyc_bypass`, and hidden tier allocations.
* **Webhook Signature Verification:**
  * For off-chain quest/bounty rewards (e.g. Buzz/conversion postbacks), check HMAC-SHA256 signature requirements (`X-*-Signature`, `X-*-Timestamp`).
  * Verify canonical JSON sorting rules and test whether timestamp drift tolerances (e.g., ±300s) allow replay attacks.

## 3. Scope Reality Check & Production Deployment Verification
* **Scope Asset Hygiene:**
  * Bug bounty documentation pages frequently reference out-of-date assets.
  * Verify whether listed GitHub repos return 404/private and whether browser extensions remain active on official stores before deep exploitation.
* **Production Deployment Verification (Repo vs Live dApp):**
  * Finding a bug in an organization's public GitHub repo (e.g., hardcoded decimal truncation in a widget or SDK) does **not** automatically mean the live web application is vulnerable.
  * **Verify Live Bundle Inclusion:** Check the target's `_buildManifest.js`, inspect the relevant page chunk (e.g. `/cross-chain-swap`), and verify if the flawed component is actually imported or if the live dApp uses an alternative implementation (e.g. custom in-house UI vs standalone widget).
  * **Strict Triage Distinction:** Clearly label findings as `[CONFIRMED: Repo-Level]` vs `[CONFIRMED: Live dApp Deployment]`. Web bug bounty programs mandate reproducible live impact; submitting an unlinked repository issue to a web bounty queue will result in rejection (Informational / Out-of-Scope).

## 4. Next.js Build-ID Drift (Session-Validated)
* **Never hardcode the build ID path** in scripts that span multiple turns or sessions. Vercel deployments rotate build IDs between deploys.
* Always re-derive the manifest path at the start of JS analysis:
  ```bash
  curl -sL -A "Mozilla/5.0" "https://target.com" | grep -oE '/_next/static/[a-zA-Z0-9_-]+/_buildManifest\.js'
  ```
* **Pitfall:** A previously fetched chunk URL returning 404 means the build rotated — re-fetch the HTML root and re-derive the manifest before retrying chunk fetches.

## 5. Bulk Chunk API Endpoint Mining (Session-Validated)
* Fetch all page-specific and shared chunks from `_buildManifest.js` in parallel (ThreadPool, 5 workers, 8–10s timeout) and scan for:
  - `/api/` route strings (both template-literal concatenations and quoted strings)
  - `axios.create({baseURL: ...})` or hardcoded `https://` API host URLs
  - `webapi.*` / `api.*` host references
* **Key insight:** API endpoint discovery almost always lives in **shared or page-specific chunks**, not in the initial HTML payload. Grepping only the HTML index will miss most internal API URLs.

## 6. Webpack Module Constant Tracing (Session-Validated)
* Next.js production bundles use minified webpack module IDs (e.g. `g.zG`, `p.default`). When you find a call like:
  ```js
  (0,p.default)("".concat(g.zG.fullAuditByCodeFiles),{auditId:e},"post",...)
  ```
  the actual URL string is defined in another module. Trace it:
  - Search all chunks for the constant name (`fullAuditByCodeFiles`) combined with `:` to locate its definition block.
  - Python pattern:
    ```python
    for m in re.finditer(r'(fullAuditByCodeFiles)\s*[:=]', js):
        print(js[max(0,m.start()-300):m.start()+300])
    ```
  - If the constant is not in the same chunk, search the shared/webpack runtime chunks.

## 7. GitHub API as Passive Source-Code Recon (Session-Validated)
* For public repos in the target org, use the GitHub Contents API **without authentication** to audit source code and commit history. Useful for finding logic flaws in widgets/SDKs that may or may not be deployed live:
  ```python
  # List files in a repo directory
  urllib.request.urlopen(f"https://api.github.com/repos/{org}/{repo}/contents/{path}")
  # Read a file (base64-decoded)
  data = json.loads(resp.read().decode())
  content = base64.b64decode(data["content"]).decode("utf-8")
  # Get commit diff (patch field)
  urllib.request.urlopen(f"https://api.github.com/repos/{org}/{repo}/commits/{sha}")
  ```
* Unauthenticated rate limit: 60 requests/hour per IP. Space requests and batch where possible.
* **Pitfall:** `404 Not Found` on a repo path can mean the repo is private, renamed, or deleted — treat it as a scope-hygiene note, not a tool failure.

## 8. Chrome Extension Recon via CRX Download (Session-Validated)
* Extensions listed in a target's documentation can be downloaded and unpacked for static analysis:
  ```bash
  curl -L "https://clients2.google.com/service/update2/crx?response=redirect&prodversion=120.0&acceptformat=crx2,crx3&x=id%3D{EXTENSION_ID}%26uc" -o ext.crx
  # CRX3 contains a ZIP payload starting at the PK\x03\x04 magic; extract with Python zipfile
  ```
* Inspect `manifest.json` for: `permissions`, `host_permissions`, `content_scripts` URL patterns, `service_worker` / `background_page`, CSP directives.
* High-value indicators: overly broad `*://*/*` host permissions, `webRequest`/`webRequestBlocking` (can intercept and modify network traffic), content scripts injected into banking/wallet domains.
* **Pitfall:** Chrome Web Store returns HTTP 204 (No Content) for delisted, region-blocked, or removed extensions — treat 204 as "extension not publicly available," not a network error.

## 9. NestJS Backend Error-Message Fingerprinting (Session-Validated)
* NestJS gateways leak backend structure in 4xx responses. A `{"statusCode":404,"timestamp":"...","path":"...","message":"Cannot GET ...","exception":{...}}` response confirms NestJS — use it to predict endpoint naming conventions (`/api/v1/resource/action`, kebab-case) and verbose error-based oracles.
* A response body of `{"message":"The API request was rejected."}` (without a `path` field) indicates a gateway-level WAF or rate-limit drop — the endpoint exists but the request was blocked before NestJS routing. Useful to confirm protection without confirming vulnerability.

## 10. IDOR Verification on Next.js Server-Side Routes (Session-Validated)
* Next.js pages using `getServerSideProps` (flagged by `__N_SSP:()=>true` in chunk code) will return HTTP 200 for any ID, including invalid ones — the page shell renders and shows a "data not found" message rather than a 404.
  ```js
  var j=!0; // __N_SSP = true — data fetched server-side before page render
  ```
* This means unauthenticated probes to `/in-depth-audit-report/999999` return 200 with an empty state, **not** 403/404 — the IDOR test requires authenticated requests (two valid user accounts) to confirm whether user A can read user B's report ID.
* **Verification protocol:**
  1. Confirm the data-fetching code path in the server-side handler (find which API the `getServerSideProps` calls).
  2. Log in as user A, obtain a valid audit ID.
  3. Log in as user B, request the same ID.
  4. If user B receives user A's data → confirmed IDOR. If user B receives empty state → access control is enforced server-side.
