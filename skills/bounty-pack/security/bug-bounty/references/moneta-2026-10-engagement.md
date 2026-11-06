# MONETA Money Bank (moneta.cz) engagement — scope, rules, verified negatives

2026-10-26. Email-only programme, no platform. Read before any re-hunt.

## Programme facts (from the live policy page + security.txt)

- IN: `https://www.moneta.cz` and `https://ib.moneta.cz` — **both explicitly "(no subdomains)"** — plus the
  mobile app **Smart Banka** (`cz.moneta.smartbanka`).
- OUT: every other subdomain. Encountered and left alone: `api.`, `sb.`, `m.`, `smlouvy.`, `esg.`,
  `smartbanka.`, `openapi.`, `sbwidgets.`, `mbs.internetbanka.cz`.
- Contact: `bugbounty@moneta.cz` (www) / `vulnerability@moneta.cz` (ib); both are in
  `/.well-known/security.txt`. PGP: `/.well-known/monetavulnerabilitypgp.asc`. Preferred languages en/cz/sk.
- **No test accounts or test environments are provided.** Account opening needs KYC/BankID ⇒ the entire
  authenticated surface is gated. Report this as a coverage limit with a concrete ask; do not fall back to
  curl-only and do not invent an identity.
- Rate-limit testing is capped: **"You will not send more than 100 requests to test rate limit."** So
  never run a rate-limit probe here — record it as deliberately not performed.
- Other bans: brute force, social engineering, modifying/accessing data that isn't yours, third-party
  provider bugs, "reports from automated tools or scans", vulnerable-library without exploitability,
  "errors thrown by a web service when using an invalid request", MITM-dependent findings, Terrapin
  without PoC, missing cookie/security headers, CORS without an exploit.
- Rewards: Low 120 / Medium 400 / High 2000 EUR, wire transfer only (no crypto/PayPal).
- **Hall of Fame = already-paid classes ⇒ dedupe-saturated** (read the list before hunting): rate limit,
  information disclosure, HTTP headers, clickjacking, directory listing, text injection, reflected XSS,
  CORS, host-header injection, Liferay portlet misconfiguration, session enumeration, chatbot file-upload
  XSS, Google API key, SSL/TLS ciphers, SSRF, outdated software, internal IP disclosure.

## Stack

- `www` → Cloudflare → F5 BIG-IP → **Liferay DXP 7.4** (theme `mmb-2024-theme`) + React widget portlets
  under `/o/react-widgets/*` (PersonalCalculator, UnifiedOnboarding, ExchangeRatesTable, SearchMap, W2c) +
  Liferay DDM forms. JSONWS is disabled.
