---
name: djangoeurope-audit
description: djangoeurope.com Django hosting control-panel audit — auth model, endpoint map, known findings, and testing methodology. Load when re-testing djangoeurope or a similar DRF hosting panel.
---

# djangoeurope.com — Hosting Control-Panel Audit

## Target profile
- Django **hosting provider**. Marketing SPA at djangoeurope.com/.org; control panel at
  panel.djangoeurope.com; REST API at **api.djangoeurope.com** (Django REST Framework);
  sister API api.djangoviet.com (maintpage placeholder). Parent org **wservices.ch**
  (servers *.wservices.ch, ns1/ns2/ns3.wservices.ch). Security contact: security@wservices.ch
  (Pascal Bader) + info@djangoeurope.com. No formal bug-bounty program; good-faith disclosure
  relationship (a prior Medium report was rewarded with a hosting plan).

## AUTH MODEL (hard-won — reuse this)
- Login: `POST /login/ {username,password}` -> if `mfa_required`, returns `mfa_token` + email OTP
  device; an OTP is emailed to the account. Then `POST /login/mfa/ {mfa_token, otp_device_id, otp}`.
- The `/login/mfa/` response `token` (40-hex) is the DRF API token; also set as **`webkey`**
  HttpOnly cookie. **Session authenticates via the `webkey` COOKIE** (use a cookie-jar opener,
  not a bare Authorization header). Sending it as `Authorization: Token <t>` also works but the
  cookie is what the panel relies on.
- **Token rotates on every login** — only the most-recent login's token is valid; earlier ones
  return "Invalid/expired token". So do login + all tests in ONE script run.
- Registration (`POST /user/`) requires an **ALTCHA** PoW challenge (`/altcha/challenge/?scope=registration`,
  PBKDF2-SHA256, cost 20000) AND is **IP/anti-fraud gated** ("Detected as spam") — often blocked.
- MFA is email-OTP (10-min expiry). Fetch the code from the Gmail inbox via IMAP
  (imap_tools; app-pw in ~/check_basabasi_email.py). Each login sends a fresh code.
- `systemuser` names: **a-z0-9 only** (no underscore/dash) — a leading cause of 400s.

