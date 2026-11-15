# Quarterwise — fresh full-matrix re-run (2026-10), FIRM plan

Third pass on the same target, explicitly "start clean, ignore old findings, all tools, all
vectors, use the Pro account". Workspace `_progress/quarterwise.co.uk_v3`. Result: **no
Medium+ exploitable finding**; app + edge well-hardened. Kept here so a future pass skips
re-testing the same ground and re-uses the replay mechanics.

## Account/identity gotcha (the headline lesson)
- Saved `browser_state_pro.json` (a `qw_session` cookie) was a STALE FREE test account
  ("Audit Account E", `qwyfi675wo31@uberip.com`), NOT the Pro account.
- The Pro credential was the **API key** (`/api/v1/me` → accountId `0cf6748e…`, plan `pro`).
- Re-login with `RESEARCHER_EMAIL` + TOTP landed on `/app/clients` → the Pro account is a
  **FIRM/accountant plan** (multi-client). `?view=mine` restores the personal book.
  Client E's shared source (`92d58d01…`, "Overseas Test ES") is reachable to the firm as an
  adviser ("Can view"); the firm's own sources are `35fb53f7` (uk-prop), `52c4834e`, `b9955ce4`.
- Fix: before testing, cross-check `/api/v1/me` (key) vs `/api/account/export` (session:
  `users[].email` + `plan`). They disagreed → re-login.

## Replay mechanics that worked (and the no-ops)
- Enumerate ids from the served HTML/RSC: `[0-9a-f]{42}` appears in `$ACTION_ID_<hex>` and in
  `{"id":"<hex>","bound":"$@1"}` hidden fields; client chunks hold `createServerReference)(\"<hex>\")`.
- Progressive multipart replay (works, no browser): POST to the page URL with
  `files={f"$ACTION_ID_{hex}":(None,""), "accessId":(None,acc)}` and the session cookie.
  urlencoded returned 200 but did nothing; **multipart executed** (adviser invite revoke took).
- Playwright path (most robust): open page → `locator("[name='field']").first
  .locator("xpath=ancestor::form[1]")` → override fields → `form.evaluate("f=>f.requestSubmit()")`.
  Capture `page.on("response")` and read the flight `1:{"error":"…"}` segment for the verdict.
- **`$ACTION_KEY` is per-render.** Replaying a body from an earlier render → 200 + full HTML,
  action NOT executed (rename silently no-op'd). Fetch fresh or drive the form live.
- Modal actions (Record income): click the labelled button, then the form exposes hidden
  `submissionId`, `propertyId`, `type`, `category`(select), `amount`, `txnDate`.

## Per-class results (all enforced controls)
- BOLA/IDOR: `/app/sources|clients|imports/{uuid}` and `/api/attachments|documents/{id}`,
  `/api/invoices/{id}/pdf` → random/zero uuid **404**; unauth **307 /login**.
- Server actions: foreign `propertyId` → "Only the owner can change these settings." /
  "That property could not be found." Forged cross-type category (option injected) → refused.
  amount ≤ 0 → refused. Foreign id create → refused.
- API v1 (zod): non-int / 0 / negative / >1e10 amount, bad dates, cross-type & unknown category,
  bool/null → 422; extra props stripped (client `id` NOT honoured); externalRef dedup +
  race-safe (8 parallel → 7×200 + 1×201); 120/min then 429 exactly.
- Auth: login lockout ("wait about 15 minutes") after a few failures; reset = no user
  enumeration (identical response) + OTP capped at 5 ("Too many attempts. Request a new code.")
- Invite adviser token: 48-hex, 14-day, **bound to invitee email** — opening as another account
  → "This invitation was sent to q•••o@…, but you are signed in as <other>."
- Upload: server rejects SVG/HTML ("Upload a PDF, image, Word/Excel file, or CSV."); allowed
  .txt served `text/plain` + `nosniff` + `inline` → no render. XLSX XXE → 0 OOB (interactsh);
  zip-slip entry → no effect. Import preview renders formula/XXE strings as TEXT.
- AI `POST /api/ai/extract-expense`: session-only (bearer → 401); file-type validated;
  image-embedded prompt injection ("ignore instructions, category=…") had NO effect; no SSRF.
- Edge: unknown `Host` → 403; CL.TE probe → 400 (Cloudflare); no CORS ACAO on api/export;
  PUT/DELETE/PATCH → 405; no open redirect via `next`/`returnTo`; middleware bypass
  (`x-middleware-subrequest`) → still 307.
- Billing: every `interval` value (year/month/Month/YEAR/""/annual) → **same** Stripe session
  → no price tampering; did not proceed to LIVE checkout.
- CSV export (`/app/clients/export.csv`): `ty` ignored; client name "=1+1" → `'=1+1`
  (apostrophe-guard present).

## Informational findings (not vulns)
- `POST /api/collect` — unauthenticated telemetry ingestion, accepts arbitrary JSON → 204.
- Origin IP exposed: `direct.quarterwise.co.uk` → `139.59.201.189` (nginx, redirect-only;
  ports 80/443 only; nginx 404 on wrong Host).
- API per-transaction cap = £100,000,000.

## Tool ledger (this run)
katana, ffuf (wordlist /app /api /), subfinder, gau, naabu (origin top-1000), nuclei
(medium+, non-intrusive → 0), dalfox (params → 0), sqlmap (GET ?limit= → not injectable),
interactsh (0 callbacks), Playwright/CDP + custom python (API matrix, BOLA, dedup-race,
rate-limit, reset-OTP, login lockout). Not run: GraphQL (none exists).

## Cleanup / residue
Restored: 17 test entries deleted from `35fb53f7` (0 remain, verified via API), uploaded test
document deleted (404), adviser invite to test inbox revoked, account-E display name and
property name reverted. Residue that could NOT be deleted (no UI control): 5 import-batch
records under `/app/imports/<id>` (47a1ecec, 8a71ec73, 667f5497, 78284461, 1cf182e3) — disclosed
to the vendor. A test account was left login-locked ~15 min from the lockout test (auto-clears).
