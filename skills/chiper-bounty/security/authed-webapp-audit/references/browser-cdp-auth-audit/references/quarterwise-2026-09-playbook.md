# Quarterwise (quarterwise.co.uk) 2026-09 — Full Session Playbook

VDP: https://quarterwise.co.uk/security/disclosure (Malden Ltd). In scope: root domain +
signed-in app + API. Subdomains OUT of scope. Rules: own accounts only, no volume
testing/DoS, no third-party email. Rewards: Critical £500 / High £250 / Medium £100.

## Session outcome
NO rewardable finding after 4 rounds (recon → authz cross-tenant → exports/logic/stored
XSS → CSRF/ATO). Every vector verified blocked. This is the reference for "what a fully
locked-down Next.js auth app looks like under real-browser multi-account testing".

## Environment reproduction (worked on Windows + git-bash + python 3.14)
- Tools: subfinder, httpx, gau, waybackurls, katana, naabu, nuclei v3.11.1, dalfox,
  sqlmap 1.8.12, interactsh-client, ffuf 2.1.0-dev, chrome 131 debug.
- Two Chrome debug profiles: 9222 (account1), 9223 (account2), each with
  `--remote-allow-origins=* --user-data-dir=...`.
- mail.tm temp inboxes: create via `POST https://api.mail.tm/accounts`
  `{address,password}`, token via `POST /token`, list `GET /messages`,
  read `GET /messages/{id}` (field `.text` contains OTP `\d{6}`).

## Key flows that worked
1. Signup through OTP: only works via real browser (form.requestSubmit). Curl POST of
   the signup form 500s — `$ACTION_*` fields are client-populated.
2. OTP verify step: `input[name=code]`, then password step `input[type=password]`,
   then name step `input[name=name]`. After finish → `/app` with HttpOnly `qw_session`
   cookie (64 hex, httpOnly, secure, samesite=Lax — server-side session, not JWT).
3. Server-action capture: Network.requestWillBeSent buffers requests; for FULL body use
   `Network.getRequestPostData {requestId}` (Chrome truncates postData in the event).
   Replay = identical multipart + `next-action` header + session cookie.
4. Cross-tenant BOLA: in account B, open a form scoped to B's own object, then set the
   hidden object id to A's — server "That property could not be found" = write-scoped.
5. CSRF proof: replay legit server-action POST with SAME cookie + evil `Origin`/`Referer`
   → 500 with digest error. Verify no state change via export JSON (`/api/account/export`).
6. Password-change re-auth proof: attempt change without current password, then on a
   FRESH cookie jar login with old password (success) + new password (fail) = rejected.
   urllib/curl 500 "login checks" are NOT reliable for this — use the browser.
7. Adviser invite token binding: accept invite as different signed-in user → server
   refuses ("signed in as ..., sign in with the invited address"). Token bound to email.

## Endpoints of note
- `GET /api/v1/openapi.json`, `GET /developers/docs.md` — public API reference.
- `GET /api/v1/me|sources|categories|sources/{id}/transactions`, `POST .../transactions`
  — all 401 without `Authorization: Bearer qw_live_...` (Pro-gated key).
- `GET /api/account/export` — returns own-account data as JSON (session-bound; param
  tampering accountId/userId/email doesn't change ownership).
- `GET /api/properties/{uuid}/export?format=xlsx|pdf&taxYear=all` — export; non-owner
  404. XLSX values in sharedStrings (`<si><t>`) = not formula-executed; PDF valid.
- `POST /api/ai/extract-expense` — multipart file → 403 "AI scanning is a Pro feature"
  for free plan (plan gate enforced server-side on direct call).
- `/app/account/advisers` — adviser invite (viewer/contributor); `/app/sources/{uuid}` —
  property page with share + settings; `#ownerPercent` ownership share validated server-side.
- `direct.quarterwise.co.uk/fph-echo` POST → `{"ip","port"}` info leak, but subdomain =
  OUT OF SCOPE (report only as hardening note to vendor).
- `reset` URL leaks `?codeLimit=12&why=cooldown` → OTP attempt cap = 12 (protection exists).

## Verification table (final state of every tested vector)
| Vector | Result |
|---|---|
| API v1 auth | 401 missing/invalid key ✅ |
| Export param tampering | own data only ✅ |
| IDOR/BOLA page-level | 404 page for other tenant ✅ |
| Server-action cross-session replay | 500 "Server action not found" ✅ |
| BOLA write (propertyId swap) | "property could not be found" ✅ |
| Viewer→contributor priv-esc | blocked (no Record income for viewer) ✅ |
| Adviser token binding | blocked for other user ✅ |
| CSRF evil-Origin replay | 500 (Origin check) ✅ |
| Stored XSS (note) | escaped in `<p>`, no img element ✅ |
| XLSX formula injection | sharedStrings only, no `<f>` ✅ |
| CSV formula injection | `'` prefix mitigation ✅ |
| sharePercent 101/-10/0 | reverted to 100 ✅ |
| Change-password w/o current | rejected (verified by real login) ✅ |
| User enum forgot | identical response for registered/unregistered ✅ |
| SQLi (sqlmap) | not injectable (403s = rate limit) ✅ |
| Nuclei tags sqli/lfi/ssti/xxe/nosqli/redirect/csrf | 0 ✅ |
| dalfox 162 URLs | 0 ✅ |
| interactsh OOB | 0 callbacks ✅ |

## Cleanup discipline
After stored-XSS/property-rename tests, restore names and delete test notes. The UI
delete for a note is a button with `aria-label="Delete note"` (NOT the "Delete this
property permanently" button — they sit side by side and the delete-property requires
typing the property name to confirm; easy to misclick).

## What was NOT testable without permission
- Pro plan: AI receipt scan, document upload (Documents tab Pro-gated), API key creation.
- HMRC Connect flow (requires Government Gateway account + 2FA enablement = real-world
  credentials beyond VDP test scope).