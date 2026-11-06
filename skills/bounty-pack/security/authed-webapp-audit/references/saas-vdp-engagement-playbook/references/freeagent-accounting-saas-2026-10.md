# FreeAgent.com (UK accounting SaaS) — VDP engagement, 2026-10-02

Program: FreeAgent Responsible Disclosure (`/.well-known/security.txt` → `/features/disclosure/`).
In scope: `signup.freeagent.com`, `<your-trial>.freeagent.com`, `dev.freeagent.com`,
`api.freeagent.com`, `api.sandbox.freeagent.com`, iOS/Android apps.
Out: `www.`, `support.`, `community.`, `api-discuss.`, `engineering.`, apex.
Result: **0 exploitable findings, 31 verified negatives, 1 candidate disproven twice.**

## 0. The program FORBIDS scanners — that overrides the launcher

FreeAgent's policy bans automated vulnerability/scanning tools outright ("IP bisa diblokir
permanen") plus mass brute force and account enumeration.  So: **no**
nuclei/ffuf/gobuster/dalfox/sqlmap/subfinder/naabu/arjun/CORScanner against any FreeAgent host,
**no** `audit-run-all.py`, and **Phase 0D (`verify-tool-usage`) is N/A-BLOCKED, not "passed"** —
its scanner evidence cannot exist without breaking the rules.  Write that in one line in the
report and then enumerate the manual/targeted work instead.  A negative result produced this way
is still a defensible deliverable: 31 rows with on-disk evidence beats a scanner dump.

## 1. Auth rig — login is password + e-mailed 6-digit code

- `login.freeagent.com/login` fields: `#login_email`, `#login_password`, submit `#login_submit`
  (the ids are **not** `#email`/`#password`; a first attempt with those times out).
- After submit you land on `<tenant>.freeagent.com/two_factor`: code field
  `input#two_factor_code`, submit `input[name=commit]`.
- The code arrives by e-mail → fetch via IMAP and filter on the **exact To: address**. Use
  plus-addressing for extra personas (`RESEARCHER_USERNAME+emp@gmail.com`) — one mailbox, many identities.
- Throttling exists: after ~10 wrong codes the page returns
  "Login attempt failed too many times".  Record it as a *control that works*.
- `permission_level 0` ("No Access") users cannot log in at all —
  "You don't have access to this account."  A blocked-login is a control, not a bug.

## 2. Getting an API token for N identities (own app)

1. dev.freeagent.com/apps → create/own app; `OAuth identifier` = client_id; the client **secret
   is shown once** — if lost, "Generate new secret" reveals a new one (old can be revoked).
2. `GET https://api.freeagent.com/v2/approve_app?client_id=…&response_type=code&redirect_uri=…&state=…`
   → always bounces through `login.freeagent.com` first, then lands on
   `<tenant>.freeagent.com/app_approvals/new` → click **Approve**.
3. The 302 to `https://localhost:8443/callback?code=…` never completes (no local TLS server) —
   capture it with a Playwright **request/response listener** matching `code=` on a non-freeagent
   host. Route interception alone was unreliable here; the response `Location` header is enough.
4. Exchange: `POST /v2/token_endpoint`, HTTP **Basic** `client_id:client_secret`,
   body `grant_type=authorization_code&code=…&redirect_uri=…` → `access_token` (1 h) +
   `refresh_token`. Do the login + approve in ONE browser session per identity.
5. Repeat step 2–4 per tenant → one token file per tenant; a tiny client that takes the token
   path from an env var (`FA_TOKEN`) keeps the matrix scripts readable.

## 3. Two-own-tenant BOLA matrix (the method that matters)

Create the object in tenant **B**, then fetch it with tenant **A**'s token and with A's web
session.  Both tenants are yours, so no victim and no enumeration — just B's own ids.

