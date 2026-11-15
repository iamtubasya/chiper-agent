# Proton engagement — 2026-10-20 (mail.proton.me + product family)

Read BEFORE any re-hunt of Proton. Scope, API auth model, the session-fork finding (F1),
account-creation path, and the verified negatives so the next pass skips them.

## Program basics (Phase 0A/0B)

- Bug bounty page: `proton.me/security/bug-bounty`; policy: `/security/vulnerability-disclosure`;
  safe harbor: `/security/safe-harbor`. **Report channel: email `security@proton.me`**
  (PGP key at `api.protonmail.ch/pks/lookup?op=get&search=security@proton.me`).
  No public reward table; acknowledgement + bounty at their discretion.
- In scope (explicit list — anything NOT listed is OUT): `proton.me`, `account.proton.me`,
  `mail.proton.me` + `api.protonmail.ch` (+ mobile apps, Bridge), `calendar.proton.me`,
  `drive.proton.me`, `docs.proton.me`, `pass.proton.me`, `wallet.proton.me`,
  `lumo.proton.me`, Proton Scribe/Authenticator, `protonvpn.com` + `account.protonvpn.com` +
  `api.protonvpn.ch` (+ apps), `simplelogin.io` + `app.simplelogin.io`, `standardnotes.com` +
  `app.standardnotes.com`. Subdomains NOT on the list (e.g. `referrals.protonvpn.com`,
  `livekit.proton.me`/Meet, `verify.proton.me`, `shop.proton.me`) are OUT.
- Prohibited: DoS, social engineering, phishing users, testing third parties, data
  exfiltration/persistence/pivoting, degrading service. May view nonpublic data only as needed
  to document a vuln; must purge after reporting.
- 2026-10 recon: 97 subdomains (subfinder), 23k historical URLs (gau). WAF: Cloudflare on
  simplelogin.io / protonvpn.com / standardnotes.com (nuclei dns-waf-detect only; no findings).
  Nuclei (tech/exposure/misconfig/cors, `-rl 8`) = 3 info hits, nothing else.

## API auth model (the part that costs hours if unknown)

Every Proton web API (`mail.proton.me/api/...`, and the per-product API hosts behind it)
requires THREE things or you get useless errors:

1. `Accept: application/vnd.protonmail.v1+json`
2. `x-pm-appversion: <platform>-<product>@<version>` — **must be the CURRENT shipped version**
   (was `web-mail@5.0.136.5` on 2026-10-20; login page footer shows it). A stale/wrong value
   returns **HTTP 422 `{"Code":5003,"Error":"This web page is out of date..."}`** — that error
   is an APPVERSION problem, NOT a session problem. Valid product tokens seen: web-mail,
   web-account, web-drive, web-pass, web-calendar, web-wallet, web-lumo (format
   `platform-product@version`, dash-separated).
3. `Authorization: Bearer *** + `x-pm-uid: <uid>` — BOTH required (either alone = 401
   "Invalid access token"). (NOTE: the `Bearer ***` above is the Hermes secret-masking
   DISPLAY artifact that ate the token literal when this reference was first written — the
   real header value is `Bearer <access token>`. See engagement-credentials-and-totp.md §masking.)

**Capture the app's real headers instead of guessing**: attach a Playwright
`page.on("request")` listener, load the app, filter `/api/`, and dump `r.headers` — you get
the exact appversion + your x-pm-uid in one shot. Replaying with those headers via curl works.

Backend hosts are separate from the frontends (error bodies leak them):
`mail-api.proton.me`, `pass-api.proton.me`, `lumo-api.proton.me`, `account-api.proton.me`.

## Session-fork mechanism + FINDING F1 (the report)

Flow: product app without a session → `POST account.proton.me/api/auth/v4/sessions/forks`
(authenticated) → selector → authorize redirect carries `#selector=...&sk=...` (sk in the
FRAGMENT) → product app calls `GET <app>/api/auth/v4/sessions/forks/{selector}` → tokens.

