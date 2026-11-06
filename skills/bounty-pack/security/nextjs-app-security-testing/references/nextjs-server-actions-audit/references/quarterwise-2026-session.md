# Quarterwise 2026-09 — full VDP engagement numbers

Concrete data from a complete authorized VDP test of quarterwise.co.uk (Malden Ltd).
App = Next.js App Router + Server Actions + RSC; Cloudflare front; MFA = TOTP authenticator.

## Lockout matrix (account-level, verified)

| Flow | Wrong attempts before block | Message / cooldown |
|---|---|---|
| Login wrong password | 11 | "Too many attempts. Please wait about 15 minutes." |
| Login MFA (TOTP) | 6 | blocked; fresh login also blocked → account-level |
| MFA recovery code | 6 | "Too many attempts. Request a new code." persists across sessions → account-level |
| Reset-code resend | server-side 58s cooldown | "Send a new code in 58s" (display-only `codeLimit` param changed hint text only) |

Takeaway: session rotation does NOT beat account-level OTP lockout. Do not keep hammering.

## Unknown /api path status-code matrix (Next.js quirk)

| Method | Body | Result |
|---|---|---|
| GET / PUT / OPTIONS / TRACE | none | 404 |
| POST | none / `{}` / `[]` / text/plain | 404 |
| POST | multipart/form-data (file field) | **500 "Internal Server Error" text/plain** (e.g. /api/import, /api/does-not-exist-xyz) |
| POST | multipart to existing route /api/documents/upload | 405, `Allow: GET, HEAD, OPTIONS` |

Vendor initially said "unknown paths return 404 across GET, POST, PUT, OPTIONS" — the 500
only appears for POST+multipart. Not a finding; a hygiene inconsistency.

## RSC escaping false-positive (XSS)

Reflected param `why=<script>alert(1)</script>` appeared in raw HTML as
`\u003cscript\u003ealert(1)\u003c/script\u003e` inside `self.__next_f.push(...)` flight data.
DOM check: zero executable img/script/svg, marker only in flight string → NOT XSS.
Lesson: grep-based reflection checks must account for `\u003c` / JSON escaping, and must
confirm in the rendered DOM, not the raw response body.

## Duplicate-submit race (the one genuine finding, Low)

- Same-tick `button.click(); button.click();` in one `Runtime.evaluate` → 2 identical
  ledger rows (verified via /api/account/export: amountPence 5555/6666/7777 ×2, ext=None).
- 150 ms-apart double-click → 1 row (modal closes). → needs scripted/replay trigger.
- Root cause: no idempotency key on the UI server action (public API v1 dedups on
  externalRef). Pitched as missing-idempotency, Low.

## Other verified-negative coverage (so a future session can skip repeating)

- IDOR/BOLA across 3 accounts: page, child-object, export, import-batch, accessId,
  role-swap, co-owner→owner, viewer→contributor → all server-side blocked.
- Stored XSS: notes, property name, reminders, import CSV/XLXS descriptions → escaped
  (`&lt;...&gt;`), 0 executable elements.
- CSV/XLSX formula injection: CSV prepends `'`; XLSX stores in sharedStrings (never `<f>`) →
  Excel won't execute.
- CSRF: same-body same-cookie with `Origin: evil` → 500; txn count unchanged.
- Auth gates: change email/password require current password + TOTP; NINO save requires
  valid TOTP (server-side, verified by reload oracle); invite tokens bound to invited email.
- User enum (signup, forgot-password): identical responses; timing 4.02s vs 4.03s → none.
- Open redirect 24 variants, Host/X-Forwarded-Host reset poisoning (500), /_next/image SSRF
  (404 — optimizer not routed), HTTP smuggling TE probe (CF 400), cache deception (404),
  CVE-2025-29927 middleware bypass (307→login), method-override/CT confusion (404) → negative.
- sqlmap L1-2 on authed export param: not injectable. nuclei incl. sqli/lfi/ssti/xxe/
  nosqli/redirect/csrf tags: only TLS 1.0/1.1 weak (info). dalfox/fuzz/interactsh: 0.

## Cookie-oracle cheat sheet (read auth state from Set-Cookie)

