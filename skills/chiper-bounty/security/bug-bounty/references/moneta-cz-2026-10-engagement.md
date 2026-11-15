# MONETA Money Bank (moneta.cz) — engagement notes, 2026-10

Bank target, **email-only programme**, no platform. Result: **no payable finding**, perimeter
unauthenticated fully closed. Kept because it is the cleanest worked example of a
*"hardened bank + KYC wall"* engagement, and because it produced four reusable probes
(§3, §4, §5, §6) that apply to any Spring/PowerAuth banking backend.

## 1. Programme shape — read before touching anything
- `https://www.moneta.cz/bug-bounty` is a static Liferay page (no JS brief, no platform).
- `/.well-known/security.txt` carries the real contacts and differs per host — read BOTH:
  - `www.moneta.cz` → `Contact: bugbounty@moneta.cz`, Policy = the HTML page
  - `ib.moneta.cz` → `Contact: vulnerability@moneta.cz`, Policy = a **PDF**
    (`/.well-known/MONETA_Responsible_Disclosure_Policy.pdf`) — pull it with pymupdf, do not skim.
- **Scope is literally two hostnames, "no subdomains":** `www.moneta.cz`, `ib.moneta.cz`, plus the
  mobile app **Smart Banka**. Everything else (`api.`, `sb.`, `m.`, `smlouvy.`, `esg.`,
  `smartbanka.`, `openapi.`, `sbwidgets.`) is OUT — even though the app talks to them and
  `api.moneta.cz` serves the same backend. Two read-only comparison requests are defensible;
  hunting them is not.
- Rewards: Low 120 / Medium 400 / High 2000 EUR. Wire transfer only.
- **Hard constraints that change your method** (not just your report):
  - "We are not providing any testing accounts or environments."
  - **"You will not send more than 100 requests to test rate limit."**
  - No brute force, no social engineering, no data modification.
  - "Reports from automated tools or scans" are ineligible → tool output alone is never the finding.

## 2. Hall of Fame = the programme's own dedupe list. Mine it first.
Already paid, so do not spend the session re-deriving them: Missing Rate Limit, Information
Disclosure, HTTP Headers, Clickjacking, Directory listing, Text Injection, Reflected XSS,
CORS, **Host header injection**, **Liferay Portlet Misconfiguration**, Session Enumeration,
ChatBot XSS (file upload), Exposed Google API Key, SSL/TLS ciphers, SSRF, Outdated software,
"Insecure communication". Also HoF-only (not money): design flaws, content spoofing / text
injection, host injection without exploit, open ports without PoC, SPF/DKIM/DMARC, internal IP
disclosure, missing rate limit.
Consequence used in this run: the `Host`-header-injection sweep was **skipped as a duplicate**,
and the mobile WebView phishing lead was **classified HoF-only, not submitted**.

## 3. Stack + the "two backends" map
```
www.moneta.cz  Cloudflare -> F5 BIG-IP -> Liferay DXP 7.4 (mmb-2024-theme) + React portlet bundles
ib.moneta.cz   195.234.207.124, F5 ASM -> Spring Boot gateway mounted at /openapi + React SPA
               legacy /ibs/ControllerServlet = 404 (decommissioned 2025-12)
Smart Banka    cz.moneta.smartbanka, native Kotlin, Wultra PowerAuth + Malwarelytics, 37 dex / 94 MB
               App talks to sb.moneta.cz, sbwidgets.moneta.cz, ib.moneta.cz/sb/*
```
The SPA's own config is the key to the API: `https://ib.moneta.cz/config.json` →
`{"API_URL": "/openapi", "OLD_IB_LOGIN_PAGE": …, "ASSISTED_CHAT_URL": …}` plus a full
`FEATURE_FLAGS` dump (which features are live, e.g. `QR_LOGIN`, `SECOND_FACTOR_SMS_LOGIN_ENABLED`,
`HASH_PASSWORDS`, `TRANSACTIONS_TAMPER_DETECTION_ENABLED`). Fetch it before probing anything.

## 4. REUSABLE PROBE — Spring route-map fingerprinting from the error body
The gateway answers three distinguishable shapes. This is the fastest unauth surface mapper
available and it costs one request per path:

