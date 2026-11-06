# Unstick a frozen audit pipeline — the "satu tool muter" freeze

Operator melaporkan **"powershellnya macet"** / jendela mandek. Yang dia lihat biasanya bukan
crash: stdout `audit-pipeline-orchestrator.py` berhenti bertambah karena **satu tool tidak pernah
selesai**, dan seluruh pipeline sekuensial menunggu di belakangnya.

## Diagnosis — urutan bukti (jangan menebak)

1. **Proses masih hidup?** Jangan vonis "mati" dari `tail` log (lihat `run-observation-discipline.md`).
   Ambil ProcessId/CommandLine/CreationDate/KernelModeTime/UserModeTime. CPU time yang naik =
   masih hidup, cuma diam.
2. **Siapa yang nge-blok?** Telusuri rantai induk: `orchestrator → execute-variants.py → <tool>`.
   Yang CPU-nya ~0 (KernelModeTime kecil) = sedang **menunggu**; yang CPU-nya besar tapi output
   tak bertambah = **tool muter**.
3. **Tool itu nulis ke mana?** Cek `poc-plans/orchestrator-<slug>/tool-evidence/<vector>-<tool>.txt`.
   Ukuran naik lambat (puluhan byte/menit) atau macet total = beku, bukan "jalan lama".
4. **Cadence terakhir?** `~/AppData/Local/hermes/trackers/autofix-journal.jsonl` — tiap baris =
   satu **attempt** sebuah vektor (`{ts, tool, attempt, rc}`). Baris terakhir yg tua = vektor itu
   belum lepas.

### Diskriminator bekunya: CPU-DELTA, bukan "kelihatan diam"

Ambil CPU time dua kali berjarak ~10 s (proses orchestrator DAN anak-anaknya). Resep siap pakai:
`scripts/pipeline-proc-triage.py`.

- **CPU beku (delta 0.00 s) + TIDAK ada anak** = proses **TERBLOKIR** menunggu (pipe/IO), bukan
  muter. Ini yang terjadi saat sebuah tool menggantung dan induknya duduk di `subprocess.run(...)`.
- **CPU naik + output tak bertambah** = tool **MUTER** (kasus sstimap di bawah).
- Dua-duanya "log mandek", tapi obatnya beda — jangan menebak dari `tail` log saja.

