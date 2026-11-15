---
name: proactive-hunt-driver
description: Use before each hunt to force offensive coverage.
metadata:
  hermes:
    tags: [security, methodology, coverage, escalation, driver, bug-bounty]
---

# Proactive Hunt Driver — anti "cuma periksa yang ada"

**Masalah yang dipecahkan:** pola pasif/reaktif — datang, probe 2-3 kelas yang
kelihatan, dapet 403, tulis "verified negative", pindah target. Ini menghasilkan
0 temuan dan coverage kosong. Driver ini memaksa mode OFFENSIF: kejar SEMUA kelas
yang fiturnya ada, chain tiap lead sampai plafon, dan ukur coverage sebagai angka.

**Skill teknik tidak kurang** — `attack-surface-index` (132 fitur→probe),
`attack-flows` (8 alur), `howtohunt-checklist`, `multi-vector-battery-audit`,
`hunt-dispatch`, `exploit-chain-graph` semuanya sudah ada. Yang hilang adalah
PEMAKSAAN menjalankannya. Driver ini = penggonggong di 2 titik kunci. Selalu
jalankan driver ini, lalu ikuti pointer-nya — jangan duplikasi teknik yang sudah ada.

**PRIORITAS SERANG 2026:** sebelum IDOR-sequential generik, cek dulu 4 kelas
bayar-gede yang jarang tersentuh — buka `bb-2026-attack-surface`:
(1) Race/TOCTOU pada money-flow, (2) GraphQL batching/alias, (3) RAG/LLM
prompt-injection & cross-tenant retrieval, (4) cache poisoning/host-header.
Kalau target punya GraphQL/AI/money-flow/cache → kelas ini dulu, bukan IDOR.

---

## Titik 1 — PINTU MASUK (0B/0C: setelah recon tahu FITUR target)

Jangan mulai probe sebelum langkah ini selesai. Recon berhenti di "ini halaman
login" = berhenti terlalu cepat. Yang dibutuhkan: daftar FITUR.

1. **Tulis daftar fitur target** (upload? import CSV? webhook? invite? checkout?
   plan/pricing? reset password? export? render URL? AI/LLM? file ID? API key?).
   Ini bukan daftar endpoint — ini kapabilitas bisnis.
2. **Buka `attack-surface-index`** → cocokkan TIAP fitur ke kelas yang ada
   (`references/*.md`). Satu fitur cocok satu baris = probe itu WAJIB.
3. **Bangun kelas matrix**: `fitur -> kelas -> probe pertama -> skill hunt-* -> status`.
4. **Aturan N/A (mengikat, dari `hunt-dispatch`):**
   - Minimum 5 probe sebelum kelas boleh N/A (fingerprint router, route confusion,
     parameter pollution, method override, trailing dot/semicolon/encoded slash).
   - N/A wajib menyebut probe yang SUDAH dicoba + hasilnya. "Tidak ada" = pelanggaran.
5. **Hitung coverage KPI di awal** - total kelas yang fiturnya ADA vs sudah diprobe.
   Jangan klaim "0 temuan" sebelum mayoritas kelas dijalankan.

## Titik 2 — TIAP LEAD / SINYAL POSITIF (0C–0E)

Dapat sinyal (status beda, error, data balik)? JANGAN langsung "negative lalu pindah".

1. **Jalankan `severity_ceiling.py <target_dir>`** dulu - jawab: lead maksimal jadi
   apa, artefak apa yang kurang. Verdict `CAPPED-DROP` (self-XSS, header hilang,
   open-redirect sendirian, "admin bisa X") = jangan bakar jam.
2. **Buka `exploit-chain-graph`** → PRIMITIF→TEKNIK→ESKALASI → kejar rantai sampai L5
   (impact terbukti) ATAU primitif betulan habis. Jangan lapor Low lalu tanya "mau
   lanjut?" — operator yang nanya "bisa naik ke Critical?" = perintah lanjut.
3. **Tiga kali sebelum "terblokir"** - ganti encoding/method/content-type/casing/nama
   parameter, baru boleh menyerah. "403 pertama" bukan jawaban.
4. **Adjacent-gate (polimerisasi)** - satu celah = uji SEMUA titik sejenis. Lapor
   sebagai klasifikasi (`/api/v1/*` N endpoint), lebih kuat dari "1 endpoint".
5. **Eskalasi wajib tertulis** - tiap temuan sebut "eskalasi berikutnya: <skill>" ATAU
   "primitif habis karena <alasan>".

## Coverage KPI — angka yang harus ada di catatan kerja

Sebelum bilang "selesai / negatif", tulis:
```
diuji : X / Y kelas (fitur yang ada)
belum : [kelas yang fiturnya ada tapi belum diprobe]
N/A   : [kelas tanpa fitur + alasan + probe yang dicoba]
lead  : [jumlah sinyal -> plafon severity masing-masing]
```
`Y` = jumlah kelas di `attack-surface-index` + `howtohunt-checklist` yang fiturnya
ADA di target. Jangan klaim "0 temuan" dengan X << Y.

## Alur siap pakai (kalau malas susun sendiri)

`attack-flows` punya 8 jalur end-to-end. Pilih yang cocok dengan fitur target:
dangling-domain→ATO · zombie-API→DB · polimerisasi · module-install→drain ·
vault-inflation→liquidation · solver-trust→theft · attestation-replay→mint-ganda ·
redirect-bocor-host-internal→proxy→endpoint-unAuth.

## Aturan anti-pasif (jangan lakukan ini)

- JANGAN "coba 1 payload → 403 → tulis negative → pindah"
- JANGAN lapor Low lalu berhenti padahal rantai belum habis
- JANGAN klaim "0 temuan" tanpa coverage KPI
- JANGAN bikin probe/injection manual (requests/curl/playwright) SEBELUM pipeline
  + 13 tool jalan (lihat `audit-execution-discipline`)
- JANGAN tulis N/A tanpa menyebut probe yang sudah dicoba

## Pitfalls

- Driver ini NOL teknik. Ia menunjuk ke `attack-surface-index` / `howtohunt-checklist`
  / `exploit-chain-graph` / `severity_ceiling.py` / `attack-flows`. Jangan salin
  payload ke sini — buka skill yang ditunjuk.
- Coverage KPI dihitung dari fitur yang BENAR-BENAR ada (recon), bukan daftar kelas
  kosong. Kelas tanpa fitur = N/A beralasan, bukan "belum diprobe".
- "Belum diprobe" dan "N/A" itu beda. Yang pertama = pelanggaran kalau dibiarkan;
  yang kedua = sah kalau alasannya benar.