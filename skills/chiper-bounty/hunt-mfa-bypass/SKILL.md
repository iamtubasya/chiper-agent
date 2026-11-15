---
name: hunt-mfa-bypass
description: "Hunt MFA / 2FA bypass — 7 distinct patterns. (1) MFA not enforced on sensitive endpoints (password change, email change accept without MFA challenge), (2) MFA-step skip via direct navigation to post-login URL, (3) MFA-token replay (same code accepted twice), (4) brute-force the 6-digit OTP without rate limit (10^6 attempts at server speed), (5) race condition on OTP validation, (6) recovery-code dump via /api/me, (7) backup factor downgrade (SMS factor with no rate limit). Plus the chain: cookie theft + password oracle + no step-up = ATO without MFA challenge. Detection: trace auth flow in Burp, find every state transition, check if MFA is middleware-gated vs per-endpoint, check OTP entropy and rate limit on OTP-validate. Validate: attacker session reaching post-MFA state. Use when hunting auth bypass, MFA flows, chaining primitives toward ATO."
sources: hackerone_public, cve_database, nist_800_63b, public_research
report_count: 5
---

> **Extra attack variants** (OpenEMR + PHP-core advisories — see §F): `skills/security/exploit-cookbook/references/openemr-php-advisory-techniques.md`


## Autonomous Testing Priority

> **Ordered battery (Tier 0→6):** `references/mfa-bypass-battery.md` — verify-defence → response-manipulation → skip-step → OTP/backup weakness → race → device-trust → enrollment-skip. Kill-signal + proof bar tiap tier. Tambahan: **prefix-oracle** (Pattern 4) yang menyusutkan 10^6 jadi ~60 tebakan.

**Try workflow bypasses before brute force — they're faster and more likely to succeed.**

**Pattern 1 — Skip the MFA step entirely (most automatable):**
1. Login with valid credentials → receive a "pre-MFA" session state
2. Without completing MFA, directly access a protected resource (`/dashboard`, `/api/me`, `/account/profile`)
3. If the response returns user data → MFA is enforced only in the UI, not server-side = Critical

**Pattern 2 — OTP replay (reuse a consumed code):**
1. Complete a valid MFA flow to get a working OTP
2. Log out, log in again with the same credentials
3. Submit the same OTP again
4. If accepted → OTP is not invalidated after use

**Pattern 3 — Submit obviously wrong OTP, observe response:**
Try submitting `000000` or `123456`. If the response is 200 or returns a session token, OTP validation is broken or client-side only.

**Pattern 4 — Partial / incremental validation (prefix oracle):**
If a guessed full code is rejected, test whether the server validates the OTP **prefix-by-prefix** instead of all-or-nothing. Submit a short partial code and compare responses:
1. Submit a 1–3 digit value (e.g. `otp=1`, then `otp=12`, …) — for a POST verify endpoint the code goes in the **request body**, not the URL query string, or the server reads an empty value.
2. If a *correct* prefix gives a DIFFERENT response than a wrong one (a success/flag, a distinct message, or a different length/timing), the validator leaks correctness one chunk at a time.
3. Walk the code digit-by-digit: keep the prefix that "responds correct," append 0–9, repeat. This collapses 10^6 brute force to ~10×N guesses (≤60 for a 6-digit code) — very feasible in a bounded test.
This is the go-to when there is no leaked code and no skip/replay path. Some apps award success on *any* correct prefix outright (so a single correct first digit can win — sweep `otp=0,1,…,9` before giving up).
**CRITICAL — stay in ONE session:** re-authenticating (POST /…/login again) regenerates the OTP, throwing away your prefix progress. Do the entire sweep against a single established MFA session; never re-login between guesses.

**On full brute force:** brute-forcing all 10^6 codes is infeasible in a bounded test — but the prefix oracle above (Pattern 4) usually makes it unnecessary. Only attempt full brute force with evidence of no rate limit AND a small key space.