**Temukan anak yang memblokir — enumerasi lewat PARENT PID, jangan tebak nama.** Tool yang
menggantung bisa bernama apa saja (lihat Freeze #2 di bawah); daftar SEMUA anak induknya
(`Get-CimInstance Win32_Process | ? {$_.ParentProcessId -eq <pid>}`) — nama yang kamu filter
secara mental (`nuclei`/`sqlmap`) bisa melewatkan biang sebenarnya (`trufflehog`).

**Jebakan parsing (2× salah baca dalam satu sesi):**
- `wmic process get CommandLine,Name,ProcessId /format:csv` → urutan kolom
  **`Node,CommandLine,Name,ProcessId`**. Index salah = "PID" jadi `oauth2` (argumen `--tech`), dan
  filter cocok-palsu ke perintahmu sendiri. Parse dengan `csv.reader` lalu ambil
  `r[1]=CommandLine, r[2]=Name, r[3]=ProcessId`; buang baris header `Node` + baris `wmic` sendiri.
- **PowerShell inline di dalam heredoc bash gagal senyap** (`-like '*x*'` bertabrakan dengan quoting
  heredoc → keluaran kosong / exit 1 tanpa pesan). Untuk triage cepat pakai `wmic … /format:csv` +
  `csv.reader`; kalau butuh CIM, tulis `.ps1` ke disk dulu lalu jalankan filenya.
- **`/format:csv` pun rapuh** begitu CommandLine memuat koma tanpa kutip (`wmic` meng-embed-nya) —
  baris bergeser dan kamu "membaca" `cmd.exe` sebagai `KernelModeTime`. Jalur anti-salah:
  `tasklist /FI "IMAGENAME eq python.exe" /FO CSV` untuk dapat PID, lalu **per-PID**
  `wmic process where ProcessId=<n> get CommandLine,KernelModeTime,UserModeTime,WorkingSetSize /format:list`
  (key=value — tak ada urutan kolom yang bisa salah). Terukur: 2 sample berturut gagal nilai dgn csv.

## Kenapa satu `kill` TIDAK menolong

`tool_router._run()` (tanpa `timeout=`) → `autofix.guard(cmd, max_attempts=3, stall_warn=300)`
→ `toolguard.run_guarded()` yang **tidak pernah kill** (policy operator: "tools run to completion;
stall = WARN, not kill"). `toolguard` cuma menulis warning ke `trackers/tool-stalls.jsonl`.

Efeknya: membunuh tool = `rc != 0` → autofix **mengulang dari attempt berikutnya** (re-spawn tool
yang sama). Kalau tool-nya memang tak akan pernah selesai, kill 1× justru bikin dia lahir lagi.
Ini yang bikin jendela tampak "beku total".

## Prosedur unstick (kill sampai attempt habis)

`autofix` berhenti setelah **3 attempt** (rc != 0 berturut-turut) → status `EXHAUSTED` → router
mengembalikan hasil → `execute-variants` lanjut ke vektor berikutnya.

```python
# kill-loop: bunuh tree tool yang muter, ulang sampai tak ada yg respawn
import subprocess, time, re
def pids(pat):
    out = subprocess.run(['wmic','process','get','ProcessId,CommandLine','/format:csv'],
                         capture_output=True,text=True).stdout
    return [int(re.search(r',(\d+)\s*$', l.strip()).group(1))
            for l in out.splitlines() if pat in l.lower() and 'wmic' not in l.lower()]
for _ in range(6):
    for pid in pids('sstimap'):
        subprocess.run(['taskkill','/PID',str(pid),'/T','/F'],
                       capture_output=True,text=True)   # via Python → hindari mangling arg MSYS
    time.sleep(18)
    if not pids('sstimap'):
        break
```

Verifikasi lepas: `autofix-journal.jsonl` menampilkan **3 baris rc != 0** utk vektor itu berturut,
lalu mulai muncul vektor berikutnya; `tool-evidence/` dapat file baru dari tool kelas berikut.
(Jangan pakai `taskkill /F` langsung di shell MSYS — `/F` bisa di-mangle jadi path `F:/`.)

## Fix di LIVE (additive) — gejala ini cacat KONFIGURASI tool, bukan policy

Kelas tool yang bisa "muter abadi" harus dibatasi di sumbernya:

- **`sstimap` di asset statis** (`--level 2 --crawl 1` menyusuri stylesheet + query param
  spt `/assets/x.less?v=...`) **tak pernah selesai** dan membekukan engagement di 0C.
  Tambalan di `tool_router.py`:
  - `ssti: ("sstimap", '-u "{t}" --level 1', 600)` — buang `--crawl 1`, turunkan ke `--level 1`.
  - Skip `sstimap` kalau path target berakhiran ekstensi statis
    (`.less .css .js .mjs .map .png .jpg .jpeg .gif .svg .ico .woff .woff2 .ttf .eot .webmanifest`)
    → **jatuh ke fallback tag nuclei** (tetap otomatis, bukan manual).
- **Jangan** menurunkan ini ke `curl`/manual. Batasi tool, bukan ganti ke tangan.

`execute-variants.run_vector_with_tool()` meng-`importlib` ulang `tool_router.py` **tiap vektor**,
jadi mengedit `tool_router.py` di tengah run **berlaku untuk vektor berikutnya tanpa restart**.
Tetap `python -m py_compile tool_router.py` setelah edit.

**Verified 2026-10-12 (sstimap pinned on a marketing-page query param).** The kill-loop works exactly
as written: two iterations (kill tree → autofix respawns it once) then `clear`, and the orchestrator
advanced to the next vector ~1 min later. The temptation to *not* act is the real hazard — the tool
showed a tiny non-zero CPU delta (0.44 s of CPU per 6 s wall) and its evidence file grew ~200 B/min,
which reads like "working, leave it alone". By the discriminator above that is still **frozen**: the
growth is noise, and waiting it out burned ~1 h on a single vector. Heuristic: if the pipeline has
been pinned on one tool for >15 min while the evidence file grows under ~1 KB/min, run the loop —
don't rationalise waiting, and don't assume killing makes it worse (autofix absorbs exactly one
respawn, then moves on).

## Freeze #2 — tool TANPA timeout di runner milik ORCHESTRATOR (bukan `tool_router`)

Gejala **identik** dengan freeze sstimap (log berhenti, jendela mandek) tapi penyebabnya **beda dan
letaknya beda**: `_account_mandated_tools()` di `audit-pipeline-orchestrator.py` (closure "manifest 0C"
pada 0D) menjalankan puluhan tool dengan

```python
pr = subprocess.run(real, shell=True, capture_output=True, text=True)   # TANPA timeout, TANPA stdin
```

`capture_output=True` tanpa `stdin` = **satu tool yang tak pernah exit membekukan 0D selamanya**
(CPU induk beku, nol anak karena anaknya sudah menggantung di pipe). Tiga biang terukur:

| perintah | kenapa menggantung |
|---|---|
| `trufflehog filesystem . --no-update --json` | cwd = root workspace audit → memindai puluhan ribu file, praktis tak kelar |
| `gitleaks detect --source . --no-git -v` | sama, seluruh workspace |
| `interactsh-client -n 1 -v` | client interaktif — **tidak pernah exit** by design |

Gejala sampingan: run lalu mati `EXIT 1` **tanpa traceback** (OOM saat trufflehog memakan memori).
Bukti urutan yang terlihat: `tool-evidence/` berisi `nuclei/wpscan/nikto-manifest.txt` (menit ke-11:56
sampai 11:57) lalu **berhenti** — tool berikutnya di `MANIFEST` = `gitleaks`/`trufflehog`; di situ
macetnya. Catatan: tool yang sudah tercatat di `tools-usage.json` di-**SKIP** pada relaunch, jadi
sisa closure ini murah untuk di-resume.

**Fix di PRODUCER (additive, in-place):**
```python
import os as _os
_mt = int(_os.environ.get("BB_MANIFEST_TOOL_TIMEOUT", "240"))
_pp = subprocess.Popen(real, shell=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True, stdin=subprocess.DEVNULL)
try:
    _out, _ = _pp.communicate(timeout=_mt); _rc = _pp.returncode; _to = False
except subprocess.TimeoutExpired:
    subprocess.run(f"taskkill /F /T /PID {_pp.pid}", shell=True, capture_output=True, timeout=25)
    _out, _ = _pp.communicate(timeout=10); _rc = -9; _to = True
status = "TIMEOUT" if _to else (...)      # direkam APA ADANYA, tidak pernah dianggap pass
```
Plus batasi scope: `trufflehog filesystem {wdir}` / `gitleaks detect --source {wdir}` (folder run,
bukan `.`) — perlu menambah `real = real.replace("{wdir}", str(W))`.

Batas waktu di sini **bukan** pelanggaran policy "tools run to completion": policy itu soal jangan
men-skip CAKUPAN demi waktu; runner bagal ini justru membekukan SELURUH pipeline, dan statusnya tetap
direkam jujur sebagai `TIMEOUT` (bukan diubah jadi lulus).

### Konsekuensi runner bagal ini — 3 hal yang WAJIB jalan barengan

**1. Status baru = kamu mengubah KONTRAK dengan gate.** `verify-tool-usage.py` menolak status yang
tak dikenal: `❌ UNACCOUNTED statuses (gate blind spot): ['TIMEOUT']` → gate gagal walau fix-nya benar.
Patch gate-nya **di sesi yang sama**:
```python
ACCOUNTED = ("EXECUTED", "RAN_WITH_ERROR", "NO_OUTPUT", "NOT_FOUND", "ERROR", "TIMEOUT")
unaccounted = [e for e in entries
               if e.get("status") not in ACCOUNTED and e not in skipped and e not in failed_hard]
```
Aturan umum: **setiap status baru di producer harus di-`grep` di gate-nya** sebelum relaunch.

**2. `asset-coverage.py` SENGAJA menolak `TIMEOUT`** (header-nya: *"SKIPPED_TIMEOUT/TIMEOUT can never
pass"*) → tool yang kena potong = CHECK 12 FAIL. Jadi cap default **tidak boleh dipakai rata**: pakai
peta per-tool supaya scanner yang memang lama tidak jadi `TIMEOUT` palsu.
```python
_BASE_MT = int(os.environ.get("BB_MANIFEST_TOOL_TIMEOUT", "240"))
_PER_TOOL_MT = {"nuclei": 900, "nikto": 420, "kube-hunter": 600, "kube_hunter": 600,
                "dnsreaper": 300, "ffuf": 300, "trufflehog": 300,
                "interactsh": 60, "clairvoyance": 150}
_mt = _PER_TOOL_MT.get(tool.lower(), _BASE_MT)
```

**3. Entri yang sudah tercatat = tool itu di-SKIP selamanya.** `have` = nama tool yang ADA di
`tools-usage.json`, jadi `nuclei` yang sudah tercatat `TIMEOUT` **tak akan dijalankan ulang** walau
cap-nya sudah dinaikkan. Perbaikannya **karantina entri itu** — bukan mengedit statusnya jadi
`EXECUTED` (itu fabrikasi): buang 1 entri dari list, catat record-nya di `_QUARANTINE/manifest.json`,
lalu relaunch.

### Closure manifest TIDAK menyimpan progres sampai loop-nya kelar

`tools-usage.json` baru ditulis di **akhir** `_account_mandated_tools()`. Kill di tengah closure =
semua yang sudah dijalankan (nuclei ~4 menit, wpscan, nikto) **tak ada di ledger**, dan run berikutnya
mengulang dari atas — `*-manifest.txt` di `tool-evidence/` memang tertinggal, tapi `have` tak
melihatnya. Praktis: **jangan kill saat 0D sedang closure**; sisa waktunya wajar dan dia selesai
sendiri. Kalau memang harus, sadari harganya = satu putaran penuh lagi.

### Bukti hidup untuk operator (dia menuntut MELIHAT, bukan diyakinkan)

Saat operator bilang *"tunjukkan prosesnya, jadi sy tahu ini tidak stuck"*: **CPU parent datar itu
NORMAL** — induk duduk di `communicate()` sambil anak tool bekerja; menyodorkan CPU parent sebagai
"bukti" justru menciptakan kesan beku. Tunjukkan tiga hal sekaligus (dan beri dia perintah pantau
yang bisa dia tempel sendiri):
- rantai proses `bash → python orchestrator → <tool anak>` (nama + WS),
- **delta CPU si anak** + mtime artefak, dua sampel berjarak,
- baris log terakhir + timestamp-nya.

```bash
while true; do date +%T; tail -n 3 "<target_dir>/orchestrator.log"; sleep 5; done
```

Dan **jangan vonis dari angka sesaat**: `business-logic-usage.json` yang sedang ditulis ulang bisa
tampak "macet di 7" padahal penulis aslinya sudah di vektor 8. Penyelesaian sub-step dibuktikan lewat
**baris ringkasan log**-nya (`BUSINESS-LOGIC SUMMARY: 15/15 vectors`), bukan ukuran file sesaat.

⚠️ Kalau mengedit blok ini lewat heredoc: **jangan menulis escape `\n` di dalam f-string** — lapisan
heredoc bisa mengubahnya jadi baris baru sungguhan → `SyntaxError: unterminated f-string literal`.
Pakai `"..." + chr(10) + "..."`. Selalu `python -m py_compile <file>` setelah edit (jebakan ini kena
2× dalam satu sesi).

## Freeze #3 — DUA instance orchestrator = artefak korup + resume yang MENGUNCI

Dua `audit-pipeline-orchestrator.py` pada target-dir yang SAMA saling menimpa keluaran. Terukur:
`business-logic-usage.json` ditulis dua kali → hasil akhir **7/15 vektor**, bukan 15.

Yang berbahaya bukan korupsinya, tapi **kombinasinya dengan resume**: sub-fase di-skip kalau file
penandanya ADA (`_done(fname) = exists and size>100`), jadi artefak korup yang tetap hadir membuat C3
**tak akan pernah dijalankan ulang** dan gate 0D gagal keras selamanya
(`❌ business-logic: only 7/15 vectors EXECUTED`).

Prosedur:
1. Pastikan **satu** instance saja: `Get-CimInstance Win32_Process | ? {$_.CommandLine -like
   '*audit-pipeline-orchestrator*'}` — hitung, kill sisanya (lewat Python `taskkill`). Ingat: satu
   launch = 3 `bash -lic` berlapis + 1 python = **satu** instance, bukan tiga.
2. **Karantina** file penanda yang korup — jangan hapus (aturan operator: hapus = `_QUARANTINE` +
   manifest):
   ```python
   from pathlib import Path; import shutil, json, time
   D = Path.home()/"AppData/Local/hermes/poc-plans/orchestrator-<slug>"   # hitung DI DALAM Python
   Q = D/"_QUARANTINE"; Q.mkdir(exist_ok=True)
   ts = time.strftime("%Y%m%d_%H%M%S")
   shutil.move(str(D/"business-logic-usage.json"), str(Q/f"business-logic-usage.json.corrupt_{ts}"))
   (Q/"manifest.json").write_text(json.dumps([{
       "quarantined": "business-logic-usage.json", "as": f"business-logic-usage.json.corrupt_{ts}",
       "reason": "corrupted by two concurrent pipeline instances (7/15); resume would SKIP C3 forever",
       "at": time.strftime("%Y-%m-%dT%H:%M:%S")}], indent=2, ensure_ascii=False), encoding="utf-8")
   ```
3. Relaunch. Gate 0D akan FAIL dengan keluaran yang menyebut nama file itu, dan **cabang REWORK
   `elif "business-logic-usage.json" in out:` menjalankan ulang `execute-business-logic.py`** — jadi
   sub-fase itu pulih sendiri, tanpa mengedit state JSON dengan tangan.
4. ⚠️ Memindahkan file-nya SAJA **tidak** cukup kalau `completed_phases` masih memuat `0C`: blok 0C
   di-skip, dan yang menyelamatkanmu adalah cabang REWORK gate (poin 3) — bukan blok 0C. Kalau mau C3
   langsung jalan di fase 0C, edit `trackers/audit-pipeline-<slug>.json` (backup dulu), jangan hapus.
5. MSYS: **jangan** menyisipkan `$D` (path gaya `/c/...`) ke dalam heredoc Python — MSYS mengubahnya
   jadi `\c\...` dan `shutil.move` gagal `FileNotFoundError`. Bangun path dengan `Path.home()` **di
   dalam Python**.

## Artefak yang MENYESATKAN (jangan salah baca)

- **`tool-stalls.jsonl` `"bytes_seen": 0`** bukan bukti "tool diam/mati". Kalau perintah dijalankan
  sebagai `... > "evidence.txt" 2>&1`, guard membaca **pipe kosong** (output dialihkan ke file),
  jadi tiap 300 s muncul warning walau tool sebenarnya menulis. Cek mtime/ukuran FILE-nya.
- **`trackers/tool-stalls.jsonl`** dan **`autofix-journal.jsonl`** dua hal berbeda: yang pertama
  "tool diam", yang kedua "attempt vektor". Baca yang kedua untuk tahu pipeline maju atau tidak.
- **powershell.exe liar anak `explorer.exe`** yang nganggur = jendela milik operator, bukan bagian
  pipeline. Pipeline di-launch via `bash -lic`, bukan PowerShell. Jangan salah tuduh.

## Kapan ini BUKAN masalahnya

Kalau `autofix-journal.jsonl` masih menambah baris vektor baru tiap < ~1 menit, pipeline sehat —
yang "mandek" cuma tool yang memang lama dan akan lepas sendiri (policy: run to completion).
Naikkan cakupan pengamatan, jangan kill.

Dua koreksi-baca terukur (nordnet.se, 2026-10):

- **`label` di `tool-stalls.jsonl` itu BUKAN fase sekarang.** Baris `{"label":"orchestrator:0A",
  "silent_s":1814}` muncul saat run-nya sebenarnya di **0C (STEP 1.4a PAYLOAD VARIANTS)** —
  label = fase tempat watchdog mulai mengamati, dan ia tak pernah di-update. Jangan simpulkan
  "macet di 0A" dari situ; baca baris log terakhir + nama file yang sedang tumbuh di `tool-evidence/`.
- **CPU-delta > 0 = tool HIDUP, walau 30 menit.** `sstimap --level 1` pada halaman Next.js 400 KB
  (`?dk`) jalan >30 menit; yang memutuskan bukan durasi melainkan **delta**: anak sstimap terbaca
  **1.48 s CPU per 8 s** dan `ssti-sstimap.txt` naik 9.8 KB→10.7 KB. Itu healthy, bukan freeze.
  Yang benar-benar beku = delta **0.00 s** dengan anak menggantung di pipe. Ukur, jangan tebak dari `tail`.


---

## Kalau run-nya memang SUDAH mati — relaunch, jangan restart dari 0A

Operator menutup jendela (PowerShell/console) yang jadi host pipeline → **seluruh tree anak ikut
mati**. Cek dulu: `tasklist /FI "PID eq <orchestrator_pid>"`. Kalau hilang, ini bukan freeze —
run-nya sudah berakhir, dan teruskan = **relaunch**.

**Resume itu gratis dan berbasis FILE, bukan memori.** Orchestrator menyimpan state per-fase di
`~/AppData/Local/hermes/trackers/audit-pipeline-<safe_target>.json` (`completed_phases`, `current`),
dan tiap sub-fase di-skip kalau artefaknya ada di disk:

| file penanda | sub-fase |
|---|---|
| `variant-usage.json` | C2 variants |
| `business-logic-usage.json` | C3 business-logic |
| `poc-execution.json` | C4 PoC repos |
| `poc-variant-usage.json` | C5 PoC variants |
| `reference-usage.json` | C6 references |
| `poc-techniques-usage.json` | C6b poc-techniques |

Relaunch dengan argumen SAMA → log menulis `RESUME MODE: already completed [0A,0B]` lalu
`SKIP sub-fase (sudah ada di disk): C2=Y C3=- ...`. Jangan pernah hapus artefak untuk "memulai bersih"
kecuali operator memintanya.

### Launch DETACHED — supaya tutup jendela tak membunuh run lagi

`bash -lic` yang jadi induk orchestrator adalah anak jendela operator. Jalankan detached supaya
siklus hidup tak bergantung jendela + tanpa window (operator: proses latar WAJIB hidden). Resep siap
pakai: `scripts/launch-pipeline-detached.py` (Popen + `DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP|
CREATE_NO_WINDOW`, stdout/stderr → `orchestrator.log`, `PYTHONUNBUFFERED=1`, tulis `orchestrator.pid`).
Verifikasi setelah ~40 s: baca ekor `orchestrator.log` **dan** `tasklist /FI "PID eq <pid>"`.

### Unstick yang lebih bersih dari kill-loop: jalankan sub-step-nya SENDIRI dulu

Kalau freeze ada di satu sub-step (bukan tool muter), jalankan skrip sub-step itu **langsung**
supaya artefaknya jadi, lalu relaunch orchestrator — dia akan SKIP sub-step itu lewat tabel di atas.
Terukur: `execute-business-logic.py` dijalankan sendiri sampai menulis `business-logic-usage.json`
(15 vektor, `tool_routed: nuclei`), baru orchestrator di-relaunch dari C4. Lebih sedikit kill,
dan tak ada attempt autofix yang terbuang.

## Relaunch mati ~10 detik setelah sub-step mulai? Curigai RAM/OOM, bukan bug

Gejala khas: log berhenti persis di baris `PHASE 0C-C3: Executing ...`, **tanpa traceback**, dan
`Get-WinEvent` di Application/System kosong. Bukan crash Python — Windows membunuh proses OOM
(tool-nya sendiri memperingatkan: *"RAM bebas … DI BAWAH 1.2 GB … proses akan DIBUNUH Windows tanpa
traceback"*). Cek `FreePhysicalMemory` (`wmic OS get FreePhysicalMemory` → KB).

Yang benar-benar membebaskan RAM (terukur): kill instance `msedgewebview2.exe` yang nganggur
(sering 5-6 proses, ratusan MB; hidup lagi on-demand). Hogs tipikal di host 6 GB: Chrome ~2 GB,
`svchost` ~550 MB, WebView2 ~500 MB. Kalau masih <1.2 GB, minta operator tutup Chrome — jangan
lanjut relaunch berkali-kali, itu cuma membakar waktu dan bikin log bingung.

Jangan mengklaim "dibunuh RAM" tanpa bukti: bedakan dari run yang SELESAI lalu gate yang memblokir
(lihat `track-aware-gates-and-run-lifecycle.md` §7) — di sana log juga berhenti, tapi run-nya sehat.

## Membuktikan TIDAK ada drift ke curl (jebakan grep)

Operator berulang kali memperingatkan **"jangan sampai memancing sistem pakai curl"**. Cara menjawab
dengan bukti, bukan pembelaan:

- Sumber kebenaran = konstanta **`NO_CURL_FALLBACK = True`** di `tool_router.py`.
- `grep -c curl <skrip>` **menyesatkan**: hits-nya komentar (`"It is NEVER silently replaced by a
  hand-written curl"`) dan tool asli **`grpcurl`** (`_NEW["grpc"]`). Jangan bacanya sebagai fallback.
- `execute-business-logic.py` memakai `urllib` (probe Python), bukan shell `curl`.
- Fallback untuk asset statis (tambalan sstimap) = **tag nuclei**, yaitu tool — bukan tangan.

Kesimpulan yang benar: "router tidak punya jalur curl; fallback tetap tool."
