# Zenya / iProva — 2026-10-30 round 3 (post-nuclei, remaining hosts, anonymous write surface)

Companion to `zenya-iprova-2026-10-30-round2.md` (which covers the spec-version sweep, the
feature-gate ordering probe, the sanitizer allowlist bypass and the multi-tenant Host-header
negative). This file covers what round 3 added: the **anonymous write-endpoint reachability
oracle**, **third-party SaaS classification**, the **Module Federation dead-end proof**, and the
**nuclei concurrency diagnostic**.

Target: `zenya-software.com` (+ the `*.zenya.work` tenant estate). Product = iProva/Zenya, a
healthcare quality/risk/ISMS suite. Policy:
`https://www.zenya-software.com/coordinated-vulnerability-disclosure`.

---

## 1. The nuclei run was degraded — read the `Errors:` counter, not just `Matched:`

The in-scope sweep finished and looked clean:

```
nuclei -l zenya_inscope.txt -rl 25 -c 12 -timeout 10 \
  -severity low,medium,high,critical -tags exposure,misconfig,cve,default-login,panel,tech,ssl
[1:14:15] | Templates: 6111 | Hosts: 11 | RPS: 30 | Matched: 6 | Errors: 7853 | Requests: 134345/168817 (79%)
[INF] Scan completed in 1h14m. 6 matches found.
```

`Matched: 6` and a clean `Scan completed` line read as a verified negative. They are not:
**7,853 errors and 79% template coverage** means ~34,000 template-host pairs were never issued.
The 6 matches were all previously known and all policy-OOS (TLS 1.0/1.1 on `t`, WP user-enum on
`developer`, 3× Fastly debug headers on `support`).

Re-run focused on the four hosts that mattered, with lower concurrency and retries:

```
nuclei -l zenya_focus.txt -rl 15 -c 6 -timeout 12 -retries 2 \
  -severity low,medium,high,critical -tags exposure,misconfig,cve,default-login,panel,tech
[0:08:00] | Templates: 6106 | Hosts: 4 | RPS: 21 | Matched: 0 | Errors: 34 | Requests: 10560/61392 (17%)
```

**30 errors at 17%** versus 7,853 at 79% — same template corpus, same hosts. The original run was
self-throttling: `-c 12` against hosts that were already rate-limiting produced timeouts that
counted as errors, and each error is a template that did not get a real answer.

**Rules:**
1. `Errors:` in the `-stats` line is a coverage number, not noise. A high error count means the
   run is measuring the network, not the target.
2. `Requests: N/M (<100%)` is the honest coverage figure. Write it into the ledger verbatim
   (`79%`, `17%`) — never promote a partial run to "clean".
3. When errors spike, drop concurrency and add `-retries 2` before re-running. On this estate
   `-c 6 -rl 15 -retries 2` was stable where `-c 12 -rl 25` was not.
4. A 1h14m run that yields 6 known-OOS hits is a signal to narrow the host list, not to widen it.

---

## 2. Anonymous write endpoints: the business-object error is the reachability oracle

The public incident-report form is the one *designed* anonymous write path. `POST /api/cases`
takes `{form_id, fields[{field_id, value}], gps_location}`.

### 2.1 The differential that proves the handler ran

| tenant | request | response | reading |
|---|---|---|---|
| `trial` | `{form_id:151, fields:[{field_id:1,value:"probe"}]}` | `404 Not Found` | route not deployed for anonymous use |
| `zgvtest` `dedimo` `treant` `sherpa` `radboudumc` `sevagram-test` | same shape | `400 "Form is not found"` | **handler ran** — auth passed, died in lookup |
| `trijn` `heilighartlier` `arubahospital` `lunetzorg` `meandermc` `mgzl` `haprijnmond` | valid form_id | `400 "Case type of the form does not allow reporting new cases"` | handler ran, business rule refused |
| `azsintblasius` `meandermc` | valid form_id | `400 "The reporter form is not enabled"` | handler ran, feature flag off |
| `vives` `udiagnostics` `azzeno` `azvesalius` `kei` `opzcrekem` `uzbrussel` | valid form_id | `400 "Field 1 has an invalid value"` + `extrainfo: ["Subject with name or external id 'probe' not found"]` | handler ran, field validation |

Only `403 "Anonymous user not allowed"` means gated. Every `400` naming a business object is
emitted *after* the authorization middleware — that is the whole signal.

### 2.2 The error text is a free object-model oracle

```
400 {"title":"Field 1 has an invalid value",
     "extrainfo":["Subject with name or external id 'probe' not found"]}
```

Disclosed, with no credential: the field's real type (a Subject lookup), that it accepts either a
name or an external id, and that the lookup is by exact match. Keep mutating the value until the
message changes and you have the field's semantics.

### 2.3 Mass assignment — probed and closed

