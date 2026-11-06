# CANDIDATE LIFECYCLE — temuan ≠ finding sampai lolos rantai ini

Operator rule: temuan HARUS divalidasi minimal **3×**. Lolos → dicatat sebagai **CANDIDATE**
(note + list; BELUM report). Di akhir, candidate divalidasi ULANG. Hanya survivor yang jadi
draft email + PDF PoC → disimpan di Gmail.

## Rantai (urutan WAJIB)
```
RAW FIND       : sesuatu yang "kelihatan" bug (dari scanner/tool/manual)
   │
   ▼  1. VALIDASI ≥3×  (3 eksekusi independen, tool/stack berbeda bila bisa)
CONFIRMED?     : tidak → buang (log sebagai negatif, jangan report)
   │ ya
   ▼  2. CATAT SEBAGAI CANDIDATE  (BELUM report)
candidates.json: {id, title, class, asset, severity_estimasi, evidence[], replays:3, first_seen, status:"CANDIDATE"}
candidates.md  : list manusiawi (1 baris per candidate)
   │
   ▼  3. LANJUT AUDIT (candidate boleh menggantung; jangan langsung tulis laporan)
   │
   ▼  4. RE-VALIDASI AKHIR (saat semua fase selesai) — ulangi ≥3× lagi
status: CONFIRMED → lanjut | FALSIFIED → keluarkan dari list (catat kenapa)
   │ CONFIRMED
   ▼  5. REPORT: 1 temuan = 1 draft email LENGKAP + 1 PDF PoC TERLAMPIR
   │            → simpan ke Gmail sebagai DRAFT (JANGAN kirim)
   │            → EXCEPTION: temuan yang saling terkait dalam SATU CHAIN ATTACK boleh
   │              digabung dalam 1 draft (chain = A→B→C yang saling bergantung untuk
   │              mencapai impact). Selain itu WAJIB dipisah.
   ▼  6. Hall of Fame / submission oleh operator
```

### Aturan penggabungan (HARD)
- **Default: 1 temuan = 1 draft + 1 PDF.** Jangan bundel beberapa temuan "biar rapi".
- **Pengecualian tunggal:** temuan hanya boleh digabung bila membentuk **satu chain attack** —
  yaitu B bergantung pada A, dan impact akhir (C/I/A/ATO/RCE) tercapai hanya lewat rantai itu.
  Contoh sah: open-redirect + OAuth misconfig → ATO. Contoh TIDAK sah: 3 IDOR tak berhubungan
  di 3 endpoint → tetap 3 draft.
- Draft chain: subject menyebut "chain", body menulis urutan A→B→C + satu PDF PoC yang
  merekam rantai lengkap. Temuan yang tidak termasuk rantai tetap dipisah ke draft sendiri.
- Tiap draft (termasuk draft chain) tetap: English, ber-intro, lampiran PDF, read-back verified.

## Bar validasi (≥3×)
- Tiap replay: **request identik, hasil identik** (body diff = bukti). Bukan "kelihatannya".
- ≥2 tool/stack berbeda untuk Critical/High (mis. curl + Python requests + browser).
- Marker unik & non-guessable; cek baseline dulu (anti false-positive reflection) — lihat bb-methodology.
- Timing-based → n≥10 interleaved + selisih ≥2σ (bukan 1 outlier).
- Bypass → wajib beda BODY, bukan cuma status code (Body-Diff Rule).

## Artefak wajib
- `candidates.json` (+ `candidates.md`) — sumber tunggal status candidate.
- Per candidate: `candidate-<id>/replays/` (≥3 respons tersimpan) + `poc-<id>.pdf`.
- Draft Gmail: 1 draft per candidate CONFIRMED, subject English, body ber-intro (greeting + siapa +
  channel + "In short"), lampiran PDF PoC. Verifikasi read-back: sha256 lampiran == file lokal + magic `%PDF-`.

## Larangan
- JANGAN tulis laporan sebelum 3× lolos (RULE 18 anti-premature-classification).
- JANGAN gabung beberapa temuan jadi 1 email (1 temuan = 1 draft = 1 PDF).
- JANGAN kirim email sendiri — simpan draft, operator yang kirim.
- JANGAN naikkan severity tanpa rantai (chain) yang terbukti.
