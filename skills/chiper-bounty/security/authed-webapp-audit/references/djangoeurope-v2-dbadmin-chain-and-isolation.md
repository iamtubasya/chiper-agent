# djangoeurope v2 — DB-admin exposure chain, shared-server isolation, disclosure refinements

Continuation of `djangoeurope-v2-quota-bypass-and-disclosure.md` (same target, fresh pass +
deep-dive, 2026-10-24). Captures four reusable techniques.

## 1. Cracking the auth: the `webkey` cookie is the real authenticator, not the header

DRF app, login = email-OTP MFA. The mechanics that matter:

- `POST /login/` → `{mfa_token, devices, email_sent}` (device `otype:"email"`).
- `POST /login/mfa/ {mfa_token, otp_device_id, otp}` → `{token, id, expires_at}` **and** sets
  `Set-Cookie: webkey=<40-hex>; HttpOnly; SameSite=Lax; Secure`.
- **The JSON `token` and the `webkey` cookie are DIFFERENT values, both 40-hex.** The panel JS
  sends `Authorization: Token <cookie>` but the endpoint that actually authenticates the API is
  the **`webkey` cookie** (session). Proof: `GET /ip/` through a cookiejar opener (cookie rides
  along) → `200 []`; the same call with only the `Authorization: Token <json_token>` header via
  bare `urlopen` → `401 "Invalid API token."` / `"API token has expired."`
- **Token rotates on every login** — a new `/login/` invalidates the prior token. So a token
  saved to disk and reused in a *later* script 401s. **Do login + all tests in ONE script**, and
  make every request through the cookie-jar `opener` (not `urllib.urlopen`).
- OTP is flaky to fetch: poll IMAP for the newest `info@djangoeurope.com` "Your login
  verification code" mail, take the 6-digit code, submit within its ~10-min window; retry the
  whole login up to ~6× (each attempt sends a fresh OTP). Cost ~40-90 s per login → batch many
  tests per session.

## 2. The DB-admin exposure chain (the reportable finding, DE-v2-03)

`GET /server/` **unauthenticated** leaks per server: hostname, exact OS/package versions, SSH
host-key fingerprints, **and the DB-admin panel URLs**. Those panels are internet-exposed and
standalone (no panel auth in front):

- phpMyAdmin **5.2.2** → `phpmyadmin-s{20,24,25,26,27}.wservices.ch` (HTTP 200 login page).
- Adminer **5.2.1** → `adminer-s31.wservices.ch` (HTTP 200 login page).
- **Functional login confirmed**: created a `dbuser` via `POST /dbuser/ {systemuser, dbms:"mysql",
  name, password}` (name must match `^[a-z0-9]+$` — underscores rejected with "a-z and 0-9 are
  allowed"), waited ~8-10 s for propagation, then logged into phpMyAdmin-s24 with those creds.
- **No SSRF**: phpMyAdmin `server` field is a hidden input fixed to `"1"` (local DB); Adminer has
  no server field. Cannot pivot the panel to another DB host.
- **DB isolation proper**: the logged-in customer DB user sees only `information_schema` — no
  co-tenant databases. So the panel does NOT hand over cross-tenant data; DB compromise is
  confined to the attacker's own DBs.
- **Known-vulnerable versions**: Adminer 5.2.1 < 5.4.3 → CVE-2026-56703 (RCE, SQLite `VACUUM
  INTO`) + CVE-2026-25892 (unauthenticated DoS via version-check endpoint); phpMyAdmin 5.2.2 <
  current 5.2.3. The RCE is a **conditional** escalation — it needs DB creds *on s31*, and the
  `server` field on `systemuser`/`dbuser` creation is tenant-pinned to your own server, so you
  cannot mint s31 creds from a single account. Do NOT fire the unauth DoS to "confirm" it.

Chain framing (see chain-to-impact): the unauth recon's value is the target list it hands the
attacker; report the chain, not the bare info-leak.

## 3. Shared-server isolation test via paramiko (customer → escape to co-tenant?)

You have a legit `systemuser` on a shared server (here s24, 40+ co-tenants). To test isolation:

- Add an SSH key via `POST /sshkey/ {pub, description}` — **but key auth often does not deploy**
  (no audit-log entry, repeated `Permission denied`). The reliable path: **set a password on the
  systemuser** (`PATCH /systemuser/{id}/ {password}` flips `has_password:true`), then SSH with
  **password auth via paramiko** (`look_for_keys=False, allow_agent=False`). No `sshpass` on this
  host; paramiko handles it.
- Read-only isolation battery (all came back PROPER on s24):
  - `ls -la /home/` → co-tenant dirs are `drwx------` (0700); `ls /home/<other>` → Permission
    denied. (Minor: you *can* enumerate co-tenant usernames from the listing — low value.)
  - MySQL: `mysql -uroot`/anon via the world-accessible socket → `Access denied`. PostgreSQL:
    prompts for password (not trust). Redis 6380: `NOAUTH Authentication required`.
  - `ss -tlnp` → DB/mail/redis all bound to `127.0.0.1` (not cross-tenant reachable); the one
    `0.0.0.0:5666` listener is firewalled externally (probe from outside → timeout).
  - `sudo -l` → password required (no passwordless sudo).
- Clean up: `DELETE /sshkey/{id}/`. Note the systemuser password you set (revert in panel if the
  original `has_password:false` state matters).

## 4. Disclosure-artifact refinements (reportlab PDF + PIL PNG + IMAP draft)

Building on `djangoeurope-v2-quota-bypass-and-disclosure.md`:

- **Gmail PDF-preview compatibility**: a reportlab PDF with non-WinAnsi glyphs (em-dash `—`,
  smart quotes) can fail Gmail's attachment preview. Regenerate the PDF **ASCII-clean** (plain
  hyphens/quotes in all `Paragraph` text) — the PDF bytes are still binary, but the *text
  content* being ASCII avoids the preview choke. Verify source files with `pypdf` (opens, page
  count, `extract_text`) and `PIL .verify()` before attaching.
- **Verify attachments survive the draft**: fetch the draft back via IMAP, `walk()` the MIME
  parts, `get_payload(decode=True)` each, and compare sha256 to the source files — confirms
  nothing corrupted in the APPEND and the Content-Type/CTE are right.
- **Swap a draft cleanly**: to replace a staged draft, `search` it by a unique subject token
  (quote multi-word phrases — IMAP `SEARCH` needs `(HEADER Subject "two words")`, a bare
  space-separated arg → `BAD Could not parse command`), `+FLAGS \Deleted`, `expunge()`, then
  APPEND the new one.
- **Preserve the operator's edits**: if the user hand-edited the draft in Gmail (added a
  recipient, shortened the subject), read those back from the stored draft and carry them into
  the rebuilt draft. On djangoeurope the operator added `security@wservices.ch` (Pascal Bader —
  the parent org wservices.ch runs the servers; a better disclosure contact than `info@`).
- **IMAP path trap**: `execute_code` runs native-Windows Python — use `D:/...` or
  `C:\...` paths, NOT the git-bash `/d/...` MSYS form (→ `FileNotFoundError`).
