---
name: proton-engagement
description: "Proton AG bug bounty engagement (proton.me estate). Scope table, submission channel (email, no portal), reward bands, by-design list already disproven so it is not re-burned, session-recovery recipe for the test account, and the one live finding (Lumo tool-schema $ref SSRF). Load before any Proton audit run."
metadata:
  hermes:
    tags: [security, bug-bounty, proton, vendor, scope, engagement]
    related_skills: [hunt-llm-ai, audit-pipeline-operations, hunt-ssrf, signup-block-ops]
---

# Proton AG — engagement profile

Self-run program, **email submission only**. Not on HackerOne/Bugcrowd. Load this before a Proton
run so scope, channel and the already-disproven surface are not rediscovered.

## 1. Authority + channel

- `https://proton.me/.well-known/security.txt` — Contact `security@proton.me`, Policy
  `proton.me/security/bug-bounty`. Safe harbour: `proton.me/security/safe-harbor`.
- Submit to **security@proton.me** (plaintext / rich / HTML; PGP optional). No portal, no form
  triage, no duplicate check available — so verify a finding yourself before sending.
- Disclosure hold: **120 days** from acknowledgement.
- Rewards: max USD 100,000; Critical 25k-50k, High 2.5k-25k, Medium 1k-2.5k, Low case-by-case with
  **no default money**. Novelty is an explicit scoring factor — only the first valid report pays.

## 2. Scope (VDP host list — host-list scope, NOT wildcard)

IN: `proton.me`, `account.proton.me`, `mail.proton.me`, `api.protonmail.ch`, `calendar.proton.me`,
`drive.proton.me`, `docs.proton.me`, `pass.proton.me`, `wallet.proton.me`, `lumo.proton.me`,
`protonvpn.com`, `account.protonvpn.com`, `api.protonvpn.ch`, `simplelogin.io`,
`app.simplelogin.io`, `standardnotes.com`, `app.standardnotes.com`, "Proton Scribe", plus
mobile/desktop apps (Android/iOS/Windows/macOS/Linux, Bridge, browser extensions).

OUT (verbatim exclusions): `shop.proton.me` (Shopify), `proton.me/support/contact`,
`support/help.protonmail.com`, `protonmail.zendesk.com`, `partners.proton.me` (TUNE),
`localize.proton.me` (Discourse), `status.proton.me` (Atlassian), WordPress bugs, DoS/resource
exhaustion, spam, social engineering, physical access, content injection without significant risk,
scripts on sandboxed domains, out-of-date software/browsers.

Ambiguous hosts that resolve but are **not listed** — treat as out of scope deliberately and say so
in coverage: `meet.proton.me`, `sheets.proton.me`, `verify.proton.me` (resolve);
`scribe.proton.me` (NXDOMAIN as of 2026-10). `protondns.net` is a different brand, not listed.

Policy forbids degrading operation => all scanning is gentle automated (`nuclei -rl 6..15 -c 2..5`,
`ffuf -rate 12`, `dalfox --delay 300`, `sqlmap --threads 1`). Gentle automated, never manual-only.

## 3. By-design — already disproven, do not re-burn

| Surface | Why it is not a finding |
|---|---|
| `POST /auth/v4/sessions/forks` -> claim with selector only (no secret) | the SPA's own client calls `pullFork` `unauthenticated:true` with the selector alone; selector IS the intended bearer credential. Fork tokens also lack `password`/`locked` scopes and privileged calls correctly 403 `MissingScopes`. |
| `RecoverySecret` returned by `GET /core/v4/users` to any token | recovery FILE = decrypted private keys encrypted with that random 32-byte secret; the file blob is local, server stores only `{RecoverySecret, Signature}`. Secret alone is useless. |
| `GET /drive/urls/{token}/info` unauthenticated | returns SRP handshake params only (`Modulus`, `ServerEphemeral`, `UrlPasswordSalt`, `SRPSession`) — required to render the password prompt. No PII, no metadata. |
| `GET /core/v4/users/available?Name=` 409/200 split | documented availability check; `Suggestions` are **synthetic** (verified: suggested names are themselves free). No other user's username leaks. |
| `GET /payments/v5/web-configuration` | Chargebee **publishable** key, client-side by design. |
| `GET /core/v4/trials/{anything}` | identical static plan catalogue for every path, not caller-bound => no eligibility oracle. |
| `POST /ai/v1/chat/completions` honouring a client `system` role | self-scoped model behaviour; content-policy territory, and VDP excludes content injection without significant risk. |
| `standardnotes.com` ACAO `*` | static wildcard, no credentials. |
| mail HTML sanitizer + `sandbox="allow-same-origin allow-popups"` (no `allow-scripts`) | message body cannot execute. |

