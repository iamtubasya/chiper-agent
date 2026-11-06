# Quarterwise VDP Case Study (2026-09) — Hardened Target Evidence Trail

Target: `quarterwise.co.uk` (Malden Ltd, UK MTD tax software) — official VDP with safe harbor,
rewards £100–£500. In scope: root domain + signed-in app + API. Subdomains / Stripe / Postmark /
Cloudflare / HMRC APIs out of scope. Rules: own accounts only, no volume testing, no other-people's
data. This file records what was tested and the exact mitigations that held, so a future session can
(a) avoid re-testing, (b) confidently write "hardened" findings, (c) reuse the exact attack shapes.

## Setup used
- Chrome profiles: port 9222 (acc1/owner), 9223 (acc2/co-owner+adviser), both
  `--remote-allow-origins=* --user-data-dir=<temp>/qw-chrome-debug[2]`.
- 3 mail.tm identities (acc1 owner, acc2 adviser+co-owner, acc3 fresh invite target).
- TOTP enrolled via Python RFC 6238 from on-page base32 secret (enabled authenticator 2FA,
  unlocking the /app/hmrc connect flow).

## Attack surface map
- Public API `/api/v1/*` (OpenAPI at /api/v1/openapi.json, docs at /developers/docs.md):
  me, sources, categories, sources/{id}/transactions GET+POST — bearer keys, Pro plan only.
- `/api/account/export` — full account JSON export (session-bound).
- `/api/properties/{id}/export?format=xlsx|pdf&taxYear=all` — per-property export.
- `/api/ai/extract-expense` — AI receipt scan (multipart file upload), 403 unless Pro.
- `/api/collect` — analytics beacon, 204, no CORS ACAO.
- Server actions: every state change is a multipart POST to the page URL with `next-action`
  header + `$ACTION_ID/_KEY` hidden fields (browser-generated — not curl-replayable).
- Adviser flow: `/app/account/advisers` invite (role viewer|contributor), accept via emailed
  token `/app/advisers/accept?token=...`.
- Share/co-owner flow: `/app/sources/{id}` "Share this property" (email + sharePercent),
  accept via `/app/shares/accept?token=...`; invites sum to 100% max.
- HMRC connect: `/app/hmrc` — NINO + TOTP code required, then Government Gateway OAuth.

## Test matrix and results (all verified server-side)
| Vector | Test | Result |
|---|---|---|
| API auth | no/bad bearer on all /api/v1 | 401, uniform error shape |
| Export param tamper | accountId/userId/email params | always own account |
| Page-level IDOR | acc2 → acc1 `/app/sources/{uuid}` | 404 "can't find that page" |
| Server-action replay cross-account | acc1 body + acc2 cookie | 500 / "Server action not found" |
| propertyId write BOLA | acc2 session + acc1 propertyId on their own form | "That property could not be found" |
| Settings rename cross-role | co-owner replay of owner save action | `{"error":"Only the owner can change these settings."}` |
| Adviser role tamper | radio value viewer→owner before submit | submitted `_1_role=owner`, rendered CAN VIEW (enum fallback) |
| Invite token binding | acc3 invite accepted by acc2 session | rejected: "sign in with invited address" |
| Share over-allocation UI | invite 60% when 100% allocated | "already fully allocated" |
| Share over-allocation replay | tampered `_1_percent=60` raw replay | `{"error":"That would take the property over 100% owned. There is 40% left to allocate."}` |
| sharePercent invalid | ownerPercent 101 / -10 / 0 | rejected, reset to 100 |
| CSRF server action | same body+same cookie, Origin evil.example.com | 500 digest error; txn count stayed 1 |
| Stored XSS (Notes) | `<img src=x onerror=alert(1)>` note | escaped `&lt;img...&gt;` in `<p>`, reload persists escaped |
| XLSX formula injection | prop name `=SUM(A1:C1)` → export | in `xl/sharedStrings.xml` as `<si><t>` (no `<f>` element) = not executed |
| CSV formula injection | account name `=2+2` → clients CSV | server prepends `'` → `'=2+2` |
| User enum forgot-password | registered vs unregistered email | identical response (anti-enum) |
| OTP rate limit | repeated wrong codes | cooldown + `codeLimit=12` in reset URL |
| Change password w/o current | new pw only, then old-pw login | old pw still works → current pw required |
| Session cookie | 64-char hex, HttpOnly, Secure, SameSite=Lax | server-side opaque session, not JWT |

## Score: NO reportable finding in scope
Every medium-class vector a typical target ships was present but server-enforced. The two
observations worth sending as hardening notes (not rewards): `direct.quarterwise.co.uk/fph-echo`
leaks `{"ip","port"}` (out of scope), and HTTP 500 on unknown `/api/*` paths (Next.js footprinting).

## Reusable shapes
1. MFA-gated flow unlock: enroll TOTP programmatically (secret regex `[A-Z2-7]{20,}` on page,
   code via RFC 6238) to access HMRC-connect / other gated surfaces.
2. Over-allocation replay: capture a legit invite POST (lower owner share first to make UI allow
   it), then raw-replay with tampered percent to test server-side sum check.
3. CSRF-on-server-action: replay MUST use same cookie + evil Origin; 500/digest error = enforced.
4. Cookie-swap replay: action binding dies cross-session ("Server action not found") — proves
   action IDs are session-bound, not just a CSRF token.