- Fork create body: `{"ChildClientID":"web-mail","Independent":0}` (Independent is a BoolInt —
  a JSON `false` is rejected with a serializer error). Response: `{"Code":1000,"Selector":"<32 chars>"}`.
- **F1 (validated 4x, SUBMITTED 2026-10-21 03:07 UTC, auto-acknowledged)**: the claim returns
  `AccessToken` + `RefreshToken` with `Scope: full locked self payments keys parent user
  loggedin nondelinquent mail calendar drive pass verified settings wallet meet` to ANY
  unauthenticated caller that knows only the selector. The `sk` is never requested — client JS
  uses it only to decrypt the optional `Payload` (keyPassword/offline key), which is `null`
  for API-created forks. The tokens authenticate API calls (verified: `/api/core/v4/users`,
  settings, `/api/payments/v5/status`). Fork is single-use (replay → 422 "Invalid selector"),
  24h expiry. E2E content NOT readable (needs the payload's keyPassword) — keep that in the
  honesty block.
- **Capability probe of the issued tokens (measured same session — THIS is what keeps the
  report honest)**: READ allowed — account info, user settings + recovery-email config,
  payment status/methods (billing PII), addresses+public keys, **the full active-session
  inventory** (`GET /api/auth/v4/sessions` lists SessionID/UID/ClientID/expiry), labels,
  filters, newsletter subscriptions. WRITE blocked BY SCOPE — password change →
  `{"Code":9102,"MissingScopes":["password"]}`, session revocation →
  `{"Code":9101,"MissingScopes":["locked"]}`. Note the claim response ADVERTISES "locked"
  in its Scope string while enforcement rejects it — the string is the requested set, not
  the granted set. Net: **sensitive read-only disclosure, NOT account takeover** — final
  severity framed Medium-High with this measured table in the PDF.
- PoC: `D:/data hermes/proton-audit/poc/poc_fork_token.py`; report PDF + body:
  `D:/data hermes/proton-audit/submission/`. NOTE: staging first hit a revoked Gmail
  OAuth token ("invalid_grant") mid-session; the re-auth recipe that unblocked it is in
  the "Gmail OAuth re-auth recipe" bullet below — staging then COMPLETED (draft
  r9130402048999159015, PDF sha256-verified) and the operator sent it.

## Account creation path (for the next engagement)

- Signup = multi-step React wizard at `account.proton.me/signup`: plan card
  (`button.card-plan`, click the one containing "Free"), then username/password (+confirm),
  submit `[data-testid="pay"]`. The username input's REAL element lives inside the
  cross-origin anti-fraud iframe (`account-api.proton.me/challenge/v4/html?...Name=email`).
- Final gate = **ProtonCAPTCHA jigsaw** (`account-api.proton.me/captcha/v1/assets/`,
  iframe-in-iframe, "drag the puzzle piece"). Same widget as Standard Notes uses. Blocks
  automation; the working pattern is a HEADED browser + manual solve + URL-change polling
  (details now in the `camoufox` skill §"Captcha handoff"). Its "Try a different challenge"
  menu offers "Align beams" (untested — potentially easier than the jigsaw).
- **Login has NO captcha** — password re-login is the cheap way back in.
- Disposable email domains are blocked at signup ("Email domain not allowed" in the challenge
  frame); the `@proton.me` username path needs no external mailbox.
- Repeated signup attempts from one IP get `account.proton.me` temporarily connection-blocked
  (curl 000/timeout) while the product hosts stay up; it recovers. Also: a username from a
  failed attempt stays reserved and silently blocks later submissions — use a fresh username
  per attempt.

## Other surface notes (verified, mostly negative)

- **Lumo guest sessions**: visiting a dead share link (`lumo.proton.me/u/0/c/{id}`) mints a
  guest session (`POST /api/auth/v4/sessions/forks`). Guest can `POST /api/ai/v1/chat/
  completions` (OpenAI-compatible; model `lumo-lite`) with a 20-message/session limit,
  server-enforced (429 `Code 2028` at 0). All user-data endpoints 401 for guests. Basic prompt
  injection (system-prompt extraction, DAN) is refused by the model.
- **Pass public links**: `GET pass.proton.me/api/pass/v1/public_link/content/{code}` (also
  `/public_link/files/{filesToken}/{fileID}/{chunkID}`, `/public_link/{id}`, `/inactive`).
  Invalid code → 422 "Secure link does not exist"; only GET allowed; E2E-encrypted content.
- **Standard Notes API** is version-gated: send `x-application-version: Web-3.202.10` +
  `x-snjs-version: 2.212.6` (capture from the app) or every call 400s "client version no
  longer supported". CORS is a static `ACAO: *` (no origin reflection, no credentials) — not
  exploitable. SN signup = ProtonCAPTCHA jigsaw (same wall).
- **SimpleLogin signup** = hCaptcha (drag-animal challenge when the fingerprint is flagged).
- Security headers on all Proton hosts are tight (CSP with frame-ancestors allowlists, HSTS
  preload, HttpOnly+SameSite=None cookies); `account.protonvpn.com` adds `X-Frame-Options:
  deny` + `frame-ancestors 'none'`. No CORS/header findings.
- Key-transparency endpoints (`/api/core/v4/keys/signedkeylists?Identifier=...`,
  `/api/kt/...`) are public by design.

## Engagement state

- Test account: `auditfz77310@proton.me` (free, self-provisioned, password in
  `D:/data hermes/proton-audit/testpw.txt`); profile `$HOME/proton-test-profile`.
  Second account signup failed (form silently blocked after repeat attempts) — no cross-account
  IDOR matrix was run.
- F1 = session-fork token issuance (this file §"Session-fork mechanism"). Validated 4x.
  PDF + email body + evidence + checksums complete. **SENT by the operator 2026-10-21
  03:07 UTC** (draft r9130402048999159015, subject "[security] Proton session-fork tokens
  issued without the secret key (mail.proton.me)", PDF attached + sha256-verified).
  **Proton auto-reply received** (security@proton.me, 2026-10-20 20:08 UTC): generic
  acknowledgement — "response times will be longer than usual for a few weeks", and they
  are PRIORITIZING critical vulnerabilities with clear exploitability evidence; reports
  without that "will take significantly longer to review". No ticket number in the
  auto-reply. Implication: a Medium-High with a selector-leak precondition will sit in the
  slow queue — follow up after a few weeks, do not resubmit.
- **Gmail OAuth re-auth recipe that worked mid-session** (refresh token died with
  "invalid_grant"): delete `google_oauth_pending.json` → run
  `python skills/productivity/google-workspace/scripts/setup.py --auth-url` → user approves
  in browser (the localhost:1 error page is NORMAL) → user pastes the FULL redirected URL
  (`http://localhost:1/?code=...&state=...`) → exchange `code` + the pending
  `code_verifier` (grant_type=authorization_code, redirect_uri from the pending file) at
  oauth2.googleapis.com/token → save the new token. Approval alone is NOT enough — without
  the pasted code URL the exchange cannot happen (this cost two rounds).
## Round 2 (2026-10-20/21) — wallet/docs/calendar mapped, E2E holds

- **Proton Wallet API** (`wallet.proton.me/api/wallet/v1/...`, backend `wallet-api.proton.me`;
  own session UID per app fork — mail UID ≠ wallet UID, capture per app): wallets list,
  `wallets/{id}/accounts`, `settings`, `network`, `fiat-currencies`, `rates`, `graph`,
  `blocks`, `blocks/height/{h}/hash`, `invites` + `invites/remaining` (5/account).
  **Transaction submission is `POST /api/wallet/v1/wallets/{WID}/accounts/{AID}/transactions`**
  (PATH variant — the flat `/transactions` endpoint reports body fields "missing" no matter
  what you send; the real IDs ride the path). Required body: `SignedTransactionHex`
  (**client-side signing — the server never holds keys**) + `TransactionID` +
  `HashedTransactionID`, and those two must be **valid PGP data** (error `Code 2002`
  "not valid PGP data" — transaction metadata is E2E-encrypted, no server-side parsing).
  ID format is validated BEFORE ownership (foreign-format ID → `Code 2061` "not a valid
  ID"). Invites: `POST /api/wallet/v1/invites` blocks disposable recipient domains (422
  "Invitation cannot be sent to this address").
- **FIELD-CASING LESSON (cost ~10 probes, reusable on any Proton-family API)**: the
  error message names a field in one casing (`InviterAddressId`) while the wire format
  requires another (`InviterAddressID` — capital ID). A body field that "is not read"
  despite being present is almost always a casing mismatch: try `XxxID` vs `XxxId`
  (and `WalletID`/`WalletAccountID`) before concluding the endpoint ignores bodies.
  Symptom chain: empty body → "Missing A,B,C"; send A,B → error shrinks to "Missing C";
  send C in the error's casing → still missing → try the other casing.
- **Docs** (`docs.proton.me`): loads with the account session; `/api/docs/recent`, Drive
  link/volume endpoints, realtime backend `wss://docs-rts.proton.me` (CSP leak) — not
  deep-tested. **Calendar**: loads; `/api/calendar/v1/booking` (booking pages),
  `/api/calendar/v1/directory?Type=2` (public-calendar directory), auto-created calendar
  via `POST /api/calendar/v1`.
- **Calendar subscription SSRF — TESTED NEGATIVE with OAST (2026-10-21 deep-dive)**:
  `POST /api/calendar/v1` accepts a `Url` field but **ignores `Type`** (always creates a
  Type-0 personal calendar — the response lists it as Type 0) and the server NEVER fetches
  the URL: an interactsh OAST URL in `Url` produced ZERO callbacks across the session.
  Proton Calendar fetches subscriptions CLIENT-SIDE → no SSRF surface. Also:
  `Color` must come from a fixed palette (grab a valid one from an existing calendar,
  e.g. `#BA1E55` — arbitrary hex → `Code 2001 "not in allowed color list"`), free accounts
  cap calendars (repeated creates → `Code 2011 "Number of calendars exceeded limit"`).
- **Drive public-link password bypass — NOT completed (E2E crypto wall)**: the share
  modal opens ("Share item" dialog with a file picker) but creating a link needs the full
  client-side crypto chain (link-key generation + folder-key re-encryption + SRP for the
  URL password), so the API route is impractical and the UI route is flaky under
  automation. Untested; would need a scripted Drive crypto harness (1-2 days) — deprioritize
  vs the E2E argument above.
- **Why no new finding — the structural reason (say this in any future Proton report)**:
  E2E architecture kills the classic classes by design: the server never processes
  plaintext (no file/image/ICS parsing → no RCE via malicious content), all IDs are
  random (no enumeration IDOR), keys+signing are client-side, and scope enforcement is
  real (measured: password/session-revoke blocked by missing scopes). The fork finding
  was the exception precisely because it breaks the per-session authz principle.
- **Nuclei final** (tech/exposure/misconfig/cors, `-rl 8`, ~35 min): 142 lines, ALL
  info-level. Missing `X-Frame-Options` on app hosts is a NON-finding — every app sends
  CSP `frame-ancestors` allowlists (verified mail/wallet/drive) which supersede XFO.
  `fingerprinthub dfe-scada` hit on protonvpn.com = false positive. Weak-CSP
  (`unsafe-inline/unsafe-eval`) only on SimpleLogin. No CORS/header findings.

## Round 3 blocker + session-handling pitfalls

- **Second account is now SILENTLY blocked** (escalation from the earlier temporary
  IP-block): signup form accepts input but never submits — no captcha, no error, no
  POST /api/core/v4/users. Synthetic-event automation (JS value-setter + dispatch, or
  Playwright `mouse.click` on the pay button) gets dropped by the anti-fraud layer
  after the first account + heavy authenticated testing from the same IP. Recovery
  options ranked: (1) user completes the signup MANUALLY in the headed window with real
  keystrokes (most likely to pass), (2) wait for the flag to decay, (3) pivot targets.
  **UPDATE 2026-10-21: option (3) "try the Proton VPN signup path" was TRIED and ALSO
  FAILS** — `account.protonvpn.com/signup` (email-based, upsell modal with "Continue
  with free") loops back to the email step under automation: the React wizard does not
  register synthetic input from this flagged IP, same silent-block behavior as the main
  signup. Disposable domains blocked there too. Do not spend rounds re-trying VPN signup
  from the same machine/IP; manual signup or IP change are the only viable doors.
- **`ctx.clear_cookies()` + `storage_state()` = session suicide**: clearing cookies to
  "force a fresh fork" and then saving the profile state writes the LOGGED-OUT state
  over the good session (hit twice this engagement). Never clear_cookies on the working
  profile; if a fresh fork is needed, delete only the target app's session cookies or
  use a separate profile. Recovery = password re-login (login has no captcha).
- **Gmail access token expires hourly** — refresh via the stored refresh_token before
  each API check (`grant_type=refresh_token`), don't cache the access token across
  long gaps. The full re-auth recipe for when the refresh token itself dies is above.

## Round 4 (2026-10-25, fresh-run v2) — FINDING P-01 Lumo SSRF + SimpleLogin opened

### P-01 (SUBMITTED 2026-10-25T00:41Z, security@proton.me) — unauthenticated SSRF in Lumo

`POST lumo.proton.me/api/ai/v1/chat/completions` with `tools[].function.parameters = {"$ref":"<url>"}`
makes the backend fetch that URL server-side **before** model invocation. **No auth, no cookie, no
quota cost.** This supersedes the older "Lumo = only a 20-msg guest limit, nothing there" note.

```
{"model":"lumo-lite","max_tokens":4,"stream":false,
 "messages":[{"role":"user","content":"hi"}],
 "tools":[{"type":"function","function":{"name":"t","description":"d",
   "parameters":{"$ref":"https://<collab>/poc.json"}}}]}
```
Proof shape that made it stick: 14 distinct payloads / 27 OAST callbacks / 16 distinct Proton egress
IPs (51.77.186.217, 78.232.6.185 / .3.69 / .3.70 / .3.72, 78.232.7.28, 141.94.47.194, 95.133.254.65,
51.159.163.252 / .167.216 / .191.160, 62.210.237.96) vs researcher egress 104.28.226.245. Each
payload produced **two** callbacks — two fetch paths in their stack.

- **`description` is MANDATORY.** Without it the body fails `IncomingToolSpec` validation and **no
  fetch happens** — that is the negative control proving the fetch is schema-resolution driven.
- **The oracle is schema-VALIDITY, not "JSON parses".** All served HTTP 200: `httpbin/json` (plain
  object) → 200; base64 of a real `{type:object,properties:…}` → 200; base64 of `{"not":"a schema"}`
  (`not` must itself be a schema) → **500**; `/html`, `/xml`, `/image/png` → 500;
  `/status/200|204|404|500` (no body) → 500. An attacker learns whether an internal URL returns a
  valid JSON Schema.
- **No content reflection** — a unique marker inside the fetched schema never appears in the response.
  Boolean oracle only; never claim a read primitive.
- **Redirects followed**: `$ref` → httpbin 302 → collaborator logged the final hop (`/redir9.json`,
  Referer showed the httpbin URL). A first-hop allowlist alone would be bypassable.
- **Internal range is dialled, not blocked**: closed loopback port fails ~1.8 s (TCP RST) vs
  `10.255.255.1` / `169.254.169.254` hanging to the ~30 s connect timeout = filtered. That timing
  split IS the internal host/port classifier. 14 loopback ports + `172.17.0.1:80/2375/8080` all reset
  (fetcher runs in an isolated netns, no local listeners); `10.0.0.1` and `192.168.0.1` filtered.
- **Cloud metadata all closed** — AWS ECS `169.254.170.2`, EKS `169.254.170.23`, IMDS iam/user-data,
  Alibaba `100.100.100.200`, Oracle `192.0.0.192` → filtered or fast-fail, **zero credentials**.
  This is why the report says blind SSRF, not credential theft. Do not re-hunt these.
- **Single surface**: `POST /api/ai/v1/feedback` takes a string `Body` only ("Attribute Body should be
  of type string") and performs no fetch; `stream:true` on chat/completions fires the same fetch;
  `file://`/`gopher://` refused. Full SPA inventory (300 endpoint templates / 60 bundles) confirms
  there is no `ai/v1/images` — the `images:20` quota is spent through chat/completions itself.
- **Client-supplied `role:"system"` is honoured** (a PirateBot system message overrode Lumo's
  ~416-token prompt). Self-scoped model behaviour only → NOT reportable; recorded so the next pass
  does not re-litigate it.
- Evidence: `D:/data hermes/proton-audit-v2/0C/ssrf/` (FINDING-P01.md, oast-interactions.jsonl,
  ssrf-timing.json, port-matrix.json, request/response, canonical-verification.json) +
  `submission/Proton_Lumo_SSRF_P01.pdf` (5 pp) + `body_P01.txt`.

### Signup decoy field — precise mechanism (refines the older "real input is in the iframe" note)

The current single-signup UI keeps `#username` in the DOM with a **real bounding box but
`visibility:hidden` and `x=-956` (off-screen)** — a decoy that catches "fill every input" automation.
`#password` is the only genuinely visible input. Clicking the `Free` plan card flips
`aria-pressed=true` but does NOT reveal the username field; "Use your current email instead" only
swaps a label; 40 Tab presses never land on a visible text input; JS-forcing visibility then clicking
yields "Element is outside of the viewport" and **zero POST**. Telemetry emits `random_uid_created`
(the address is pre-generated before submit). Conclusion: the HV gate works — this is a *coverage
limit*, not a bug, and it is why a second Proton identity cannot be self-provisioned. Say that plainly;
do not burn rounds on it. (The browser was `headless=False`; this is not a headless artifact.)

### SimpleLogin — now ACTIVATED and usable (product is in scope)

Self-provisioning DOES work here, so this is the one identity you can create yourself:
`POST app.simplelogin.io/api/auth/register {email,password,password_confirm}` needs a real mailbox
(proton.me addresses and disposable domains are rejected as "personal inbox"); the verification mail
contains a **6-digit code, not a link**; activate with
`POST /api/auth/activate {"email":…,"code":…}` → `{"msg":"Account is activated…"}`.
Code-only (`{"code":…}` or `{"Code":…}`) returns **500 Internal error** — that 500 means the shape is
wrong, not that the account is bad. Login returns a 60-char `api_key`; the JSON API then wants header
**`Authentication: <api_key>`** (the `slapp` cookie alone is not enough; `/api/aliases` without it →
500). Useful paths: `/api/mailboxes`, `/api/aliases?page_id=0` (paging is mandatory),
`/api/aliases/{id}`, `/api/aliases/{id}/activities|contacts?page_id=0`. `/api/user/info` → 404.

Verified negatives (skip these): authz sweep over 7 ID-bearing routes — own alias 200, foreign alias
**403 Forbidden**, and the server-rendered dashboard routes **redirect to `/dashboard/`** (deny);
`GET /api/aliases/{id}` splits 403 (exists, not mine) from 400 "Unknown error" (absent) = existence
oracle only, info-only. A custom-domain claim stays unverified without the `sl-verification=<30 chars>`
TXT + MX records; clicking Verify causes **no state change and no POST** (the server re-checks DNS).
Reserved subdomains (`admin`,`test`,`mail`,`support`,`api`) are rejected. **The subdomain quota is 5
and the UI text lies**: "Currently you can create up to N subdomains" is the REMAINING allowance, not
the plan limit (1 used → "up to 4"; 5 used → "up to 0", Create disappears) — do not file that as a
bypass. No public directory endpoints (all 404).

### Other Round-4 negatives (artefacts under `D:/data hermes/proton-audit-v2/0C/`)

- **Drive public-link SRP**: contract is `POST /api/drive/urls/{token}/auth {ClientProof,
  ClientEphemeral, SRPSession}` → `ServerProof, UID, AccessToken`; `/urls/{token}/info` returns only
  `{Modulus, ServerEphemeral, UrlPasswordSalt, SRPSession, Version, Flags}` (no Share, no token).
  Seven malformed variants (null, empty, garbage b64, each required field omitted, server-ephemeral
  replayed as client, integer 0) all rejected 400/422 — **no token ever issued**, and the client
  verifies `ServerProof` ("Unexpected server proof"). Minting your own password link needs ~10
  client-computed E2E fields (`SRPVerifier`, `SharePassphraseKeyPacket`, both salts, `Permissions`,
  `MaxAccesses`) → still UNTESTED.
  **Rate-limit claim warning:** 30 rapid `/auth` calls gave 30×422 with no 429, but they were rejected
  at **parameter validation** (a random 256-byte ephemeral is not an SRP group element), so they were
  never password guesses. Do NOT report "no brute-force protection" off that.
- **Wallet**: `GET /wallets/{id}` is **405 (Allow: DELETE)** — only the list is servable; wallet IDs
  are opaque base64 (no enumeration). `blocks/height/abc` is parsed leniently to 0 and returns the
  genesis hash (public chain data → info-only). A burst of wallet calls returns
  `422 {"Code":2028,"Error":"Our systems detected unusual activity…temporarily limited access"}` —
  an **account-level anti-abuse throttle after heavy testing**: operational state, not a finding.
- **Docs importer autodiscovery** `GET /api/importer/v1/mail/importers/authinfo?Email=` on docs.proton.me:
  static provider map (`gmail`→imap.gmail.com, `outlook`→outlook.office365.com, everything else no
  host), **zero DNS/HTTP callbacks** to an OAST domain, IP literals rejected → no SSRF, no user enum.
- **Pass public links**: `/public_link/content/{t}` is a uniform `422 Secure link does not exist`
  **whether authed or not** (no privilege confusion); `/public_link/files/{t}` → "This token is not
  valid"; `/files/{t}/{f}/{c}` → `400 Code 2061 Invalid ID` (format check fires before any lookup).
- **Cookies**: `AUTH-*` / `REFRESH-*` / `Session-Id` are HttpOnly+Secure+SameSite=None; only the
  non-sensitive `Tag` cookie lacks HttpOnly. No finding.
- **nuclei coverage** — the 6-tag set (exposures, exposed-panels, misconfiguration, default-login,
  takeovers, unauth; med/high/crit) **completed** on all 22 hosts: 1h42m, 1 111 templates, 58 089
  requests, 95% of 60 830, **0 matches**, 779 template-level errors (1.3%), every host still answering
  afterwards = legitimate negative **for that tag set only**. The 11-tag set (cve/jwt/graphql/swagger/
  homegrown) died at ~12% twice. Check RAM first: this host runs several simultaneous engagements and
  5 nuclei instances push free RAM under 400 MB. Killing your run is correct; claiming "clean" is not.
- FFUF across 7 app hosts flags `.env`/`.git/config`/`actuator/*`/`Dockerfile` as 200/403 — **all
  soft-404**: identical SPA index sha256 to a random path, while `/api/doesnotexist` is a real 404
  JSON. `dalfox` on `calendar/signup?ref=` is a **false positive** (param never reflected; identical
  8 205-byte body with and without payload; the bundle only does `params.append("ref", …)` into a
  redirect URL — no DOM sink).