| probe | response | verdict |
|---|---|---|
| `field_id: 999999` | `400 "Non existing field_id 999999 found"` | membership validated |
| `field_id: 2`, `field_id: 3` (valid ids, wrong form) | `400 "Illegal field passed"` | form-scoped |
| extra top-level props (`state`, `case_id`, `reporter_id`) | ignored | no mass assignment |
| `gps_location: {latitude:"x", longitude:"y"}` | ignored | no injection point |

Three verified negatives, which is what lets the report say "no mass assignment" rather than
"untested".

### 2.4 Read before write

The write probe was built entirely from the anonymous read surface:

- `GET /api/cases/reporter_forms` → `form_id`, `case_type_id`, `title`, `group.visibility: public`
  for 20+ tenants (opzcrekem had 16 public forms incl. a whistleblower form; arubahospital 12;
  lunetzorg 15 incl. "Datalek melden")
- `GET /api/case_types/{id}/fields` → the complete field list (38 fields on vives form 6)

Do the read sweep first; it converts the write probe from guesswork into a contract replay.

### 2.5 The honest limit

A `201` on an anonymous create would prove reachability, **not** stored XSS — there is no
authenticated view to re-read the stored value. State that limit in the report rather than
claiming the chain. (On this target no `201` was reached anyway: every tenant either 404'd the
route or refused at the business-rule layer.)

---

## 3. Third-party SaaS on an in-scope subdomain — classify by asset origin

TLS `CN` is one eligibility tell. The faster one on modern estates is **which domain the page loads
its own runtime from**.

| host | asset origin / header | platform | verdict |
|---|---|---|---|
| `werkenbij.zenya-software.com` | `static.homerun.co/employers/v3/{cookie-banner,job-list,main}.js`, `feed.homerun.co/zenya`, `x-amz-*` (S3) | **Homerun** careers/ATS | third-party → OOS |
| `support.zenya-software.com` | `portal-library.devrev.com/_next/static/chunks/remoteEntry.js`, `x-devrev: backend=support,slug=zenya` | **DevRev** support portal | third-party → OOS |
| `e.zenya-software.com` | 302 → `sentby.spotler.com/sendpro` | **Spotler** email | third-party → OOS |
| `update` `status` `my` `community` | 302 → `infoland.eu` / `infoland.nl` (Azure App Service edge) | vendor's own other estate | redirect target out of scope |

### 3.1 The SPA catch-all trap on the Homerun host

`/wp-json/wp/v2/users` returned **35,011 bytes — byte-identical to the homepage**. That is the SPA
shell, not a WordPress user list. nuclei's `wp-user-enum` did *not* fire here (it fired on
`developer.zenya-software.com`, a real WordPress). Always `sha256` the body against `/` before
believing a path result on a catch-all host.

Also on that host: `/.env`, `/wp-login.php`, `/phpinfo.php`, `/.git/config` → `403` (S3-style
denial, correct); `/admin`, `/login`, `/api`, `/graphql` → `302` to the shell. Sitemap = 13 job and
`/nl/apply` URLs. Nothing there.

### 3.2 A 302-to-third-party at the edge leaves no pre-redirect surface

`update`, `status`, `my`, `community` 302'd for **every** path probed, including `/.env`,
`/wp-login.php`, `/xmlrpc.php`, `/wp-json/`. Three sensitive paths returning an identical 302 is
enough to close the host — it is a redirector, not an app.

### 3.3 Dead and unidentified hosts

- `blog.zenya-software.com` — DNS resolves, connection refused on 80 and 443 (and `www.blog`).
  Dead.
- `collect.zenya-software.com` — GCP (`35.205.199.78`). Returns **400 + 0 bytes + a `Trace-Id`
  header** for every path and method except `/robots.txt` (200, `Disallow: /`). Probed 19
  analytics-beacon contracts (Plausible `/api/event`, Umami `/api/send`, Matomo `/matomo.php`,
  GA `/j/collect` + `/g/collect`, PostHog `/e/` + `/i/v0/e`, Amplitude `/api/2/e`, plus
  `/v1/track`, `/track`, `/script.js`, `/health`, `/ping`) — all 400. A host that answers 400 with
  an empty body and a correlation id on *everything* is an edge/service contract mismatch, not an
  application. Closed as unidentified.

---

## 4. Module Federation: the portal origin has no API surface

`support.zenya-software.com` is a Next.js **Pages Router** app
(`buildId GOz-W2tSS0h1LiEi5bST6`) whose `webpack` chunk loads
`https://portal-library.devrev.com/_next/static/chunks/remoteEntry.js` and
`https://default-portal-template.devrev.com/_next/static/chunks/remoteEntry.js`. The route
components are fetched at runtime from DevRev, so every data call is made by *that* code against
*that* origin.

`_buildManifest.js` gave the complete route list for free (19 routes):

