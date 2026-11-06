# Fintech / Tax SaaS — Business Logic Matrix (rounding, currency, idempotency)

Checklist 2026 untuk aplikasi pembayaran/pajak. Ber-overlap dengan `tax-rule-verification`
(HMRC/MTD + arithmetic pajak spesifik) — file ini menambah permukaan umum yang belum tercakup.

## Surface yang diuji

1. **Precision & rounding manipulation** — input nominal aneh: desimal ekstrem (`0.001`,
   `0.0000001`), negatif (`-100`), scientific notation (`1e10`, `1e-8`). Cek validasi backend
   konsisten dengan frontend; selisih pembulatan = uang.

2. **Kalkulasi pajak/diskon berantai** — banyak diskon/kredit pajak sekaligus; cek urutan
   perhitungan bisa dimanipulasi (apply order beda → hasil lebih kecil / favorit penyerang).

3. **Currency / exchange rate race** — submit transaksi multi-currency saat rate berubah;
   cek apakah rate di-lock (snapshot) saat konfirmasi atau bisa berubah client-side. Race pada
   read-rate vs commit = `hunt-race-condition`.

4. **Negative balance / overdraft via race** — banyak request withdraw/transfer paralel melebihi
   saldo (double-spend). Bukti = saldo akhir negatif / transfer melebihi dana.

5. **Idempotency key abuse** — kirim ulang request dengan idempotency key SAMA tapi body BEDA:
   same key + same body = dedup (OK); same key + DIFFERENT body = harusnya DITOLAK; kalau diterima
   /overwrite = bug (lihat `hunt-business-logic` idempotency half-2).

6. **KYC / verifikasi gate bypass** — aksi sensitif (transfer besar) diakses sebelum status KYC
   "approved" via endpoint API langsung (skip gate UI).

7. **Data onboarding tanpa gate** — rute alternatif (`/f/*` vs `/app/*`, subdomain lama, API mobile
   vs web) yang skip validasi dokumen legal/identitas (pola kasus Fintual).

8. **Filing / submission ganda** — submit dokumen pajak sama dua kali dengan data beda; cek mana
   yang final (idempotency / ACID). Verifikasi lewat read-back, bukan status code.

9. **Session mencakup banyak entitas** — user kelola pajak untuk beberapa badan usaha; cek isolasi
   antar entitas dalam satu akun (mirip multi-tenant dalam satu sesi).

## Aturan triage

- Rounding/negatif/notation = bukti backend arithmetic (bandingkan nilai SERVER, bukan UI).
- Idempotency = buktikan half-2 (same key diff body), bukan cuma "dedup jalan".
- KYC/onboarding bypass = bukti aksi sensitif jadi bisa tanpa status approved.
- Negative balance = saldo akhir yang terbukti negatif, bukan "2× 200".