**Proof:** A session token or protected resource data in the response without completing MFA confirms the bypass.

---

## 19. MFA / 2FA BYPASS
> Growing bug class — 7 distinct patterns. Pays High/Critical when it enables ATO without prior session.

### Pattern 1: No Rate Limit on OTP
```bash
# Test with ffuf — all 1M 6-digit codes
ffuf -u "https://target.com/api/verify-otp" \
  -X POST -H "Content-Type: application/json" \
  -H "Cookie: session=YOUR_SESSION" \
  -d '{"otp":"FUZZ"}' \
  -w <(seq -w 000000 999999) \
  -fc 400,429 -t 5
# -t 5 (slow down) — aggressive rates get 429 or ban
```

### Pattern 2: OTP Not Invalidated After Use
```
1. Login → receive OTP "123456" → enter it → success
2. Logout → login again with same credentials
3. Try OTP "123456" again
4. If accepted → OTP never invalidated = ATO (attacker sniffs OTP once, reuses forever)
```

### Pattern 3: Response Manipulation
```
1. Enter wrong OTP → capture response in Burp
2. Change {"success":false} → {"success":true} (or 401 → 200)
3. Forward → if app proceeds → client-side only MFA check
```

### Pattern 4: Skip MFA Step (Workflow Bypass)
```bash
# After entering password, app sets a "pre-mfa" cookie → redirects to /mfa
# Test: skip /mfa entirely, access /dashboard directly with pre-mfa cookie
# If app grants access without MFA = auth flow bypass = Critical
curl -s -b "session=PRE_MFA_SESSION" https://target.com/dashboard
```

### Pattern 5: Race on MFA Verification
```python
import asyncio, aiohttp

async def verify(session, otp):
    async with session.post("https://target.com/api/mfa/verify",
                            json={"otp": otp}) as r:
        return r.status, await r.text()

async def race():
    cookies = {"session": "YOUR_SESSION"}
    async with aiohttp.ClientSession(cookies=cookies) as s:
        # Fire ~30 concurrent submissions of the SAME OTP to hit the TOCTOU
        # window before the server marks it used. Two requests are NOT enough —
        # they almost always resolve sequentially as "already-used" (false negative).
        # Best done as a single-packet / 20+ HTTP-2-stream attack (Turbo Intruder).
        results = await asyncio.gather(*[verify(s, "123456") for _ in range(30)])
        # Race confirmed if >1 success (or 1 success among many "already-used").
        for status, body in results:
            print(status, body)
asyncio.run(race())
```

### Pattern 6: Backup Code Brute Force
```
Backup codes: typically 8 alphanumeric = 36^8 = ~2.8T (too large)
BUT: check if backup codes are only 6-8 digits = 1-10M range = feasible with no rate limit
Also test: can backup codes be reused after exhaustion? Some apps regenerate predictably.
```

### Pattern 7: "Remember This Device" Trust Escalation
```
1. Complete MFA once on Device A (attacker's browser)
2. Capture the "remember device" cookie
3. Present that cookie from a new IP/browser
4. If MFA skipped = device trust not bound to IP/UA = ATO from any location
```

### Pattern 8: Enrollment skip — MFA is opt-in at first login (appliance consoles especially)

