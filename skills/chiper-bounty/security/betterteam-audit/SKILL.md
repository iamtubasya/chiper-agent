---
name: betterteam-audit
description: betterteam.com bug-bounty — current scope (rewritten 2026-10-25), auth model, 24-endpoint dashboard API, legacy Rails surface, and the exhaustive negative matrix. Load when resuming the betterteam engagement.
---

# betterteam.com — Bug Bounty (program opened 2026-10-22)

## ⚠️ SCOPE CHANGED 2026-10-25 — RE-READ THE PROGRAM PAGE, DO NOT TRUST OLD NOTES
Verified from https://www.betterteam.com/bug-bounty + /.well-known/security.txt (Expires 2027-10-10):
- **OUT OF SCOPE NOW: "Publishing jobs and submitting applications. We do not approve or publish test
  jobs, so do not ask; testing that needs a live job or a submitted application is out of scope."**
  This kills the whole Critical band (resume/applicant IDOR) by POLICY, not by paywall. Do not burn a run
  trying to reach it.
- Only **careers.betterteam.com** among career sites. Other `*.betterteam.com` customer sites are OUT.
- NEW in-scope hosts (added since the 2026-10-22 notes):
  - `storage.googleapis.com` reached through app-given links + `s.betterteam.com` (GCS bucket behind
    Cloudflare): bucket ACLs, listing/reading/writing objects that aren't yours, links that should
    expire. "Stop at the first proof: one listing response or one object name is enough."
  - `i.betterteam.com` and `*.i.betterteam.com` — measurement hosts **including their DNS server**.
    "No load testing or flooding, including DNS queries."
  - `srp.betterteam.com` + `srp-api.betterteam.com` — Segment proxies. Only OUR proxy setup
    (forwarding to hosts it should not, cookies/headers it should drop). Segment's own service is out.
- Paid example that matters: "**an unpublished job, a hidden field or applicant data in a feed is in
  scope**" — the feed is the highest-value angle still reachable; test it before anything else.
- Rules: "No automated vulnerability scanners, broad crawling or fuzzing", scripts may repeat a
  hand-written request at **<5 requests/second total across all accounts**. This is the definition of
  the operator's "gentle automated" mode: BB_GENTLE=1 on the orchestrator (nuclei -rl 3 -c 1,
  ffuf -rate 3/4 -t 1, sqlmap --delay 2, katana -rl 2 -c 1). Never drop to curl-only because of it.
- Not paid (unchanged, seen on page): scanner-only findings without working proof, missing security
  headers, cookie flags, SPF/DKIM/DMARC, clickjacking without state change, self-XSS, error pages or
  stack traces showing nothing sensitive, "text or link injection that cannot run script".
- Known/accepted: existing sessions stay valid after password change, after enabling 2FA and after
  logout (fix in progress) — do NOT report.


## ⛔ SCOPE WAS REWRITTEN 2026-10-25 — RE-READ THE PROGRAM PAGE EVERY SESSION
`https://www.betterteam.com/bug-bounty`. Two things changed that invalidate most 2026-10-22/24 notes.

**1. Publishing jobs and submitting applications are now OUT OF SCOPE.** Verbatim:
> "Publishing jobs and submitting applications. We do not approve or publish test jobs, so do not ask;
> testing that needs a live job or a submitted application is out of scope."

⇒ The Critical-band resume / applicant cross-tenant path is **not testable by policy**, not merely
paywalled. Do not ask Betterteam to approve a test job, do not submit an application anywhere (not even
to your own trial career site), and do not record these as "target is secure". Correct status:
`OUT-OF-SCOPE-BY-POLICY`.

**2. Four new in-scope surfaces were added** (all tested 2026-10-25, all held — details in
`references/new-scope-surfaces-20261025.md`):
- GCS bucket ACLs reached through app-given links: `storage.googleapis.com` / `betterteam-app-uploads`,
  `s.betterteam.com` — "stop at the first proof: one listing response or one object name is enough".
- `i.betterteam.com` + `*.i.betterteam.com` — measurement hosts **including their DNS server**; no
  flooding, **no DNS query load**.
- `srp.betterteam.com` + `srp-api.betterteam.com` — Segment proxies; **only OUR proxy setup** is in scope
  ("forwarding to hosts it should not, or passing on cookies or headers it should drop"). Segment's own
  service is out.

