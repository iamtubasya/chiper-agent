# Zenya / iProva — round 2, 2026-10-30

Worked example for §7 / §7b / §7c of this skill. Round 1 was 2026-10-24 (see §7 intro); this round
extended it to the full estate and the full spec.

## Target and policy

- Written scope: `*.zenya-software.com`. Vendor also operates `*.zenya.work` (165+ customer tenants)
  and `webshare.zenya.work`; the latter's `/.well-known/security.txt` 302s to
  `www.zenya-software.com/.well-known/security.txt`, so it is covered by the same policy.
- Product: Zenya (formerly iProva / Iris) — healthcare quality, risk and ISMS suite. .NET / ASP.NET
  REST API behind nginx, Azure-fronted.
- **Policy exclusions, verbatim** (decisive — read before probing):
  - "An API route that returns 200 without credentials, when it serves one of the functions above"
  - "A different response for 'no credentials' than for 'invalid credentials'"
  - "The public API documentation (OpenAPI/Swagger), feature flags and version information"
  - Anonymous requests are "handled as a built-in anonymous account that has no permissions. Routes
    that anonymous users are not meant to use refuse this account with 403."
  - Also excluded: missing security headers, URL redirection to a valid page, clickjacking,
    rate-limiting with no apparent impact, third-party-hosted services, TLS misconfiguration without
    a PoC, "simple fingerprinting or version listings".
- Contact: CVD form at `/coordinated-vulnerability-disclosure`. Reward: tiered, "serious security
  problem that is yet unknown to us".

## Estate

`zenya-software.com` (17 subs): www (WordPress/openresty), developer (API docs, WordPress+Azure),
support (Next.js "Klantenportaal" on Vercel), marketing-mcp (nginx 1.18.0, AI chat), intranet +
intranet-acc (SAML → Microsoft tenant `9bd835c3-578d-49d2-8791-c43ddffbdcd4`), collect (analytics
beacon, 400 on every shape), status/community/update (redirect to `*.infoland.nl` / `*.infoland.eu`),
t (Cloudflare 0-byte 200), e (→ spotler.com), blog, werkenbij.

`zenya.work` (165+ tenants, one `subfinder -d zenya.work -all`): lumc, amsterdamumc, erasmusmc,
radboudumc, umcutrecht, mumc, uzbrussel, arubahospital, prinsesmaxima, … plus `test`, `trial`,
`*-test` / `*-acc` / `*-acceptatie` staging twins and `zenya-westeurope-{default,slow,alpha}lane`
(+ `-tls10` variants).

## API surface

| version | paths |
|---|---|
| v1 | 428 |
| v2 | 428 |
| v3 | ~440 |
| v4 | ~470 |
| **v5** | **538** (112 new vs v1) |

v5 additions include the entire `/risks/*` module, `/users`, `/users/password_requests`,
`/users/me/jit_activations`, `/agents/*`, `/support_access`, `/tokens/*`. 566 operations, 359 of them
writes. Global security: `[{basic},{bearer}]`.

Anonymous GET sweep of 310 endpoints → `403`×111, `404`×104, `400`×58, `200`×34, `500`×3. Every 200
was policy-by-design (card-file `/objects`, portal content, case-field schema for the public FLOW
report form, glossary, themes, reporter forms, version/jwks/openid-configuration).

## Findings

### F1 — Sanitizer allowlist bypass (Medium, impact unproven) — §7c
`POST /api/sanitizer`, anonymous, all tenants. Caller-controlled `whitelisted_nodes` permits `on*`
attributes. Control run (no allowlist) strips everything; with the allowlist the payload returns
`result_code:"ok"` untouched. Impact unproven: the front-end uses client-side DOMPurify
(`./sanitize-*.js`, `$sanitize()`), not this endpoint.

### F2 — ~~OAuth authorization request omits `state`~~ — **RETRACTED 2026-10-31, NOT A FINDING**
Originally recorded as Low-Medium (CWE-352 / OAuth 2.0 BCP §4.2.1) on the strength of a `Location`
header read from output **truncated at 220 characters**. The full header is 354 characters and does
contain `&state=eyJuIj...1nYs&prompt=select_account`; decoded, `state` is a base64 JSON nonce
`{"n":"Qg1_dgktk2clD1VdXMTWLQ"}`, **different on every request**, and the callback rejects arbitrary
state values. The CSRF protection is correctly implemented.

Kept in the file only as a recorded retraction so the next round does not re-derive it. The reusable
rule is in `bug-report-delivery`: **never conclude from a truncated value — print `len(value)` and
parse structured values rather than eyeballing a substring.**

### F3 — `/api/license` entitlement disclosure (Low, likely OOS)
Anonymous on all 138 responding tenants. Returns every license part with its enabled flag plus
`has_issues`, `issue_type` (e.g. `licensed_part_exceeded`), `issue_started_date_time`.