Distinct from Pattern 4 (skip an existing user's challenge). Here the account has **no factor
enrolled yet**, and the console offers a decline path during enrolment:

```
Enable two-step verification | [Enable two-step verification] | [Continue without two-step verification]
```

Testing discipline:
1. Provision a **new** account (self-service trial, or admin-created) and log in for the first time.
2. If a decline/skip control exists, take it, then log in again.
3. Now the decisive question: **does the instance have a policy that requires MFA?** If a
   "require MFA for all admins" setting exists and a non-enrolled account still logs in cleanly,
   that is a real bypass. If MFA is per-user opt-in by design, it is **not** a finding — do not
   report it.
4. Compare against a privileged account: if that one gets a hard OTP dialog with **no** skip
   control while a second admin account gets a skippable prompt, that asymmetry is the signal to
   chase the setting, not the finding itself.

Same shape applies to "Allowable IP Settings" / first-access dialogs that accept an **empty**
submit. Check whether a limit is actually configured first: `Number of Auth IPs = 0` means no
allowlist exists, so an empty submit breaches nothing.

### Generating your own codes: decode the enrolment QR instead of asking the operator for a code

When you control the test account, never wait for a 6-digit code (30s expiry, one per login,
hundreds of logins per engagement). Google Authenticator's "export accounts" produces an
`otpauth-migration://offline?data=<base64 protobuf>` QR. Decode it once → base32 secret →
`pyotp.TOTP(secret).now()` forever after.

Run `scripts/totp_from_qr.py` (OpenCV `imread` + `zxingcpp.read_barcodes`, then a minimal
protobuf walk for field 1 = secret, 2 = name, 3 = issuer, 4 = algo, 5 = digits, 6 = type).
Try plain read first, then 2–8× upscale, then threshold/adaptive/invert/OTSU — a phone photo of
a screen usually needs one of those. Fall back to tiles if the whole image fails.

Pitfall: the same TOTP secret is often reused across the vendor's estate (portal login **and**
the product console login both enrolled from one enrolment URI). Extract once, reuse everywhere —
and note it, because one shared second factor across two trust boundaries is itself worth a line.

### MFA Chain Escalation
```
Rate limit bypass + no lockout = ATO (Critical)
Response manipulation = client-side only check = Critical
Skip MFA step = auth flow bypass = Critical
OTP reuse = persistent session hijack = High
```

---

## Verifying the defences without manufacturing a bypass (do this before claiming one)

Half of an MFA engagement is proving the controls work, because a false "bypass" here is
expensive. Verified-clean checklist from a TOTP deployment (Quarterwise, 2026-09):

1. **Half-auth state must not reach app routes.** After the password step (before the code),
   request the post-login URLs directly: authenticated pages should 307 back to `/login`.
   Note: an unknown path may return `200` with the SPA/marketing shell — that is a 404 page,
   not access. Assert on the *content*, not the status code.
2. **Sensitive actions must demand their own code — but the field may only appear on step 2.**
   The account-security form rendered with just name+email; the `mfaCode` + `currentPassword`
   inputs appeared **only after submitting step 1**. Do not conclude "email change needs no
   MFA" from the first render. Submit the step and re-read the form fields. (Here: email change
   required current password + TOTP + a code sent to the NEW address = proper double opt-in;
   password change required current password + TOTP.)
3. **Attempt cap → is the lockout account-level, and does it expire?** Five wrong codes gave
   "Too many attempts. Please wait about 15 minutes"; a *fresh* session with the CORRECT code
   was still refused during the window (account-level, good), and a normal login succeeded
   ~15 minutes later. Verify the expiry so you do not leave the account locked — and do not keep
   retrying, since each attempt may extend the window.
4. **TOTP replay: use two full logins, not a side action.** Complete login #1 with code X, then
   immediately start a *fresh* login and submit X again in the same 30-second window. Accepted
   twice = reusable code; "That code is not correct" = replay prevented. Do NOT test replay
   against a side action whose input has its own validator — a NINO-format rejection was once
   mis-read as replay protection.
5. **Appraise, and do not trigger, the recovery path.** A "Lost your authenticator?" flow that
   disables the factor only after 24 hours and emails a warning first is a *control*, not a
   bypass. Read it, report it as a positive, and leave the button alone so you do not start a
   24-hour countdown on somebody else's account.
6. **Check what MFA does NOT cover.** Static credentials usually bypass it entirely: while the
   account was locked out of interactive login, its API key still returned `200` on
   `/api/v1/me` and `/api/v1/sources`. Expected for machine access, but a real expectation gap
   worth one line in the report, together with what happens to existing keys when MFA is
   enabled/disabled.