| Response fragment | Verdict |
|---|---|
| `openapi.process.request.exception` / `"No static resource <path>."` | **route NOT mapped** → drop it |
| `cbl.missing.userid.exception` | route mapped, **session enforced** (good control) |
| `ERROR_GENERIC` + `POWER_AUTH_SIGNATURE_INVALID` | route mapped, **PowerAuth step-up enforced** |
| `{"status":"ERROR","responseObject":{"code":"NotNull","message":"<field>"}}` | mapped + **open**, and it hands you the required schema field by field |
| `{"timestamp":…,"status":400,"error":"Bad Request","path":…}` | different layer (Spring default handler) — path malformed, not route info |
| `{"supportID": "…", "response_type": "General"}` | **F5 ASM block**, see §5 |

Automate with ffuf using the unmapped string as the filter instead of guessing:
```bash
ffuf -u https://T/openapi/unsecured/portal/FUZZ -X POST \
  -H "Content-Type: application/json" -H "User-Agent: $BROWSER_UA" -d '{}' \
  -w words.txt -rate 10 -t 2 -fr "No static resource" -s -o out.json
```
⚠️ `-ac` (auto-calibrate) **zeroed out a genuine hit** on this target (it saw the 46650-byte
block-page baseline and discarded everything). Use `-fr <app-error-string>` or an explicit
`-fs <baseline_size>`, never `-ac`, on a WAF-fronted host.
The `NotNull` message ladder is also free schema discovery: send `{}`, read `must not be null:
amount`, add `amount`, read `insurance`, etc. It mapped a whole loan calculator in 3 requests.

## 5. REUSABLE PROBE — HTTP-200 WAF block pages (F5 ASM)
The single biggest time-sink of the run. F5 ASM does **not** return 403 for everything:
- `POST` with a body it dislikes → **`200` with an identical 46650-byte HTML body on every path**
  (and a `supportID` JSON body when the path is an app route). 75/75 "hits" in one ffuf run were
  this page. Always establish the baseline size first, then `-fs 46650`.
- XML / `<!DOCTYPE` payloads → `{"supportID": "...", "response_type": "General"}`,
  so **XXE is unreachable by design** — record it as "WAF blocks before the parser", not as a
  failed test and not as a finding.
- Directory-traversal-shaped paths and markup in log fields → same block page.
- Real directories answer `403` with a *different*, smaller body (48397 B here) while absent paths
  answer `404` with the app's own 490053 B page. That three-way size split is the WAF/app tell.

## 6. REUSABLE PROBE — is an unauthenticated token actually predictable?
Two QR-login endpoints were open with no session:
`POST /unsecured/cbl-idm/ib-login/generate-qr {"scopeType":"IB"}` → `{authenticationId, qrCode}`,
`POST /unsecured/cbl-idm/ib-login/login/commit {authenticationId}` → poll status.
Format: `40 hex (160-bit) + "-" + sequential unix-seconds counter`.