| Cookie | Meaning |
|---|---|
| `qw_pending` | in-progress flow (signup / reset) — NOT authenticated |
| `qw_session` | authenticated |
| `qw_reset` | password-reset flow in progress (separate jar from login) |

Cheap state signals: protected route → `307` to `/login` = auth enforced; the SAME route →
`404` while authenticated as a *different* user = correct owner-scoping (a clean negative,
not a bug). Same route → `404` before accepting a pending invitation, `200` after = the
invite `Accept` really persisted.

## Two-session isolated harness (Camofox, no CDP)

`POST localhost:9377/tabs/open` with `{"userId":"hermes"}` (account A) and a second call
with `{"userId":"hermes2"}` (account B) → isolated cookie jars. Verified: after logging
in as A on `hermes`, a `hermes2` tab still rendered the logged-OUT public header.
**`sessionKey` does NOT isolate** — different `sessionKey` values shared one jar. Tabs are
reaped after 300s idle (chain open → sleep → act). Submitting a form React-style from a
page tab needed `f.requestSubmit()` on the matched `<form>`; plain `.submit()` trips
React's "unexpectedly submitted" guard, and plain `click()` on a duplicate `Log out` ref
logged the *other* account out.

## Raw-HTTP Server Action replay (worked end-to-end, no browser)

All four required: `next-action: <hex>`, `Accept: text/x-component`,
`next-router-state-tree: <URL-encoded JSON>`, multipart FormData with `_<i>_<argName>`
fields + `0=["$K1"]`. Consequences observed:

- Login over plain HTTP works: `requestLogin` → `303` + `Set-Cookie: qw_session`.
- Skipping `next-router-state-tree` ⇒ 500 for **every** action and every payload.
- The URL-encoded-arg theory was never needed — plain `_1_propertyId=<uuid>` style fields
  worked for many actions; four hidden-field-style actions (`updateOwnerShare`,
  `updateSourceSettingsAction`, `deletePropertyAction`, and `removeShare`) kept returning a
  constant digest each ⇒ untestable via harness, reported as such rather than as "passed".
- **Lesson:** the SAME action can behave differently for different FormData shapes — do the
  legit-session control on a resource the account genuinely owns, and only then classify.
  Illusory "authz holds" results came from digest-shaped construction failures that were
  never validated against a positive control.

## Action inventory (49 base + 35 filing/annual, mapped by category)

- **auth:** `startSignupEmail`, `submitSignupEmailCode`, `submitSignupPassword`,
  `submitSignupName`, `requestSignup`, `requestLogin`, `requestPasswordReset`,
  `submitPasswordReset`, `resendResetCode`, `submitLoginMfa`, `sendLoginSms`,
  `sendAccountSmsCode`, `confirmMfaDisable`, `cancelMfaDisable`, `resendMfaDisableCode`,
  `submitCode`, `logout`
- **source:** `addPropertyAction`, `addSeSourceAction`, `deletePropertyAction`,
  `addTransactionAction`, `deleteTransactionAction`, `updateTransactionAction`,
  `updateSourceSettingsAction`, `updateInvoiceSettingsAction`, `createInvoiceAction`,
  `markInvoicePaidAction`, `markInvoiceUnpaidAction`, `deleteInvoiceAction`,
  `addNoteAction`, `updateNoteAction`, `deleteNoteAction`, `addDocumentAction`,
  `deleteDocumentAction`, `deleteAttachmentAction`, `addReminderAction`,
  `updateReminderAction`, `toggleReminderAction`, `deleteReminderAction`,
  `registerForeignPropertyAction`, `viewForeignPropertyDetailsAction`