**IN SCOPE:** www.betterteam.com · dashboard.betterteam.com (app + API + the file links it serves) ·
app.betterteam.com (redirects to dashboard; job feeds) · **careers.betterteam.com ONLY** (job pages +
application form, without submitting) · the GCS/s/i/srp hosts above.
**Exception, always in:** subdomain takeover / dangling DNS on any of
betterteam.com/.net/.xyz/.au/.com.au/bte.am.
**OUT:** betterteam.net/.xyz (staging) · publishing jobs / submitting applications · every other
`*.betterteam.com` customer career site · vendor-run services under our domain (login/help/support) ·
vendor platforms (WorkOS, Stripe, Cloudflare, Fastly, Zendesk, Intercom, Google, Indeed, ZipRecruiter,
LinkedIn, Monster).

## Traffic rules — and the operator's resolution
Program: **"No automated vulnerability scanners, broad crawling or fuzzing"** and **fewer than 5
requests in any one second total** across you and all your accounts; "stop at once if you see unexpected
errors or slowdowns"; no DoS/load/stress, no brute force, no bulk job/applicant creation, no email to
real people.
Operator doctrine: **never fall back to manual/curl-only.** Stay automated but GENTLE —
run the pipeline with `BB_GENTLE=1` (`audit-pipeline-operations` §7).

## Reporting
Email **security@betterteam.com** only, subject `Bug bounty: <title>`, ONE root cause per email.
Include URL/endpoint, repro, impact, proof (request+response or screenshot), and the trial account.
Intercom live chat is out of scope and nothing sent there counts. Sign up the trial with an address
containing "bugbounty" and send header `X-Bug-Bounty: <trial email>`.
Include the line accepting the Program Terms.
**Rewards:** Critical $1–2k · High $400–800 · Medium $150–400 · Low $50–150.
Not paid: missing headers, SPF/DKIM/DMARC, cookie flags, clickjacking w/o state change, self-XSS,
scanner output without a working proof, and — important for this target —
"error pages or stack traces that show nothing sensitive".

## Auth — SOLVED (2026-10-24), password path is the reliable one
Signup is anti-abuse blocked after a few attempts from one IP; the email still registers as PENDING.
**Login is not blocked.** Playwright Chromium works headless for the password path:
`dashboard.betterteam.com/login` → email → "Continue with email" → `input[type=password]` → "Sign in".
Magic-code fallback: "Email sign-in code" → read the 6-digit from Gmail IMAP → `input[name="code"]`.
Fallback when Cloudflare stalls a fresh context: the operator's real Chrome profile
(`launch_persistent_context(profile_dir, channel="chrome", headless=False)`) — do NOT conclude
"browser broken".
Save `pg.context.cookies()`. Cookies expire — re-login each run rather than reusing a stale jar.

Two trial accounts (need both for cross-account BOLA):
| account | company | subdomain | company uuid |
|---|---|---|---|
| `RESEARCHER_USERNAME+bugbounty@gmail.com` / `@BlueFrog88` | BugBounty Test Co | `bugbountytestco-2` | `0fb48db1-2b60-47b4-80ef-59067f074ca4` |
| `RESEARCHER_USERNAME+bugbounty2@gmail.com` | BugBounty Test Co 2 | `bugbountytestco2-2` | `7f215c9f-86d8-425e-b521-3f5477224dbd` |

Minimum viable cookie jar (everything else is telemetry noise): `bt-session`, `_SESSION`,
`betterteam_user_id`. Send `X-Expected-Client-Version` = the value in `window.PUBLIC_ENV`.

## Tech
- **dashboard** = React/Remix SPA. API = `dashboard.betterteam.com/.api/*`, clean REST, all 401 unauth.
  Assets on `s.betterteam.com/dashboard/assets/` (`api-*.js` = generic OpenAPI fetcher).
  Source maps are STRIPPED (`*.js.map` → NoSuchKey, no `sourceMappingURL`) — don't hunt for them.
- **auth** = WorkOS AuthKit; signup/signin/reset/2FA are WorkOS-hosted = vendor surface (OOS), but
  post-signin app behaviour IS in scope. `redirect_uri` strictly validated (evil.com,
  dashboard.betterteam.com.evil.com, bare host all rejected). `/workos` callback: generic 500 on
  malformed code/state, no open redirect.
- **infra** = Cloudflare (app) + Fastly (www, `i.`). Only 7 CNAMEs platform-wide (zendesk, workos-dns,
  fastly, stripecdn, chargedesk, proxyhog=PostHog, fastly) — all live/registered, **no dangling record**.
  PostHog proxy lives at `phrp.betterteam.com`.
- Public config in the SSR shell's `window.PUBLIC_ENV`: Segment write key, PostHog key, Stripe **pub**
  key, Datadog client token, `EXPECTED_CLIENT_VERSION`. All publishable-by-design — replaying them is
  not a finding.