```
/  /_error  /auth/callback  /email-verify  /survey-response
/[portalSlug]                                   /[portalSlug]/access-denied
/[portalSlug]/article/[articleSlug]             /[portalSlug]/callback/sso
/[portalSlug]/directories                       /[portalSlug]/directories/[directoryId]
/[portalSlug]/hc/[lang]/articles/[articleId]    /[portalSlug]/login
/[portalSlug]/search                            /[portalSlug]/survey-response
/[portalSlug]/tickets/[...params]               /[portalSlug]/tickets/create
/[portalSlug]/[revSlug]/tickets                 /[portalSlug]/[revSlug]/tickets/create
/[portalSlug]/[revSlug]/tickets/[...params]
```

Every one of them is a dead end **on this origin**:

| probe | result |
|---|---|
| `/api/v2/self`, `/portals`, `/articles`, `/directories`, `/search` | `404` (Next.js catch-all page) |
| `/api/v2/tickets` | `200` — but it is the catch-all page too, not data |
| `/internal/rev-users.self.get`, `/internal/parts.get`, `/internal/projects.get`, `/internal/custom-objects.get`, `/internal/plug-settings.get`, `/internal/translations.languages.list`, `/internal/experience.toggles.get`, `POST /internal/experience.toggles.set` | **all `404`** — the micro-frontend calls these on the DevRev origin |
| `/nl-NL/zenya/directories/1..5` and `/abc` | byte-identical 13,053 B — client-rendered, no server-side IDOR |
| `/nl-NL/zenya/hc/nl/articles/1..4` and `/abc` | byte-identical 6,782 B — same |
| `/nl-NL/<payload>` reflected XSS (`"><script>alert(1)</script>` etc.) | `406` at the edge |
| `/nl-NL/<slug>` for 19 slugs | all `200` with the generic shell; slug echoed into `<title>` but entity-encoded |
| `/api/translations` | `400 {"error":"Could not fetch translations","message":"Request failed with status code 400"}` — proxies the upstream status into the body |

Header leakage worth one line in a report: `x-devrev: backend=support,slug=zenya`,
`x-devrev-timing`, `x-devrev-cache`, `x-vercel-id`, plus the Fastly debug headers nuclei found.

**Rule:** once `remoteEntry.js` from a third-party domain appears in a chunk, stop fuzzing the
portal's own `/api/*`. The profitable surface is the vendor's origin and the vendor's own programme.

---

## 5. What round 3 closed, and what remains open

**Closed (with evidence on disk, `/home/agentuser/zenya_audit\`):**
all 17 `zenya-software.com` subdomains; the 165-tenant `zenya.work` API surface (OpenAPI v1–v5,
310-endpoint anonymous GET sweep, 359 write ops); WebShare document ACL; the marketing-mcp
OAuth/MCP chain; the DevRev portal; `collect`; `werkenbij`; `blog`.

**Still open — and it is the whole reason this round produced no Critical:**
**no authenticated session.** `/risks/*`, `/documents/*`, `/audits/*`, `/compliance/*`,
cross-tenant object access, and the AI agent's `search_documents` / `create_case` tools are all
untested. A self-provisioned tenant account is the gate.

**Scope caveat carried forward:** `*.zenya.work` sits outside the written `*.zenya-software.com`
scope, though `webshare.zenya.work/.well-known/security.txt` redirects to the Zenya policy and the
in-scope `developer.zenya-software.com` links to it. The one reportable finding (the sanitizer
allowlist bypass, which lives on every tenant) needs that scope call resolved before submission.

### ⛔ RETRACTION (2026-10-31): the "OAuth missing `state`" finding was WRONG — do not re-report it

An earlier pass concluded that `GET marketing-mcp.zenya-software.com/chat/auth/login` issued a
Google OAuth authorization request **without a `state` parameter** (CWE-352, login CSRF). **That
conclusion was false and the finding is retracted.**

Cause: the `Location` header was read from output truncated at 220 characters. The visible portion
ended at `&scope=openid+email`, which looked like the end of the query string. The **full** header is
354 characters and does contain the parameter:

```
https://accounts.google.com/o/oauth2/v2/auth?client_id=499793245051-...&redirect_uri=...&response_type=code&scope=openid+email&state=eyJuIj...1nYs&prompt=select_account
```

Decoded, `state` is a base64 JSON nonce — `{"n":"Qg1_dgktk2clD1VdXMTWLQ"}` — **different on every
request**. The callback additionally rejected every arbitrary `state` value sent to it
(`"Ongeldige login-state, probeer opnieuw."`). The CSRF protection is correctly implemented.

**The reusable rule:** never conclude from a truncated value. Print `len(value)` next to any header,
token, URL or hash you reason about, and *parse* structured values rather than eyeballing a
substring — `urllib.parse.parse_qs(urlparse(loc).query)` settled this in one call. A conclusion
drawn from a prefix is a hypothesis; the 3x re-verification rule only helps if each run reads the
whole value. Full write-up lives in `bug-report-delivery` ("Never conclude from a TRUNCATED value").

Only the sanitizer finding survived this round. Everything else on `marketing-mcp` — the OAuth
server's `redirect_uri` and `client_id` validation, the absence of open dynamic client
registration, and the MCP endpoint's Bearer requirement — was verified secure.
