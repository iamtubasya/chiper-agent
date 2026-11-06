# Multi-tenant SaaS authorization matrix (reusable)

Generalised from a UK accounting-SaaS engagement (2026-10) where every row below was run against
two own tenants + one low-privilege identity + an own OAuth app. All rows are cheap; the value is
that they are *systematic* and each has an expected-secure answer, so a deviation is unambiguous.

## Setup that makes the probes real

- **2 own tenants** (A, B) — one of them disposable, because brute-force/throttle probes lock accounts.
- **1 low-privilege user inside A** (invite → accept → set password). This is what turns "can a user
  do X" into a fact.
- **Your own OAuth app** registered on the target's developer portal, so you can mint a token per
  identity. Mechanics that worked: hit `approve_app`, and capture the callback URL from the response
  `Location` header / a `request`+`response` listener — Playwright `route` interception can miss the
  redirect — then exchange the code at the token endpoint with HTTP Basic `client_id:client_secret`.
  Re-issue per identity; a permission change in the user record takes effect on an existing token.
- If login is email-OTP, wire IMAP so account minting + re-login is scripted (`email-gated-signup-harness.md`).

## The matrix

| # | Probe | How | Expected-secure |
|---|---|---|---|
| 1 | BOLA per resource type | create objects in B, `GET /<res>/{B_id}` with A's token — contacts, invoices, credit notes, estimates, bills, expenses, projects, tasks, timeslips, price lists, users, attachments, and any NEW sub-resource endpoint | `404` for every one |
| 2 | Session-based IDOR | same object ids in the **other tenant's web UI** (not just the API) | `404` / "not allowed" page |
| 3 | BFLA | low-priv identity against every privileged collection | `403` on all |
| 4 | Field-level filtering vs real leak | fetch the SAME object as owner and as low-priv | 200 + **reduced representation** = by design. Only a *full* record for the low-priv user is a finding |
| 5 | Permission escalation | (a) low-priv raises its own `permission_level`; (b) it creates a user with a higher level; (c) it demotes/changes/deletes the owner | (a) 200 but **clamped**; (b) created user **clamped to creator's level**; (c) 403 |
| 6 | Tenant-key mass assignment | `company_id` / `account_id` / `subdomain` / `id` injected into `PUT /company` and into resource create | unknown attrs rejected/ignored; objects stay in the authenticated tenant |
| 7 | URL / verb / header authz mutation | trailing slash, `.json`/`.xml`/`.js`, `%2F`, `%00`, `;`, case, `//`, dot segments, `HEAD`, `OPTIONS`, `X-HTTP-Method-Override`, `_method=`, `X-Original-URL`, `X-Rewrite-URL`, content-type swap | all still 403/404. **Send each mutation to the forbidden path** — pointing the override header at a permitted path returns 200 and proves nothing |
| 8 | Shadow API | documented + plausible undocumented paths (`/admin`, `/internal`, `/debug`, `/webhooks`, `/events`, `/audit_log`, `/api_keys`, `/me`, `/session`) | 404; only documented resources answer |
| 9 | Signed-URL tampering | decode the thumbnail/asset token, keep the signature, swap the object key / zero the signature / change the bucket | 403 unless the exact signed URL is used |
| 10 | Accounting / domain integrity | force a terminal state without its triggering event; unbalanced manual journal; over-reconcile a credit note; write into a "locked"/"closed" period | rejected — and re-check against a **derived artefact** (balance sheet / trial balance), not just the status code |
| 11 | Auth throttle threshold | N wrong passwords from one IP, then the correct one | lockout exists; the *number* is the finding only if it is unusable (single digits) or absent |

## Newly-added endpoints are the best row-1 target

Endpoints added in the last release notes (here: a new "…attachments" sub-resource, a new CIS/plan
resource) have the least accumulated review. Diff the changelog page, then point the whole matrix at
the new paths first.

## Verify before reporting — three near-misses from this engagement

1. **A 200 on a "forbidden" resource.** Low-priv user could `GET /contacts` while the UI denied
   `/contacts`. Looked like BFLA. Owner vs low-priv comparison showed the low-priv response omitted
   email/phone/address/balance → permission-aware field filtering, by design. Always do row 4 before
   calling row 1/3 a finding.
2. **Writable state inside a locked/closed period.** Draft documents could be created/edited/deleted
   inside a locked period while expenses/bills were refused. The ledger check settled it: drafts do not
   post, and *posting* into the locked period was refused (`… is locked`). Coherent, not a bug.
3. **"No rate limiting."** Six consecutive failures showed no throttle → tempting finding. At the
   sixteenth, the correct password returned "too many attempts": the lockout existed, the sample was
   just too short. State the bound ("no throttle observed in N attempts") instead of asserting absence.

## Reporting shape that survives review

Per row: the exact request, the exact response, and the *expected-secure* answer it was measured
against. Keep the disproven candidates in the report too — a documented near-miss is evidence of
method, and it stops the next reviewer from re-raising the same false positive.
