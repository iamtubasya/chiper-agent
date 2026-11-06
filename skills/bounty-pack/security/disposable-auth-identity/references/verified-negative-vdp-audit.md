# Verified-Negative VDP Audit Cookbook (Next.js SaaS)

Source session: quarterwise.co.uk (Malden Ltd) VDP audit 2026-09-26. Authorized via
public VDP + safe harbor. Outcome: **zero rewardable findings** — the report itself was the
deliverable, backed by a per-tool evidence matrix. This cookbook encodes what made that
audit fast, defensible, and honest.

## 1. Scope gate before ANY probing (kills wasted effort)
- Fetch `/.well-known/security.txt` and its linked `/security/disclosure` page FIRST.
- Parse exact scope: apex + signed-in app + API vs out-of-scope. QWC example: **all
  subdomains** (dev/direct/mail/www) out of scope, third-party SaaS (Stripe/Postmark/
  Cloudflare/HMRC API) out of scope — testing them means reports auto-N/A.
- Rules that shape testing: own accounts only, never touch others' data, no DoS/volume
  testing, no email to strangers, confidentiality until fix / 90 days.

## 2. Full tool coverage map (answers "did you use ALL tools, not just curl?")
Run every class tool and keep outputs on disk. curl is only a session-holding HTTP
verifier (cookie'd 200/401/404 checks) — never a vuln scanner on its own.

| Class | Tool | QWC result |
|---|---|---|
| subdomain | subfinder | 5 hosts (out of scope) |
| probe/tech | httpx | Cloudflare, Next.js, HSTS |
| URL discovery | gau + waybackurls + katana | 129+ URLs |
| ports | naabu top-1000 | CF edge only |
| vuln scan | nuclei general (rl 8, low→crit) | 2 TLS weak (low/info) |
| vuln-by-class | nuclei -tags sqli,lfi,ssti,xxe,nosqli,redirect,csrf | 0 |
| discovery | ffuf root + /api/ (70 words each) | 8 paths, all already mapped |
| SQLi | sqlmap --level 1-2, authenticated param | not injectable (87x HTTP 403 = CF rate-limit working) |
| XSS | dalfox 162 URL targets | 0 |
| OOB | interactsh-client | 0 callbacks |
| authz / IDOR | Chrome CDP, 2 profiles + 2 accounts | all cross-tenant actions denied |

## 3. Verified-negative is a legitimate deliverable
- Zero findings is honest when the matrix above is populated from disk artifacts — the
  user's "did you use all tools?" is answered by the table, not by a claim.
- Report shape: scope gate → methodology table → per-vector results with denial strings →
  observations (non-rewardable hardening) → conclusion + follow-ups requiring more
  authorization (full OTP brute-force, Pro-plan features).
- Collect denial strings verbatim as evidence (QWC examples):
  - foreign property page: **"We can't find that page"**
  - foreign txn write: **"That property could not be found."**
  - owner-only settings: **"Only the owner can change these settings."**
  - replayed/stale server action: HTTP 500 `E{"digest":"..."}` (expected — NOT a finding)

## 4. OTP / forgot-password probing within VDP policy
- VDPs ban volume testing: probe with YOUR OWN account only, ≤ ~6 wrong codes, then stop.
- QWC observations: wrong code → **"That code is not correct."**; no lockout after 6 tries;
  resend cooldown ~12s; code TTL 10 min; registered vs unregistered email → IDENTICAL
  "Set a new password" page (anti-enum good).
- Brute-forcing a 6-digit OTP needs ~5e5 guesses / 10-min TTL → impractical AND breaches
  the no-volume-testing rule. Stop at observing the missing lockout; report as a hardening
  observation, not a vuln.

## 5. Chrome CDP session mechanics
- `--remote-allow-origins=*` is REQUIRED for Python `websocket-client` CDP, else
  403 "Rejected an incoming WebSocket connection" (the in-session browser harness uses its
  own allowed origin; external websockets do not).
- Restarting Chrome with the SAME `--user-data-dir` keeps the session cookie; the tab may
  show /login while the stored session is still valid — re-login via CDP and re-capture the
  `qw_session` cookie for curl.
- Stuck debug port: `netstat -ano | grep :9222` → LISTEN pid, kill with
  `powershell Stop-Process -Id <pid> -Force`. MSYS mangles `//F` for single-PID taskkill;
  CLOSE_WAIT entries linger after death — check LISTEN, not any port match.
- Full server-action POST body: attach `requestId` from `Network.requestWillBeSent`, then
  `Network.getRequestPostData {requestId}` — the event's own `postData` is truncated.

## 6. False-positive traps that manufacture a finding out of nothing

Each of these produced a scary-looking result in the 2026-09 Quarterwise session that dissolved
under one extra control. Run the control BEFORE writing anything down.

- **Following redirects turns a denial into a bypass.** After the password step of a 2FA login the
  app issues a pre-MFA cookie (`qw_mfa`) and nothing else. A naive `requests.get('/app')` with
  `allow_redirects=True` (the default) followed the 307 to `/login`, got the login page, and
  reported `200 / 49652 bytes` — which reads exactly like an authenticated-data leak. Re-run with
  `allow_redirects=False`: `307` to `/login`, and every API path `401`/`307`. Always set
  `allow_redirects=False` when the question is 'did this request succeed', never when it is
  'where does this end up'.
- **A 200 with a full HTML page from a server-action POST is a no-op.** See the sibling reference;
  verify the state change, not the status code.
- **XLSX cells that start with `=` are usually NOT live formulas.** Before claiming CSV/Excel
  injection, unzip the export and inspect the sheet: a cell rendered as
  `<c r="D6" t="s"><v>11</v></c>` with `<t>=2+2</t>` in `sharedStrings.xml` is a SHARED STRING —
  Excel displays it as text and never evaluates it. A real injection needs a formula cell
  (`<f>` element) or an un-prefixed `=` in a CSV that a spreadsheet will re-parse on open. Report
  the round-trip (raw value survives ledger, PDF and adviser CSV feeds) as a LOW/informational
  hardening note, and say plainly that the xlsx path is not exploitable. Do not inflate it.
- **A 500 from a replayed action is not automatically an authorization block.** It means something
  threw. Get the control: same action, same jar, attacker's OWN object → 200 with a visible
  mutation. Only then does 500-on-the-swap mean 'guarded'.
- **An empty grep is not an absence.** Searching the rendered HTML of the adviser page for the
  victim's NINO returned nothing, but so did searching for the words 'National Insurance' — the
  first pass was a broken pattern, not a clean result. Always include a positive control string in
  the same grep to prove the search itself works.

## 7. Cache deception / cache poisoning probe set

Cheap, high-yield, and usually omitted. On a CDN-fronted app the question is whether an
authenticated page can be pulled from cache by an unauthenticated request.

1. Append static-looking suffixes to an authed path and read the response headers, not the body:
   `/app/account/x.css`, `.js`, `.jpg`, `.png`, `.woff2`, `.txt`, `/app/account;.css`,
   `/app/account%00.css`, `/app/account.json`.
   Verdict is in `cf-cache-status` (or `x-cache`) plus `Cache-Control`. `BYPASS`/`DYNAMIC` +
   `private, no-cache, no-store` = not cached, no deception.
2. For genuinely cached public pages, compare the body byte-for-byte across three identities
   (owner cookie, unrelated cookie, no cookie) — `md5sum` per identity. Identical hashes = the
   cached variant carries no per-user data.
3. Grep that cached body for a positive control: the victim's name, email, session-cookie name,
   `Log out`, `Dashboard`. Zero hits on all of them is the evidence.
4. Check for `Set-Cookie` on cached responses — a cached `Set-Cookie` is a session-confusion bug.
5. Unkeyed-header poisoning: replay a page with `X-Forwarded-Host`, `X-Host`, `X-Forwarded-Server`,
   `X-Forwarded-Proto`, `X-Original-URL`, `X-Rewrite-URL`, `Forwarded` and diff the body md5
   against the baseline. No hash change and no reflection of the injected host = clean.
   A `Cache-Control: private, no-store` response reporting a cache HIT is worth a second look, but
   if the body is identical across identities it is a caching-rule curiosity, not a leak.

## 8. OAuth / OIDC callback state-binding matrix

For any connect/authorize flow (HMRC, Google, bank aggregators) the callback is the testable part
even without valid provider credentials. Discover it by probing `/api/<provider>/callback` — note
that the app-level path (`/app/<provider>/callback`) may 404 while the API-level one answers.

Send the SAME valid `state` (lifted from the authorize URL the app just generated) four ways and
record the redirect target for each:

| Attempt | Expected |
|---|---|
| valid state + the issuing session | proceeds (fails later at code exchange — expected with a fake code) |
| valid state + a DIFFERENT account's cookie | state mismatch → no connection |
| tampered/mutated state + issuing session | state mismatch |
| no state, and unauthenticated | mismatch / redirect to login |

All four deny = CSRF and session-binding are enforced, verified negative. A `state` shaped
`<hex>.<base64url>` is a signed token; if you can mutate the signature or the payload independently
and still get past the check, that is the finding.

## 9. Declare the zones you could not reach

The honest close of a verified-negative report names the surfaces that were gated and what would
unlock them, so the client never reads 'no findings' as 'audited everything'. On a tiered SaaS that
is usually: paid-plan features behind a subscription (API keys, receipt/AI processing, document
store, multi-object limits) and any third-party connect flow that needs a real provider sandbox.
State the unlock explicitly (for example: a Pro subscription, or a provider developer sandbox
account) and offer to continue — do not silently imply coverage you did not have.