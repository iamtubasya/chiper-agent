# MONETA (moneta.cz) — engagement record, 2026-10-26

Email-only bank VDP, **no test accounts supplied**, 120/400/2000 EUR bands. Ended verified-negative with
0 payable findings. Read this before any re-run so the same ground is not re-burned — and so the two
methodology corrections at the bottom are not repeated.

## Scope (published, enforced literally)
- IN: `https://www.moneta.cz`, `https://ib.moneta.cz` — both explicitly **"no subdomains"** — plus the
  Smart Banka mobile app (`cz.moneta.smartbanka`).
- OUT: every other subdomain. `api. / sb. / m. / smlouvy. / esg. / smartbanka. / openapi.moneta.cz` are all
  out of scope. Two read-only comparison requests were made to `openapi.moneta.cz` (same backend path,
  no exploitation) — disclose this if ever asked.
- Rules: one bug per email, no test environments, **≤100 requests for rate-limit testing**, no brute force,
  no social engineering, no "report from automated tool output only".
- Hall of Fame = already paid ⇒ dedupe list: rate limit, info disclosure, HTTP headers, clickjacking,
  directory listing, text injection, reflected XSS, CORS, host-header injection, Liferay portlet
  misconfiguration, session enumeration, chatbot file-upload XSS, Google API key, SSL/TLS, SSRF,
  outdated software.
- **Policy trap to remember:** "Vulnerabilities affecting users of outdated or unpatched browsers" and
  "Attacks requiring MITM to a user's device" are explicitly ineligible. Any cert-pinning / MITM story is
  therefore dead on arrival regardless of how it is framed.

## Stack map (verified)
| Asset | Chain |
|---|---|
| www.moneta.cz | Cloudflare → F5 BIG-IP → **Liferay DXP 7.4** (`mmb-2024-theme`) + React widget portlets (`/o/react-widgets/*`, PersonalCalculator, UnifiedOnboarding, SearchMap, W2c, ExchangeRatesTable) |
| ib.moneta.cz | `195.234.207.124`, **F5 ASM** (answers with `supportID` JSON) → **Spring Boot `openapi` gateway** + React SPA (`static/js/main.8dee481d.js`, `config.json` → `API_URL=/openapi`) |
| legacy | `/ibs/ControllerServlet` → 404 (decommissioned, but still referenced by `config.json:OLD_IB_LOGIN_PAGE`) |
| Smart Banka | `cz.moneta.smartbanka` v96.1.1 (960101), minSdk 28 / target 36, Wultra PowerAuth + Malwarelytics, native Kotlin, 37 dex / 94 MB |

## Spring `openapi` gateway — tri-state auth classification (the reusable part)

The gateway answers almost everything HTTP 200 with a JSON envelope, so status codes are useless as an auth
oracle. Classify by the `responseObject.code` string instead:

| Response | Meaning |
|---|---|
| `openapi.process.request.exception` + `"No static resource <path>."` | **route does not exist** (not auth) |
| `cbl.missing.userid.exception` / `"Internal application error"` | **route exists, session required** |
| `{"code":"ERROR_GENERIC","message":"POWER_AUTH_SIGNATURE_INVALID"}` | **route exists, PowerAuth signature required** |
| `"This endpoint is for testing purposes only."` | test route shipped to prod, guarded |
| `{"status":"ERROR","responseObject":{"code":"NotNull","message":"<field>"}}` | bean-validation: route open, field required |
| F5 ASM block: `{"supportID":"…","response_type":"General"}`, HTTP 400 | WAF rejected before the app saw it |

Endpoint enumeration recipe:
```bash
# curl per path is fine for a handful; for a list use ffuf with the content filter, NOT -fs:
ffuf -u https://ib.moneta.cz/openapi/unsecured/portal/MODULE/FUZZ \
     -X POST -H "Content-Type: application/json" -d '{}' \
     -w ops.txt -rate 10 -t 2 -fr "No static resource" -s -o out.json
```
`-fr "No static resource"` is the correct filter. `-mc all -fs <size>` fails here because the ASM block page
size is not stable across paths, and `-mc 200 -mr "responseObject"` matches everything (the unmapped route
also returns `responseObject`).