- **sharing:** `inviteShare`, `updateSharePercent`, `updateOwnerShare`, `removeShareAction`
  — `removeShare`/`updateSharePercent`/`inviteShare` require a `shareId` **plus** a current
  MFA/share code ("Sharing gives someone else sight of these books, so it needs a current
  code"). Co-owner UI hides owner-only settings ("Only the owner can change settings for
  this property") **and** the server enforces it.
- **HMRC:** `saveNino`, `syncBusinessesAction`, `setPeriodTypeAction`,
  `viewBusinessDetailsAction`
- **filing/annual (35):** `triggerCalcAction`, `confirmCalculationAction`,
  `finalDeclarationAction`, `viewCalculationAction`, `listCalculationsAction`,
  `amendPrepareAction`, `amendReturnAction`, `checkFinalObligationAction`,
  `confirmOtherIncomeAction`, `submitAnnualAction`, `seAnnual{View,Submit,Delete}Action`,
  `foreignAnnual{View,Submit,Delete}Action`, `bsas{Trigger,View,Adjust}Action`,
  `periodsOfAccount{View,Submit}Action`, `ladr{View,Disapply,Withdraw}Action`,
  `loss{View,Submit,Delete}Action`, `tla{View,Submit,Delete}Action`,
  `cis{View,Create,Delete}Action`, `annual{View,Delete}Action`
- **No API-key action exists** — key creation is gated server-side to Pro; every candidate
  key route (`/api/v1/keys`, `/api/v1/me/keys`, `/app/account/api/keys`, …) returns 404.

## 2FA filing gate — enforced SERVER-SIDE (verified)

`finalDeclarationAction` and `submitAnnualAction` fired from a free, MFA-less owner →
`{"error":"Two-factor authentication is required before connecting or filing with HMRC..."}`.
The UI banner was not client-side theatre. `NINO` save requires a valid TOTP too.

## Plan gates held (all verified server-side)

- 2nd property / 2nd self-employment: rejected ("Your free plan includes 1 property you
  own…"). 12 concurrent `addProperty` → 12/12 rejected, no TOCTOU.
- `/app/other-income` and `/app/imports` render for free accounts *and* import works — but
  CSV/Excel import is in the documented **free** tier, so it is by-design, not a finding.
  Check the vendor's own plan text before calling a reachable feature a gate bypass.

## Negative coverage added this pass

- Password-reset OTP brute force: `/forgot` then `submitPasswordReset` — 5 wrong codes then
  "Too many attempts. Request a new code." (same 5-then-block as signup OTP).
- Share-invite token: `/app/shares/accept?token=<64hex>` — `307` without session; invalid/
  short/SQLi token variants all rejected; response is `no-store`; token accepted twice
  (no single-use enforcement — hygiene, not impactful).
- `dev.` / `mail.` subdomains: 403 nginx on every path incl. `/api`, `/.env`, `/.git/HEAD`;
  `Host`/`X-Forwarded-For`/`X-Original-URL`/`CF-Connecting-IP` all still 403.
- Origin bypass: `--resolve` with SNI against the leaked origin IP (139.59.201.189,
  DigitalOcean) → no response; apex is Cloudflare-locked, `direct.` is a 301 redirector.
- `/fph-echo`, `/admin`, `/api/v1/keys`, `/__nextjs_original-stack-frame` → 404 / catch-all.
- Secrets sweep of all downloaded chunks (sk_live/AIza/JWT/db-URI patterns) → none.

## Pipeline note (audit-pipeline-orchestrator.py on an SPA)

Orchestrator ran 0A–0B fine (4 subdomains; 13 tool-evidence files: sqlmap, dalfox,
CORScanner, gobuster, ffuf, race-checker, graphqlmap, interactsh, nuclei) then sat in
0C-variants for ~40 min fanning payloads at a dynamic Cloudflare SPA root — killed;
state file saved → resumable. **Its tools all target the site root and return nothing
meaningful on an App Router SPA**; the browser-driven, dual-account server-action testing
in this file is the real coverage. Also: the URL list is scraped from page content, so the
orchestrator can end up scanning a third-party URL that merely appeared on the page
(here a `gov.uk` product listing) — filter recon URLs by registrable domain before firing.


- Report PDF (reportlab, no watermark) attached once via Gmail SMTP
  (RESEARCHER_EMAIL app-password from ~/check_basabasi_email.py). Drafts go to
  `[Gmail]/Draf` with `flag_set=MailMessageFlags.DRAFT`; verify after append; delete via
  uid. User rule: send once, verify first, never resend without confirmation.

## Account/mailbox crib from the session

- acc1/acc2/acc3 disposable mail.tm mailboxes (uberip.com), TOTP secret enrolled on acc1
  was `VDV5IWTHKVJHUZEFM25LHFVS4MOALRQ6` (test data only — rotated/expired by now).