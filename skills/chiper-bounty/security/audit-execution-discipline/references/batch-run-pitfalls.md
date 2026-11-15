# Batch & Nonstop Run Pitfalls — measured 2026-10-22 (batch1, 10 target)

Semua di bawah **terukur**, bukan teori. Sumber: batch1 (docs.obol.org, zkb.ch,
galaxus.at, obdev.at, orf.at, studentjob.at) + koreksi operator sesi ini.

---

## A. Full reset sebelum batch mulai dari nol

Operator: *"stop n kill dl semua proses sebelum mulai baru dr awal utk batch ini."*

Urutan wajib:
1. **Kill semua proses audit** — `orchestrator`, `execute-variants`, `execute-poc*`,
   `force-full*`, `dom-xss`, `rce-verify`, `impact-verify`, `batch_watchdog`,
   `tool_sweeper`, `audit-run-all`. Pakai tree-kill (`taskkill /T /F`).
   **Cek dulu** daftar proses dan cocokkan dengan hint `protect_process` — engagement
   paralel (mis. quarterwise) TIDAK boleh ikut mati.
2. **Hapus TIGA file state per target** (kalau kurang satu, pipeline resume):
   - `trackers/audit-pipeline-https___<domain>.json`  (state fase)
   - `trackers/force-state-https___<domain>.json`     (state force-execution)
   - `trackers/https___<domain>.json`                 (state skill-loading)
3. Hapus `target-pool/audited.json` (penanda target selesai).
4. Verifikasi `PHASE_LOG.md` timestamp = run baru (bukan lama).

**Tanpa langkah 2, pipeline resume dari 0C dan artefak 0B lama jadi STALE** → gate
menolak evidence (lihat E).

---

## B. Exit code harus jujur

| gejala | penyebab | fix |
|---|---|---|
| `rc=0` padahal pipeline gagal | `cmd \| tail -60` → `$?` = exit code **tail** | redirect Python: `open(out,"w")` + `subprocess.run(stdout=fh)` |
| `rc=-1` dalam 1 detik | `bash -c "... > D:\path\file"` — bash tak kenali path Windows | jangan pakai bash redirect; Python `open()` |
| `rc=124` | timeout watchdog | naikkan timeout, JANGAN potong coverage (lihat C) |

Sumber kebenaran progres = **PHASE_LOG.md + hitung artefak**, bukan exit code.

---

## C. Coverage TIDAK dipotong — pakai timeout

Koreksi operator: *"jgn batasi variants, nnti skillny truncated"* dan
*"jangan batasi variants/max-varians; coverage penuh, pakai timeout bukan potongan"*

Terukur di zkb.ch (539 subdomain):
- `execute-variants --max-variants 100 --rate 3` → >60 menit, tampak macet
- `rce-verify --limit 12 --sleep 5 --timeout 20` → >25 menit (network wait, CPU hanya 38s)

Aturan: **jumlah/parameter TETAP, tambahkan timeout**:
- variants: `timeout=2700` (45m) → `TimeoutExpired` → pakai artefak parsial, lanjut
- rce-verify: `timeout=1500` (25m) → sama
- watchdog per target: `timeout=4800` (80m)

Setelah timeout, artefak yang sudah jadi **tetap dipakai** — jangan diulang dari nol.

---

## D. Bug catalog (gejala → akar → fix)