Do not eyeball entropy — test derivability directly:
```python
hexpart, counter = aid.split('-')
for label, cand in {
  'sha1(counter)': sha1(counter), 'sha1(session)': sha1(sess_cookie),
  'sha1(uuid)': sha1(base64_decode(SESSION_cookie)), 'sha1(uuid+counter)': …,
  'sha1(session+counter)': …, 'sha1(now)': sha1(int(time.time())),
}.items(): print(label, cand.upper() == hexpart.upper())
```
All false ⇒ not reconstructible from anything the client holds. Note `SESSION` cookie is
base64 of a plain UUID — nice-to-know, not a vuln.
Second half: **cross-session oracle test**. Session B polling session A's `authenticationId`
returned the *same* `WRONG_AUTHORIZATION` as A itself ⇒ no state leak, no hijack primitive without
the user's app confirming. Also test parameter whitelisting (`scopeType` accepted `IB/SB/PSD2/
PAYMENT/CARD/AI`) — accept-all with no observable effect on the issued QR = **no impact**, say so.

## 7. Lead closed: test code shipped to production
`POST /openapi/testing/skip-login {userId, contextId, entityId}` exists in prod and answers
`"This endpoint is for testing purposes only."` — a custom guard, so `skip-login` is *deployed but
disabled*. Ran the full bypass battery before believing the guard (12 variants):
`trailing /`, `/.`, `;`, `;a=b`, `//`, `%00`, `%20`, case change, `?x=1`, `./`, `..;/`, `//path`.
All blocked except `%00` (fell through to the SPA 404) and `;`/`..;/` (Spring's own `400`).
Verdict: control works. **A guard message that names the feature is still a guard** — 3 attempts
on the obvious variants, then move on; the remaining value is only in the two `400` shapes, which
are Spring's default handler and reveal nothing.

## 8. Lead closed: ssl-pinning.json — and the truncated-output trap (read this twice)
`https://ib.moneta.cz/sb/ssl-pinning.json` is **200, public, 2054 B** on an in-scope host, with
`name` / `fingerprint` / `expires` / ECDSA `signature` per entry.

**I first concluded "all pins expired → pinning is dead." That was wrong, and the cause was a
truncated terminal read.** The first 4 entries were the expired rotation tail; the file actually
holds 8 entries = 4 expired + 4 valid, overlapping correctly:
`sb.moneta.cz`→2026-11, `mbs.internetbanka.cz`→2027-01, `openapi.moneta.cz`→2027-03,
`sbwidgets.moneta.cz`→2027-04.

**Rule: never score a security control off a truncated stdout.** Re-read the artifact in full
(dump to a file, count entries, print `len()`) before writing the sentence "control X is broken".
A 4-of-8 view is exactly the shape that manufactures a false critical.
Hostnames inside the file (`mbs.internetbanka.cz`, `openapi.moneta.cz`, `sbwidgets.moneta.cz`) are
internal-host disclosure = HoF-only for this programme, and all OOS anyway.

## 9. Endpoint inventory actually reached (so a re-run starts from here)
Open without session — nothing exploitable found:
`/unsecured/cbl-idm/ib-login/{generate-qr,login/commit}` · `/unsecured/maintenance/{version,banners}`
· `/unsecured/codetable/{lang}/{name}` (returns `{"values":[]}` for every name) ·
`/unsecured/publicregistry/{company,address}/search` (public-registry proxy; real data, but public) ·
`/unsecured/ib/payment/payu/{check-url,gpt-create,gpt-update,check-availability}` (encrypted-input flow;
`check-url` with no param returns `payu.decryptionError`) ·
`/unsecured/portal/ploan/calculator/{setup,calculate}`.
Guarded / auth: `/session/ib/*` (`cbl.missing.userid`), `/secured/dispo-model/onboarding/po/login*`
(`POWER_AUTH_SIGNATURE_INVALID`), `/testing/*`.
Not mapped: 360 of the 364 paths grepped out of the prod bundle — the bundle mixes **client routes
with API routes**, so expect ~99% dead ends and do not read the ratio as "surface is small".

## 10. Mobile static: what was verified good (skip re-testing)
`debuggable` absent · `allowBackup=false` · cert pinning via Wultra `ssl-pinning` (see §8) ·
`EncryptedSharedPreferences` + `androidx.security.crypto` + Tink `AndroidKeystoreKmsClient` ·
biometric key on the **real** `IBiometricKeystore` with `invalidateByBiometricEnrollment` honoured ·
all 4 providers not exported, `FileProvider` not exported · App Links `autoVerify=true` with a
matching `/.well-known/assetlinks.json` on **both** `www` and `api` (compare the cert fingerprint
against the signing cert) · no AWS/Stripe/private keys, no JWT, no `client_secret`.

**`DummyBiometricKeystore` appears exactly once in 94 MB of dex — its own class declaration.**
Absence of a reference is the proof it is not wired; state it that way rather than "the SDK ships a
dummy so biometrics may be weak".

## 11. Open gap (the only thing worth re-engaging for)
~360 authenticated endpoints under `/openapi`: accounts, transactions, cards, documents, limits,
disponents, standing orders, PSD2. Programme supplies no account and opening one needs KYC/BankID.
That is where BOLA/IDOR and payment business logic live. Report it as a **coverage limit with one
concrete ask** (client test login: IB ID + password + SMS-receivable number), never as "target clean".
