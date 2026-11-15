---
name: hunt-forgot-password
description: "Hunt Forgot Password / Account Recovery Authentication Flaws — 5 distinct patterns: (1) username enumeration via different responses for valid vs invalid email, (2) reset token exposed directly in the API response body, (3) reset token not invalidated after use (replay), (4) password reset link works from a different IP/browser (no binding), (5) no rate limit on the reset request endpoint. These are the standalone recovery-flow broken-auth primitives — distinct from reset-email host-header poisoning (hunt-host-header) and the full ATO chain (hunt-ato owns password-reset as an ATO path; prove the primitive here, chain it there). Detection: trace the full forgot-password flow from request to token to use; check response diffs between valid/invalid emails; test token replay after consumption. Medium to High (enumeration=Medium, token-reuse=High, account-takeover=Critical when chained to known-email)."
sources: hackerone_public, public_research
report_count: 6
---

## Live-account pitfall — you can lock yourself out (learned the hard way)

Testing this flow against the account you are *also* using for the engagement is a trap:

- On some apps the reset **request alone invalidates the current password**. Login then fails with a
  generic `…_ERROR_LOGIN` ("email or password are incorrect") even though the password is unchanged
  and the reset was never completed. Nothing in the UI tells you this is the cause.
- Consequence: you lose the session, the RBAC comparison account, and every authenticated surface
  mid-audit — usually right after you had just proven a finding and wanted to verify one more thing.

**Playbook**
1. Never fire a reset request for an account you still need — do it as the *last* action on a
   disposable identity, or better, probe the reset flow with a non-existent email first (exercises
   the endpoint and the throttle without touching a real account).
2. If you already locked yourself out: request **one** reset, use the newest link promptly. Repeat
   requests inside a few minutes often produce no new mail (throttle) and can invalidate the earlier
   token (`LINK EXPIRED`). Check the mailbox's other folders and any forwarding relay
   (`forward-bot@<alias-domain>` wraps the original subject — search the relayed subject, not the
   raw one).
3. Decode ESP click-tracking to get the real link
   (`mandrillapp.com/track/click/…?p=<b64url>` → base64-decode → JSON → `p.url` →
   `/change-password/<token>`), open it, set the new password.
4. **Immediately write the new credential into the engagement log** — the old one is dead for the
   rest of the engagement, and TOTP usually survives a password reset (so re-login = new password +
   existing TOTP secret).
5. Then revert whatever state you changed while authenticated (display name, role, phone) and note
   the revert in the same log entry.

**Distinguishing signals worth recording** (these feed pattern 1): "check your inbox" for
existing+confirmed, an explicit "email has not been confirmed" for existing+unconfirmed, and a
silent no-op for non-existent — three different behaviours from one endpoint is a usable
enumeration oracle, though most programs rate it P5/informational.

## Autonomous Testing Priority

**Start with username enumeration — it's the fastest win and gates the rest.**

**Pattern 1 — Username enumeration (response difference for valid vs invalid email):**
1. POST to the forgot-password endpoint with a clearly invalid email (e.g. `nonexistent@fakedomain12345.com`) — record the response body, status code, and length
2. POST with an email you know exists (or try common patterns like `admin@target.com`, `test@target.com`, `user@target.com`)
3. Compare responses: different message ("Email sent" vs "Email not found"), different HTTP status, or meaningfully different body length = username enumeration confirmed
4. Proof: enumeration is confirmed when the two responses differ measurably (baseline vs probe) in message text, status code, or body length

**Pattern 2 — Reset token exposed in the API response:**
Some APIs return the reset token directly in the response body (instead of only emailing it). POST to the forgot-password endpoint and look for a token, link, or code in the JSON/HTML response. If a token appears that lets you reset the password, that's an immediate account-takeover vector.

**Pattern 3 — Reset token replay (reuse after use):**
1. Complete a full password reset cycle: request token → use it to reset password
2. Immediately try submitting the same token again to the reset-password endpoint
3. If the second submission returns 200 or "success" → token not invalidated after use

**Pattern 4 — No rate limit on reset requests:**
Submit the forgot-password endpoint 10-20 times rapidly with the same email. If all succeed without a 429, lockout, or CAPTCHA → no rate limit (enumeration + token flooding is possible).