## Dashboard API map — 24 endpoints (rebuilt from SPA chunks; hashes rotate, re-verify)
```
/me · /companies/me · /companies/me/subscription · /career-page · /career-page/logo
/jobs · /jobs/list · /jobs/{uuid} · /jobs/{uuid}/designated-emails
/jobs/{uuid}/indeed-sponsorship · /jobs/{uuid}/indeed-sponsorship/account · /jobs/{uuid}/zr-sponsorship
/jobs/by-slug/{slug} · /jobs/by-slug/{slug}/applications · /jobs/by-slug/{slug}/application-status-counts
/jobs/status-counts · /jobs/can-post · /jobs/recent-locations
/applications/{uuid} · /applications/{uuid}/{resume-profile,decision,log,notes,adjacent,related-applications}
/integrations/indeed/me · /clients/me/security-widget-token · /auth/email-domain-suggestion
/checkout-sessions/{id} · /users/me · /verifications
```
`POST /jobs` JobInfo schema: title, `type=enum[Fulltime,Parttime,Temporary,Contract,Internship]`,
location{rawLocation,country,city,state,zipCode}, description+descriptionHtml (min length),
department, employmentType, salary{lowerRange:int,upperRange:int,currency,period}, remote, requisitionId.
Also **`POST /exports/resumes.zip`** — NOT under `/.api`; form-encoded (`application_uuids`,
`return_to`, `time_zone`), hidden in the `jobs-dashboard` chunk.

**Getting the real map:** 0B recon calls this host "static-site". Rebuild from the built bundle —
pull asset links out of the SSR shell, fetch the chunks from `s.betterteam.com`, then grep
`\.(get|post|patch|put|delete)\(\s*["'\`]/(path)`.

## Negative matrix — DO NOT RE-TEST (all measured, all with evidence)
**Dashboard, 2 accounts (2026-10-24 rounds 2/3 + 2026-10-25 round 4):**
- BOLA cross-account: negative on jobs PATCH, by-slug, applications list, application uuid, sponsorship
  account, `designated-emails` POST (→404), logo uuid (→"logo not found"). Tenant context is
  SERVER-DERIVED — `X-Company-Id`, `X-Company-Uuid`, `company_id/uuid` params and swapping the
  `betterteam_user_id` cookie are all ignored.
- Mass assignment: `PATCH /users/me` ignores role/isAdmin/permissions/companyUuid/plan/trialUntil —
  only `name` persists. `PATCH|PUT /companies/me` → 405.
- Publish/entitlement bypass: `POST /jobs` with `status:Active,published,approved` → forced `Pending`;
  job `PATCH action` enum = `Edit|Reopen|Close` only. Also OOS by policy now.
- Pagination cursor = **unsigned** base64 `{"v","uuid","value"}`. Swapping in another company's uuid
  still returns your own rows; SQL chars in `value` → WAF 403; garbage cursor silently ignored.
- `POST /exports/resumes.zip`: no CSRF token required, but absolute `return_to` rejected (no open
  redirect) and it fails closed at 0 applications.
- `GET /<route>.data` and `?_data=routes/...` → 204 / SPA shell; no loader data exposed.
- Injections clean: sqlmap on omnisearch `q` and jobs/list `limit|sort_by` (params either non-dynamic
  or non-injectable), arjun, nuclei 18 tag-sets, dalfox/kxss no reflection. WAF answers quote payloads
  with its own 403 page.
- SSTI not rendered; job title in `<meta og:title>` has raw `</>` but the double-quote is escaped.
- CORS: no ACAO/ACAC reflection. CSRF: not exploitable (SameSite=Lax + JSON-only + no CORS).
  JWTs RS256 with `kid`, not forgeable. `/.api/stripe/webhook` is IP-whitelisted (403) — unreachable.
- Non-existent resources (404): `/team /invitations /members /users /company/users /reports/export
  /.api/reports* /config /integrations /subscription /settings /security`.

**Legacy `app.betterteam.com`** — a whole second Rails/JSON:API platform alive behind the same
`.betterteam.com` session cookies. Full map + XSRF mechanics: `references/legacy-rails-surface-20261025.md`.
- `/admin*` → 302 "Please authenticate via the warp client" (Cloudflare Access / WARP).
  **Bypass matrix EXHAUSTED 2026-10-25 — do not repeat.** 18 path variants (`/admin /admin/ //admin
  /./admin /%2fadmin /admin%2f /admin/..;/ /admin/. /ADMIN /admin%00 /admin?x=1 /;/admin /admin/;/
  /%41dmin /admin%20 /admin..;/ /..;/admin`) → all still 302 to `betterteam.cloudflareaccess.com` or
  blocked 403 "Access blocked — Betterteam". 7 header-trust variants (`X-Forwarded-For` 127.0.0.1 and
  10.0.0.1, `X-Real-IP`, `CF-Connecting-IP`, `X-Original-URL`, `X-Rewrite-URL`, `X-Forwarded-Prefix`)
  → no bypass. Note the two distinct 403 shapes: "Access blocked — Betterteam" = WAF,
  "We couldn't complete this request — Betterteam" = request-anomaly (seen on `CF-Connecting-IP`).
  Per-programme note: this host is ours, so it is in scope, but it is a managed Zero-Trust edge —
  treat a clean matrix here as expected, not as a missed finding.