Payment logic is correctly guarded: invoice creation returns `No valid payment method available`
**before** price evaluation, `subscription/check` rejects bad quantity/cycle/currency and 4-code
coupon stacking, and 8-currency sweeps showed `Amount == AmountDue` everywhere. Do not spend a card
on a live PSP to "confirm" tampering — that path is gated, record it as gated.

## 4. Live finding to carry forward

**P-01 — unauthenticated SSRF in Lumo chat completions.** `POST /api/ai/v1/chat/completions` with
`tools[].function.parameters.$ref = https://attacker` makes Proton infrastructure issue the GET
before model invocation: no token, no cookie, no quota cost, redirects followed, and a
**schema-validity** oracle (valid JSON Schema 200 / anything else 500, no reflection). Escalation
floor measured: loopback + docker-bridge ports all RST (isolated namespace), RFC1918 and every cloud
metadata endpoint (AWS ECS/EKS/IMDS, Alibaba, Oracle) filtered at ~31 s, `file://`/`gopher://`
refused => blind SSRF with boolean oracle and host/port discrimination, **Medium**, not credential
theft. Full technique: `hunt-llm-ai` → `skills/hunt-llm-ai/references/tool-schema-ref-ssrf.md`.

**Status: SENT to security@proton.me 2026-10-25** (plaintext body + 5-page PDF; Message-ID
`<...@gmail.com>`, verified present in the Sent folder by IMAP). Proton only *encourages* PGP, so
plaintext was compliant — but if you resubmit or reply, use `pgp-email-submission`
(key `https://api.protonmail.ch/pks/lookup?op=get&search=security@proton.me`). **Do not resend the
same finding in a new thread** — reply inside the existing one, or the triager sees a duplicate.

## 5. Session recipe (test account + API shape)

- Test identity from the 2026-10 run: `auditfz77310@proton.me`, self-provisioned free account.
  **Only one identity exists** — every cross-tenant test is blocked on a second one.
- Recover a dead session from a saved Playwright profile: read `AUTH-<uid>` / `REFRESH-<uid>`
  cookies, then
  `POST /api/auth/v4/refresh` with body
  `{"ResponseType":"token","GrantType":"refresh_token","RefreshToken":"<rt>","RedirectURI":"https://protonmail.com"}`
  — same-origin `Origin`/`Referer` and `x-pm-uid` required, an empty body returns `400 Invalid input`.
  `GET /core/v4/auth/scopes` tells you whether the session still carries `locked` (needed to revoke
  sessions / rewrite keys).
- Every API call needs `x-pm-appversion` (e.g. `web-mail@5.0.136.5`, `web-account@5.0.430.0`,
  `web-lumo@1.3.0`) and `Accept: application/vnd.protonmail.v1+json`. Missing appversion =>
  `5002 Missing x-pm-appversion header`; without it sqlmap/dalfox see 400s and their verdicts are
  worthless.
- Login form uses bare ids `#username` / `#password` with a `button[type=submit]`; typing with a
  delay works where `fill` silently fails. `mail.proton.me` -> `/u/N/inbox` after auth.
- Endpoint inventory: `grep -o 'url:\s*[`"][^`"]*'` over the SPA chunks. yields ~320 (account),
  ~105 (docs), ~131 (pass), ~300 (lumo) templates — cheaper and more complete than crawling.

## 6. Known blockers (operational, not negative results)

- **Second Proton identity**: `POST /api/core/v4/users` is human-verification gated (400/422
  `Invalid input` / `Email contains invalid characters`; no public `/human-verification` path).
  Needs one manual signup in a headed browser. Until then BOLA across Drive/Docs/Pass/Calendar/
  Wallet shares, org-role escalation, referral abuse and proration stay **untested, not negative**.
- Standard Notes signup requires an `hvm_token`.
- **SimpleLogin is NO LONGER a blocker** — see §8. It is unblocked and half-audited.
- `wallet.proton.me` has its **own** anti-abuse limiter: a burst of wallet calls returns
  `422 Code 2028 "unusual activity ... temporarily limited access"`. It is scoped to wallet on that
  account — mail/pass/drive/account kept returning 200 at the same moment. That is a throttle on
  YOUR test account, never a finding and never a negative result; pace wallet calls (~1 per 4 s) and
  record the reduced coverage explicitly.

## 7. Reporting notes