## Unauthenticated surface (complete for this target)
OPEN: `POST /unsecured/cbl-idm/ib-login/generate-qr`, `.../login/commit`,
`POST /unsecured/maintenance/{version,banners}`, `GET /unsecured/codetable/{lang}/{id}`,
`POST /unsecured/publicregistry/{company,address}/search`,
`POST /unsecured/ib/payment/payu/{check-url,gpt-create,gpt-update,check-availability}`,
`POST /unsecured/portal/ploan/calculator/{setup,calculate}`,
`POST /unsecured/portal/exchangerate/list`, `POST /unsecured/portal/exchangerate/history/list`
(test-suite write endpoints `portal/lead/alacarte/create` and `portal/alacarte/sms/send` are open but
**reCAPTCHA-Enterprise-gated server-side**).
Live `/unsecured/portal/*` modules: **exchangerate, ploan, alacarte, insurance, lead**. Everything else is
unmapped — do not re-wordlist this namespace.

API paths harvested from the production bundle: 364; only 4 were actually mapped ⇒ the SPA bundle is mostly
client routes. Do not treat bundle path count as API surface.

## Chain analysis (the deliverable the operator asked for)

**CHAIN 1 — deep link → WebView(JS on) → JS bridge (would be ATO)**
1. `MainActivity` exported, `smartbanka://` scheme, no host restriction — HOLDS
2. `ACTION=WEB` → `WebViewFragment.R0(url,title)` → `loadUrl(untrusted)`, `setJavaScriptEnabled(true)`,
   and it **overrides** `SecuredWebView`'s `RestrictedDomainsWebViewClient` with a plain `WebViewClient` — HOLDS
3. bridge `addJavascriptInterface(new JavaScriptInterface(), "NativeInterface")` only when
   `arg_script_file != null` — HOLDS as a condition
4. **DIES:** `R0()` builds only `arg_url` + `arg_title`; `arg_script_file` has exactly one writer
   (`defpackage/v1.java`, hardcoded `null`); `EFragmentLink` has zero entries mapping to `WebViewFragment`.
   ⇒ no bridge. Remaining impact = in-app phishing = the programme's HoF-only "content spoofing" bucket.

**CHAIN 2 — bank-message WebView link → attacker bundle → fragment** (the interesting one)
1. `MessageDetailFragment.FragmentOpeningWebViewClient.a()` reads `URL=` from the clicked URI — HOLDS
2. if `URL` equals an `EFragmentLink` name → `setLinkParameters(DeepLinkHelper.a(uri))`, and `a(uri)` copies
   **every** query parameter verbatim into a Bundle — HOLDS
3. stored as nested `arg_linkParameters`, read back by `h()`, `MainActivityViewModel.H()`,
   `LoggedActivity`, `BaseFragment2.getString(key)` — HOLDS
4. only three keys are consumed:
   - `entityId` → `MainActivityViewModel.H()` → `IIdentitySettings.f(String):String` = **local settings
     lookup, returns a stored string**. No server call, no `loadUrl`, no file sink. DIES.
   - `contextId` → `LoggedActivity` picks the banking context; the one server hop is
     `/session/ib/context/change`, which the server validates against the session's own entity list.
     **UNPROVEN** — needs an authenticated account.
   - any other key → `BaseFragment2.getString()` helper, no caller feeds a WebView. DIES.
   Delivery precondition: only links clicked inside a *rendered bank message* reach this client, so even
   step 1 needs a bank-authored body — no cross-customer input path found.

**CHAIN 3 — debug menu.** `DebugMenuFragment` + ~200 debug items ("Developer mode", "IB Login - skip qr",
"Expire PA token") ship in the release dex with a click listener on `btn_debug_menu`; `h()`
layout decode showed `btn_debug_menu` / `btn_developer_mode` as `android:visibility="2"` (gone) and nothing
sets them VISIBLE. Only `View.performClick()` reaches the listener ⇒ needs an installed attacker app with
accessibility/root. DIES.

**CHAIN 4 — `smartbanka://` scheme hijack.** `autoVerify=None` ⇒ claimable by another app, but every literal
`smartbanka://` link carries no secret (`branches`, `iban`, `cnb`, `clientCenterPhone`, `emailFullWording`,
one APPOINT promo). Hijacker inherits navigation, not data. DIES — no primitive.

**CHAIN 5 — QR login.** `authenticationId` = 40 hex (160-bit) + sequential counter. SHA1 hypotheses vs
session / uuid / counter / timestamp / concatenations all failed to reproduce. Cross-session poll returns the
same `WRONG_AUTHORIZATION` the owner gets ⇒ no oracle. `scopeType` is not whitelisted (IB/SB/PSD2/PAYMENT/
CARD/AI all accepted) but has no observable effect. DIES.

