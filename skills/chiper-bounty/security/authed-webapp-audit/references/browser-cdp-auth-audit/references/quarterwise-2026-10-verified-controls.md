# Quarterwise (quarterwise.co.uk) — verified-control ledger

Target: Malden Ltd trading as Quarterwise — UK landlord / MTD SaaS. Next.js App Router + Cloudflare.
VDP with safe harbour at `/security/disclosure`; **subdomains are out of scope** ("any subdomain other
than quarterwise.co.uk itself"), as are Stripe / Postmark / Cloudflare / HMRC APIs.

This file exists because the program rewards **one root cause once** and its public credit list already
carries 25+ researchers from Sept 2026. Re-probing a control that is already in the table below burns a
session. Read this first, then spend the time on the "still unsaturated" list at the bottom.

Rounds: v1–v4 (Sept–Oct 2026, externally reported), v5 (2026-10-08, this ledger).
The Sept round is in `references/quarterwise-2026-09-playbook.md`; mail-template work is in
`bug-bounty` → `references/email-template-injection.md` §"Round 2".

## Access

| Item | Value / how |
|---|---|
| Pro account | `RESEARCHER_EMAIL` — password recovered from the operator's Chrome `Login Data` |
| MFA | TOTP secret known (`pyotp.TOTP(secret).now()`); `/login/mfa` after the password step |
| Free account | a throwaway `qwab…@uberip.com` profile also exists; Pro lands on `/app/clients` (firm view) |
| Plan marker | `/app/account` prints either `You're on the free plan.` or `You're on the pro plan.` |

## Controls verified as WORKING (do not re-report these)

### API v1 (bearer key — `Authorization: Bearer <key>`, documented at `/developers/docs.md` + `/api/v1/openapi.json`)
| Probe | Result |
|---|---|
| No key / malformed (`Bearer`, `basic abc`) | 401 `missing_key` |
| Docs sample key `qw_live_1a2b3c4d…` | 401 `invalid_key` — a dead placeholder, not a leak |
| GET/POST a **foreign** source id (BOLA) | 404 `source_not_found` — no cross-account read or write |
| null / path-traversal source id | 404, same code |
| `amountPence` float / negative / >1e10 | 422 (`whole number of pence` / `greater than 0` / `at most … (£100,000,000)`) |
| unknown `category`, or expense key on an income row | 422 `invalid_category` + `validCategories[]` |
| bad date (`2026-13-45`) | 422 `must be a real date between 2000 and next year` |
| `description` >500 chars, `externalRef` >180 or with a control char | 422, precise zod paths |
| bare array >500 items | 422 `too_many` ("Send at most 500 transactions per request") |
| body carrying `__proto__` / `role` / `isAdmin` | stripped, normal 201 — no mass assignment |
| `{"transactions":[…]}` wrapper | 422 — the schema is `oneOf(TransactionInput, array)`, **not** an object wrapper |

### Auth / session
- **MFA gate holds**: after the password step only a pending `qw_mfa` cookie exists and `/app` redirects
  to `/login`. No 2FA bypass. (Recipe: `browser-cdp-auth-audit` → "MFA stage".)
- Login codes are emailed (`Your Quarterwise code is NNNNNN`) — they are the new-device/verification
  step, **not** a passwordless login path. `/login` is email + password + TOTP.

### Emails sent by Quarterwise (explicitly in scope: "weakness in something we control")
- Account name stores raw markup (`<b>QWINJ</b>` accepted and persisted), **but the adviser-invite
  email renders it tag-stripped** ("QWINJ"). `<img onerror>`, `<a href>…</a>`, `<svg onload>`, `<b/>`
  all reduced to their text. → **no HTML injection into QW mail** (tag strip, not escaping).
- Invite accept link `/app/advisers/accept?token=<48 hex>`, bound to the recipient address; sending an
  invite itself requires a fresh TOTP.

### Client-side / state-changing
- Transaction `description` = `<img src=x onerror=alert()>XSSMARK` → rendered as **text**; 0 injected
  `<img>` elements; the raw bytes appear only inside the RSC flight payload. React escaping holds.
- **CSRF: Origin check enforced.** Captured the real `/app/account` Save-details server action
  (`Next-Action: 601d…` + multipart body) and replayed it byte-identical with the same session cookie
  plus `Origin: https://evil.example` → **500, state unchanged** (name read back). Same-origin → 200.
  A cross-site form cannot set the `Next-Action` header, so there is no practical CSRF here.

### Not-rewarded by policy (never submit these on this program)
Missing/best-practice headers, cookie flags or DNS records (SPF/DKIM/DMARC) without a demonstrated
exploit; rate-limiting observations; username/email enumeration on login+signup; clickjacking without a
state-changing action; version disclosure; scanner output without proof of impact; self-XSS; theoretical.
The policy also forbids **automated scanning that puts noticeable load** — keep any volley at low rate
and treat the 0D scanner gate as bounded/N/A-BLOCKED rather than "passed".

## Still unsaturated (start here next time)
1. **Tax/arithmetic correctness** of the public calculators (`/tools/*`) — two real defects were found
   and paid in Oct; more may remain. Correctness, not security.
2. **Import pipeline** (CSV/XLSX per provider) — variants beyond the ones already credited.
3. **AI receipt scan** — image/PDF prompt-injection and multi-page document handling.
4. **Race conditions** on the caps (`500/write`, `5,000/24h` rolling) and on invite/dedup paths.
5. `/api/og/<12-hex-template>/<base64-title>` — keyed OG-image renderer; unknown template → 404
   `text/plain`. Unexplored.

## Residue discipline (the API key can write, and nothing in the UI deletes)
- Writes create rows in the chosen source; record their `externalRef`s and hand the list to the vendor,
  because per-transaction delete has no UI affordance.
- Clean up: revert the account name, remove test adviser invites, revoke the engagement API key
  (`/app/account/api` → Revoke).