Email body style that fits this program: plain text, lead with the one-paragraph plain-language
statement of the flaw, then the exact HTTP request, then what was measured vs not measured, then what
the researcher did not do (own account only, no other user's data, no retention), then the fix. Attach
a PDF with the raw collaborator log and the negative control. Do not include a reward request.

## 8. SimpleLogin (app.simplelogin.io) — unblocked 2026-10-25, already half-audited

Server-rendered **Flask + htmx** app: there is no JSON API list in its bundles (grep returns 0
endpoints) and forms POST to `/dashboard/*` with `csrf_token`. The documented JSON API instead takes
header `Authentication: <api_key>` (60 chars) from `POST /api/auth/login`.

**Signup/activation recipe** (this is what was blocked before — it works now, with any readable mailbox):
1. `POST /api/auth/register {"email","password","password_confirm"}` — rejects `@proton.me`
   ("cannot use ... as personal inbox") and blocklisted disposable domains; plain Gmail / `+tag` is fine.
2. The mail delivers a **6-digit code, not a link** ("Just one more step to join SimpleLogin").
3. `POST /api/auth/activate` with `{"email": "...", "code": "......"}` -> `{"msg":"Account is
   activated..."}`. Send the code **alone** and you get a generic `500 Internal error` — that 500 is
   what makes people think the endpoint is broken. Read the code from IMAP.
4. `POST /api/auth/login` returns `api_key`; every API call then needs `Authentication: <key>`.
   Note the `+tag` is normalised away (`+sl1@gmail.com` logs in as `RESEARCHER_EMAIL`) — same identity.

**Disproven on this product — do not re-burn:**

| Surface | Result |
|---|---|
| Authz sweep of all 7 ID-bearing routes (`/api/aliases/{id}`, `/activities`, `/contacts`, dashboard `alias_contact_manager`, `alias_log`, `alias_transfer/send`, `alias_activities`) | own ID 200, foreign ID `403 Forbidden` or redirect to `/dashboard/` -> **no IDOR** |
| Custom-domain ownership (add a domain you do not own, then hit Verify) | TXT `sl-verification=...` **and** MX enforced server-side; Verify produces no state change and no POST -> no bypass |
| Reserved subdomain names (`admin`,`test`,`mail`,`support`,`api`) on shared roots | all rejected; only random names create |
| Subdomain quota | total 5 for the trial, enforced (Create disappears) |
| Directory / user search (`/api/directory`, `/api/directory/search`, `/api/users/search`) | 404 unauth and auth -> no public directory |

**Info-only, do NOT report:** `GET /api/aliases/{id}` distinguishes `403` (alias exists, not yours)
from `400 "Unknown error"` (no such alias) — an integer-existence oracle that leaks no owner/email
data. The program excludes info-only findings.

**UI-text trap worth remembering:** the subdomain page reads "Currently you can create up to N
subdomains", and N is the **remaining** allowance, not the plan limit. Counting it as "the limit was
bypassed" is a false positive — verify by counting the actual rows and watching the Create button.
Same class of trap as a soft-404: read the state, not the label.

Still untested here (needs a second identity): `alias_transfer` hijack, duplicate/catch-all domain
claims between two users, premium-trial restart after the 7-day window.

## 9. Wallet / Pass / Docs — mapped and negative (2026-10-25)

- **Wallet** needs browser capture, not bundle grep (its index is lazy-loaded; grep finds 0 endpoints).
  Real surface: `/api/wallet/v1/{network,settings,wallets,wallets/{id},rates,graph,blocks,
  blocks/height/{h}/hash,invites/remaining}`. IDs are opaque base64 (no enumeration) and
  `GET /wallets/{id}` is not even routed (405, Allow: DELETE). `blocks` serves public Bitcoin data, so
  `height/abc` parsing leniently to genesis is sloppy input handling but **public data = info-only**.
- **Pass public links**: `content/{token}` and `files/{token}` return uniform `422`; the chunk path
  `files/{t}/{f}/{c}` returns a format-check `400 Code 2061` before any lookup. Authenticated vs
  anonymous changes nothing -> no oracle, no privilege confusion.
- **Docs importer autodiscovery** `GET /api/importer/v1/mail/importers/authinfo?Email=` is a **static
  provider map** (gmail -> imap.gmail.com, outlook -> outlook.office365.com) with **zero** DNS/HTTP
  callbacks to an interactsh domain and IP literals rejected -> not SSRF, not enumeration.
- **Cookie flags**: `AUTH-*`, `REFRESH-*`, `Session-Id` are all `HttpOnly; Secure; SameSite=None`.
  Only the non-sensitive `Tag` UI cookie lacks HttpOnly. No finding.
