# Case Study — Quarterwise (Malden Ltd) deep audit, 2026-09

Complete record of a multi-day authorized VDP audit of quarterwise.co.uk (Next.js 14/15 app + Cloudflare + server actions + public API v1). Used to ground the playbook in `authed-webapp-audit`.

## Engagement facts
- VDP: quarterwise.co.uk/security/disclosure — scope = main domain + signed-in app + API; subdomains & Stripe/Postmark/Cloudflare/HMRC out of scope.
- Accounts: 3 temp-mail (mail.tm) accounts; MFA TOTP enrolled on acc1 (secret from enrollment flow generates valid codes).
- Browser: 2 Chrome profiles on ports 9222/9223 for cookie isolation.

## Tool matrix (all real, artifacts on disk)
| Tool | What it produced | Value |
|---|---|---|
| subfinder/httpx/gau/waybackurls/katana/naabu | recon/ url sets | surface map |
| nuclei (general + 7 vuln tags) | 2 TLS weak (low), 0 vuln tags | negative |
| sqlmap (L1-2, authed endpoint) | not injectable | negative |
| dalfox (162 targets) | 0 | negative |
| ffuf (root + /api, small words) | known paths only | negative |
| interactsh | 0 callbacks | negative |
| katana AUTH crawl (`-H "Cookie:..."`) | 1363 URLs incl. /api/blog-image/*, /api/attachments | **new endpoints** |

## Lockout numbers (OWN account, small N)
- Login MFA wrong OTP → block at attempt 6.
- MFA-recovery code wrong → block at attempt 6; persists across fresh session (account-level).
- Login wrong password → block at attempt 11, "wait about 15 minutes".
- Forgot/resend cooldown: server-side 58s; `/reset?codeLimit=N` only changes displayed text (display-echo, not enforcement).

## Findings result
- 1 candidate: duplicate-submit race on Add-transaction UI (same-tick double click → 2 rows; 150ms apart → 1 row). externalRef null; API v1 dedups on externalRef but UI doesn't. Reportable as Low/P4 missing-idempotency.
- Everything else negative or blocked: IDOR/BOLA (3 acct), stored XSS (notes/reminders/import/property name all escaped), CSV/XLSX formula injection mitigated, CSRF origin-bound, XXE-XLSX safe, reset-link poisoning 500/403, /_next/image 404, blog-image allowlist, OTP/session-rotation blocked, priv-esc & role boundary enforcement, ty=/open= params ignored.

## 500-vs-404 reproduction sent to vendor
Unknown /api paths: GET/PUT/OPTIONS/POST-no-body → 404; **POST + multipart/form-data → 500 "Internal Server Error"** (text/plain, cf-cache-status DYNAMIC). Reproduction list:
- /api/import, /api/imports, /api/upload, /api/uploads, /api/import/upload, /api/imports/upload
- /api/v9/nonexistent, /api/does-not-exist-xyz
- /api/properties/{uuid}/documents, /documents/upload, /receipts, /attachments
- Control: POST /api/documents/upload (real route) → 405 (Allow: GET, HEAD, OPTIONS).
Hypothesis: Next.js body/form-data parser runs before route matching for POST+multipart → 500 instead of 404. Hygiene, not vuln.

## Email timeline & correction
1. SMTP-sent report to security@quarterwise.co.uk (one send) + IMAP-append copy into Gmail Sent — user saw it as TWO emails. **Correction: one delivery path; never send then append a copy.**
2. Vendor follow-up (500 repro) was drafted, user said "save in draft" → saved to [Gmail]/Draf with DRAFT flag. Then user changed mind: delete the draft (done, uid verified 0 remaining), deep-dive instead.
3. Vendor 500-repro detail was later requested by email; exact table captured (above).

## Session-rotation OTP test shape (reusable)
- Round 1: wrong code xN until "Too many attempts".
- Round 2 fresh login: 1st wrong code → still "Too many attempts" → account-level lockout (safe).
If round 2 shows only "wrong code" → per-session counter → brute-force candidate. Quarterwise = account-level.

## Useful snippets
- Chrome WS connect: `websocket.create_connection(url, header=["Origin: http://localhost"])`
- Cookie grab: CDP `Network.getAllCookies`; HttpOnly cookies available there.
- TOTP gen: RFC6238, base32 secret from enrollment, hmac-sha1, 6 digits.
- Server action full body: `Network.getRequestPostData`.
- CSRF replay: same body+cookie, change Origin to evil → 500 = origin-bound.
- Email draft: imap_tools `append(msg.as_bytes(), "[Gmail]/Draf", flag_set=MailMessageFlags.DRAFT)`; delete by uid with `mailbox.delete([uid])`.