### F4 — Feature-gate ordering leaks tenant AI entitlement (Low, likely OOS) — §7 Rule 3
`POST /api/agents/chat` anonymous: **131/164 → `400 "License required"`**, zgvtest →
`400 "Consent required"`, 30 → `403`. Only when licence+consent both pass does authz run.
`GET /api/features/zenya_ai_chat` (anonymous) returns `has_license` / `consent_enabled` /
`all_dependencies_enabled`. Three tenants had everything enabled (mumc, opzcrekem,
radiotherapiegroep) and correctly answered 403. Agent tools per the spec: `search_documents`,
`create_case`, `update_case`, `submit_case`, `list_field_options`, `handoff`.

### F5 — Unhandled 500s anonymously (Low)
`/api/dashboarding_healthprobe`, `/api/scheduled_tasks`, `/api/vueprojects/{id}` → 500 with
`error_number` / `error_date`. WebShare `DocumentResource/{bad-guid}/Document.html` → "An unexpected
error occurred. The error code is <guid>".

### F6 — Internal backend hostname disclosure (Low)
`https://webshare.zenya.work/api` → 301 → `https://inf-cs-production-doc-appservice.azurewebsites.net/api/`.
The backend itself is IP-locked (403 "Web App - Unavailable").

### F7 — WordPress user enumeration (Low, likely OOS)
`developer.zenya-software.com/wp-json/wp/v2/users/` → hilbert, proddev, "Beheerder Infoland",
"Hilbert Leijen", "Product Development", beheerder.

### F8 — TLS 1.0/1.1 (Low, OOS)
`t.zenya-software.com:443` — nuclei `[tls10 TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA]` and the tls11 twin.

## Verified negatives (with the probe that proved them)

- **Tenant isolation.** Host override on another tenant's connection returns that tenant's data
  (correct routing); `X-Forwarded-Host`, `X-Original-Host`, `X-Zenya-Tenant`, `X-Zenya-Domain`,
  `X-Tenant-Id`, `?tenant=`, `?domain=` all ignored. `/api/zenya_url_tokens` binds `tenant_id` to the
  Host (118 trial / 806 lumc) but the resulting JWT is rejected 401 on every protected route.
- **WebShare document ACL.** Share token validated (wrong token → 400), document GUID scoped to the
  token (wrong GUID → error page). `GetHeaderLogo.ashx?WebShareId=` returns the same default PNG for
  any value — no enumeration.
- **marketing-mcp OAuth server.** `/register` rejects foreign `redirect_uri`
  (`invalid_redirect_uri`), `/authorize` rejects them too, `/token` validates `client_id`
  (`invalid_client`). No open dynamic client registration. `/mcp` requires OAuth Bearer and publishes
  correct RFC 9728 protected-resource metadata.
- **Search endpoints.** `/search/answer`, `/search/suggestion`, `/search/chunks` → 403
  "Anonymous user not allowed".
- **Other write surface.** `/support_access`, `/tokens/support_access_token`,
  `/tokens/sharing_content_api`, `/users/me/jit_activations`, `/hyperlinks`, `/support/questions`,
  `/portals/search_feedback`, `/search/feedback` → 403 anonymous.
- **Password-reset oracle.** `PUT /users/password_requests` → 204 for every login code including
  SQLi/XSS payloads; median latency 1.09-1.48 s with no separation between plausible and nonsense
  codes; no injection error leak. Clean.
- **Anonymous case creation — no mass assignment.** `POST /cases` is anonymously reachable on many
  tenants (400 "Form is not found" / "Case type of the form does not allow reporting" / "Field N has
  an invalid value"), but field membership is strictly enforced: unknown id → "Non existing field_id
  999999 found", out-of-form id → "Illegal field N passed".
- **Intranet non-SAML paths.** 49-path sweep on `intranet` and `intranet-acc`: everything redirects to
  Microsoft SAML or 404s. The prior round's "non-gate path" lead did not reproduce.

## Not tested (the honest gap)

- **The entire authenticated surface.** No test account was minted. IDOR/BOLA inside a session, the
  `/risks`, `/documents`, `/audits`, `/compliance` modules, and the AI agent's `search_documents` /
  `create_case` tools with a real credential are all untested. This is where the Critical lives.
- **Stored-XSS end-to-end.** Submitted content could not be read back without credentials.
- **`*.zenya.work` scope status** — outside the written `*.zenya-software.com` scope; needs operator
  confirmation before submission.

## Artifacts

`C:\Users\WINDOWS10\zenya_audit\`: `COVERAGE-LEDGER.json`, `swagger_v5.json` (2.5 MB full route map),
`swagger.json` (v1), `anon_sweep.json` (310-endpoint results), `fingerprint.json`, `sweep.py`,
`sweep_list.json`, plus saved HTML for developer / portal / webshare / mcp-chat.
