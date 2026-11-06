# PHASE EXECUTION MANDATE — setiap fase meninjau ULANG & MENJALANKAN semua aset

Prinsip operator: **jangan ada yang cuma dilihat lalu dilewatkan.** Setiap skill, tool, reference,
payload, cookbook, exploit-book yang kita punya harus **dipanggil DAN dijalankan**, dengan bukti di disk.
Timeout ≠ skip → retry / tool lain / manual harness (RULE 3, RULE 2b).

## Definisi "DIPAKAI" (bukan cuma dibaca)
Sebuah aset dihitung DIPAKAI hanya jika ada **bukti eksekusi di disk**:
- tool  → output di `tool-evidence/*.txt` (≥100 B) / `tools-usage.json` status EXECUTED|RAN_WITH_ERROR|NO_OUTPUT
- skill → checklist-nya menghasilkan minimal 1 request/uji nyata (catat di `asset-coverage.json` + evidence)
- reference → minimal 1 clue dari ref itu di-fire ke target (`reference-usage.json`)
- payload/cookbook/exploit-book → minimal 1 payload dieksekusi (`variant-usage.json`, `poc-variant-usage.json`, `poc-techniques-usage.json`)

"READ_ONLY" (dibaca tapi tak ada request) = **FAIL**, bukan lulus.

## Ledger: `<target_dir>/asset-coverage.json`
Setiap aset punya 1 entri:
```json
{"asset":"sqlmap","class":"tool","phases":["0C"],"status":"USED","evidence":"tool-evidence/sqlmap.txt","reason":""}
```
status: `USED` | `READ_ONLY` (FAIL) | `SKIPPED_TIMEOUT` (FAIL) | `N_A` → `N/A` (wajib reason nyata) | `PENDING`/`NOT_RUN` (FAIL)

**Ledger TIDAK diisi manual.** `audit-pipeline-orchestrator.py` memanggil
`asset-coverage.py <dir> --init` lalu `--derive` tepat SEBELUM gate 0D.
`--derive` membaca artefak nyata (`tools-usage.json`, `variant-usage.json`,
`business-logic-usage.json`, `poc-execution.json`, `poc-variant-usage.json`,
`reference-usage.json`, `poc-techniques-usage.json`, `subs/live/urls.txt`,
`loaded-skills.txt`) dan menetapkan `USED` HANYA bila buktinya ada di disk.
Aset yang tidak jalan → `NOT_RUN` → **0D FAIL dan menyebut nama asetnya.**

Skill: `loaded-skills.txt` (ditulis orchestrator, berisi skill wajib track) —
tiap skill di dalamnya WAJIB punya entri `applied:true` + `evidence` di
`skill-usage.json`, atau 0D FAIL. Ini yang membuat "skill cuma dibaca" tak bisa lolos.

Checker: `scripts/asset-coverage.py <target_dir> --phase 0C` → exit≠0 kalau ada
READ_ONLY / SKIPPED_TIMEOUT / NOT_RUN / PENDING untuk aset wajib fase itu.

Terbukti 2026-10-07: fixture "pipeline selesai penuh" → **ALL 13 CHECKS PASSED**;
satu bukti tool dihapus → CHECK 2 + CHECK 12 FAIL, menyebut `0C:tools:sqlmap [NOT_RUN]`.

## ⛔ DESIGN RULE — tidak ada GATE tanpa PRODUCER (+ uji gate DUA ARAH)

Dua mode kegagalan, keduanya kena di 2026-10-07:

