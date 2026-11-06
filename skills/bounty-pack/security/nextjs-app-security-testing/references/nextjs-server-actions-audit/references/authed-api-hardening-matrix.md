# Authed API + MFA hardening matrix (observed results, reusable as expected-values)

From a full VDP engagement against an authed Next.js tax app (2026-09). Use the tables as a
checklist of what to probe and as the "expected" column when a target looks similar. Numbers
are what that target did — treat them as calibration, not as rules the next target must obey.

## Public API (`/api/v1`-style, bearer key)

| Probe | Observed | Note |
|---|---|---|
| No key / junk key / key+1 char | 401 `missing_key` / 401 `invalid_key` | key parser is strict, no prefix matching |
| Key with surrounding whitespace, or bare key without `Bearer ` | accepted | parsing leniency, not reportable alone |
| Revoke in UI → reuse key | immediately 401 | revocation is effective; keys stored hashed |
| Source id from another account (random uuid) | 404 `source_not_found` | no BOLA on read *or* write |
| Path traversal / null byte / oversize id | 400 / 400 / 404 | |
| Category not valid for source type | 422 `invalid_category` | whitelist runs — so a category that IS accepted is a deliberate product decision, report it as such |
| amountPence 0 / negative / float / "100" / 1e18 | 422 | |
| Impossible dates (2026-02-30, 0000-00-00, 9999-12-31, free text) | 422 | |
| `[]` / 501-item array / >500-char description | 422 `empty_body` / `too_many` / `invalid_transaction` | |
| SQLi + traversal payloads in sourceType / cursor / from / to / limit | 422, no timing anomaly, no error leakage | |

## Idempotency on a client-supplied reference id

| Case | Observed |
|---|---|
| two different refs in one array | created 2 |
| SAME ref twice inside ONE array | created 1, deduplicated 1, `existing` points at the same id |
| same ref in a later request | 201 then 200 (`created: 0`), original row/amount preserved even if the retry sends a different amount |
| 8 concurrent posts, one ref | exactly one 201 |
| same ref across two sources of one account | deduplicated (matches documented "in the account's books") |
| empty ref / >180 chars / control chars | 422 (the 180-char cap was NOT in the OpenAPI doc) |
| quote + SQL-ish ref | accepted, echoed back JSON-escaped |
| ref case | case-SENSITIVE: `IDEM-CASE` ≠ `idem-case` |
| ref with leading/trailing spaces | NOT trimmed → `" ref "` ≠ `"ref"` (double-import risk from messy spreadsheets) |

## Rate limiting

- Response carried `x-ratelimit-remaining` (max seen 120) but the documented
  `429 rate_limited` was never observed.
- A SLOW loop proves nothing (window refills): 120 requests over 50s (~143/min) → zero 429.
- FAST burst is the decisive test: 140 parallel in 3.9s (~2,163/min) → 140 × 200, no 429,
  no `Retry-After`. Header value lagged (99–107 mid-burst, 37 after 5s, 119 after 15s).
- After the cumulative load Cloudflare returned `Error 1010` for ALL API traffic from that
  IP for a while, legitimate calls included. Blunt edge block ≠ per-key quota; note both.

## Document store / upload

| Probe | Observed |
|---|---|
| filename `../../..//evil.png` | sanitised to basename |
| HTML bytes declared `image/png` | stored, served as `image/png` + `nosniff` → no render (check BOTH headers before calling it clean) |
| ~11 MB when copy claims 10 MB | rejected |
| fetch without session | 307 → login |
| fetch with another account's session | 404 |
| `.html` / `.svg` | refused (accept-list + server validation) |
| AI scan endpoint | upload-only (no URL param → no SSRF), rejects non-images, does NOT persist the scanned image |
| UI delete | `button[aria-label="Delete document"]` — check for it so you can restore state |

## Stored-content rendering

- HTML/JS in a description or in an API key label → rendered as TEXT (escaped), no injected
  element, no event. Confirm by querying for real `img/script` nodes, not by grepping HTML.
- Formula payloads (`=1+1`, `=cmd|'/C calc'!A0`, `@SUM`) → XLSX cells stay string-typed;
  a `format=csv` adviser export applied an apostrophe guard (`'=1+1`). Verify the guard by
  putting the payload in a field YOU control (e.g. the account name) and re-exporting.

## MFA (see also the matrix in SKILL.md)

| Probe | Observed |
|---|---|
| half-auth → `/app`, `/app/account` | 307 → `/login` |
| sensitive action with wrong code | refused, state unchanged (server-side) |
| wrong codes until break | 5th → 15-minute lockout |
| fresh login + correct code during lockout | still refused → account-level counter |
| one code reused for login + sensitive action | second use rejected (re-run with a changed VALUE to be sure) |
| "Forgot MFA?" | 24h-delayed disable + email notice; do not trigger on a vendor account |
| API key during MFA lockout | still works — MFA covers interactive login only |
