# Pipeline Harness Fixes — 2026-10-22 (batch1 run)

Semua di bawah TERUKUR pada batch 10 target (docs.obol.org, zkb.ch, galaxus.at, obdev.at, …).
Kode: `scripts/force-full-execution.py`, `scripts/tool_sweeper.py`,
`scripts/audit-pipeline-orchestrator.py`, `scripts/batch_watchdog.py`,
`scripts/depth_gate.py`, `skills/security/audit-execution-discipline/scripts/asset-coverage.py`.

---

## 1. NOT_FOUND salah deteksi — koreksi operator: "tools itu udh ad semua"

**Gejala:** tool TERPASANG (`kiterunner.exe` 22.9MB di `go/bin`) tercatat `NOT_FOUND`.

**Akar:** status `absent` ditentukan dari OUTPUT string, bukan dari keberadaan binary:
```python
absent = bool(re.search(r"is not recognized|command not found|No such file", body, re.I))
```
CMD manggil `kr` → resolve ke **shim rusak** di `Python314/Scripts/` → output
`'...kiterunner.exe' is not recognized` → tercatat NOT_FOUND, padahal
`shutil.which('kiterunner')` menemukan binary asli.

**Aturan (orchestrator + tool_sweeper):**
```python
absent = bool(re.search(r"is not recognized|command not found|No such file", body, re.I))
if absent:
    probe = shutil.which(tool) or shutil.which(real.split()[0])
    if probe:
        absent = False   # binary ADA -> RAN_WITH_ERROR (CMD salah), BUKAN NOT_FOUND
```

**Bedakan tiga hal:** `NOT_FOUND` (binary tak ada) · `NOT_RUN` (ada tapi tak dijalankan) ·
`RAN_WITH_ERROR` (CMD salah). Hanya `NOT_RUN` yang memblokir negative-audit gate.

---

## 2. MSYS path → FileNotFoundError

Orchestrator dijalankan dari git-bash → mem-pass `/c/Users/...` ke tool Python native.
`Path('/c/Users/x')` → `\c\Users\x` → `write_text` gagal `FileNotFoundError`.
**Terukur:** obdev.at `force-full-execution` gagal total, 0 artefak, 20 menit terbuang.

**Fix (constructor tiap tool):**
```python
_s = str(output_dir).replace("\\", "/")
if len(_s) > 2 and _s[0] == "/" and _s[2] == "/" and _s[1].isalpha():
    _s = _s[1].upper() + ":" + _s[2:]
self.output_dir = Path(_s)
```

---

## 3. Tool terpasang tapi TAK PERNAH dipanggil

**Terukur:** 13 tool ada di host tapi tak masuk `MANDATORY_TOOLS` di force-full-execution.py
→ jatuh ke default `FUZZ_ONLY` → tak pernah dijalankan.

Tool: `ffuf, kiterunner, puredns, shuffledns, hakrawler, byp4xx, subzy, dnsreaper,
trufflehog, graphw00f, clairvoyance, xsstrike, grpcurl`.

**Dua hal yang WAJIB saat menambah tool:**
1. tambah ke `MANDATORY_TOOLS` (key = vektor, value = list tool)
2. tambah branch `elif tname == "<tool>":` dengan command BENAR — tanpa branch tool
   jatuh ke `FUZZ_ONLY` dan tidak dijalankan

**CMD yang sudah teruji:**

| tool | command | catatan |
|---|---|---|
| kiterunner | `kiterunner scan {host} -q` | pakai **HOST** bukan URL; binary `kiterunner`, bukan `kr` |
| puredns | `puredns resolve {subs.txt} -q --bin shuffledns` | massdns TAK terpasang; shuffledns pengganti |
| shuffledns | `shuffledns -l {subs.txt} -r {resolvers.txt} -mode resolve` | butuh `resolvers.txt` |
| byp4xx | `byp4xx {url}` | |
| subzy | `subzy run --targets {subs.txt} --hide_fails` | butuh **FILE**, bukan string domain |
| trufflehog | `trufflehog filesystem {dir} --json --no-verification` | versi baru tak punya subcommand `web` |
| dnsreaper | `dnsreaper domain --domain {host} --out {file}` | |
| graphw00f | `graphw00f -u {url}/graphql` | probe `/graphql` dulu |
| clairvoyance | `clairvoyance {url}/graphql` | probe `/graphql` dulu |
| xsstrike | `xsstrike -u {url}/?q=XSSTRIKE --crawl` | probe refleksi parameter dulu |
| grpcurl | `grpcurl -plaintext {host}:443 list` | |
| hakrawler | `hakrawler -url {url} -depth 2 -plain` | |
| ffuf | `ffuf -u {base}/FUZZ -w {wl} -mc 200,204,301,302,307,401,403 -t 20 -s` | |

Kalau prasyarat tak ada (`subs.txt` belum ada, `/graphql` 404) → `SKIP_NO_PARAM` +
alasan eksplisit. **JANGAN** `FUZZ_ONLY` diam-diam.

---

## 4. tool_sweeper.py — paksa semua tool relevan JALAN sebelum gate 0D

`scripts/tool_sweeper.py` dipanggil orchestrator **sebelum** `verify_tool_usage()`.
Alur: `guard` (which + validasi shim) → probe relevansi → run → catat → append ke
`tools-usage.json` via `usage_ledger.append_entries` (append-only).

