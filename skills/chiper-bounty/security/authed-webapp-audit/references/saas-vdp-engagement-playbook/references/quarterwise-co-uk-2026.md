# Quarterwise (quarterwise.co.uk) — VDP Engagement Notes 2026-09

Concrete evidence and numbers from the full-scope VDP engagement that shaped the class playbook. Researcher-owned accounts only.

## Target

- Next.js (build id `KIbLcwwGlEGXVAGU7Shr-`) + Cloudflare; VDP at quarterwise.co.uk/security/disclosure (Malden Ltd). Scope: main domain + signed-in app + API. Subdomains (dev/direct/mail/www) and Stripe/Postmark/Cloudflare/HMRC out of scope.
- Public API `/api/v1/*` (openapi.json + /developers/docs.md): bearer-key auth on all endpoints; sources/categories/transactions; writes "idempotent on externalRef".

## Test Rig

- Chrome CDP profiles: port 9222 (acc1) / 9223 (acc2), `--remote-allow-origins=*`, separate `--user-data-dir`.
- mail.tm temp mailboxes (uberip.com domain) — acc1 `...@uberip.com`, acc2 + others for cross-user tests.
- acc1 MFA enrolled via authenticator: TOTP secret `VDV5IWTHKVJHUZEFM25LHFVS4MOALRQ6`; generated codes with RFC 6238 python (hmac/sha1/struct).
- Cookie header captured via CDP `Network.getAllCookies` → `recon/cookies_header.txt`.

## Verification Matrix (all own-account, small N)

| Test | Result |
|---|---|
| Login wrong-password lockout | Blocked at attempt 11, "wait about 15 minutes" |
| Login-MFA wrong OTP | Blocked at attempt 6 |
| MFA-recovery wrong code | Blocked at attempt 6 |
| Fresh session after MFA-recovery block, 1 wrong code | "Too many attempts" persists → account-level lockout (SAFE) |
| OTP reuse cross-signup | Old acc1 code on fresh signup → "That code is not correct" (bound) |
| Signup user-enum | Existing vs fresh → identical step-2 page, cooldown differs by ≤1s → no oracle |
| Forgot-password timing | existing 4.02s vs fresh 4.03s (n=4) → no oracle |
| SQLi timing probe `page=';WAITFOR DELAY '0:0:5'--` | One trial 12.1s → n=10 interleaved: control mean 1.66s/σ1.35, payload mean 1.05s → **jitter, debunked** |
| Admin/role tamper (adviser role=owner) | `_1_role=owner` sent, server enum validates → falls back viewer |
| Over-allocation sharePercent (50+50+60) | `"That would take the property over 100% owned. There is 40% left to allocate."` |
| Contributor delete owner entry | Pure contributor: delete buttons 0 on owner entries; own entry only → promised boundary enforced |
| CSRF evil-origin replay on add-income | 500; export shows 1 txn (not 2) → Origin/action bound |
| Stored XSS (notes, reminders, import desc) | Payload renders as `&lt;img...&gt;` in `<p>`; 0 executable elements after reload |
| CSV/XLSX formula injection | CSV gets `'` prefix; XLSX uses sharedStrings not `<f>` → no formula exec |
| Duplicate race same-tick double submit | **2 identical rows** (5555p ×2, 6666p ×2, 7777p ×2, all externalRef null) — verified in account export; 150ms double-click → 1 row |
| X-Fwd-Host / Host reset-link poisoning | HTTP 500 → blocked by proxy |
| /_next/image SSRF | 404 for all (optimizer not routed) |
| /api/blog-image/{slug} | 200 only for allowlisted slugs; `..`/URL/169.254 → 404 "Not found" |
| XXE via XLSX import (external entity) | No signal — parser safe |
| CVE-2025-29927 middleware bypass header | All 307 → auth enforced |
| /api unknown path POST multipart | 500 (body-parser); GET/PUT/POST-empty/OPTIONS → 404 (reported to vendor as hygiene) |

## Findings Reported

1. **Duplicate ledger entries via same-tick/replay submission (missing idempotency on UI transaction action)** — Low; PDF report generated with reportlab, sent once via Gmail SMTP to security@quarterwise.co.uk. Evidence: export rows with duplicated (date,type,amountPence), externalRef null. Root cause argument: API v1 dedups on externalRef, UI path does not.

## False-positive traps hit (check the playbook for the pattern)

- RSC flight-data reflection (payload in `self.__next_f.push` JSON with `\u003c`) looked like reflected XSS; verified DOM → no executable element.
- `codeLimit` param echoed in UI text ("about 1 seconds") but resend cooldown stayed 58s server-side → display-only, not a bypass.
- Unescaped-marker auto-detector flagged `\u003c` payloads; needed explicit `&lt;/\\u003c/\\x3c` check + DOM verification.