**1. Checker yang input-nya tak dibuat siapa pun = HARD-BLOCK permanen.**
CHECK 12/13 (`asset-coverage.json`, `skill-usage.json`) ditambahkan ke
`verify-tool-usage.py` sementara orchestrator tidak pernah membuat file itu →
0D akan FAIL di SETIAP audit, selamanya. Gerbang yang tak mungkin lulus lebih
buruk daripada tak ada gerbang: ketakutan operator ("dibilang udah, ternyata
di-skip") berganti jadi "pipeline mati lalu di-bypass".
→ **Tiap gate WAJIB dibarengi auto-producer-nya.** `audit-pipeline-orchestrator.py`
kini memanggil `prepare_coverage_gate()` (→ `asset-coverage.py --init` + `--derive`)
tepat SEBELUM gate 0D, dan `final_coverage_gate()` setelah 0F.

**2. Penandaan manual bukan penegakan.**
Kalau ledger harus diisi tangan, ia merosot jadi "didaftar, bukan dipakai".
Producer harus **derive** `USED` dari artefak yang sudah ada di disk — bukan dari klaim.

**Uji gate DUA ARAH dengan fixture — selalu.** Checker yang cuma diuji pada input
yang lulus berarti belum teruji:
```
A. fixture lengkap        → harus PASS (0B/0C/0D/0E/0E-REVIEW/0F PASS,
                                         verify-tool-usage: ALL 13 CHECKS PASSED)
B. sabotase SATU aset     → harus FAIL dan MENYEBUT namanya:
   hapus bukti sebuah tool      → FAIL 0C:tools:sqlmap  [NOT_RUN]
   timpa dgn 2000 byte "x"      → reason: lacks '# TOOL EVIDENCE:' marker
   ubah # TARGET: ke host lain  → reason: target mismatch
   set # TIMESTAMP: ke tahun lalu → reason: predates the run (stale)
```
Cara ini menangkap 3 bug di kode gate-nya sendiri, yang tak satu pun kelihatan dari
run yang lulus: path `evidence_file` relatif tak pernah di-resolve ke `target_dir`
(CHECK 2/5/9/10/11 gagal-palsu di tiap audit yang sudah selesai), `NameError`
`pathlib.Path` dari import yang tak lengkap, dan helper yang dirujuk tapi tak pernah
didefinisikan.

**Fragilitas yang harus dijaga:** string marker (`# TOOL EVIDENCE:`, `# VARIANT
EVIDENCE:`, `# BUSINESS-LOGIC EVIDENCE:`, `# REFERENCE-DRIVEN ATTACK EVIDENCE`)
adalah KONTRAK dengan para *penulisnya* (`force-full-execution`, `tool_router`,
`execute-*`). Kalau penulis mengubah headernya, cek kualitas akan diam-diam
menggagalkan semuanya. Grep penulisnya dulu sebelum mengubah marker ke arah mana pun.

## VALIDASI KUALITAS BUKTI (filler tidak lolos)

Ukuran saja tidak cukup: file 2000 byte berisi "x" akan lolos cek ≥100 B. Karena itu
`--derive` juga menuntut **marker penulis asli** di 4 KB pertama file bukti:

| kelas / asset | marker wajib |
|---|---|
| tools, recon | `# TOOL EVIDENCE:` (force-full-execution / tool_router) |
| variants(C2) | `# VARIANT EVIDENCE:` |
| business-logic-15(C3) | `# BUSINESS-LOGIC EVIDENCE:` |
| references(C6), refs | `# REFERENCE-DRIVEN ATTACK EVIDENCE` |
| poc-variants(C5), poc-techniques(C6b) | `# TOOL EVIDENCE:` / `# VARIANT EVIDENCE:` |

Tanpa marker → `NOT_RUN` + reason `evidence lacks '<marker>' (filler / fabricated?)`.
Terbukti: ganti satu bukti dgn 2000 byte "x" → `FAIL 0C:tools:sqlmap [NOT_RUN]`.

## KONSISTENSI LINTAS-ARTEFAK (bukti pinjaman ditolak)

`run-meta.json` ditulis orchestrator di 0A (`target`, `tech`, `started_at`, `pid`).
`--derive` memakainya untuk memeriksa **setiap** file bukti berstatus USED:

- `# TARGET:` di header bukti harus **sama** dengan target audit → beda = `NOT_RUN`
  (`target mismatch: evidence says ...`).
- `# TIMESTAMP:` / `# TS:` harus **dalam rentang run** (toleransi −1 jam) → lebih tua =
  `NOT_RUN` (`timestamp ... predates the run ... stale/hand-me-down evidence`).
- Tanpa `run-meta.json` (run manual) kedua cek ini di-skip → tidak ada gagal palsu.

Terbukti: ubah `# TARGET:` satu bukti ke host lain → `FAIL 0C:tools:sqlmap [NOT_RUN]`;
set `# TIMESTAMP:` ke 2025-01-01 → `FAIL 0C:tools:nuclei [NOT_RUN]`.

## 0C refs — "dibaca" ≠ "dipakai"
`reference-usage.json` menyimpan field `ref`. Kelas `refs` menuntut tiap sumber
(`bugbounty-playbook`, `poc-technique-atlas`, `security-arsenal`, `audit-execution-discipline`)
**menghasilkan ≥1 request nyata**. Terbukti: buang fired-clue satu sumber → `FAIL 0C:refs:<sumber> [NOT_RUN]`.

## GATE pasca-0D
0D jalan SEBELUM 0E/0E-REVIEW/0F, jadi `final_coverage_gate()` di orchestrator (setelah 0F)
memeriksa artefak 0E (`findings/chains/gated/validated/ready-candidates.json`),
0E-REVIEW (`review-candidates.json`, `REPORT-survivors.md`), 0F (`AUDIT-REPORT.md`, `drafts/`,
`poc-pdfs/`) + menjalankan `audit-checkpoint.py --phase all`. Ada yang kurang → **RuntimeError**,
audit TIDAK dianggap COMPLETE.

## ⛔ PITFALL DESAIN CHECKER — baca sebelum menambah gate baru

Empat kesalahan nyata saat membangun gate 0D ini (2026-10-07). Semua terbukti lewat uji-rusak,
bukan dugaan. Ulangi kalau menambah check/gate baru:

1. **Gate baru tanpa POPULATOR = pipeline HARD-BLOCK selamanya.**
   Menambah CHECK 12/13 ke `verify-tool-usage.py` padahal orchestrator tidak pernah membuat
   `asset-coverage.json` / `skill-usage.json` → 0D gagal terus, `RuntimeError` setelah 3x rework,
   audit mustahil selesai. Bukti: `❌ CHECK 12 FAILED: asset-coverage.json not found`.
   **Aturan: setiap gate baru wajib punya jalur yang mengisi datanya secara otomatis**
   (`asset-coverage.py --derive` dipanggil `prepare_coverage_gate()` sebelum gate).
   Gate yang hanya bisa dipenuhi manual = gate yang akan dilewati orang.

2. **Path bukti di `*-usage.json` RELATIF ke `target_dir` — `Path(x).exists()` polos salah.**
   Cek lama (CHECK 2/3/5/7/9/10/11) memakai `Path(ev).exists()` tanpa resolve, sehingga
   SEMUA artefak nyata dilaporkan hilang → gagal palsu pada audit yang sebenarnya selesai.
   Selalu resolve: `p if p.is_absolute() else target_dir / p` (helper `_ev()` / `_ev_ok()`).

3. **Status baru wajib masuk daftar FAIL.** `NOT_RUN` awalnya tidak ada di set `FAIL`, jadi
   laporan berbunyi `unknown status 'NOT_RUN'` alih-alih menamai asetnya. Nilai status baru
   harus ditambahkan ke `PASS`/`FAIL` sekaligus.

4. **`--derive` harus menurunkan status dari artefak nyata, bukan menandai USED asal ada.**
   Termasuk: klaim `EXECUTED` tapi file bukti hilang → `NOT_RUN` (bukan "unknown status"),
   `N/A` dengan alasan mengandung "timeout/skip/gak sempat" → DITOLAK, dan marker penulis asli
   wajib ada (`# TOOL EVIDENCE:` dst) supaya file isian seukuran tidak lolos.

**Cara memverifikasi gate, bukan mengasumsikannya:** bikin fixture "pipeline selesai penuh"
→ harus `ALL 13 CHECKS PASSED`; lalu rusak SATU aset (hapus file buktinya / ubah `# TARGET:` /
set `# TIMESTAMP:` basi) → harus FAIL **sambil menyebut nama asetnya**. Gate yang tidak bisa
menunjuk aset mana yang bolong belum layak dipercaya.

## Checklist per fase (WAJIB)
### 0B RECON — SEMUA sumber recon, bukan 1
subfinder + amass + puredns → DNS; httpx (title/tech/status); katana + gau + waymore → urls.txt;
jsluice (URL+secret); naabu (top-1000); dork (dork-recon.py 3 lapis). Semua hasil → FILE (CO-1).
Ref: `references/rules/*` + `bugbounty-playbook/references/recon/`.

### 0C EXPLOIT — INI YANG PALING KETAT: tinjau ULANG SEMUA yang kita punya
Sebelum mengklaim 0C COMPLETE, jalankan **seluruh** ledger berikut (tiap item = entri asset-coverage):
1. **Tools** — force-full-execution (C1) menjalankan SEMUA tool yang terpasang (bukan subset). Tool yang timeout → retry dgn timeout lebih besar / flag lain / versi manual.
2. **Payload variants** (C2) — `execute-variants.py` per vector; tiap vector EXECUTED + evidence.
3. **Business logic** (C3) — `execute-business-logic.py` 15/15 vector.
4. **PoC repos** (C4/C5) — `track-poc-execution.py` + `execute-poc-variants.py`: repo cocok tech WAJIB dieksekusi, bukan cuma di-clone.
5. **References** (C6) — `execute-references.py`: clue dari SETIAP ref dipakai → request nyata (`reference-usage.json`).
6. **PoC techniques** (C6b) — `execute-poc-techniques.py`: teknik dari `poc-technique-atlas` (28 kelas/~1900 teknik) dijalankan (`poc-techniques-usage.json`).
7. **Skills** — untuk SETIAP skill yang di-load (hunt-* / platform-*): jalankan checklist-nya sampai ada request/uji nyata; catat di `skill-usage.json` (`{"skill":"hunt-ssrf","applied":true,"evidence":"...","requests":N}`).
8. **Cookbook / exploit-book** — `exploit-cookbook`, `security-arsenal` (payload pack), `bugbounty-playbook/references/chains/` → minimal 1 teknik dari masing-masing dijalankan bila relevan ke permukaan target; kalau betul tak relevan → `N/A` + reason konkret (bukan "tidak sempat").
9. **Shelf** — `poc-technique-atlas/references/*` dipilih 1 kelas sesuai permukaan, dijalankan.

**Aturan rotasi (anti "curl doang"):** tiap endpoint/param dieskalasi ke ≥1 tool khusus + ≥1 payload variant + ≥1 teknik-cookbook sebelum boleh disimpulkan negatif. `curl` = LAST RESORT & pelengkap, bukan pengganti.

### 0D GATE — verify-tool-usage.py + asset-coverage.py WAJIB lulus
HARD BLOCK. Ada 1 FAIL → kembali ke 0C (auto-rework ×3). Jangan lapor.

### 0E / 0E-REVIEW — findings → candidate lifecycle
Lihat `references/candidate-lifecycle.md`.

### 0F REPORT — hanya untuk candidate yang lolos re-validasi
1 temuan = 1 draft email + PDF PoC terlampir → Gmail draft (jangan kirim).
**JANGAN gabungkan beberapa temuan dalam 1 draft.** Pengecualian tunggal: temuan yang saling
terkait dalam **satu chain attack** (B bergantung pada A; impact hanya tercapai lewat rantai
A→B→C) boleh jadi 1 draft — subject menyebut "chain", body menulis urutan rantainya.
Selain itu selalu dipisah (lihat `candidate-lifecycle.md`).
