# ATO Path Battery — ordered, run top-to-bottom

Dokumen ini adalah **battery eksekusi berjenjang** untuk `hunt-ato` (12 path + battery).
Jalankan berurutan dari Tier 0 → Tier 7. Setiap tier punya **kill-signal** (kapan berhenti
karena sudah ada bukti) dan **proof bar** (bukti minimal agar layak lapor). Additive-only:
12 path detail tetap di `SKILL.md`; di sini disusun jadi urutan kerja per target.

Aturan umum (verbatim dari `STATE.md` + `hunt-ato`):
- Unauth surface dulu, baru authed. Akun tes dibuat sendiri (max 5× gagal berturut-turut → move on).
- Temuan wajib revalidasi ≥3× sebelum lapor.
- ATO wajib bukti **takeover lintas akun**: jalankan flow sebagai A, buktikan dampak ke B
  (akun B ikut berubah / token B terbaca / login sebagai B).

---

## Tier 0 — Reset/Verification flow senza auth (money surface paling sering lemah)

Uji **tanpa login** dulu — ini yang paling sering bayar dan paling cepat dibuktikan.

| # | Battery step | Kill-signal | Proof bar |
|---|---|---|---|
| 0a | Password reset: inject `Host`/`X-Forwarded-Host` → cek apakah link reset pakai host itu | Link reset berisi attacker host | Link reset dikirim ke inbox test (atau redirect membawa token) |
| 0b | Reset token: capture N token → cek predictable (md5(ts)/sequential) | Token bisa diprediksi dari waktu/urutan | Reset akun B tanpa akses inbox B |
| 0c | Reset token no-expiry / reuse / cross-account | Token lama masih valid / token A buat reset B | Login sebagai B pasca-reset |
| 0d | OTP 4-6 digit (magic link / email code): no rate-limit → brute | 5-6 digit tanpa cap | Login sebagai B |

**Kill-signal tier:** kalau 0b/0c/0d menghasilkan login sebagai akun B → **ATO terbukti, stop,
revalidaasi 3×, laporkan.** Jangan lanjut ke tier berikut untuk target ini.

---

## Tier 1 — Email/identifier change tanpa re-auth (Path 5)

- **Email change without step-up**: `PUT /api/me` ubah email → token verifikasi lama masih valid
  buat email baru? (GitLab CVE-2022-4037 class).
- **Identifier pada verification endpoint** (Path 11): endpoint verifikasi menerima
  `email`/`phone` opsional → branch unhardened → register email korban duluan (pre-account takeover).
  ⚠️ Pre-hijack yang KORBAN bisa atasi sendiri saat daftar = BUKAN temuan (DedSec 1.0.3 lesson) — hanya
  temuan bila korban TIDAK bisa change-email sendiri setelahnya.

**Proof bar:** email akun B berubah / verifikasi diteruskan ke identitas lain tanpa seed-confirm B.

---

## Tier 2 — JWT & token crypto (Path 6) → use `hunt-jwt-crypto` matrix

Hard battery ke `references/jwt-header-attack-matrix.md` (sudah ada). Di sini cuma urutan tercepat:
1. `alg:none` (hapus signature) → 2. `RS256→HS256` key confusion (sign pakai JWKS public key tsb)
→ 3. weak HMAC crack offline → 4. `kid` injection (`../../../dev/null`, SQLi di `kid`).

**Kill-signal:** token hasil modifikasi diterima → ATO/priv-esc terbukti.

---

## Tier 3 — Password change without step-up + login oracle (Path 7)

- Password-change tanpa `current_password` / tanpa MFA challenge (step-up) → ubah password akun B
  langsung dari sesi A jika endpoint BOLA.
- **Login oracle**: bedakan response "email not found" vs "wrong password" → harvest valid email;
  lalu 2FA-bypass / brute pass.

**Proof bar:** password akun B berubah dari identitas A (bukan akun sendiri).

---

## Tier 4 — Social recovery / security-question abuse (Path 8)

- Brute jawaban recovery (low-entropy, unthrottled).
- Echo jawaban di `/api/me` / page source (client-side check = oracle).
- Question reveals OSINT-able PII (mother maiden, first car).

**Proof bar:** recovery flow akun B terbuka tanpa akses inbox/email B (jawaban brute).

---

## Tier 5 — Subdomain takeover @ OAuth redirect_uri (Path 9) → use `hunt-subdomain` + `hunt-oauth`

1. Enumerate accepted `redirect_uri` pattern (wildcard `*.target.com`?).
2. Cari dangling subdomain (CNAME → deprovisioned Heroku/S3/Azure/GH-Pages).
3. Klaim host, serve callback log `?code=`.
4. Kirim authorize URL ke B → token B mendarat di host claim.

**Proof bar:** `?code=` nyata milik akun B tertangkap di host penyerang.

---

## Tier 6 — Multi-tenant / role-confusion token surfaces (authed)

- Authz token yang cuma validasi signature, bukan `sub`/`user_id` claim (JWT → anti-sub-swap).
- BFLA: token user A dipakai ke endpoint admin → role escalation.
- Cross-tenant: token tenant A dipakai ke resource tenant B (≠ IDOR, ini token-scope hole).

**Proof bar:** resource/role milik tenant/role lain dapat diakses dengan token akun A sendiri.

---

## Tier 7 — Chain ke kelas lain (eskalasi, jangan berhenti)

Setiap primitif ATO di atas di-chain:
- ATO + IDOR → baca/tulis data lintas akun (upgrade severity).
- Reset-token leak + open redirect → token dieksfiltrasi ke host penyerang.
- Token sub-swap + mass-assignment → role escalation → full admin.

Lihat `exploit-chain-graph` L0→L5. `depth_gate.py` memblokir temuan yang buktinya cuma status code.

---

## Quick-ref summary (yang jarang diuji, bayar tinggi)

1. **Reset token predictable** (md5(timestamp)/sequential) — jarang diuji, sering ada.
2. **Email-change tanpa re-auth** + token lama valid buat email baru (GitLab class).
3. **Login oracle** sebagai langkah mandiri sebelum brute — identifikasi valid email dulu.
4. **Subdomain takeover di redirect_uri** — perlu `hunt-subdomain`, sering lolos.
5. **Identifier opsional di verification endpoint** (unhardened branch) — hanya bila korban
   tidak bisa change-email sendiri (hindari false-positive pre-hijack).