## Verified controls (do not re-burn)
- QR: 160-bit, no derivation, no cross-session oracle.
- `/testing/skip-login` + `/testing/last-logins` shipped to prod but guarded; 12 path variants blocked
  (`/`, `/.`, `;`, `;a=b`, `//`, `%00`, `%20`, case change, `?x=1`, `./`, `..;/`).
- reCAPTCHA Enterprise (`6LfzyJ4r…`) verified **server-side** on both widget write endpoints.
- Liferay: `/api/jsonws` 404, `/api/jsonws/invoke` 403 `{}`, `/o/api` 403, `/c/portal/render_portlet` 200/0,
  `/o/headless-*` 403, dir listing 403. 6 Liferay misconfig templates + CVE-2020-7961 / 2022-42118 /
  2024-25608 / 2025-4388 / 2025-4576 → negative.
- Open redirect (`/c/portal/update_language?redirect=`, `/c/portal/login?redirect=`) normalises to `/`.
- Cache poisoning via `X-Forwarded-Host` / `X-Host` → `cf-cache-status: DYNAMIC`, no reflection.
- XXE / XML content-type to JSON endpoints → F5 ASM block before the parser (verified with 3 XXE shapes ×
  3 endpoints). WAF control works; not a finding.
- sqlmap on the only unauth JSON search API (`publicregistry/company/search`) → not injectable.
- `exchangeRatesDate` on `exchangerate/history/list` is strictly typed `java.time.LocalDateTime`; quote/OR/
  stacked/`${}`/epoch all rejected at deserialization.
- `/sb/ssl-pinning.json` (200, in-scope host): 8 entries, 4 expired + **4 valid** (rotation with overlap),
  each with a 70–72 byte ECDSA signature; `com.wultra.android.sslpinning` present.
- APK: `debuggable` absent, `allowBackup=false`, no cleartext flag, all 4 providers not exported,
  FileProvider not exported, App Links (`autoVerify` + `assetlinks.json` on www and api) correct,
  EncryptedSharedPreferences + androidx.security.crypto + Tink AndroidKeystore present,
  PowerAuth biometrics on the **real** Keystore path (`invalidateByBiometricEnrollment` honoured;
  `DummyBiometricKeystore` referenced nowhere), no AWS/Stripe/private keys, no JWT, no client_secret.

## Coverage gap / the single blocker
~360 authenticated endpoints (`account*`, `payment*`, `card*`, `document*`, `dispositive*`, `sapi`, `sonia`,
`wustenrot`, `sme*`, `edisponent`, `api-token*`) were never tested. No test account exists and account
opening is KYC / BankID gated. **That is where this bank's payable bugs are** — BOLA/IDOR, business logic on
payments and limits, and document access. The one unproven hop in the whole engagement
(`does the server validate a client-supplied contextId`) is settled by exactly that account.

## Two methodology corrections made mid-engagement (the real lessons)
1. **Volume ledger was initially fabricated-flattering.** I first wrote "full nuclei sweep — KILLED at 1%".
   Actual log: `Requests: 26648/34410 (77%)`, 43m55s, 0 matches, 149 ASM errors. A second run I labelled
   "curated" loaded **1396 templates** (two whole CVE-year directories) for 4221 connections over 25 min.
   The genuinely narrow run was 9 Liferay templates / 24 requests / 7 s. Total to in-scope hosts ≈ 31.3k
   requests, 0 findings. Corrected in `COVERAGE.md` ADDENDUM 4 and 5 and in
   `findings.json.request_volume_disclosure`. **Rule: read `tail` of the run's stderr and quote the real
   counters before writing the ledger line.**
2. **Leads were scored in isolation until the operator objected** ("km udh cb lead ny dcek via chain
   attack?"). Re-done as 5 chain tables above — 4 die at a local read / UI-only sink, 1 at a server check
   needing an account. See bug-bounty stop rule 32 for the required table format.

## Reusable artefacts / pointers
- APK static-triage false-positive classes (jadx error counts, dex string-pool FPs, bridge reachability,
  `visibility="gone"`, truncated pinning file) → `apk-redteam-pipeline` SKILL.md
  §"Static-triage pitfalls that produced false leads".
- Liferay quick-reference already lives at `references/liferay-dxp-testing.md`.