7. **Enrolling MFA does not invalidate existing sessions** — note it; a stolen session keeps
   working after the victim turns the factor on unless the app revokes sessions.

## OWASP Top 10:2025 anchor + ASVS V6.5/V6.6 test plan (added 2026-10-30)

MFA failures sit in **A07:2025 Authentication Failures**. ASVS 5.0 V6.5/V6.6 is the
requirement-level checklist for exactly the patterns above — cite the ID:

| ASVS | Lvl | Requirement | Our pattern |
|---|---|---|---|
| **6.5.1** | **2** | lookup secrets / OOB codes / TOTP **usable only once** | Pattern 2 — OTP not invalidated |
| 6.5.2 | 2 | lookup secrets < 112 bits stored hashed | code review |
| 6.5.4 | 2 | OOB codes ≥ **20 bits entropy** (4 alnum / 6 digits) | Pattern 6 — backup-code brute force |
| **6.5.5** | **2** | OOB codes / TOTP have a **defined lifetime** | TTL probe |
| **6.6.1** | **2** | PSTN/SMS OTP **off by default** | config |
| **6.6.2** | **2** | OOB codes **bound to the original request** | cross-session code reuse |
| **6.6.3** | **2** | OOB codes **rate-limited** against brute force | Pattern 1 — no rate limit on OTP |
| 6.6.4 | 3 | push MFA rate-limited (push bombing) + number matching | flood test |
| **6.4.3** | **2** | password reset **does not bypass MFA** | Pattern 4 — workflow bypass |
| **6.3.3** | **2** | MFA required for sensitive access | Pattern 8 — enrollment skip |
| 6.5.8 | 3 | TOTP checked against a **trusted** time source, not client-provided | clock-skew abuse |

Full map + score tables: `security/exploit-cookbook/references/owasp-top10-2025-asvs5-access-auth.md`

## Naikkan severity — komposisi K/A/B/X (wajib sebelum lapor, added 2026-10-30)

MFA bypass adalah **B (Bypass)** kelas atas: ia menghapus faktor kedua sepenuhnya. Tapi severity naik kalau ada **A (Action)** di belakangnya — reset-password yang menulis ke email tak terverifikasi, atau OTP yang tidak terikat request.

Klasifikasikan temuan lo dengan apa yang ia **supply**, lalu cari tepi yang menyambung:

| Part | Yang ia beri penyerang |
|---|---|
| **K — Knowledge** | identifier / versi / schema |
| **A — Action** | server melakukan sesuatu atas nama lo |
| **B — Bypass** | menghapus cek yang memblokir hop berikutnya |
| **X — Amplifier** | primitif kecil → banyak / tampilan aktor lain |

Pola yang **terbukti** mencapai High/Critical:

```
B + X   missing rate limit (B) + account enumeration (B) + spray (A)  =  credential-stuffing ATO
K + B + A + X   error-leak (K) → unthrottled enumeration (B) → unverified email change (A)
                → IDOR/export amplification (X)                          =  mass ATO
K + A   version/stack leak (K) → CVE pada versi itu persis (A)          =  RCE
```

Prosedur (di **0E**, sebelum lapor ditulis): INVENTORY → LABEL → EDGES → SINK → PROVE → REPORT.
**Satu laporan rantai**, judul = impact terminal, severity = impact terminal.

Skill lengkap: `security/chain-to-impact` · `exploit-depth` (L0→L5) · `lead-to-critical`.

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Response manipulation: ubah `{"mfa_required":true}` jadi `false` | Validasi client-side |
| 2 | Status/step parameter: akses `/dashboard` langsung setelah login | Step dilewati |
| 3 | Backup code brute: ruang kecil tanpa rate limit | Bypass via kode cadangan |
| 4 | Enrollment skip: daftarkan device tanpa verifikasi | Bypass pendaftaran |
| 5 | Race pada verifikasi: 2 request paralel sebelum state berubah | TOCTOU |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis
N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Gate 0 Validation