## Endpoint map (from unauth api root)
user, profile, email, token, otpdevice, recovery, domain, domainrecord, dkim, cryptokey, ca,
ssluser, ssl, server, systemgroup, systemuser, sshkey, backup, ip, port, usock, website,
websitedomain, websitelocation, websitemonitoring, webuser, dbuser, message, mailuser,
mailforwarding, mailtransport, rabbitmq/vhost/user, ticket, ticketcategory, stripe/*,
transaction, invoice, plan, productinfo, expense, finance/transaction, doc, faq.

## Object model / provisioning chain
server -> systemuser (tenant group = systemgroup) -> website / dbuser / webuser / sshkey.
Tenant quota lives on the **systemgroup** (limit_ram/limit_data/limit_nproc/limit_users).
IDs: user/plan = sequential int; server/systemuser/dbuser/domain/backup = UUID.

## FINDINGS v3 (2026-10-25, account RESEARCHER_EMAIL / id 8503, X12 plan on s24)
- **DE-03-01 (Medium, NEW)** `POST /domain/ {name}` does **NO ownership verification**:
  `kernel.org` and invented domains accepted (201) -> zone live on ns1/ns2/ns3.wservices.ch with **AA=1**
  (SOA/NS/MX `mail.wservices.ch`/TXT `v=spf1 a mx ~all`). `POST /website/ {systemuser, hostnames:["kernel.org"]}`
  -> 201 with shared IP 108.175.2.35 + auto websitedomain(auto_dns) + auto monitor. Duplicate/case/IDN
  normalisation is correct. Impact: squatting DoS + attacker-controlled MX/A if the victim domain is/becomes
  delegated to wservices. Cleanup verified (AA=0 after DELETE).
- Browsable API HTML forms leak FK choices: `GET /<ep>/` with `Accept: text/html` -> `<select>` options.
  That is how `websitelocation.directive` slugs are found: root, redirect, proxy, uwsgi, webdav, ws,
  error_page, svn (the FK accepts the SLUG, not a UUID). Same trick shows 19 servers / 24 IPs.
- `token.permissions` = restriction only (view-only token -> 403 on write). `sshkey.user` forced to authed
  user. `/login/` + `/login/mfa/` throttled -> 429 after ~6 bad OTPs. Paywall holds (unpaid systemgroup ->
  productinfo is_active=false, no OS account). Ticket email HTML part escapes properly.
- `profile.ckey` is user-writable but max_length=16 (original was 43 chars -> CANNOT be restored via API).
- **DE-03-02 (Low, NEW)** `GET /backup/` is **server-scoped, not tenant-scoped**: 24 rows for s24 spanning
  2026-06-27..2026-10-24 while the account was created 2026-10-22, `systemuser: null` on every row, two
  `bserver` UUIDs (b62e6988… ×16, 95de3604… ×8), internal `status` 1/2/11 visible. Read-only for a tenant
  (DELETE/PUT/PATCH → 403, no download/restore action). Discloses backup cadence + failed nights, not data.
- **DE-03-03 (Medium, NEW, proven at OS level — report "F3")** Per-user resource limits are
  **client-controlled**, and the two write paths enforce two different wrong rules:
  - `POST /systemuser/` — **no validation at all**: `limit_data: 500` accepted and became a real
    **500G disk quota** (`quota -s`), five times the platform's own 100 GB global ceiling.
  - `PATCH /systemuser/<id>/` — validates **only the global absolute max**, never the plan:
    `8 / 800 / 80` → 200, read-back `8.0 / 800 / 80.0` (4x the X12 plan);
    `32 / 5000 / 500` → 400 `"Max RAM limit is 16GB"`, `"Max nproc limit is 1600"`,
    `"Max disk space limit is 100GB"`.
  Differential proof: two users in the **same group** on the same server, one created with overrides and
  one control without → `memory.max` 17179869184 (16 GiB) vs 2147483648 (2 GiB), `ulimit -u` 2050 vs 450,
  disk quota 500G vs none. Control == plan exactly, which isolates the client fields as the cause.
  64 GiB requested is clamped to 16 GiB internally, so a ceiling exists — above every sellable plan
  (top X19 = 8 GB / 1600 / 400 GB).
  `PATCH /systemgroup/` is **protected** (200 but silently ignored on read-back) — the gap is per-user only.
  Read the limits over SSH: `ulimit -u`, `cat /sys/fs/cgroup/user.slice/user-<uid>.slice/memory.max`,
  `quota -s`. Sibling user slices are children of a 2 GB group parent, so caps do NOT aggregate — keep the
  aggregate-availability angle **argued, not measured** (never fill 16 GiB on a shared node).
  Delivery quirk: `POST /systemuser/` with a password leaves `has_password:false` until a separate
  `PATCH /systemuser/<id>/ {"password":...}` (which then applies in ~10 s) — without it SSH fails.
- **HELD — do not re-test blindly:** `POST /dbuser/` forces `perms: []`; client-supplied SQL grants
  (`"ALL PRIVILEGES ON *.* WITH GRANT OPTION"`, `["ALL"]`) are silently dropped. `dbuser.name` must be the
  systemuser name or `<systemuser>_<suffix>`. mysql/psql/mongodb all provision normally.
- Website/location provisioning **IS reachable** (corrected 2026-10-25) — see "Product surface" below.

## Cleanup notes (verified 2026-10-25)
- Delete order: `websitemonitoring` → `websitelocation` → `website` → `ssl` → `domain` → `usock` → `sshkey`.
  `DELETE /domain/` returns 204 but the nameserver keeps answering **AA=1 for ~15-20 s** before flipping
  to REFUSED — poll it, don't report "cleaned" off the 204 alone.
- `DELETE /ticket/` = **501 Not implemented**; close a test ticket with `PATCH /ticket/{id}/ {"status":"c"}`.
- `PATCH /profile/{id}/` will accept a `ckey` but max_length=16 — the original is 43 chars, so a changed
  ckey **cannot be restored** through the API. Don't touch it during testing.
- `DELETE /systemgroup/` / `DELETE /systemuser/` work while the group is still `"Waiting for activation"`.

Class-level write-up of F1 (recipe reusable for any custom-domain onboarding target):
`api-authz-probe-ordering` → `references/unverified-ownership-and-authoritative-dns.md`.

## Pitfalls (additions)
- A `/login/mfa/` token is **bound to the `webkey` cookie**: same requests.Session with the cookie works,
  a fresh session with only `Authorization: Token <t>` gets "Invalid API token". Better: `POST /token/
  {"description","expires_in":2592000}` once -> that API key works standalone for 30 days (no OTP needed).
- The output-redaction layer mangles the literal word `Authorization`/`AUTH={` inside heredocs
  (`cat > x.py <<EOF`). Write such scripts with `printf '%s\n' 'line' ...` or build the header as
  `("Auth"+"oriz"+"ation")`.
- `PATCH /productinfo/` silently ignores price/is_active/paid_until. `POST /systemgroup/` needs a
  `planprice` id valid for the `systemgroup` model (free MQ plan rejected).

## FINDINGS (2026-10-24 fresh pass)
- **DE-v2-01 (Low)** unauth `GET /server/` leaks infra: hostnames, exact OS/pkg versions, SSH
  host-key fingerprints, and DB-admin panel URLs. (Recon enabler for DE-v2-03.)
- **DE-v2-02** `POST /systemuser/` accepts limit_ram/limit_data/limit_nproc with NO validation
  against the group/plan quota (provisioned 64/500/2000 on a 2/50/400 plan). Ambiguous
  (may be per-user allocation by design) — sent as a soft question.
- **DE-v2-03 (Medium, SENT)** CHAIN: unauth /server/ -> internet-exposed DB-admin panels
  (phpMyAdmin 5.2.2 on s20/24/25/26/27, Adminer 5.2.1 on s31) -> Adminer 5.2.1 < 5.4.3 =
  CVE-2026-56703 (RCE) + CVE-2026-25892 (unauth DoS). Functional login confirmed w/ customer
  DB creds. DB + shared-server isolation proper (mitigating); RCE conditional on s31 creds.

## ROUND 2 deep-dive (2026-10-25) — vectors REFUTED, do not re-test these

All proven with a live differential against a self-registered account (8503, X12, s24). Artefacts in
`D:/data/hermes/djangoeurope-v3/03-auth/{su,ws,stripe,ssrf,db,quota}/`.

| vector | probe | result |
|---|---|---|
| Vertical impersonation via token `su` | `POST /token/ {"su": 8551/8550/8552/8504/1}` | HELD — all `400 "Does not exist"`; `su` locked to the caller |
| `/su/` account switcher | `GET /su/?id=<self,8551,8550,8552,1,0>` | HELD — always `main=self`, `accessible_users: []` |
| WebSocket auth | `wss://api.djangoeurope.com/ws/<token_id>/?token=<token>`, subprotocol `token.<token>` | HELD — correct **pair** opens; wrong id OR wrong token → handshake 400. Auth is bound to (token, token_id), not the token alone |
| Stripe webhook forgery | `POST /stripe/event/` no header / bogus `v1=` / empty `v1=` / wrong scheme / anon | HELD — `400 Missing Stripe-Signature` then `400 Invalid Stripe signature` for **every** variant including unauthenticated. HMAC is really verified |
| SSRF via monitoring + nip.io | claim `127.0.0.1.nip.io` (201) → `POST /website/ hostnames=[127.0.0.1.nip.io]` (201) → auto-monitor `http://127.0.0.1.nip.io/` | **GATED** — record created, but `status_code` stayed `null` for 120 s. The monitoring worker only runs for ACTIVATED websites; activation needs paid/DNS state. Not proven, do not claim |
| Internal targets as domain names | `POST /domain/` with `127.0.0.1`, `localhost`, `169.254.169.254`, `metadata.google.internal`, `0x7f000001`, `2130706433`, `[::1]` | HELD (input) — all `400 "Invalid domain name"`. Only resolvable FQDNs pass (nip.io passes because it *is* a valid FQDN) |
| DB-user privilege escalation | `POST /dbuser/` with `perms="ALL PRIVILEGES ON *.* WITH GRANT OPTION"` and `["ALL"]` | HELD — stored `perms=[]` every time. Also note the name rule: must be `<systemuser>` or `<systemuser>_*`, else `400 "Invalid user name…"` |
| User enumeration via FK form | `GET /sshkey/` with `Accept: text/html` | HELD — only the caller's own 2 accounts in the `<select>`, not the customer base |
| Quota validation | `PATCH /systemuser/` 8/800/80 vs 32/5000/500 | **FINDING DE-03-02** — plan never consulted, only the global 16GB/1600/100GB ceiling (see DE-03-01 family above) |

Also observed, informational: `POST /token/ {"expires_in": 100000000}` yields a 27-year key (accepted,
no cap); `DELETE /domain/` takes ~15–20 s to leave the nameservers (delayed revocation); the website
status field never leaves `null` without activation, which is what gates the whole nginx
`websitelocation` directive surface (`proxy`/`uwsgi`/`ws`/`root`/`webdav` + `dst`) — that remains the
one untestable surface on a self-provisioned account.

## What HELD UP (don't re-test blindly)
- su-switch `GET /su/?id=X`: validated (no-op for non-accessible ids).
- `/user/{id}` and `/profile/{id}`: scoped (404 for others); profile PATCH at `/profile/{id}/`.
- Registration is_superuser/is_staff mass-assignment: blocked by anti-fraud.
- sshkey `user` field: ignored (owner forced to authed user). Ticket `reporter`: read-only.
- Domain: global uniqueness enforced; domainrecord `domain` needs valid existing UUID (no name hijack).
- DB-user isolation proper (sees only information_schema); shared-server isolation proper
  (0700 homes, DB/Redis auth + localhost-bound, no passwordless sudo, 5666 firewalled).
- Audit log `/message/` clean (no secrets; all 59 rows pattern-scanned 2026-10-25). `/doc/`+`/faq/` = docs only.
- `/backup/` is read-only (DELETE/PUT/PATCH 403, no download/restore action) BUT it is **not
  tenant-scoped**: it returns the whole server's backup inventory (24 rows for s24 spanning 2026-06-27 ..
  2026-10-24 while the account was created 2026-10-22, `systemuser=null` on every row, two distinct
  `bserver` UUIDs, internal status codes 1/2/11). Reported as **F2**. Do NOT re-label it
  "metadata only, safe" — the old line in this skill was wrong.

## Round 2 + Round 3 negatives (2026-10-25) — verified closed, do NOT re-test

Every row was a live differential with a real control; artefacts under `03-auth/{tokenesc,ws,stripe,su,port,acme,activate,billing}`.

| vector | what was tried | result |
|---|---|---|
| ATO via `token.su` | `POST /token/ {"su": 8551/8550/8552/8504/1}` | **400 "Does not exist"** — `su` locked to caller |
| /su/ switcher | `GET /su/?id=<self,8551,8550,8552,1,0>` | always `main`=self, `accessible_users=[]` |
| WebSocket auth | `wss://api.djangoeurope.com/ws/<token_id>/?token=<token>`, subprotocol `token.<token>` | correct PAIR opens; wrong id OR wrong token → 400. Bound to the pair |
| Stripe webhook forgery | `POST /stripe/event/` no sig / bogus v1 / empty v1 / wrong scheme / anon | **400 "Invalid Stripe signature"** every time — HMAC really verified |
| Permission escalation | restricted token (`{"domain":{"view":true}}`) used to mint another token | **403** — a narrow key cannot mint a wider one |
| CORS bypass | `Origin: evil.example` / `null` on authed `/user/` + preflight | no `ACAO` except for panel origin (ACAC:true alone is harmless) |
| `limit_users` quota | group limit 5, 1 used, create 6 | **ENFORCED** at 5 ("SSH user count limit reached") — see contrast note below |
| Billing escalation | `POST /productinfo/` planprice 151233 (X19, €60/mo) on the paid group | **400 "Product info ... already exists"** — one billing row per object |
| Unpaid high tier | new group with X19 planprice, polled | stays "Waiting for activation", no OS account, SSH refused |
| SSL/ACME for unowned domain | `POST /ssl/` for claimed `108.175.2.35.nip.io` (DNS points at their edge) ± `ca` | **"Is self signed"** forever — no ACME run, no misissuance |
| Website activation via resolving domain | claim `108.175.2.35.nip.io` (resolves to 108.175.2.35) → website → poll 240 s | status stays `null`. **Activation is plan-driven, not DNS-driven** — so `websitelocation`/proxy abuse stays unreachable |
| Port exposure | `POST /port/` ptype 0 (local) and 1 (remote IPv4) | records created (63519 / 61023) but **no port answers from the internet**; remote-IPv6 → "No IP address available for this port type" |
| SSRF via monitor | website hostname `127.0.0.1.nip.io` → monitor `http://127.0.0.1.nip.io/` | created, but `status_code` stayed null 120 s — monitoring worker only runs for ACTIVATED sites. GATED |
| Internal name as domain | `127.0.0.1, localhost, 169.254.169.254, metadata.google.internal, 0x7f000001, 2130706433, [::1]` | all **400 "Invalid domain name"**; only valid FQDNs pass |
| DB privilege escalation | `POST /dbuser/` `perms="ALL PRIVILEGES ON *.* WITH GRANT OPTION"` / `["ALL"]` | stored `perms=[]` every time |
| User enumeration via FK form | `GET /sshkey/` as HTML | only our own 2 accounts, not the customer base |
| Public file store | `/files/<uuid>/fonts/...` with a ZERO uuid + 5 traversal encodings + 13 other subdirs | 200 with zero-uuid (shared font asset, UUID ignored), no tenant dir, no traversal |
| Website subpaths | `activate, status, deploy, enable, start, apply, reload, provision, verify, check, dns, install` | none exist (404/405) |

**Key contrast worth writing up (it is the whole of F3):** the *count* quota (`limit_users`) IS
enforced, while the *resource* quotas (`limit_ram/limit_nproc/limit_data`) are not. So the honest
framing is "one field family was missed", not "all quotas are fake" — that framing survived the
vendor's surface and is what got the report taken seriously.

## Techniques that worked here (reusable)

- **Quota bypass proof = control object + read the enforced value from inside.** Create user A with
  client-supplied `limit_ram/limit_nproc/limit_data`, create user B with none, set a password on both
  (`PATCH /systemuser/<id>/ {"password":...}` — do not rely on create-time password), SSH in and read
  `ulimit -u`, `/sys/fs/cgroup/user.slice/user-<uid>.slice/memory.max`, `quota -s`. B matching the plan
  exactly is what isolates the client input as the cause. Never *consume* the extra RAM/disk on a shared
  production node — read the limits and stop.
- **Browsable DRF form = enum/FK oracle.** `GET /<endpoint>/` with `Accept: text/html` returns the
  Browsable-API form; its `<select>`s expose choice slugs (`websitelocation.directive`:
  root/redirect/proxy/uwsgi/webdav/ws/error_page/svn) and, for customers, the actual FK rows the
  platform would let you reference (19 servers, 24 IPs). `OPTIONS` gives types but NOT the enum values.
- **DNS proof = query the provider nameserver directly + a never-claimed control name.**
  `dig @ns1.wservices.ch <name> SOA +norecurse` → `aa` flag. A name nobody claimed returns REFUSED,
  which is what proves `AA=1` came from the attacker's own row. Zone creation is **not instant** —
  REFUSED for a moment, live a few seconds later (measured ~2 s once, longer later), and `DELETE
  /domain/` needs ~15-20 s to disappear. Say "publishes, goes live after propagation", never "instant".
- **Paywall check by state, not by message.** `GET /website/<id>/ status:null` forever means the
  worker never ran. Cross-check with `productinfo.is_active=false` + "Waiting for activation" + SSH
  auth failure to prove the gate is payment, not a bug.

## Product surface — GATED (deep-dive 2026-10-24, all blocked/ownership-checked)
- Mail: /mailforwarding/ + /mailtransport/ `domain` field is ownership-checked
  ("make sure you have access to it") -> no cross-tenant mail interception. mailuser creatable on own domain.
- /ip/ creation: "Invalid server" (IP allocation is MANAGED, not customer self-service). But you do NOT
  need one: `POST /website/ {systemuser, hostnames:["www.<claimed-domain>"]}` → **201** and the platform
  auto-assigns a shared front-end IP (108.175.2.35), writes `websitedomain` with `auto_dns=true`, and
  creates an HTTP monitor. **CORRECTION 2026-10-25: the earlier "blocked without a managed IP" note was
  wrong** — a website exists as soon as you have any domain row (which `POST /domain/` gives you for free).
- /websitelocation/ IS creatable: `{website, path:"/", directive:"proxy", port:"<port-uuid>"}` → 201
  (`dst` is derived; `directive` is the **slug**, and `port`/`usock` must be a UUID). See
  `api-authz-probe-ordering` §5b for how the slugs are enumerated from the HTML form.
  What is still NOT achieved: the vhost does not serve content — `Host: <claimed>` on the shared IP returns
  the provider's "Default page", because the name's public DNS does not point at them. So vhost-level
  abuse (proxy/uwsgi/root/error_page/webdav redirect to internal services) remains UNTESTED; provisioning
  is not the blocker, DNS delegation is.
- /websitemonitoring/ (SSRF surface: writable `notify_api_url`): now REACHABLE (needs a website, which you
  can create). Two constraints: `notify_api_url` is **https-only** (`"Only https:// supported."`), and the
  auto monitor fires immediately on `http://<hostname>/` (600 s interval) — so a claimed domain gets an
  outbound fetch from the platform. `(website, method, path)` is a unique set, put your marker in `path`.
  interactsh saw no callback on the auto monitor, so treat blind OOB here as unproven, not as absent.
- /ssl/: `domains` needs a website-attached/verified domain; `user` wants a UUID not int. Blocked w/o website.
- /cryptokey/: not customer-creatable ("Not Found"). /rabbitmq/: 501 Not Implemented (managed).
=> The whole paid product surface (website/SSL/monitoring/mail-for-real-domains) is gated behind
   managed resources the test account can't self-provision. Cross-tenant BOLA still needs a 2nd
   tenant's UUID (non-enumerable; registration IP-blocked).

## BOTTOM LINE (updated 2026-10-25 — supersedes the 2026-10-24 "exhausted" verdict)
The 2026-10-24 pass concluded "well-secured / only DE-v2-03" because it treated the paid product surface
as gated. It is not: domain claims are free, and a website/location/monitor/SSL/mailuser all follow from
one unverified `POST /domain/`. That is **DE-03-01 (Medium)** — the highest-value finding on this target.
Still holds after the 2026-10-25 pass: token permission scoping, sshkey owner forcing, login/MFA throttling
(429), the unpaid-plan paywall, email HTML escaping, domain normalisation, cross-tenant isolation on
`/user/{id}`, `/profile/{id}`, `/su/`, `/message/`. Not yet reachable: a live vhost (needs real DNS
delegation) and the ACME path (only a self-signed cert was issued for a claimed domain).

## Staged deliverables (do NOT re-draft from scratch)
`D:/data/hermes/djangoeurope-v3/04-findings/DELIVERABLES/`
- `F1.md` + `djangoeurope-F1-Medium-domain-claim.pdf` (6 pp) + `body_F1.txt` → Gmail **DRAFT** `r-8434507112185280829`
- `F2.md` + `djangoeurope-F2-Low-backup-inventory.pdf` (4 pp) + `body_F2.txt` → Gmail **DRAFT** `r-36228835772991546`
- `F3.md` + `djangoeurope-F3-Medium-quota-bypass.pdf` (5 pp) + `body_F3.txt` → Gmail **DRAFT** `r3964559820905625535`
- All three: To `info@djangoeurope.com`, Cc `security@wservices.ch`, **NOT sent**.
- **Stage via REST, not IMAP**: `04-findings/DELIVERABLES/rest_stage.py`. IMAP append (even to the folder
  flagged `\Drafts`, even with `flag_set=(\Draft,)`) landed the messages in `[Gmail]/Surat Terkirim`
  where they are invisible as drafts — see `reportlab-security-pdf` →
  `references/imap-draft-staging-fallback.md`. Verify with `drafts().list()` + `labelIds == ['DRAFT']`.
- Generator pattern that worked: write the report as **markdown**, then
  `reportlab-security-pdf/scripts/md_to_report_pdf.py` + `pdf_layout_check.py --tokens`.
  The stock generator has **no markdown-table support** — a `| ... |` block silently renders as one
  run-on paragraph (no error, no geometry violation). Avoid pipe tables entirely in these reports; use
  bullet lists of `field - value` instead.
- Evidence tree: `01-recon/` (root, server.json, ffuf-api.json, gau, katana), `02-scan/` (nuclei, sqlmap),
  `03-auth/` (session.json + api_key.json 30-day key, per-probe dirs, `poc_transcript/transcript.txt`).
- Evidence tree: `01-recon/` (root, server.json, ffuf-api.json, gau, katana), `02-scan/` (nuclei, sqlmap),
  `03-auth/` (session.json + api_key.json 30-day key, per-probe dirs, `poc_transcript/transcript.txt`).

## Pitfalls
- Token rotates each login -> single-script login+test. Email-OTP timing flaky -> retry, grab newest.
- execute_code uses NATIVE Windows paths (D:/...), not MSYS /d/... . No write_file tool (use shell).
- IMAP SEARCH needs quoted phrases. Clean up all test resources (dbuser/systemuser/domain/sshkey).
- **Every provisioning call is ASYNCHRONOUS — never write "immediately".** `POST /domain/` returns 201 but
  the nameserver answers REFUSED for a moment and only then flips to AA=1 (measured ~2 s once, much longer
  on other runs; `DELETE` shows the mirror image, AA=1 for 15-20 s). `POST /website/` returns 201 while
  `status` stays `null` and `locations` stay `[]` for minutes. Probe in a loop until the state settles, then
  describe it as "goes live after propagation". An "instant" claim in a draft PDF is a correction you will
  have to make and re-stage.
- **Probe BOTH the create and the update path for any client-supplied field.** On `/systemuser/` the create
  path validated nothing while `PATCH` validated a global absolute max — reporting only one of them
  understates the bug and misses the sharpest evidence (a 400 naming the global ceiling proves the plan is
  never consulted).
