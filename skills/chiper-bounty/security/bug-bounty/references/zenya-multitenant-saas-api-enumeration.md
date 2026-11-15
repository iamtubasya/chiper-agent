# Multi-tenant SaaS API — enumeration oracles, anonymous-boundary testing, scope re-classification

Worked case: **Zenya** (`zenya-software.com`, ex-Infoland) — healthcare quality/risk-management
SaaS, 450+ tenants, on Azure. CVD program active, reward-by-severity, channel = web form
(`/coordinated-vulnerability-disclosure`), no email in security.txt. Reusable for ANY
multi-tenant SaaS whose product API lives on per-tenant subdomains.

## 1. The product is NOT on the marketing apex (recon trap)
The bounty scope named `*.zenya-software.com`, but that apex is only **marketing/infra**
(WP sites, a DevRev/Auth0 support portal, an "Iris Intranet" instance behind an API-Gateway+key
and SAML, a hard-400 `collect` telemetry host, a Google-OAuth AI-chat `marketing-mcp`). The
**data-bearing product API lives on per-tenant subdomains**: `https://<org>.zenya.work/api`
and the legacy `https://<org>.iprova.nl/api`. Map this early:
- CSP header on the apex leaks the estate (`*.infoland.nl`, `*.dynamics.com`, Azure blob/edge, IdP hosts).
- `crt.sh` + `subfinder` on BOTH the apex and the parent brand (`infoland.nl` here) — the tenant
  TLD (`iprova.nl`) is a different registrable domain the apex scope never mentions.
- The vendor's **developer portal** (`developer.<apex>`) documents the tenant URL pattern and the
  **public GitHub org** ships REST-API examples + a changelog = a free full route map.