- `ib` → 195.234.207.124, **F5 ASM** (`supportID` error pages, uniform 46650-byte block page) →
  **Spring Boot "openapi" gateway** + React SPA (`/config.json` → `API_URL=/openapi`).
  Legacy gateway `/ibs/ControllerServlet` is decommissioned (404 with a 490053-byte Ashburn page — that
  490053 size is the host's generic 404, not a block).
- Smart Banka 96.1.1 (960101), minSdk 28 / target 36, Wultra PowerAuth + Malwarelytics, 37 dex / 94 MB.

## Verified negatives — do not re-test these

Web (`www`):
- Liferay: `/api/jsonws` 404, `/api/jsonws/invoke` 403 `{}`, `/o/api` 403, `/o/headless-*` 403,
  `/c/portal/render_portlet` 200/0 bytes, `/c/portal/login` 302→`/`, document-library 404, dir listing 403.
  6 Liferay nuclei templates + CVE-2020-7961 / 2022-42118 / 2024-25608 / 2025-4388 / 2025-4576 → negative.
- Open redirect: `/c/portal/update_language?redirect=` and `/c/portal/login?redirect=` normalise to `/`.
- Cache poisoning: `X-Forwarded-Host` / `X-Host` → `cf-cache-status: DYNAMIC`, nothing reflected.
- XXE / content-type confusion: XML bodies to 3 JSON endpoints → F5 ASM block before the parser.
- SQLi: sqlmap on `unsecured/publicregistry/company/search` → not injectable; manual quote/template → no
  differential.
- reCAPTCHA Enterprise (site key `6LfzyJ4r…`) enforced **server-side** on `portal/lead/alacarte/create`
  and `portal/alacarte/sms/send` (zero-token and forged-token both rejected).
- Onboarding widget API surface is exactly 4 endpoints; `/documents/<g>/<f>/<uuid>` are public marketing assets.

IB gateway (unauth surface, all that exists):
- OPEN: `unsecured/cbl-idm/ib-login/{generate-qr,login/commit}`, `unsecured/maintenance/{version,banners}`,
  `unsecured/codetable/{lang}/{id}` (returns empty for every name), `unsecured/publicregistry/{company,address}/search`,
  `unsecured/ib/payment/payu/{check-url,gpt-create,gpt-update,check-availability}` (encrypted-input flow),
  `unsecured/portal/ploan/calculator/{setup,calculate}`, `unsecured/portal/exchangerate/{list,history/list}`.
- AUTH ENFORCED: `/session/ib/*`, `/secured/dispo-model/onboarding/po/login*` →
  `ERROR_GENERIC / POWER_AUTH_SIGNATURE_INVALID`.
- GUARDED: `/testing/skip-login`, `/testing/last-logins` → "This endpoint is for testing purposes only."
  12 path variants all blocked.
- QR login: 160-bit random hex + `-<unix-seconds>`; no SHA1 correlation with session/uuid/counter/timestamp;
  cross-session polling returns the same `WRONG_AUTHORIZATION` ⇒ no oracle. `scopeType` unwhitelisted
  (IB/SB/PSD2/PAYMENT/CARD/AI accepted) but has no observable effect.
- `exchangerate/history/list` takes only `{"exchangeRatesDate":"<LocalDateTime>"}`; quote/OR/stacked
  `PG_SLEEP`/`${7*7}`/epoch all rejected by Jackson. Future date silently returns today's table (public
  data, no impact).
- `ib.moneta.cz/sb/` exists (403), `/sb/ssl-pinning.json` is a valid rotating pin set (4 expired + 4 valid
  through 2026-11/2027-04, ECDSA-signed). `/sb/{caapi,drc1x,live3x,openapi}` 404 on this host.

Mobile (static only — no AVD/emulator available on a 6 GB host):
- Good: not debuggable, `allowBackup=false`, no cleartext, cert pinning, EncryptedSharedPreferences +
  Tink AndroidKeystore + real PowerAuth keystore path (`invalidateByBiometricEnrollment` honoured),
  providers/FileProvider not exported, App Links with `autoVerify` + assetlinks.json on www and api,
  no AWS/Stripe/JWT/client_secret.
- Rejected lead — deep link `smartbanka://open?ACTION=WEB&URL=<any>`: reaches `WebViewFragment.loadUrl()`
  with JS on and replaces `SecuredWebView`'s allowlisted client, but the `NativeInterface` JS bridge is
  only added when `arg_script_file != null`, which no deep-link path sets ⇒ in-app phishing only =
  the programme's HoF-only "content spoofing / text injection" bucket.
- Rejected lead — debug menu in release: `DebugMenuFragment` + ~200 debug items are in the dex and
  `btn_debug_menu` has a listener, but the layout declares it and `btn_developer_mode` as
  `android:visibility="gone"` and nothing sets them VISIBLE ⇒ unreachable.
- Custom scheme `smartbanka://` has `autoVerify=None` (claimable by another app) but every literal link
  carries no secret (`branches`, `iban`, `cnb`, `clientCenterPhone`, `emailFullWording`, one promo).

## The one remaining unlock

The ~360 authenticated `/openapi` endpoints (accounts, payments, documents, limits, disponents) are where
this bank's payable bugs will be — BOLA/IDOR, business logic, document access. Everything unauthenticated
is hardened to a genuinely high standard. One client test login (IB ID + password + SMS-capable number)
is the single thing that reopens this engagement.

## Deliverable decision

No draft was staged: a report on the WebView/deep-link lead would be rejected under "hypothetical flaw
without PoC" and the pin/header/rate-limit classes are HoF-only. Correct output here was a
verified-negative ledger, not a report.