**WAJIB: tulis marker `# TOOL EVIDENCE:` di setiap log.** `asset-coverage.py --derive`
memerlukan marker itu. Tanpa marker, tool yang EXECUTED terbaca `NOT_RUN`
(terukur: 6 tool EXECUTED tapi gate bilang NOT_RUN sampai marker ditambahkan manual).

---

## 5. `.BAT` / `.CMD` butuh `shell=True`

`subprocess.run(["nikto", ...])` gagal `FileNotFoundError` untuk shim `.BAT`:
```python
use_shell = len(cmd) == 1 and cmd[0].lower().endswith((".bat", ".cmd"))
subprocess.run(cmd, shell=use_shell, ...)
```

**Shim rusak = anggap TIDAK terpasang** (menunjuk binary yang tak ada):
```python
if pp.suffix.lower() in (".bat", ".cmd"):
    body = pp.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r'([A-Za-z]:\\[^\s"\']+\.(?:exe|py))', body):
        if not Path(m.group(1)).exists():
            return ""   # shim rusak -> bukan tool terpasang
```

---

## 6. RAM & proses zombi (host 6GB)

**Terukur:** 3× `dalfox.exe` = 780MB + 569MB + 157MB ≈ **1.5GB**. `kxss` gagal dengan
`0xC0000142` (Windows tak bisa start proses) saat RAM habis.
Run yang terputus (gateway restart / timeout) meninggalkan anak proses: orchestrator,
execute-variants, dalfox, dom-xss-test.

**Aturan:**
- Sebelum re-run, enumerasi proses by `CommandLine` + umur; bunuh duplikat **LEBIH TUA**
  untuk target yang sama.
- **JANGAN bunuh proses oleh nama generik.** Selalu cek `CommandLine` untuk domain target.
  Koreksi operator 2026-10-22: *"Jgn matikan quarterwise, itu lg proses d topik sebelah"* —
  itu engagement lain di topik lain. Bunuh hanya yang targetnya == engagement-mu.
- Batch watchdog harus `wait_running()` sebelum spawn orchestrator baru (cegah dobel).

---

## 7. Coverage JANGAN dipotong — pakai TIMEOUT

Koreksi operator: *"Jgn Batasin, nnti skillny truncated, kn kt atur smlm saling melengkapi"*.

Jangan turunkan `--max-variants` / `--limit` supaya cepat. Batasi **WAKTU**, pakai artefak parsial:
```python
try:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=2700)
except subprocess.TimeoutExpired:
    r = subprocess.CompletedProcess(cmd, 0, "", "timeout-parsial")  # lanjut, jangan gagal
```
Terukur: zkb.ch (539 subdomain) variants >45m; rce-verify >25m. Timeout dipasang
(variants 2700s, rce-verify 1500s) **tanpa memotong jumlah varian/kandidat**.

---

## 8. Negative audit harus DIBUKTIKAN

Koreksi operator: *"negative audit ttp harus berdasarkan hasil proses skill dan tools yg
berjalan. Kl tools da skill ny hanya djalankan secara tipis di permukaan aj, atau malah
hanya curl aja, ttp harus ditolak, wajib djalankan ulang, spy hasilnya beneran 0 temuan."*

`_gate_negative_audit()` — dipanggil di 0F **hanya kalau 0 temuan**:
- tool `EXECUTED >= 25` (default; env `NEG_AUDIT_MIN_EXECUTED`)
- `NOT_RUN == 0` (`NOT_FOUND` = tool tak terpasang = N/A sah, **tidak** memblokir)
- 4 fase inti ada: `business-logic-usage.json`, `reference-usage.json`,
  `impact-verification.json`, `dom-xss-usage.json`

Gagal → `RuntimeError`, wajib dijalankan ulang.

---

## 9. Gate N/A: bedakan penyerahan vs kondisi sah

`_BAD_REASON` jangan terlalu agresif. Status sah yang harus LOLOS:
- `documented skip: SKIP_NO_PARAM|STARTED_NO_TOKEN|NEEDS_REQUEST_TEMPLATE|SKIPPED_NO_SOLIDITY_TECH|NO_OUTPUT|FUZZ_ONLY|SKIP_WITH_REASON`
- `tool tidak terpasang` / `tool not installed`
- negative audit: `produced empty|no rows to record|nothing to draft|negative audit|0 validated findings|0 findings|no candidates|0 survivors`

---

## 10. depth_gate: hanya file LAPORAN

`depth_gate.py` awalnya memindai `findings.json` (kandidat **mentah** dari 0C-C7) →
memblokir **123 artefak** yang bahkan bukan kandidat. Sekarang hanya memindai file yang
akan DILAPORKAN: `passed-findings.json`, `survivors.json`, `validated-findings.json`.
Kandidat 0C → 0E yang menuntun ke L5, **bukan** input gate.

---

## 11. Batch runner / watchdog

- **rc dari pipe (`| tail`) = exit code `tail`, BUKAN orchestrator.** Ambil dari
  `subprocess.returncode` langsung.
- **Bash redirect gagal untuk path Windows** (`D:\...` → "No such file or directory").
  Pakai Python `open(out,'w')` + `stdout=fh`.
- **Fase terbaca dari `PHASE_LOG.md`** (`## PHASE 0X — …\nCOMPLETE`), bukan dari rc.
- Putaran terakhir + 0 temuan → **SKIP 0F**, tandai audited, lanjut target (koreksi operator).
- Verifikasi tiap run: hitung `EXECUTED` vs `NOT_RUN` dari `tools-usage.json`,
  bukan cuma rc. `rc=1` dengan `EXECUTED=138` ≠ kegagalan; `rc=0` dari pipe = bohong.