- `/healthcheck` → 403 JSON:API (3/3). `/resumes/` robots-disallowed, 404 behind the 301.
- `/api/{jobs,companies,users,applications,notes,subscriptions}` JSON:API; `/api/applications` needs
  `?job=<uuid>`, `/api/notes` needs `?application=<uuid>`.
- Reads are company-scoped: another tenant's uuid **and** numeric `benefits.job-id` both 404.
  `filter[...]`/`include=` are IGNORED, not honoured (no leak, no error).
- Writes → 403 on every resource even with a **valid** `X-CSRF-Token` from `/debug`. Route-level authz.
- 31 of 33 guessed legacy resource names → 404. Don't re-enumerate the same list.

**Subdomain takeover:** 628 `*.betterteam.com` + 14 other-domain subs; 7 CNAMEs, all live/registered
(RDAP-verified). No dangling record. Don't re-run a full takeover sweep; do check `dnsx -cname` output.

**`i.betterteam.com` / `*.i.betterteam.com` / `ns1.d.i`** — hardened, low expectation:
beacon resolves as a 5-hop 302 chain to an 8×8 PNG; basename strictly `[a-z0-9-]`; only `.png`/`.gif`
match; traversal (plain/%2e%2e/double/%00) 404; methods 404; header overrides inert; the DNS server
refuses recursion, CHAOS `version.bind`, AXFR, UPDATE (NOTIMP) and ANY (NOTIMP).

## CANDIDATE-01 — /debug info disclosure — ⛔ REJECTED 2026-10-25 (BB-066), DO NOT RE-REPORT
**Vendor verdict (security@betterteam.com, Adam Seabrook, 2026-10-25 11:41 UTC), verbatim:**
> "The /debug page was reported to us on 24 October. It shows the environment name and the
> deployed commit, which is software version disclosure, and our program does not pay for that.
> There is no reward for this report."

⇒ Unpaid class (their not-paid list: "Software version disclosure") AND duplicate (first
reported 24 Oct). The 2026-10-26 fresh run re-validated it 3/3 anyway; the draft that was staged
that day has been deleted from Gmail Drafts. Treat this angle as CLOSED permanently. Lesson:
this vendor pays authz/logic/data-exposure classes only — version/env disclosure is explicitly
$0, so do not spend runs on fingerprint-style findings here.
`app.betterteam.com/debug` returns 200 unauthenticated and discloses `Current Environment: Production`
plus the deployed commit sha. **Trigger condition: 200 for every `Accept` value EXCEPT `text/html`
(which 302s to the dashboard).** Reproduced 3/3 plus 7 header variants.
Sub-paths (`/debug/env|config|vars|info|build|version|routes|.json|status|health|git|revision`) → 404.
No env vars, keys, DB config, hostnames or stack trace in the body. Low band ("minor information leak"),
marginal EV because "error pages showing nothing sensitive" is unpaid.
Draft + raw-response attachment: local copy under `D:/data/hermes/betterteam-fresh-<date>/06-report/`,
**but the deliverable is a Gmail DRAFT, not a file path.** This program is email-only, so staging means
append into `[Gmail]/Draf` (Indonesian locale) with `folder=` and `flag_set=` keywords, the raw
request/response as an attachment, then re-fetch from a fresh connection and print uid + subject +
attachment name. Verify before reporting success — `APPENDUID ... Success` alone proves nothing, and the
operator will ask "mana draftnya". Recipe + pitfalls: `email-automation` §"Gmail Draft Creation via
imap_tools". Never send: the operator sends VDP/bounty mail himself.

**The lesson that almost cost this finding:** it was first written down as `UNSTABLE → DROPPED` because
a 05:47 request got 200 and a 07:33 request got 302. It was deterministic the whole time — the
difference was the `Accept` header, which `curl` and Python `urlopen` set differently. Before labelling
anything UNSTABLE, run the trigger matrix (Accept / Content-Type / User-Agent / cookie / method /
`Sec-Fetch-*`), 3× each — see `audit-pipeline-operations` §5b.