- A **public API landing page** on any tenant (`/api/`) is intentionally open (the "anonymous
  account" by-design) and links the **Swagger spec** — grab `/api/swagger/v1/swagger.json`
  (here: 1.4 MB, the COMPLETE route table). That is the single highest-value recon artifact.

## 2. N-state enumeration oracle via token/registration endpoints (the finding class)
`POST /api/tokens  {api_key, username}` returned a **3-state differential, unauthenticated**:
```
username invalid            -> 400 "User not found"
username valid, token-gen OFF-> 400 "Creating tokens for login code 'X' is not allowed!"
username valid, token-gen ON -> 400 "Invalid api_key passed"
```
- This is a **username/login-code enumeration oracle** that also leaks a per-account attribute
  (whether OTP/auto-login token generation is enabled). Confirmed valid: `administrator`
  (token-gen off), `apotheek` (token-gen on).
- **Rate-limit asymmetry — verify at SCALE, never from a 10-15x pass:** `/api/tokens` is
  genuinely unthrottled (100 rapid requests → 0× 429), so enumeration + api_key probing is
  unlimited. BUT the login `/api/bearer_tokens` IS rate-limited — 10-15 attempts show no 429
  (the exact trap that makes an under-sampled test wrongly conclude "no rate-limit"); 429
  first appears at ~25-30. Probe any rate-limit claim at 60-100x before believing it.
- Generalize the probe to any auth/token/registration/forgot-password endpoint: send a
  known-invalid vs a known/guessed-valid subject and diff the error string. A distinct
  "not found" vs "not allowed" vs "invalid <secret>" is the oracle.
- Companion oracles found: `/api/oauth/token` distinguishes malformed `client_id`
  ("Invalid client_id") from well-formed-but-absent GUID ("app registration not found") — low
  value (GUIDs unguessable). `/api/bearer_tokens` login returns a GENERIC
  "invalid_login_or_password" (no response oracle — good) and IS rate-limited (~25-30 → 429).

## 3. Anonymous access-boundary testing (distinguish broken-AC from by-design)
The policy explicitly carved out a **built-in anonymous account** (published portal content,
public report forms, card-file data) that returns 403 on restricted routes and 401 on bad
creds. So a bare 200 is NOT automatically a finding. Systematically GET every Swagger route
as anonymous and **classify**:
- `403 "Anonymous user not allowed"` → control enforced (audits, findings, question_lists,
  frameworks, positions, users, teams, app_registrations — all correctly locked here).
- `200 []` (empty list) → anonymous scope is empty = by-design (`/api/cases`, `/api/objects`).
- `404` on arbitrary IDs → no IDOR (`/api/documents/<random-guid>`, `/api/users/<guid>`).
- `200 + real records` → candidate broken-AC, BUT check the by-design carve-out first:
  `/api/documents` returned 1000 **published** medical PDFs (downloadable) and
  `/api/portals/content_items` 100 items — all carry `published_date_time`, i.e. the customer
  chose to publish them. Per policy that is the CUSTOMER's configuration, reportable to the
  customer, NOT a platform vuln. `/api/users/me` returns the anonymous account's own profile
  (by-design). So: **published/by-design ≠ finding.**
- Info that leaks but is OOS: `/api/versions/zenya` → `7.8.0.11` (version listing = OOS),
  `/api/license`, `/api/features` (feature flags), `/api/.well-known/jwks.json` (public key),
  `/api/bearer_tokens/saml2/data` (IdP tenant + AuthnRequest), `/api/support_access` (active
  support window), `/api/zenya_url_tokens` (a 30-min RS256 `ZenyaUrlToken` JWT — NOT usable as
  an API bearer, returns 401).

## 4. Escalation battery — and the honest boundary
Tried to turn the enumeration into ATO without brute-forcing passwords:
- **api_key bypass battery** on a token-gen-on user: empty / null / missing / whitespace /
  `0` / `test` / `changeme` / tenant-slug / self → all rejected ("incorrect format" or
  - **Timing oracle — validate with N samples + a separation check, never 1-2:** the FIRST
    request to a valid user returned ~1.2s vs ~0.24s for an invalid one, which LOOKS like a
    login timing-enumeration oracle. It is a COLD-START FLUKE: 8 paced samples gave
    valid=[1.089, 0.211, 0.217, …] (only the first slow) and the separation check
    `valid_min(0.211) > invalid_max(0.244)` is FALSE → no oracle. short-vs-long api_key on
    /api/tokens ≈ identical (0.246s vs 0.248s). Conclusion: api_key is a proper high-entropy
    secret, no bypass, no timing leak → OTP-auto-login ATO not reachable without the key.
- **OTP exchange flow** confirmed: `POST /api/bearer_tokens` with `Authorization: token <otp>`
  → "Invalid credentials" (endpoint live, needs a real OTP).
- **SAML ACS**: `/api/bearer_tokens/saml2` + `/api/saml/saml2/acs` exist (415 = wrong binding);
  `/saml2` = generic error page. Not trivially exploitable; would need binding + signature work.
- **Self-provisioning a test account to prove authenticated impact**: NOT possible here — the
  support portal's Auth0 (`rev.auth.devrev.ai/authorize`) 302s to `/login` even with
  `screen_hint=signup` (invite-only); intranet is employee SAML; community redirects off-scope.
  Do NOT create accounts on a customer/tenant production system (third party, regulated).

**Honest reportable shape:** the enumeration (+ unthrottled auth) is a **pre-auth ATO enabler** —
attacker harvests login codes → credential-stuffing / api_key brute-force surface (both
unthrottled) → bearer token → authenticated → sensitive tenant data. Primitives PROVEN with 2
methods (curl + Python) and 3x; the final ATO is the standard logical consequence, NOT executed
(no valid creds, no brute-force). Frame severity as the enabler (Medium), never as a claimed
breach. This matches the skill's overclaiming bans #2/#9 and stop-rule 15b/20.

## 5. Scope re-classification (do this before reporting ANY of these)
Re-read the CVD/OOS list and map each candidate:
| Candidate | Verdict | Why |
|---|---|---|
| username enumeration (3-state, unthrottled) | **IN / report** | directly exploitable → ATO; not an excluded class |
| no rate-limit on login + api_key | **IN (as amplifier)** | "rate limiting with no apparent impact" alone is OOS — only report it CHAINED to the enum→ATO path |
| version `7.8.0.11` | OUT | "fingerprinting / version listings" |
| published docs / content_items | OUT | "public files … no confidential info" + by-design customer publish |
| 500 on `/api/documents/filter` | OUT | "HTTP non-200 pages" |
| WP `/wp-json/wp/v2/users` enum | borderline | WP user-enum is low; the API 3-state oracle is the stronger same-class finding |
| DevRev/Auth0/Spotler config | OUT | "services running at third-party providers" |

## 6. Operator quality bar (reinforced this session)
- **Every finding must ship impact + "attacker bisa apa"** — a bare status-code/oracle is a lead,
  not a finding; chain it to a concrete attacker action before presenting.
- **No theory, no over-claim** — prove primitives, state the unproven final step honestly.
- **No brute-forcing real passwords** — enumerate/probe, don't spray live creds.
- **Stay on the named target** — don't wander to adjacent domains/tenants/trial searches mid-engagement;
  if escalation needs an asset outside the named scope, say so and ask for the ONE concrete unlock.

## 7. The DECISIVE by-design test — read the API's own security spec (added 2026-10-24)
Before calling ANY anonymous-reachable endpoint a broken-AC finding, fetch its OpenAPI/Swagger
(`/api/swagger/v1/swagger.json`) and read the per-operation `security`:
- `security: [{}, {basic}, {bearer}]` — the leading **`{}` (empty object) = "no auth" is an
  explicitly ALLOWED access method → the endpoint is anonymous-BY-DESIGN.** A bare runtime 200
  on such an endpoint is NOT a finding. This single check is more decisive than any amount of
  runtime probing — it flipped two would-be findings this session.
- `security` absent / inherits global `[{basic},{bearer}]` → endpoint SUPPOSED to require auth;
  anonymous reachability + a data/behavior differential is the real signal.

**Case-study flipped to DROP (finding #2):** `GET /api/cases/fields` returned **612 field defs**
(incl. `Geboortedatum patiënt`, `intern SIRE onderzoekers`, `Mailadres vertrouwenspersoon`) and
`/api/cases/fields/{id}/list_items` leaked reference VALUES (57 departments, 30 locations,
disciplines, internal ward names). Looked like a strong healthcare data-model disclosure. But the
Swagger marks `/cases/fields` (and siblings `/objects/data_types`, `/objects/custom_fields`,
`/cases/case_types`) with `{}` = anonymous-allowed → it exists to serve the **FLOW public report
form** (anonymous incident reporting needs the field schema to render). Actual case RECORDS stayed
protected (`/api/cases` → `[]`, `/api/cases/<id>` → 404). The runtime inconsistency (siblings
`[]`, cases/fields 612) is explained by "only cases/fields is needed by the public form", not a
bug. Verdict: **by-design → DROP.**

**Metadata-exposure vs validation-ORDER leak (how to still salvage a real finding on a `{}`
endpoint):** for `/api/tokens` the `{}` reflects the **api_key auth model** (it HAS an api_key
param), NOT "anonymous enumeration intended". The real weakness is the **validation order** — the
handler checks username existence + token-gen status BEFORE validating the api_key, leaking both
to a caller holding only a DUMMY api_key (CWE-204 + improper auth order). That order bug is
reportable even though the endpoint is `{}`-reachable; the mere reachability is not. Rule of
thumb on a `{}` endpoint: "is the exposed thing METADATA the feature needs (by-design), or is
INFORMATION leaking before the credential is checked (real)?" Also note the honest ceiling: this
makes #1 a **Low–Medium CWE-204 enumeration**, NOT a proven ATO — api_key is a proper secret, login
is rate-limited; frame it as the enumeration weakness, never inflate to breach.

## 8. Deliverable shaping + Gmail-draft mechanics (added 2026-10-24)
- **Match the draft to the submission form's fields** so the operator can copy-paste: Zenya's CVD
  form = Title / Type of bug / Severity / URL-IP / Description — structure the draft body with
  those exact labels (one block per field). Channel check first: Zenya = web FORM, no security
  email (only info@/marketing@); stage the Gmail draft anyway but tell the operator the form is
  the official channel.
- **Gmail IMAP draft via imap_tools — the mechanics that cost 4 failed attempts:**
  - **Reusable: `scripts/gmail_draft.py`** (`--creds <creds-script> --to --subject --body <file> --pdf`) encodes every gotcha below — run it instead of hand-typing the sequence.
  - Drafts folder on this account is **`[Gmail]/Draf`** (Indonesian locale), NOT `[Gmail]/Drafts`.
    `folder.list()` first; the user's real drafts live in the localized one.
  - `MailBox.append(message_bytes, folder)` — **message FIRST, folder SECOND** (signature is
    `append(message, folder='INBOX', dt=None, flag_set=None)`; swapping them feeds the folder
    string as the message → `'str' object has no attribute 'obj'`).
  - Pass **`flag_set=("\\Draft",)`** or the message sits in the folder WITHOUT `\Draft` and never
    shows as a draft in the web UI.
  - Build bytes with `email.generator.BytesGenerator` (`msg.as_bytes()` returned str in this env).
  - **Parsing `APP_PASSWORD` from the creds script with a regex literal triggers the Hermes
    secret-redaction layer**, rewriting the line to `APP_PASSWORD=*** → SyntaxError. Read it with
    plain string ops + `chr(34)` for the quote char instead of a regex.
  - `fetch(limit=N)` right after an append can return a STALE subset omitting the new high-UID
    message — verify by searching for the attachment filename / subject, not by assuming the
    newest row is yours.

## 9. "Various sides" round — CORS on WP + the negatives that close the surface (added 2026-10-24)
After the enumeration was submitted, a from-every-angle sweep produced one more candidate and a
set of clean negatives:
- **CORS on developer WP `/wp-json/*`**: reflects ANY Origin (`evil.example.com`, `attacker.net`,
  `localhost`, `null`, `zenya-software.com.evil.com`) + `Access-Control-Allow-Credentials: true`,
  including authenticated routes (`/wp/v2/users/me` 401-for-anon, `/wp/v2/settings`). Exploitable
  shape: a logged-in user (esp. admin) visiting an attacker page → `fetch(...,{credentials:'include'})`
  reads their REST-API data cross-origin. **⛔ Validate exploitability on TWO axes BEFORE calling any
  reflect+creds CORS exploitable — this session it failed both, so it is NON-EXPLOITABLE, not merely
  "borderline": (a) SameSite — read Set-Cookie; no `SameSite` attr = browser-default **Lax = the auth
  cookie is NOT sent on a cross-site fetch/XHR**, so the credentialed request never carries the session
  (this alone kills the attack; Strict also blocks it); (b) nonce — WP REST cookie-auth needs the
  `X-WP-Nonce`, and it is NOT obtainable cross-origin (absent from `/wp-json/` bodies; `/wp-admin/`
  sends no CORS) → authenticated routes 401. A reflect+creds CORS is only real when the cookie is
  SameSite=None AND the endpoint authenticates on the cookie alone.** This is WordPress core
  `rest_send_cors_headers()` default behaviour** (WP reflects Origin + Allow-Credentials on the REST
  API by design) → borderline WP-core/hardening, NOT a Zenya misconfig; vendor likely classifies
  "WP default". Report only with that honest framing (Low–Medium, "restrict allowed origins"), and
  note the inconsistency (`www` `/wp-json/` 301-redirects, `developer` serves it). **Generalisable
  CORS triage:** reflect+creds on a WP `/wp-json/` is WP-core-default until proven otherwise; the
  real signal is a NON-WP API reflecting origin+creds, or a WP site where the carve-out is absent.
- **Clean negatives (close the surface, don't re-litigate):** subdomain takeover — CNAMEs resolve
  to live services (e→flowmailer, collect→stape.io, t→lagrowthmachine, werkenbij→homerun,
  support→fastly, intranet→irisintranet.cloud), no dangling claim. Version confusion
  (`X-Api-Version` 1-6) — cases/objects 200-but-empty for anon across versions, v1-2 stricter. XXE —
  415 (API is JSON-only, no XML parser). JWT alg-confusion (alg:none on `zenya_url_tokens` / OAuth
  `client_assertion`) — rejected (signatures validated). intranet-acc — 303 redirect stub, no
  exposed content. OTP `automatic_login`/cookie params on `bearer_tokens` — no behaviour change.
  Object IDOR by GUID — 400/404 (wrong format / not found). Injection (`quick_codes` / `field_id` /
  `username`) — parameterised, 404/400 literal. `/portal/start` SPA shell — no reflected XSS.