1. **Apa yang bisa melakukan penyerang SEKARANG?** "Penyerang dengan password korban bisa melewati MFA dengan mengubah respons verifikasi" — tunjukkan akses yang didapat.
2. **Apa yang hilang dari korban?** Kontrol akun meski MFA aktif. Tunjukkan sesi yang didapat.
3. **Bisa direproduksi 10 menit dari nol?** Gunakan akun B milikmu; sertakan langkah dan respons.

## Eskalasi wajib (jangan berhenti di kelas ini)

**Primitif:** lewati faktor kedua

**Teknik pengembangan:** OTP re-routing; brute; backup-code reuse; response manipulation

**Eskalasi ke:** `hunt-ato`

**Depth target:** L3 -> L5

Satu temuan di kelas ini WAJIB menyebut eskalasi berikutnya (atau alasan primitif habis).
Lihat `exploit-chain-graph` + `exploit-depth` (L0-L5). `depth_gate.py` memblokir temuan
yang buktinya cuma status code.

## Related Skills & Chains

- **`hunt-ato`** — MFA bypass is a primitive; ATO is the destination. Chain primitive: cookie theft (via XSS or session-fixation) + password oracle (login response timing/length diff reveals valid passwords without lockout) + no MFA step-up on password-change endpoint = persistent ATO without ever facing the OTP challenge → password rotated, attacker locks victim out.
- **`hunt-race-condition`** — Pattern 5 (OTP race) lives in race-condition territory; load both skills together. Chain primitive: same 6-digit OTP submitted via 20 parallel HTTP/2 streams (single-packet Turbo Intruder attack) before the server marks it used → 1 success + 19 "already-used" → race window confirmed → attacker doesn't need to brute, just guesses once and parallelizes → ATO.
- **`hunt-auth-bypass`** — MFA-step-skip is auth-flow bypass at the workflow layer. Chain primitive: pre-MFA cookie issued after password step + direct navigation to `/dashboard` skipping `/mfa` route + server only middleware-gates `/mfa` not `/dashboard` = full post-auth access from password-only state → MFA never enforced because the route gate was misplaced.
- **`hunt-misc`** — Recovery-code dump via `/api/me` is a misc-class info disclosure that becomes Critical when chained. Chain primitive: `/api/me` returns full user object including `backup_codes` array (plaintext, never rotated) → attacker with any read-IDOR or XSS exfils backup codes → uses one backup code → MFA satisfied → ATO without OTP knowledge.
- **`security-arsenal`** — Pull the OTP-brute-force payload section (000000-999999 wordlist generator, ffuf rate-limit-evasion patterns with `-t 5 -p 0.5-2`, distributed-IP rotation via proxychains) and the JWT-token-replay table when "MFA satisfied" claim lives in a JWT claim that can be forged.
- **`triage-validation`** — Run the Pre-Severity Gate before claiming Critical on an MFA bypass that only works when the attacker already has the password. Standalone MFA bypass is High; chained-with-password-oracle is Critical; chained-with-cookie-theft-only is Critical. The chain question separates the two.

---

## 2026 sweep (dork pass 2026-10-18)

- **CVE-2026-106610** — miniOrange OTP Verification ≤ 5.5.7: **unauthenticated account
  takeover via OTP re-routing**. The plugin fails to verify that the phone number supplied
  for the OTP belongs to the account being authenticated. Lesson: on any OTP flow, test
  whether the *destination* of the code is bound to the *identity* being verified — a
  mismatch there is an ATO with no credentials at all.



## Critical severity anchor (kelas ini bisa Critical — syaratnya)

Critical hanya kalau MFA adalah satu-satunya faktor kedua DAN bisa dilewati (no rate limit OTP, OTP tidak invalidate, response manipulation, skip step, race pada verifikasi, backup code brute-force, remember-device trust escalation). Kalibrasi: MFA yang bisa di-enroll ulang oleh attacker yang sudah punya sesi = bukan bypass MFA, itu ATO.