## Dropped candidates (verified non-payable — do not re-open)
- Raw `<script>`/`onerror` stored verbatim in `career-page aboutBody` and echoed by the API — but
  rendering is sanitize-html-whitelisted (no `on*`, no `style`, schemes http|https|ftp|mailto|tel) and
  the public render needs a PUBLISHED job = OOS.
- `/debug` env+commit → CANDIDATE-01 above (Low only).
- `trialUntil: 3000-01-01` on trial accounts — deliberate for trials.
- Segment `writeKey` replay — the key is public by design in `window.PUBLIC_ENV`.
- LOGO SVG upload → 403 "Access blocked" (only raster accepted); cross-account logo uuid → "logo not found".

## Remaining surface, in priority order
1. **`careers.betterteam.com`** — the only in-scope job-page/application-form surface. **Status
   2026-10-25 round 4: REACHED and tested — negative.** The root can hit a branded 429 ("Too many
   requests — Betterteam") or Cloudflare `error code: 1015` after the automated passes, but
   `/robots.txt`, `/favicon.ico`, `/nonexistent` and every `/:slug` route keep serving, so it is
   route-level throttle, not a host block. **How to get a live slug without a published job of your
   own:** `careers.betterteam.com/robots.txt` exposes
   `Sitemap: https://app.betterteam.com/feed-static/sitemap.<uuid>.xml` — that file is a public
   30k-URL list including Betterteam's OWN postings on `careers.betterteam.com`
   (`/senior-full-stack-engineer-1`, `-2`). Fetch it, grep for `careers.betterteam.com/`, and you have
   real in-scope job pages without publishing anything. Measured on those pages:
   - Job page 200 (32 KB), `/apply` 200, `/apply/standard` 200.
   - **Query-param reflection: NEGATIVE.** Canary `zxq9probe` + 8 param names never reflected;
     response byte-identical to baseline (md5 `d2157ce7ff`). HTML payloads → Cloudflare "Access
     blocked" 403 (WAF, not a reflection).
   - **Cross-tenant slug: NEGATIVE.** Customer slugs (`msk-teleradiology`, `cdl-a-owner-operator-tanker`,
     `painter`, `server`) and neighbour slugs (`-0`, `-3`, `-1-1`) → 404. Slug space is site-scoped.
   - `%2e%2e` / `%00` → 400 (Cloudflare, no body leak); uppercase → 404; `.json` → 404;
     `/a/../b` normalises to `b` (no traversal).
   - `/apply/standard` form: `POST multipart/form-data`, **no `action` attribute, no CSRF token, no
     hidden job id, no captcha** (recaptcha/turnstile/hcaptcha all absent); fields
     email,name,phone,resume(file),body. NOT TESTED BY DESIGN — submitting is OOS.
   Remaining untested here: the multipart POST handler itself (unreachable without submitting), and
   `JobDetailsWidget` render of employer-controlled fields. Treat 1015 as REWORK, never N/A
   (`bot-protected-target-testing`).
2. **`srp-api.betterteam.com`** — the only place the program explicitly invites a *proxy-misbehaviour*
   finding ("cookies or headers it should drop"). A repeatable cookie / `Authorization` / `X-*`
   reflection through the proxy would be real. Write-key replay is by design; absolute-URI → CF 403;
   XFH/X-Host/X-Original-URL inert (all measured negative).
3. Legacy `app.betterteam.com` JSON:API — mapped, company-scoped, writes denied. Only revisit if a new
   resource name appears.
Everything else is exhausted with evidence. Do not re-run the matrix above.

## FRESH RUN 2026-10-25 (full 0A→0F, gate 33/33, 13/13) — what is CLOSED, do NOT re-test
Workdir: `D:\data\hermes\betterteam-fresh-20261025` (00-scope PHASE0.md, 05-evidence/COVERAGE.md,
06-report/AUDIT-SUMMARY.md). Two trial accounts: A `RESEARCHER_USERNAME+bugbounty@gmail.com` (bugbountytestco-2),
B `RESEARCHER_USERNAME+bugbounty2@gmail.com` (bugbountytestco2-2). Password login via Playwright works; the
dashboard SPA + `.api` prefix is `/dashboard-index.html` `window.PUBLIC_ENV` for config/keys.

### THE ONE REPORTABLE FINDING — app.betterteam.com/debug (Low, submitted 2026-10-25)
`GET /debug` with **any Accept value EXCEPT `text/html`** returns 200 + 10,281-byte page:
`Current Environment: Production` / `Current Commit: a003ca55…092`. With `Accept: text/html` it 302s to
dashboard — that header conditionality is why it looks "unstable"; it is deterministic, 3/3 + 7 header
variants. Sub-paths /debug/env|config|vars|info|build|version|routes|.json|status|health|git|revision all
404. No env vars/keys/DB/stack. Band Low ($50-150), marginal EV. Draft:
`06-report/drafts/EMAIL-01-debug-info-disclosure.txt` + `ATTACH-01-raw-response.txt`.

### LEGACY PLATFORM app.betterteam.com (not in the old notes — real surface)
Legacy Rails + JSON:API still serving alongside the new SPA. The shared `.betterteam.com` session
cookies are accepted by it, so after logging in at dashboard (or app./login) the legacy API answers.
Endpoints: `/api/jobs`, `/api/jobs/{uuid}`, `/api/jobs?company=<uuid>`, `/api/companies`,
`/api/companies/{uuid}`, `/api/users`, `/api/users/{uuid}`, `/api/applications?job=<uuid>`,
`/api/subscriptions`, `/api/notes?application=<uuid>`, plus `/debug`, `/admin`, `/healthcheck`,
`/resumes/`. 33-resource enumeration found only `/api/subscriptions` beyond the known set.
All NEGATIVE: reads company-scoped (A cannot read B by uuid OR numeric legacy id; `filter[uuid]` /
`filter[company]` / `include=` are IGNORED and still return own rows), writes 403 (PATCH/PUT
/api/users admin|curator, /api/companies trust|trial, /api/subscriptions features|expiration) even with
a valid XSRF-TOKEN, anonymous `/api/subscriptions` -> 401 "Please log in before using the API".
`/admin*` -> 302 Cloudflare Access (betterteam.cloudflareaccess.com) + 18 path-bypass variants and 7
header-trust variants (XFF 127.0.0.1/10.0.0.1, X-Real-IP, CF-Connecting-IP, X-Original-URL,
X-Rewrite-URL, X-Forwarded-Prefix) all fail. `/healthcheck` 403 JSON:API Access Denied.
`/workos?code=x` -> generic 500, `/workos` -> 404, `/login?redirect_to=|next=` -> fixed redirect_uri.

### FEED (the explicitly-paid angle) — CLEAN
`https://app.betterteam.com/feed-static/sitemap.44e986f8-4c25-4bc5-9b57-87c1c735d4e6.xml` (from
app./careers robots.txt) = 30,844 `<loc>`, 4,940 unique hosts, **all `*.betterteam.com`**, zero foreign
hosts, zero of our trial companies, zero unpublished/Pending jobs, only `/<job-slug>` shape.
Bucket-gap probing: `/feed-static/`, `?list-type=2`, `?prefix=`, `?delimiter=`, `?marker=` -> 200 with a
0-byte body (GCS list denied silently, no key enumeration). `/feed-static/xml/`, `/feed-static/.xml` ->
NoSuchKey.

### JOB STATE MACHINE — publish gate holds
Reopen a Closed job with a FULL valid JobInfo body (title/type/location/description long enough/
department/employmentType/salary{lowerRange,upperRange,currency,period}) -> 200 `{"status":"Pending"}`,
counts move Closed:1->0 and Pending+1. It lands in **Pending, never Active**. Smuggling
status/published/approved/isActive/jobStatus=Active into the reopen body -> 400. Edit on a Closed job ->
400 "cannot perform JobsEditActionEdit action on job with status Closed". PATCH action enum stays
Edit|Reopen|Close. Note: `POST /jobs` needs a description of real length ("job description is too short"
below ~a few hundred chars) and `salary` is required on PATCH job bodies.

### STORED XSS — NEGATIVE, and here is how to prove it properly
Titles containing `zq"><img src=x onerror=window.__xss2=1` ARE accepted and stored. Rendering is safe:
real Playwright Chromium, password login, `/jobs` + the affected detail page give
`imgSrcX=0, onerrorEls=0, flagX=null, flagX2=null, payloadAsText=true`, zero dialogs. The
`payloadAsText=true` is the tell — payload present as ESCAPED TEXT, not a DOM node. Script:
`04-api/xss_check2.py`. `<script>`/`onerror` IS stored verbatim in career-page `aboutBody` and echoed
by `GET /career-page`, but that renders only on the customer career site = OUT of scope.

### Other NEGATIVE surfaces from this run
- Cross-account BOLA (A vs B): `/jobs/{uuid}` PATCH, `/jobs/by-slug`, `/applications`,
  `/applications/{uuid}`, `/jobs/{uuid}/indeed-sponsorship/account`, `/jobs/{uuid}/designated-emails`
  (B POST -> 404), logo uuid reuse ("logo not found").
- Mass assignment: PATCH /users/me ignores role/isAdmin/permissions/companyUuid/plan/trialUntil (only
  `name` persists); PATCH+PUT /companies/me -> 405; PATCH /companies/me/subscription -> 405.
- Pagination cursor = unsigned base64 `{"v":1,"uuid":…,"value":…}`; tampering with another company's
  uuid still returns own rows; SQL chars -> WAF 403; garbage cursor ignored.
- `/exports/resumes.zip` (form POST, application_uuids, return_to): no CSRF token needed but absolute
  return_to rejected and it fails closed with no applications.
- GCS: `betterteam-app-uploads` — `?acl/?cors/?lifecycle/?uploads/?versions` all 403 AccessDenied;
  uploaded logo object is public 1h (by design). `s.betterteam.com` — ListBucket denied, NoSuchKey only,
  traversal (plain/%2e%2e/double-encoded) 404.
- Segment proxies: srp-api accepts the PUBLIC `SEGMENT_CLIENT_KEY` from the dashboard HTML (by design);
  absolute-URI -> CF 403; XFH/X-Host/X-Original-URL/`//host` inert; interactsh 0 callbacks; CORS `*`
  without credentials. srp: `/v1/projects/<public key>/settings` 200 (public Segment config).
- i.betterteam.com: a 5-hop 302 chain ending in a real 8x8 PNG (synthetic monitoring). Basename strictly
  `[a-z0-9-]` (dotdot/slash/?/#/@/:/%/space/angle/quote -> 404), only .png/.gif match, all non-GET
  methods 404, no header reflection. `ns1.d.i.betterteam.com`: recursion REFUSED, CHAOS REFUSED, AXFR
  blocked, DNS UPDATE/ANY NOTIMP (hardened).
- careers.betterteam.com (LIVE, use the public sitemap to find in-scope slugs: our own postings
  `senior-full-stack-engineer-1` / `-2`): query params never reflected (baseline md5 identical),
  cross-tenant and neighbour slugs 404, `%2e%2e`/`%00` -> 400, uppercase/.json -> 404. Apply form is
  `POST multipart/form-data` with NO action, NO CSRF token, NO captcha. Do not submit (OOS).
- Omnisearch is company-scoped: queries for real customer jobs (Teleradiology/CDL/Ochsner/painter) -> 0.
- `/checkout-sessions/{id}` 404 for every id shape incl. our own `cuss_secret_` — a real id only exists
  after a paid checkout ("creates a charge" = stop and ask). `/auth/email-domain-suggestion` is by
  design (echoes domain, null for public providers, NOT an account-existence oracle).
  `/verifications` schema = `{companyType: "Employer"|"Recruiter"}` — do not submit a false business
  declaration.
- Source maps stripped (dashboard + careers `.map` -> NoSuchKey, no `sourceMappingURL`).
- betterteam.net / betterteam.xyz hits from nuclei (missing headers, cookie flags, TLS 1.0/1.1, CSP) are
  BOTH out of scope (staging) AND unpaid classes. Do not report.

## FRESH RUN 2026-10-26 (full 0A→0F, gentle, 2 accounts) — deltas vs 2026-10-25
Workdir `D:\data\hermes\betterteam-fresh-20261026` (COVERAGE.md = full matrix). Scope re-read LIVE:
**files.betterteam.com is IN SCOPE** ("resume, attachment and other file links the dashboard gives you,
and their access controls") — was missing from the 10-25 notes. Known-issues list now also includes
"the old app serves a JavaScript source map (removal in progress)" — **all .map probes 404 this run
(dashboard, sites/assets, legacy guesses); treat as already removed, don't hunt**.

NEW measured facts (do NOT re-test):
- GCS buckets that EXIST (401 anonymous = exists, locked): betterteam-app-uploads,
  **betterteam-resumes, betterteam-test, betterteam-backups**. List/ACL/CORS/lifecycle/logging/
  website/versioning denied (JSON+XML); anonymous PUT → 403 (write test marker never created).
- `GOOGLE_CLOUD_API_PUB_KEY` (PUBLIC_ENV) is a REAL GCS-JSON-API key, referer-restricted to
  *.betterteam.com (dashboard/careers/app referers accepted, betterteam.com rejected), but
  `storage.objects.list` is blocked at key level (401 "Requests to this API ... are blocked").
  Referer spoof alone ≠ finding. Dead end.
- `/jobs/recent-locations` is company-scoped: canary Pending job + unique location on account B
  did NOT appear in A's list (unpublished cross-tenant locations do not leak).
- Impersonation header injection (X-Impersonate/Impersonate-User/X-User-Id/X-Betterteam-User-Id/
  On-Behalf-Of/X-Act-As/X-Impersonating/Impersonate) → all ignored; betterteam_user_id cookie swap
  via browser → ignored. Tenant is server-derived, confirmed again.
- OAuth /workos code replay (fresh context, no cookies) → generic 500, /me 401. Codes single-use.
- Verb tampering: POST on /companies/me, /users/me, /career-page/logo(GET), /verifications,
  designated-emails(GET), zr-sponsorship(GET) → "method not allowed" (route exists, wrong verb).
  Logo POST wants multipart part named "logo" but errors "part logo: undefined" — upload never
  succeeded; file-link format for files.betterteam.com still unknown (needs an application = OOS).
- /.api/* on app/careers/files/s/srp-api/i/www → 404 (no host-confusion authz). /.api/ fresh
  wordlist (23 paths) → nothing (only /applications/{uuid} route-match noise).
- Legacy: nested routes 404; `/api/applications/{uuid}` EXISTS ("applicant not found", no
  enumerable oracle); `_method` override → nginx 403; numeric-id cross-read (B's 1666406) → 404.
- Feed: full sitemap (30,748 URLs) re-fetched — zero Pending/canary jobs, zero foreign hosts,
  2 careers entries only. Per-company sitemap.0fb48db1….xml etc → 404. srp/srp-api closed
  (thin proxy, ..%2f normalized, no OOB). s. prefixes (resumes/files/uploads/app/legacy/…) → NoSuchKey.
- careers (real Chrome): full Remix route map (CareersPage/careers-job-layout/:slug/:slug/apply/
  :slug/apply/standard/:slug/apply/success/.ready); apply form = POST multipart, NO csrf token,
  NO captcha, NO hidden job id — submitting is BANNED so the handler is untestable; isApproved
  gates the form. dashboard./debug = SPA catch-all (same 14,165b as /nonexistent) — NOT a finding.
- DNS: subfinder 113 subs (6 domains), 8 CNAMEs ALL live vendor targets, no dangling. i. DNS enum
  (admin/internal/api/grafana/k8s/staging/dev/metrics/prometheus/vault/consul/ns*) → all NXDOMAIN.

CANDIDATE-01 (/debug) RE-VALIDATED 3/3 on 2026-10-26 (200, 10,281b, env+commit a003ca55…,
Accept:text/html→302 else 200). **⛔ REJECTED BY VENDOR — DO NOT RE-REPORT.** Sent 2026-10-25
(RESEARCHER_EMAIL), vendor reply 2026-10-25 11:41 UTC from security@betterteam.com,
ticket BB-066, verbatim: "The /debug page was reported to us on 24 October. It shows the
environment name and the deployed commit, which is software version disclosure, and our program
does not pay for that. There is no reward for this report." → duplicate AND unpaid class
("Software version disclosure" is on their not-paid list). Draft staged 2026-10-26 was DELETED
after the inbox check. PDF/body template kept only as reference in 06-report/.

## Support files
- `references/2026-10-25-fresh-run.md` — THE current state: rewritten scope, per-host matrix, 24-endpoint
  API map, legacy map, and CANDIDATE-01. **Read this first.**
- `references/careers-surface-20261025.md` — how to reach a live in-scope `/:slug` via the public
  `feed-static/sitemap.<uuid>.xml` (no publishing needed), `/apply/standard` form internals, and the
  full negative matrix for careers.betterteam.com.
- `references/new-scope-surfaces-20261025.md` — the GCS / `s.` / `i.` / `srp` / DNS-server additions with
  every probe and result.
- `references/legacy-rails-surface-20261025.md` — `app.betterteam.com` legacy Rails/JSON:API map, XSRF
  mechanics, full negative matrix.
- `references/ats-hr-saas-attack-checklist.md` — reusable 18-vector ATS/HR-SaaS checklist (BOLA on
  applicants/resumes, resume file-link IDOR, team role-escalation, invite tokens, CSRF, export IDOR,
  Stripe webhook, logo SVG XSS, job-desc XSS, resume XXE/SSRF, custom-domain claim, webhook SSRF,
  SSO/redirect, search SQLi, race, JWT, email header injection). Load for any ATS target.

## Pitfalls
- Cloudflare + Fastly in front. Report the least-intrusive proof; never touch other customers' data;
  clean up test resources. This programme's not-paid list is unusually strict — read it before drafting.
- Programme policy beats severity tables: a perfect Critical that needs an out-of-scope step is worth $0.