Covered and all 404 (i.e. correctly scoped): contacts, invoices, credit notes, estimates, bills,
expenses, projects, tasks, price-list items, users, attachments.  Web-app session IDOR
(`/contacts/{B_id}`, `/invoices/{B_id}`, …) also 404.  Unauthenticated API → 400
`Authorization HTTP header required`.  Dev dashboard `/apps/{other_id}` → 404.

Do the same for **documented sibling ids**: `/v2/users/{other_user_id}`, and the
`/v2/attachments/{id}` object behind an expense receipt (receipt B on B's expense, read with A).

## 4. False positive #1 — permission-filtered 200 (killed a would-be finding)

A "Time"-only user (`permission_level 1`) could `GET /v2/contacts` → **200**, while the web UI
shows "Sorry, you're not allowed to see that page" for `/contacts`.  Looked like BFLA.

Disproof: request the **same object with the owner token**.  Owner receives the full record
(`email`, `phone_number`, `address1`, `town`, `postcode`, `account_balance`, …); the low-priv
response carries only url / org name / first / last / timestamps.  The API is *permission-aware*
and shapes fields by level — deliberate, not broken.

**Rule: a 200 on a resource the UI hides is only a finding after an owner-vs-low-priv field
diff.** Same trap as the SPA catch-all: verify the *content*, not the status code.
Corollary worth recording as a control: `permission_level` 1 correctly 403s invoices, bills,
expenses, bank, journal, VAT, price lists, capital assets and `/v2/users`; only `contacts`,
`projects`, `tasks`, `timeslips` (the "Time" set) and basic `/v2/company` stay open.

## 5. False positive #2 — account lock lets DRAFTS through (killed by the ledger)

With a user account lock active (`PUT /v2/account_locks {"account_lock":{"locked_to_date":"…"}}`
→ 204; **PUT, not POST**; delete is `DELETE /v2/account_locks`, no id), writing dated *before*
the lock:

| operation | result |
|---|---|
| POST expense / POST bill dated in the lock | 422 `dated_on is in a locked period` |
| POST invoice (draft) dated in the lock | **201 — allowed** |
| PUT edit / DELETE of a draft invoice in the lock | **200 — allowed** |
| re-date a **posted** invoice into the lock | 422 `dated_on is in a locked period` |
| `mark_as_sent` on an invoice dated in the lock | 403 `Invoice is locked.` |
| `mark_as_sent` on a credit note dated in the lock | 403 `Credit note is locked.` |
| limited user (level 4) — GET/PUT/DELETE `/v2/account_locks` | 403 (only Full Access) |

The 201/200 rows look like a lock bypass.  They are not: **drafts do not post to the ledger**.
Confirm with the report endpoint — `GET /v2/accounting/balance_sheet?as_at_date=<lock date>` was
byte-identical before and after (£20 total assets, no debtors line), because every document
created was still `Draft`.  The lock is an *accounting* lock: it blocks everything that
**posts** into the closed period and allows unposted working copies.

**Rule: for an accounting/finance target, "writable in a locked period" is not a finding until a
derived report (balance sheet / P&L / export / aged debtors) moves.**  Same shape as §4g — drive
the product's own computed number.  Also note `latest_lock_date` is ~7 days in the past, so a
lock request with today's date returns a confusing 404 — read the bounds first.

## 6. OAuth `redirect_uri` — test it at the DECISION POINT, authenticated

`api.freeagent.com/v2/approve_app` always forces a fresh login, so unauthenticated probes only
prove "not validated yet".  The validation happens on `<tenant>.freeagent.com/app_approvals/new`.
Drive that with a live tenant session, 13 variants: registered exact, second registered, suffix
path, `…/callback/../../evil`, query append, fragment `#@evil.example.com`, subdomain suffix
`localhost:8443.evil.example`, `@`-trick, evil host, `http` downgrade, port swap, backslash,
omitted (defaults to first registered).  Result: only exact registered URIs accept; everything
else → "The redirect URI is invalid for this app."  Delivery of the code was watched with a
request listener — code only ever went to the registered host.

Also checked: production token against `api.sandbox.freeagent.com` → 401
`Access token not recognised` (environments isolated).

## 7. Invite / activation token binding (`/activate/<token>?user=<id>`)

It is an **unused token + a modifiable `user` query param** — classic ATO shape.  The page renders
the "Choose a new password" form for *any* `user` value, including a non-existent id, which is
just render-before-validate and proves nothing.

Decisive, non-destructive method: submit the form with `user=<owner of a DIFFERENT own tenant>`
plus a throwaway password, then **try logging in as each candidate** with that password.
Result: only the token's real owner accepted it; the other tenant was rejected.  So the param is
ignored server-side (the hidden field is `code=<token>`; the form posts to `/reset_password`) —
token is bound, no ATO.  Recording the *disproving* login attempt is what makes this a credible
negative.

## 8. Other results worth not re-deriving

- Stored-XSS: HTML in contact org-name / invoice item description → escaped (`&lt;img`), no DOM
  payload nodes, no dialogs.  E-mail sanitiser strips `<script>`/`<a>`, keeps `<br>`; `{{7*7}}`
  and `${7*7}` render literally (no SSTI).
- Headers: CSP with nonce + `frame-ancestors 'self'`, `X-Frame-Options: SAMEORIGIN`, HSTS,
  `nosniff`; `_fa_session_2` = `Secure; HttpOnly; SameSite=Lax`.
- `*.freeagent.com` is wildcard DNS (a random name resolves too) → no takeover signal.
- Trial subdomains are `<slug>.freeagent.com`; the signup "activation" mail's real link is
  `https://signup.freeagent.com/accept/<40-hex>` (a naive "activ|confirm" link regex first picks
  the marketing footer — match `/accept/` explicitly).
- Setup wizard field names: `company[name]`, `company[address1..3]`, `company[town]`,
  `company[postcode]`, `company[country]`, the industry combobox is `#company_business_category_id`
  (the hidden `company[business_category_id]` gets the numeric id), and accounting dates are
  `company[company_start_date]` / `company[first_accounting_year_end_date]` /
  `company[freeagent_start_date]` in `dd Mmm yy`, typed then `Escape` to close the datepicker.
- Credit notes require a **negative** total before `mark_as_sent`
  ("This credit note does not have a negative total value").

## 9. Tooling pitfall that cost the most time: MSYS eats `/<path>` arguments

Running `python fa_api.py GET /v2/company` from the Windows git-bash terminal made MSYS convert
`/v2/company` into a **drive path** (`C:/v2/company`), which concatenated onto the base URL and
produced a bogus host `api.freeagent.comc` — surfacing as
`socket.gaierror: [Errno 11001] getaddrinfo failed` from both `urllib` and `requests`, while
`curl` and a plain `socket.getaddrinfo()` in a fresh process worked fine (misleading "DNS is
broken" conclusion; a "DNS warm-up retry" was even added before the real cause was spotted).

Fixes, in order of preference:
1. `export MSYS_NO_PATHCONV=1` in the session before such calls, **or**
2. keep the URL path inside the script (arg = method + short token, path built in Python) —
   which is also what makes a matrix script immune;
3. when a script works but a CLI one-liner of the same code fails, **print the constructed URL**
   before blaming the network.

## 10. Reporting shape for this operator

Close the engagement with: scope constraint stated, results table (vector → what was done →
Pass/negative → evidence path), the disproven candidates with *how* they were disproven, an honest
`BELUM diuji` block (mobile apps, practice API, HMRC flows, bank feeds, race conditions,
VAT/rounding, payments/bank-transaction explanations, recurring invoices), and the plain-language
"no report will be filed because nothing qualified" conclusion.  Deliverable that worked:
`AUDIT-REPORT.md` + `PHASE_LOG.md` + `findings.json` (0 findings) + `evidence/` (68 files).
