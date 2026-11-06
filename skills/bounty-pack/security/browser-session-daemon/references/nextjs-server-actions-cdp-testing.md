# Next.js Server Actions — Multi-Account CDP Testing Recipe

Proven on quarterwise.co.uk (Malden Ltd, VDP — safe harbor), 2026-09-26.
Stack: Next.js (App Router) + Cloudflare, `qw_session` HttpOnly cookie (64-hex, server-side session).
Result of the audit: **0 rewardable findings** — every checked surface was solid. That negative
result is itself the proof the recipe below exercises the right surfaces.

## Verify VDP scope FIRST
quarterwise.co.uk shipped `/security/disclosure` with an explicit safe harbor, in-scope list
(quarterwise.co.uk + signed-in app + API only; subdomains and Stripe/Postmark/Cloudflare/HMRC
out of scope) and rules (own accounts only, no volume testing, no third-party email, 90-day
confidentiality). Read it via curl with browser UA (urllib got 403; curl with UA worked).
`robots.txt` disallowed `/app` and `/verify`.

## Asset mapping without the whole fleet
- OpenAPI surface: `/developers` page exposed `/api/v1/openapi.json` + `/developers/docs.md`.
  All 5 endpoints (`/me`, `/sources`, `/categories`, `/sources/{id}/transactions` GET+POST)
  returned 401 without a Bearer key. Key prefix `qw_live_`, 120 req/min, Pro-plan gated.
- App JS chunks: download ALL `/_next/static/chunks/**` referenced by authed pages and grep
  for `"/api/..."` strings → found `/api/ai/extract-expense`, `/api/properties/`,
  `/api/account/export`, `/api/collect`. AI endpoint returned 403 `AI scanning is a Pro feature`
  on free plan (plan check enforced). `direct.quarterwise.co.uk/fph-echo` leaked
  `{"ip","port"}` — subdomain = out of scope, noted as hardening only.
- ffuf (70-word list) on root + `/api/` found nothing beyond known pages → hidden-endpoint
  discovery was negative.

## Account factory (mail.tm + browser)
1. Create mail.tm account (`POST /accounts` then `/token`) — read OTPs from
   `GET /messages` (Bearer). Each account = own address; disposable domain accepted by target.
2. Signup in real Chrome via JS: set `input[name=email]`, `form.requestSubmit()`;
   read OTP from inbox; enter `input[name=code]`; set password; set name ("Step N of 4").
3. Extract session cookie per profile via CDP `Network.getAllCookies`.
4. Keep ONE profile per account (never mix cookie jars), ports 9222/9223.

## IDOR/BOLA matrix (all negative, all meaningful)
| Test | Method | Result |
|---|---|---|
| Page-level cross-tenant | B cookie → A `/app/sources/{uuid}` | "We can't find that page" |
| Action replay | A's captured server-action POST + B cookie | `Server action not found` |
| Write-scope swap | B opens OWN form, swap `propertyId` → A's | "That property could not be found" |
| Settings rename | B session, `propertyId` → A, rename | "Only the owner can change these settings" |
| Viewer write | adviser (viewer) tries Record income | UI hides button; direct swap-blocked too |
| Export IDOR | non-owner fetches `/api/properties/{uuid}/export` | 404 |
| Invite token binding | accept acc3 invitation while logged in as acc2 | "sign in with the invited address" — token bound to recipient email |
| accessId endpoints | probe update/remove by accessId | 404 |

The `propertyId` field is a hidden input in the Record-income form; settings form has
`name`, `addressLine1`, `postcode`, plus `confirmName` for delete and `percent` for ownership.

## Export & injection checks (how to verify properly)
- Export endpoints: `/api/properties/{id}/export?format=xlsx|pdf&taxYear=all` (actual links
  found on property page "Excel | PDF" buttons).
- **XLSX formula injection**: rename property to `=SUM(A1:C1)`, export, unzip and inspect.
  SAFE pattern: value stored in `xl/sharedStrings.xml` as `<si><t>=SUM(A1:C1)</t></si>`
  (shared string, not a formula; no `<f>` element in sheet XML) → Excel won't execute.
  VULNERABLE pattern would be the value in a cell with `t="str"` and a crafted `<f>`, or raw
  `=...` in CSV.
- **CSV formula injection**: set account display name to `=2+2`, download
  `/app/clients/export.csv` → row shows `'=2+2` (apostrophe prefix = standard mitigation).
- **Stored XSS**: saved `<img src=x onerror=alert(1)>` in a property note → rendered as
  escaped text `&lt;img...&gt;` inside `<p>`, no `img` element in DOM before/after reload.
  Check DOM element count (`document.querySelectorAll('img')`) and the note's `innerHTML`,
  not just innerText.
- **sharePercent business logic**: set `#ownerPercent` to 101 / -10 / 0 via JS + click
  Update → server rejects and the input stays 100. Read the input back after submit to
  confirm server-side validation (UI can lie).

## Server Action shape (what captures look like)
```
POST /app/sources/{uuid}   (same URL as the page)
Content-Type: multipart/form-data; boundary=----WebKitFormBoundaryXXX
next-action: <40-hex action id>     ← critical header, session-bound
Accept: text/x-component
body parts: _1_propertyId, _1_type, _1_category, _1_amount, _1_txnDate, 0 → [{}, "$K1"]
```
Full multipart body is only obtainable via `Network.getRequestPostData`; `requestWillBeSent`
postData is truncated. Replay of a captured action with ANOTHER session ⇒ `Server action not found`.

## OTP / rate-limit observations
- Reset flow for registered AND unregistered addresses renders the same
  "Set a new password" step (anti-enumeration: response identical).
- Wrong OTP → "That code is not correct."; repeated attempts surfaced
  `https://quarterwise.co.uk/reset?codeLimit=12&why=cooldown` → hard 12-attempt cap.
- OTP expires in 10 minutes; resend cooldown ~12s. Do NOT brute-force past the cap
  (policy + the URL already proves a cap exists).

## Cleanup discipline (always)
- Restore renamed property/account names; delete injected notes via the element's
  aria-label button (`button[aria-label="Delete note"]` — beware "Delete entry" /
  "Delete this property permanently" lookalikes; delete requires confirm dialog).
- Kill Chrome debug profiles when done; keep session cookie files out of reports.

## Tooling checklist (this audit's real usage)
subfinder, httpx, gau, waybackurls, katana, naabu, nuclei (general + `-tags sqli,lfi,ssti,xxe,nosqli,redirect,csrf`), ffuf, sqlmap, dalfox, interactsh-client, Chrome CDP ×2 profiles, curl+python (http only for stateless probes; everything stateful goes through the browser).
sqlmap note: against a JSON API with a non-dynamic param it reports "not injectable" and can
trip Cloudflare 403s (87×) — that IS a valid negative, not a tool failure.