| # | gejala | akar masalah | fix | file |
|---|---|---|---|---|
| 1 | `FileNotFoundError: '\c\Users\...'` | orchestrator pass path MSYS `/c/...` ke tool native | normalisasi di constructor: `/x/` → `X:/` | `force-full-execution.py` |
| 2 | 13 tool TERPASANG tapi `NOT_RUN` | tak masuk `MANDATORY_TOOLS` **dan** tak punya branch command → jatuh ke `FUZZ_ONLY` | tambah ke `MANDATORY_TOOLS` + branch `elif tname == "..."` per tool | `force-full-execution.py` |
| 3 | `kiterunner` NOT_FOUND padahal ada | CMD pakai `kr` → resolve ke shim rusak di Python Scripts | `kiterunner scan {host} -q` (host, bukan URL; tanpa `-A`) | orchestrator CMD dict |
| 4 | tool ADA tapi tercatat `NOT_FOUND` | `absent` dideteksi dari **output string** ("is not recognized") | cek `shutil.which(tool)` dulu; kalau ada → `RAN_WITH_ERROR` + catat "perbaiki CMD" | orchestrator |
| 5 | 8 tool recon NOT_RUN padahal `recon-evidence/recon-*.txt` ADA | `derive()` cuma baca `tools-usage.json`; recon nulis ke folder sendiri | fallback: baca `recon-evidence/recon-<tool>.txt`, parse `# TOOL EVIDENCE:` + `EXIT/STATUS:` | `asset-coverage.py` |
| 6 | 5 tool N/A sah FAIL gate | `derive()` tak memetakan status `N/A` | `if st == "N/A": setu(key,"N/A",reason=...)` | `asset-coverage.py` |
| 7 | `CHECK 2b FAILED: unaccounted statuses ['N/A']` | `verify-tool-usage.py` tak kenal status `N/A` | tambah `"N/A"` ke list `skipped` | `verify-tool-usage.py` |
| 8 | tool EXECUTED terbaca NOT_RUN | evidence tak punya marker `# TOOL EVIDENCE:` | sweeper tulis marker + header (tool/cmd/rc/ms/bytes) di `ok()` | `tool_sweeper.py` |
| 9 | `.BAT`/`.CMD` gagal dieksekusi | `subprocess.run` tak bisa eksekusi `.BAT` langsung | `shell=True` kalau `cmd[0]` berakhir `.bat`/`.cmd` | `tool_sweeper.py` |
| 10 | shim rusak dianggap terpasang | `shutil.which()` mengembalikan path `.BAT` yang binary-nya hilang | baca isi shim, cek target `.exe`/`.py` ada | `tool_sweeper.py` |
| 11 | `depth-gate: 123 BLOCK` | gate memindai `findings.json` = kandidat mentah 0C-C7 | gate HANYA untuk file laporan: `passed-findings.json`, `survivors.json`, `validated-findings.json` | `depth_gate.py` |
| 12 | audit negatif (0 temuan) gagal gate | `_gate_na_discipline` tak punya pengecualian status sah | `OK_RE` (SKIP_NO_PARAM/STARTED_NO_TOKEN/…/tool tidak terpasang) + `NEG_RE` (produced empty/nothing to draft/negative audit) | orchestrator |
| 13 | `kxss` rc=`0xC0000142` | Windows gagal start proses — RAM habis | bunuh dalfox zombi (769MB); RAM 1.1G → 2.6G | — |
| 14 | dua `execute-variants` utk target sama | run terputus tinggalkan zombi | cek PID + umur; bunuh yang paling tua | — |
| 15 | gate lolos padahal tool tak jalan | `_BAD_REASON` cuma 5 kata | perluas 30+ kata + `_OK_REASON` (lihat #12) | `asset-coverage.py` |

---

## E. Negative audit harus DIBUKTIKAN

Koreksi operator: *"negative audit ttp harus berdasarkan hasil proses skill dan tools
yg berjalan. Kl tools/skill hanya dijalankan tipis di permukaan, atau malah hanya curl
aja, ttp harus ditolak, wajib dijalankan ulang."*

`_gate_negative_audit()` (0F-pre, hanya kalau 0 temuan) menuntut:
1. tool `EXECUTED >= 25` (default; env `NEG_AUDIT_MIN_EXECUTED`)
2. `NOT_RUN == 0` — tool **ada tapi tak dijalankan** = BLOCK.
   `NOT_FOUND` (tool tak terpasang) = N/A sah, tidak memblokir.
3. Artefak fase inti ADA: `business-logic-usage.json`, `reference-usage.json`,
   `impact-verification.json`, `dom-xss-usage.json`

**Mekanisme pendukung yang mudah terlupa:** `asset-coverage` menolak evidence
**STALE** — kalau `timestamp` di evidence file **lebih awal** dari run start, status
jadi `NOT_RUN` dengan alasan *"predates the run — stale/hand-me-down evidence"*.
Inilah yang membuat audit "sekali jalan lalu resume" tak bisa lolos dengan artefak
run sebelumnya. Terukur: obol run fresh → `subfinder`/`httpx` (timestamp 17:25) USED,
`amass`/`katana`/`gau`/`waymore`/`naabu` (timestamp 02:11) NOT_RUN.

**Konsekuensi operasional:** kalau recon di-skip karena `subs.txt` sudah ada, evidence
tidak diperbarui → gate akan menolak. Reset state (bagian A) atau paksa re-run recon.

---

## F. Higiene proses & RAM

- **dalfox = pemakan RAM terbesar** (terukur 780MB + 569MB + 157MB = ~1.5GB untuk 3
  instance). Kalau RAM < 1.5G, bunuh instance **paling tua** (cek `CreationDate`).
- `chrome-headless-shell` juga berat (681MB) — biasanya anak dari DOM-XSS test.
- **Zombi detection**: dua proses `execute-variants.py` untuk target yang sama =
  satu zombi. Pakai umur (`AgeMin`) untuk memilih yang dibunuh.
- **Stale/hang → kill, mulai baru** (hint operator): kriteria = tak ada artefak baru
  >10 menit ATAU CPU time tak naik ATAU zombi dari run terputus.
  `hint_store.py stale_processes(max_idle_min=10)` mendeteksi ini dan
  **menghormati `protect_process`**.

---

## G. Hint discipline (konsep Cairn, `hint_store.py`)

Koreksi operator jadi **artefak persistens**, bukan ingatan chat.

- Hint **SITUASIONAL, bukan permanen** (koreksi operator: *"sesuai keadaan aj"*).
  Berlaku selama kondisinya cocok; kalau berubah → `deactivate`.
- 4 aksi: `note` · `skip_tool` · `skip_phase` · `protect_process`
- `protect_process` **memblokir kill** proses yang cocok pattern — inilah yang melindungi
  engagement paralel (quarterwise).
- Gate dicek sebelum aksi destruktif; orchestrator cetak hint aktif di awal pipeline.

```bash
python hint_store.py add --content "..." --action protect_process --pattern quarterwise
python hint_store.py add --content "..." --target docs.obol.org --action skip_tool --tool nikto
python hint_store.py list [--target X]
python hint_store.py deactivate --target _global --id h001
```
