# MFA / 2FA Bypass Battery — ordered, run top-to-bottom

Katalog eksekusi cepat untuk `hunt-mfa-bypass`. SKILL.md sudah 8 pattern + verifying-defences;
di sini disusun jadi battery berjenjang + kill-signal + proof bar. Additive-only.

**Prinsip (dari SKILL.md):** verifikasi defences dulu (jangan manufaktur bypass). MFA bypass
wajib bukti e2e: MASUK sebagai akun B tanpa kredensial/faktor MFA B. "OTP tidak ada rate limit"
tanpa brute yang mendarat = bukan ATO.

---

## Tier 0 — Verify the defence exists (sebelum klaim bypass)

Sebelum menyerang, pastikan MFA benar di-enforce (kalau tak ada, ya bukan bypass, itu absence):
- akun test B aktifkan TOTP/SMS → login → OTP diminta (positive control).
- disable MFA → login → tetap jalan tanpa OTP (negative control).

**Rule:** kalau MFA bisa di-skip karena tak di-enforce di jalur tertentu (mobile API, legacy
login), itu Pattern 4 (workflow bypass), bukan "defence ada".

---

## Tier 1 — Response manipulation (paling sering lolos, paling cepat)

| # | Bypass | Probe | Proof bar |
|---|---|---|---|
| 1a | Ubah status 401/403 → 200 | proxy intercept response OTP salah, edit jadi 200 | masuk tanpa OTP benar |
| 1b | Ubah body JSON `verified:false` → `true` | edit field verifikasi di response | diterima |
| 1c | Ubah `redirect`/`callback` ke dashboard | paksa lokasi sukses | bypass MFA gate |

**Kill-signal:** masuk sebagai B dengan respons dimanipulasi → MFA bypass = Critical.

---

## Tier 2 — Skip MFA step (workflow bypass)

```
masuk password → app set "pre-mfa" cookie → redirect /mfa
test: skip /mfa, akses /dashboard langsung dengan pre-mfa cookie
```

- Variant: akses endpoint deep-link `/api/settings`, `/api/billing` tanpa lewat /mfa.
- Variant: ganti `?step=otp` → `?step=done`, atau `?mfa=false`.

**Kill-signal:** akses dashboard/endpoint sensitif tanpa lewat MFA gate = Critical.

---

## Tier 3 — OTP / backup-code weakness (rate limit, reuse, entropy)

| # | Bypass | Detail |
|---|---|---|
| 3a | No rate limit OTP | ffuf `-t 5` (slow), 6 digit → 10^6, hit kalau tanpa cap |
| 3b | OTP tidak invalidate setelah pakai | reuse code sama 2x |
| 3c | Backup code brute | backup code pendek / unthrottled |
| 3d | OTP accept banyak percobaan paralel (race) | single-packet race (lihat `hunt-race-condition`) |

**Kill-signal:** login sebagai B via brute/reuse → Critical.

---

## Tier 4 — Race pada MFA verification (see `hunt-race-condition`)

Code verify di-check-then-mark. Single-packet attack (Turbo Intruder Engine.BURP2) kirim N kode
sekali, window sebelum `used` flag ke-set.

---

## Tier 5 — "Remember this device" trust escalation

Device-token (cookie/storage) yang bisa dipakai ulang / di-transfer lintas akun. Probe:
- ambil device token akun A → pakai di sesi B → apakah B skip MFA?
- device token tanpa binding per-akun = trust escalation.

---

## Tier 6 — Enrollment skip (MFA opt-in)

Appliance console cenderung opt-in. Register akun baru → MFA optional (default off) → tapi kalau
admin/policy paksa MFA, cek jalur register yang skip enrollment (API langsung, import user,
SSO-provisioning tanpa MFA flag).

---

## Fingerprint quick-ref

1. `POST /mfa/verify` → coba edit response (Tier 1).
2. Deep-link `/dashboard` tanpa /mfa (Tier 2).
3. OTP rate limit + reuse + backup brute (Tier 3).
4. Single-packet race verify (Tier 4).
5. Device-token cross-account (Tier 5).

## Refusal-pattern

- "OTP no rate limit" tanpa brute yang mendarat → bukan ATO (rutin ditolak).
- MFA not enforced di jalur lama = absence, bukan bypass (label jujur).
- Response manipulation yang cuma client-side (tanpa server accept) → bukan temuan.
- Bypass yang butuh korban + kredensial sudah bocor → downgrade (precondition).