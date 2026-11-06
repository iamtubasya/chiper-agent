# betterteam — legacy Rails/JSON:API surface on `app.betterteam.com`

`app.betterteam.com` is documented in most notes as "redirects to dashboard; job feeds". It is more
than that: an **older Rails app** is still mounted behind the same Cloudflare zone, and because the
auth cookies live on `.betterteam.com` (not on `dashboard.`), a dashboard session authenticates
against it directly. This is the highest-value *unmapped* surface left on the program and it costs
almost nothing to enumerate.

## Recon that finds it
`ffuf -u https://app.betterteam.com/FUZZ -w <clean sensitive-files list> -rate 4 -t 1 -mc 200,201,204,301,302,400,401,403,500`
(derive the wordlist first: `grep -v '^#' file | sed 's|^/||' | grep -v '^$' | sort -u` — otherwise
ffuf spends the run matching `#` comment lines as paths).

Findings worth knowing:
- `/debug` → **200**, `text/html`, and its only text is
  `Current Environment: Production` + `Current Commit: <40-char sha>`.
  It also **sets `XSRF-TOKEN`** (and a fresh `_SESSION`) — that is where the legacy CSRF token comes
  from: `csrfHeaderName = "x-xsrf-token"`, `csrfCookieName = "XSRF-TOKEN"` (inline in the page).
- `/admin`, `/admin/users`, `/admin/dashboard`, `/admin/login` → **302 `text/plain`**
  `Please authenticate via the warp client` (Cloudflare WARP / Zero Trust). Not bypassable — treat as
  a closed door, not a finding.
- `/healthcheck` → 403 `application/vnd.api+json` `{"errors":[{...,"status":"403","title":"Access Denied"}]}`.
- `/resumes/` → 301 to `/resumes` → 404 HTML; `robots.txt` explicitly `Disallow: /resumes/`.
- `/api/jobs` (no session) → 303 `/login`; **with** a `.betterteam.com` session → 200 JSON:API.
- Note `/api/companies` without a session returns 401 **with an HTML body**, while
  `/api/applications` without `?job=` returns 400 `"job" is a required parameter` — parameter
  validation fires before auth on some routes. Useful for enumeration, not for access.

## Endpoint map (measured)
| path | note |
|---|---|
| `/api/jobs` | JSON:API list, own company only. Each item carries `attributes.benefits.job-id` = **numeric legacy id** |
| `/api/jobs?company=<uuid>` | own uuid → 200; another tenant's uuid → **404** (route-level rejection, not a filter) |
| `/api/jobs/<uuid>` or `/<numeric id>` | other tenant → 404 (both forms) |
| `/api/companies` | own company object: `customer-id` (`cus_…` Stripe id), `description` (raw HTML!), `subdomain`, `trial-expiration`, `trust`, `uuid` |
| `/api/companies/<uuid>` | other tenant → 404 |
| `/api/users` | **object, not list**: `admin`, `curator`, `impersonating`, `email`, `intercom-hash`, `password: null`, `subscription {companyId, customerId, id, priceId, trialUntil, validTo}`, `uuid` |
| `/api/applications?job=<uuid>` | `{"data":[],"meta":{"total":0}}` for own job; other tenant's job → 404 |
| `/api/notes?application=<uuid>` | 404 for a job uuid (needs an application uuid — only from a submitted application, now OOS) |
| `/jobs/<uuid>` / `/jobs/<slug>` on app. | 302 → `dashboard.betterteam.com` |

## Auth mechanics
Login at `https://app.betterteam.com/login` bounces through WorkOS (`redirect_uri=…app.betterteam.com/workos`)
but lands on the dashboard. The resulting cookies are domain `.betterteam.com`, so
`bt-session`, `_SESSION`, `betterteam_user_id` are accepted by the legacy API. Minimum working set:
`bt-session` + `_SESSION` + `betterteam_user_id` (~1.1 KB) — everything else in the jar is analytics.

## What was tested and held (2026-10-25, two trial accounts A/B)
- Cross-tenant object authz: other tenant's job by **uuid** → 404, by **numeric id** → 404,
  `?company=<other>` → 404, `/api/applications?job=<other>` → 404. Company-scoped at the route level.
- Mass assignment: `PATCH /api/users {"admin":true,"curator":true}` and `PATCH /api/companies
  {"trust":"verified","trial-expiration":"3000-…"}` → **403 Access Denied** even with a valid
  `X-CSRF-Token` from `/debug` (JSON body and form body both). Writes are not exposed to this role.
- Injection on JSON:API params: `filter[title]=' OR 1=1-- ` → Cloudflare **403 page**;
  `sort=title,(select 1)--`, `page[size]=1'`, `fields[jobs]=title,extractvalue(1,1)` → 200 with no
  error and no observable difference. No injection signal; do not report WAF 403s as SQLi.
- `/api/users` exposing `customer-id` (`cus_…`) and `subscription.id` is **your own** data → not a finding.

## Open leads (unverified, next run)
1. `/resumes/<id>` path enumeration is robots-disallowed but not probed (resume files exist for
   customers with applications; we have none). Needs an application, which is OOS ⇒ likely dead.
2. Legacy `Accept`-header path traversal (Rails CVE-2019-5418 class) — **operator declined** this
   probe on 2026-10-25. Do not re-run without asking again; it is a read of the server filesystem.
3. Legacy routes not yet fuzzed: anything under `/api/` beyond the five resources above
   (e.g. `applications`, `interviews`, `offers`, `templates`), and `/api/<resource>/<id>/<sub>`.
4. `/debug` commit sha vs public GitHub — chasing a known patched CVE by commit is legitimate
   fingerprinting, but only if the CVE is in an in-scope component (Rails itself would be a vendor
   issue; the program does not pay third-party library bugs without a Betterteam-specific exploit).