**Content-type:** Forgot-password endpoints are often JSON-based REST APIs. Use `application/x-www-form-urlencoded` only if the endpoint is a traditional HTML form (check the login page's HTML to determine form encoding).

**Proof:** Username enumeration = measurably different response (body/status/length). Token exposure = token in response body. Token replay = second successful use of a consumed token.

---

## Vulnerability Classes in This Skill

### 1. Username Enumeration via Password Reset
Different error messages for valid vs invalid accounts leaks the user list without authentication. Even timing differences (fast "no user found" vs slow "email queued") count.

High-value targets: admin accounts, employee email patterns, API keys derived from usernames.

### 2. Weak / Predictable Reset Tokens
A reset token derived from timestamp, username, or sequential IDs can be brute-forced:
- `base64(email + timestamp)` — decodable
- 4-6 digit numeric code — 10K guesses, easily feasible with no rate limit
- Sequential `token=1234`, `token=1235` — trivially enumerable

### 3. Token Not Bound to Session or IP
Most apps generate a token, email it, and accept it from any browser. A truly bound token should only work from the same IP or require the original session cookie. If neither is enforced → link forwarding = account takeover.

**Token leak via `Referer` / third-party resources.** When the token rides in the reset-page URL (`/reset?token=…`) and that page loads any cross-origin resource (analytics, ads, fonts, a CDN image), the full URL — token included — leaks to that third party in the `Referer` header. Check the reset page's outbound requests: if the token appears in any cross-origin `Referer`, it's harvestable without the victim's inbox. Same leak via a `<meta name=referrer>` misconfig or an outbound link the victim clicks from the reset page. Disclosed token-leak→ATO class: <https://hackerone.com/reports/173551>.

### 4. Reset Link Doesn't Expire
Common best practice: reset tokens expire within ~15–60 minutes (no hard RFC mandates the exact value; OWASP recommends a short, single-use lifetime). If a token from 24 hours ago still works → persistence risk for phishing attacks.

### 5. No Rate Limit on Reset Endpoint
An uncapped reset endpoint enables:
- Email flooding (DoS against victim's inbox)
- Token brute-force if the token space is small
- Username enumeration at scale

---

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Host-header poisoning: `Host: attacker.com` / `X-Forwarded-Host` → baca email B | Reset link ke domain penyerang |
| 2 | Entropi token: minta 5 token, bandingkan panjang & pola | Token predictable |
| 3 | Token reuse & cross-account: token B dipakai untuk akun A | IDOR di reset |
| 4 | Response diff: email valid vs invalid (status, panjang, waktu) | User enumeration |
| 5 | Token di Referer/URL: halaman reset muat resource pihak ketiga | Token bocor lewat Referer |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis
N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Gate 0 Validation

1. **Apa yang bisa dilakukan penyerang SEKARANG?** "Penyerang bisa mendapatkan token reset password akun B dengan memalsukan Host header" — baca email B yang kamu kuasai.
2. **Apa yang hilang dari korban?** Kontrol penuh atas akun. Tunjukkan reset yang berhasil pada akun B.
3. **Bisa direproduksi 10 menit dari nol?** Gunakan akun B milikmu, sertakan email yang diterima (disedit).

## Eskalasi wajib (jangan berhenti di kelas ini)

**Primitif:** manipulasi pemulihan akun

**Teknik pengembangan:** Host poisoning; token reuse/cross-account; entropy rendah

**Eskalasi ke:** `hunt-ato`

**Depth target:** L2 -> L5

Satu temuan di kelas ini WAJIB menyebut eskalasi berikutnya (atau alasan primitif habis).
Lihat `exploit-chain-graph` + `exploit-depth` (L0-L5). `depth_gate.py` memblokir temuan
yang buktinya cuma status code.

## Runnable probes

Commands you can paste. `<TARGET>`/`<RPC>` are placeholders — fill them
from recon, do not guess endpoints.

```bash
# 0) baseline + the reset endpoint
curl -sS -o /dev/null -w '%{http_code} %{size_download}\n' https://<TARGET>/forgot-password
curl -sS -X POST https://<TARGET>/forgot-password -d 'email=<YOU>@example.com' -o fpA.html -w '%{http_code}\n'

# 1) HOST-HEADER POISONING — read the email you actually receive (this is the proof)
curl -sS -X POST https://<TARGET>/forgot-password \
  -H 'Host: attacker.example' \
  -H 'X-Forwarded-Host: attacker.example' \
  -d 'email=<VICTIM_B>@example.com' -o /dev/null -w '%{http_code}\n'
# then: open B's inbox, extract the reset URL, and check its HOST.

# 2) token entropy + reuse — request twice, compare
curl -sS -X POST https://<TARGET>/forgot-password -d 'email=<YOU>@example.com' >/dev/null
curl -sS -X POST https://<TARGET>/forgot-password -d 'email=<YOU>@example.com' >/dev/null
# diff the two tokens from the two emails: length, charset, any shared prefix

# 3) user enumeration — response/time differential (n>=10 interleaved, not 1 shot)
for e in real@example.com definitely-not-a-user-9f3a@example.com; do
  for i in $(seq 10); do
    curl -sS -o /dev/null -w "$e %{http_code} %{time_total}\n" \
      -X POST https://<TARGET>/forgot-password -d "email=$e"
  done
done

# 4) token in URL — does the reset page load third-party resources?
curl -sS 'https://<TARGET>/reset-password?token=<TOKEN>' | grep -oE 'src="https?://[^"]+' | head
```

**Read the outcome, not the status code:** the finding is the *email* pointing at
your host, or a token that is short/reusable/cross-account — never "the endpoint
returned 200".

---

## Related Skills

- **`hunt-ato`** — owns the account-takeover CHAIN (password-reset is its path #1). This skill finds/proves the recovery-flow primitive; hand off to hunt-ato to assemble the full takeover.
- **`hunt-cache-poison`** — host-header injection during reset email generation (different vulnerability, same flow)
- **`hunt-brute-force`** — rate-limit testing pattern applies to the reset endpoint too
- **`hunt-auth-bypass`** — if the reset flow can be skipped entirely (go to `/reset-password?token=` with empty/null token)
- **`hunt-mfa-bypass`** — if MFA is required after reset, test the bypass there

## 2026 sweep (dork pass 2026-10-26 — CVE/GHSA terverifikasi dari cve.org + GitHub Security Advisories)

- **CVE-2026-27812 — Sub2API < 0.1.85: Password Reset Poisoning via Host / Forwarded-Header trust.** AI API gateway; link reset dibangun dari header request masuk. CVSS 4.0 **8.0 HIGH** `AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:N`. CWE-116.
  Lesson: gateway/proxy produk (API gateway, AI gateway, rate-limit proxy) adalah tempat paling rawan — mereka **ada di depan aplikasi dan memang dirancang untuk meneruskan header**, sehingga `X-Forwarded-Host` sering dipercaya buta.
- **GHSA-m82j-rq33-qjx2 — authorizerdev/authorizer < 2.4.0-rc.20: reset poisoning + `iss` claim re-validated against the same attacker-controlled header.** Ini varian paling halus: server punya **cek anti-poisoning** (`iss` claim vs request `Host`), tapi kedua sisi berasal dari header yang sama yang dikontrol penyerang. CVSS 3.1 **8.1**.
  Lesson: **cek anti-poisoning yang membandingkan dua nilai dari sumber yang sama bukan kontrol.** Saat menguji, jangan berhenti karena "ada validasi host" — baca dari mana nilai pembandingnya berasal.
- **GHSA-22m3-c7vp-49fj — IRRD 4.4.0-4.4.4 / 4.5.0: Host header injection → reset link poisoning.** Link konfirmasi (pembuatan akun, reset password, migrasi mntner) dibangun dari konteks request. Perbaikan: **tolak Host yang tidak cocok dengan `server.http.url` + invalidasi semua token lama**. Catatan penting dari advisory: 2FA tetap mencegah login meski password berhasil di-reset.
  Lesson: (a) uji **semua** email transaksional, bukan hanya reset password — pembuatan akun dan migrasi punya bug sama; (b) saat melaporkan, sebutkan apakah 2FA memitigasi (itu menurunkan severity secara jujur, dan triager menghargainya).
- **GHSA-xj2c-8fw5-mr6m — Shopware < 6.6.10.23 / 6.7.13.1: admin account takeover via Host-header reset poisoning.** Alur pemulihan password Administration tidak memvalidasi host. Critical.
  Lesson: **targetkan alur reset akun privileged**, bukan user biasa — satu reset admin = seluruh instance. Cari panel admin terpisah (`/admin`, `/administration`, `/manage`) dengan alur lupa-password sendiri yang sering belum diperkuat.
- **GHSA-gv7r-3mr9-h5x8 — AzuraCast <= 0.23.5: untrusted `X-Forwarded-Host` → reset poisoning → ATO **dan 2FA bypass**.** Middleware `ApplyXForwarded` mempercaya header tanpa allowlist proxy tepercaya. Dampak: reset flow **menghancurkan konfigurasi 2FA** korban.
  Lesson: cari middleware bernama `ApplyXForwarded` / `TrustProxies` / `SetHost` dan periksa apakah ada allowlist. Dan periksa apakah reset password **mematikan 2FA** — itu mengubah severity dari High menjadi Critical karena menghapus faktor kedua sepenuhnya.
- **GHSA-rf33-hmh9-h593 — solidtime < 0.19.0: Laravel `TrustHosts` middleware tidak terdaftar.** URL reset dibangun oleh `url()` yang membaca header Host.
  Lesson: pada aplikasi Laravel, **cek apakah `TrustHosts` benar-benar terdaftar di `app/Http/Kernel.php`** — Laravel men-scaffold kelasnya tapi tidak mengaktifkannya. Satu baris yang hilang = bug High. Ini juga bisa dideteksi dari source review, bukan hanya black-box.
- **CVE-2026-29199 — phpBB < 3.3.16: Host Header Injection → reset link poisoning** (assigner: HackerOne, H1 report #3543246). Terjadi saat `force_server_vars` dinonaktifkan. CWE-640.
  Lesson: bug ini dilaporkan lewat HackerOne pada forum software — **aplikasi forum/komunitas self-hosted adalah kategori yang bagus untuk kelas ini** karena sering di-deploy di balik proxy yang salah konfigurasi.

**Pola gabungan (2026):** 7 advisori, satu akar — **link email dibangun dari konteks request**. Yang membedakan severity: (1) apakah akun target privileged, (2) apakah reset mematikan 2FA, (3) apakah ada cek anti-poisoning yang benar-benar independen.


## Critical severity anchor (kelas ini bisa Critical — syaratnya)

Host-header injection pada reset link → token dikirim ke host attacker; reset token predictable / tidak expiry / tidak invalidate setelah pakai; token di referer leak; email change tanpa re-auth. Kalibrasi: token dengan entropy tinggi + expiry + invalidate = correct; reset flow yang butuh akses inbox victim = bukan bypass.
