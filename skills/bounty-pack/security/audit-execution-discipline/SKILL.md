---
name: audit-execution-discipline
author: RESEARCHER_NAME
description: "Rules enforcing execution over skill loading. PRIMARY: audit-pipeline-orchestrator.py (force-full-execution → variants → PoC exec → PoC variants → references-exec → 13-check disk gate at 0D with auto-rework loop → validate → review → report → post-0F coverage/checkpoint gate). Secondary: manual rules for edge cases. Tool mapping: sqlmap/dalfox/SSRFmap/etc, curl=LAST RESORT."
tags: [bug-bounty, security, execution, discipline, audit, tracker]
---

# Audit Execution Discipline Protocol

> **0D gate hard-blocked after 3 rework attempts?** Read `references/0d-gate-hardblock-recovery.md` FIRST — the five bookkeeping root causes (asset-coverage derive rejecting no-payload C5/C6b ledgers; finding_gate skipping REPORT-survivors.md on zero survivors; rework destroying manual fixes; **missing `status` + `evidence` vs `evidence_file` key mismatch**; **C5/C6b empty ledger where the `_no_poc` shortcut cannot apply — with the honest scan-and-record recipe**), the kill-the-rework-loop-before-patching rule, and the exact resume procedure. Measured 2026-10-17 and 2026-10-25.17.

**User identified repeated failure modes. This protocol ENFORCES execution over loading.**

> **Before launching the pipeline** (and before reporting any run as stalled/finished) read
`references/pipeline-ops-stalls-and-workspace.md` — §10 which files prove a job FINISHED (the run
directory's absence of report.md proves nothing), §11 the reaper that killed the WRONG pid (WMIC
column order), §12 a hung tool blocking 0C forever + the `toolguard.py unblock` lever, §13 stopping a
subset of stalled jobs and resuming only the selected ones (the cron watchdogs ALERT but never relaunch
the pipeline; disarm the arms; resume from the tracker's `current`, not the watcher's lagging `phase`),
§14 long-run durability, §15 stop-all / mass-wipe recovery (`templates/rerun-queue.sh`) — and run
`scripts/audit-orphan-reaper-verify.py` (safe dry-run reaper check, kills nothing):
> background-timeout sizing for a real 0A→0C run, what `STALL-WARN` actually means, the
> diagnose-the-blocking-child (never restart the parent) rule, evidence-lags-the-log, honouring
> `NO RESULT` instead of backfilling with curl, and the one-workspace-one-tree rule for the
> twin `data hermes` / `data\hermes` directories.

## ⛔ STANDING RULES — berlaku OTOMATIS, jangan tunggu diminta (operator, 2026-10-10)

Operator menegur dua kali dalam satu sesi: hasilnya dinilai **"0 temuan" padahal tak ada yang
benar-benar diuji**. Dua aturan ini menggantikan kebiasaan lama (quick scan surface → simpulkan).
Jangan tanya, jangan tunggu aba-aba, jalankan.

### A. Deep-dive itu PROAKTIF dan digerakkan PERAN HOST — bukan daftar URL hardcoded

```bash
python ~/AppData/Local/hermes/scripts/deep-endpoints.py <target_dir> <base_url>
```
Menetapkan **peran** host dari perilakunya sendiri (`signed-redirector` / `cdn-origin` / `app` /
`api` / `static-site` / `redirector`), lalu mengenumerasi endpoint **NYATA** dari robots, sitemap,
JS bundle, dan API publik milik situs itu. Menulis `host-role.json`, `urls-deep.txt`,
`deep-dive-plan.json` (daftar kelas uji **per peran**). Sudah terpasang di pipeline: `_deep_recon()`
di 0B melipat hasilnya ke `urls.txt`.

**Uji diskriminator — kalau semua URL yang kamu tembak balasannya SAMA, kamu bukan sedang menguji
aplikasi.** Terukur: recon menulis 6 path hardcoded dan **semuanya** kena 302 redirector yang sama,
jadi 15 varian payload + 15 vektor business-logic + 11 reference menembak ke dinding. Lapor
"0 temuan" dari situ = klaim yang tak mengukur apa pun. Berhenti, cari tahu host-nya APA dulu.

### B. TIGA verifikasi independen dari awal — untuk KANDIDAT **dan** KESIMPULAN

```bash
python ~/AppData/Local/hermes/scripts/reverify.py http  <dir> <name> <url>   # kandidat, 3 putaran
python ~/AppData/Local/hermes/scripts/reverify.py probe <dir> <name> -- <cmd> # artefak, 3 putaran
python ~/AppData/Local/hermes/scripts/reverify.py sweep <dir> <base_url>      # kesimpulan, 3 sapuan
```
* putaran **terpisah** (berjeda), tiap putaran dieksekusi independen, **bertimestamp, tersimpan di disk**
  — rantai bukti harus menunjukkan **tiga** observasi, bukan satu klaim diulang.
* kandidat yang tak bereproduksi identik = **UNSTABLE → TIDAK BOLEH dilaporkan.**
* kelas hanya boleh disebut BERSIH kalau **ketiga** sapuan setuju. `"0 temuan"` tanpa sapuan
  `CONSISTENT` adalah **klaim tak teruji**, bukan hasil.
* param volatil (`Signature`/`Expires`/`Key-Pair-Id`/`Policy`/`Token`) dinormalisasi dulu supaya
  perilaku yang stabil tetap cocok 3/3, sementara perubahan nyata tidak ikut hilang.

Terpasang di pipeline: `_reverify_candidates()` sebelum gate, `_reverify_conclusion()` sebelum
laporan. Ketiganya **non-fatal** — kegagalan verifikasi dicatat, tak pernah diabaikan diam-diam.

### C. Bukti destruktif DI LUAR BATAS — nyatakan, jangan lakukan

Kalau satu-satunya cara membuktikan hipotesis adalah merusak sesuatu yang nyata (cache-poison path
artefak hidup, DoS endpoint unduhan), **jangan lakukan**. Karakterisasi mekanismenya dengan probe
aman, tandai temuan sebagai *partially verified*, dan tuliskan eksperimen persis yang vendor bisa
jalankan. Terukur: cache-key path-only membuat cache-poisoning *masuk akal*, tapi probe
non-destruktif menunjukkan CDN tetap menyajikan objek baik yang ter-cache → vonis jujurnya
"mekanisme terkarakterisasi, poisoning TIDAK tereproduksi", bukan klaim DoS.

### D. Cara menjawab "sudah deep-dive belum?" — dengan DATA, bukan pembelaan

Saat operator menantang kedalaman (`"sudah dijalankan all skill, tools dan varian attack?"`),
jawab dengan angka dari disk: sebaran **status** `tools-usage.json` (EXECUTED vs RAN_WITH_ERROR vs
NOT_FOUND), jumlah **URL nyata** yang diuji, jumlah **request** benar-benar terkirim, dan berapa
kelas yang tersentuh. Kalau angkanya bilang dangkal, **katakan dangkal** lalu perbaiki. Jangan
membela pipeline yang memenuhi kontraknya sendiri tapi tak menyentuh permukaan serang sebenarnya.

### E. Hasil akhir = DRAFT GMAIL + PDF PoC dgn IMPACT TERBUKTI — atau TIDAK SAMA SEKALI

Operator, 2026-10-10: *"draft gmail yg lengkap poc pdf nya, dgn hasil yg benar2 ada impactnya, ada
demonstrated impact dalam poc nya ... bukan berhenti di teoritis, krn wajib dibuktikan"*.

```bash
python ~/AppData/Local/hermes/scripts/final-deliverable.py check <target_dir>   # kelayakan saja
python ~/AppData/Local/hermes/scripts/final-deliverable.py build <target_dir> --to <vendor>
```

**Uji kelayakan 4-syarat — SEMUA harus lulus, kalau tidak → EXCLUDED dan alasannya DITULIS:**
1. ada di `passed-findings.json` (lulus impact gate + triage 7-pertanyaan)
2. punya rekaman **demonstrated impact** — `probe` (aksi persisnya) **dan** `observed` (output mentah,
   tak diedit, ≥40 char)
3. rekaman itu **re-verified CONFIRMED 3×** (§B)
4. ada pernyataan impact yg menyebut apa yg **dibuktikan** output itu — `"impact: potential"` bukan impact

Keluaran per temuan (aturan keras: **1 temuan = 1 draft = 1 PDF**): `poc-pdfs/<slug>.pdf` (reportlab,
struktur skill: Judul · Ringkasan · Severity/CVSS · Langkah · **BUKTI KONSEP — IMPACT TERBUKTI**
(probe + output mentah + "apa yg dibuktikan") · Verifikasi 3× + artefak · Impact · Remediasi · Bukti
pendukung) dan `email-drafts/<slug>.eml` (RFC5322, PDF terlampir; `.eml` sengaja — tanpa OAuth, bisa
diperiksa byte-per-byte, bisa diimpor ke Gmail). **Staging bukan sending.**

**Dan saat tak ada yg layak, ia MENOLAK — itu fiturnya, bukan kegagalannya:**
```
[deliverable] 0 passed triage -> 0 REPORTABLE, 0 EXCLUDED
[deliverable] nothing reportable. A draft is NOT produced ...
```
Bikin draft utk temuan tanpa impact terbukti = **persis kegagalan phantom-evidence yg bikin laporan
ditutup tanpa investigasi**. Jangan mengarang temuan supaya ada yg bisa dikirim.

Terpasang di 0F pada **kedua** jalur (positif & negatif). → §14.

### F. Per-properti: ULANGI minimal 3× dan DIFF hasilnya (STABLE / VOLATILE / ABSENT)

Operator: *"kerjakan tiap properti satu per satu serta diulang masing2 minimal 3x utk memastikan tidak
ada sisi attack surface dan deepdive yg terlewatkan"*.

```bash
python ~/AppData/Local/hermes/scripts/property-sweep.py run   <property> --rounds 3
python ~/AppData/Local/hermes/scripts/property-sweep.py queue <queue_file> --rounds 3
```

Tiga putaran menjawab tiga pertanyaan berbeda — keluarannya **bukan** "sudah dijalankan 3×":
* **STABLE** — permukaan yg muncul di SEMUA putaran → aman untuk dinalar
* **VOLATILE** — cuma muncul di sebagian putaran → **selidiki sebelum dipercaya ATAU diabaikan**
* **ABSENT** — kelas yg diminta `deep-dive-plan.json` tapi TAK ADA putaran yg menghasilkannya
  → **daftar "terlewat" yg harus dikejar**

Properti hanya disebut **COMPLETE** kalau nol volatile **dan** nol absent. Tiap putaran membersihkan
state fase dulu supaya pipeline benar-benar jalan ulang, bukan resume.

### G. Akun & CAPTCHA: kerjakan SENDIRI, jangan kembali ke operator

Operator, 2026-10-10: *"kalau butuh akun, kamu buat aja sndiri, capcha jg kerjakan sndiri, intinya
semua otomasi"*. Saat 0C tersangkut gerbang auth:

* **Daftarkan akun uji sendiri** — jangan berhenti dan bertanya. Lihat skill
  `disposable-auth-identity` / `saas-test-account-provisioning` untuk mekanik identitas sekali-pakai.
* **Selesaikan CAPTCHA sendiri** secara otomatis (Camofox tersedia; reCAPTCHA v2 invisible lewat
  fingerprint bersih sering lolos tanpa interaksi, `userId` berbeda = jar terisolasi).
* **Jangan mengarang identitas** yang menyentuh entitas teregulasi (KYC/KYB) — itu memicu ban; pakai
  data asli/sandbox atau disposable di lingkungan uji.
* Target auth-gated bukan alasan menurunkan cakupan: RULE 34/36 (API terautentikasi menggantikan URL
  fuzzable) tetap berlaku, dengan skill & tool yg sama setelah sesi login hidup.

Kembali ke operator HANYA kalau butuh keputusan yg bukan milikmu (mis. otorisasi baru di luar scope,
atau belanja berbayar) — bukan untuk hal yg bisa kau otomasikan.

→ Detail lengkap + rasional: `references/runtime-execution-policy-2026-10-10.md` §13.

### H. §G AMANDEMEN — batas jujur dari \"kerjakan CAPTCHA sendiri\" (terukur 2026-10-12)

Semangat §G benar (jangan lempar kerjaan yang bisa diotomasi ke operator), tapi ada dua gerbang yang
**tidak bisa** dilewati otomasi. Kenali, buktikan sekali, lalu berhenti menambang:

1. **Attestation gate (Firebase AppCheck / Play Integrity / App Attest) — bukan targetmu, dan bukan
   lubang.** Mobile-first app sering punya jalur BEBAS-CAPTCHA yang ditutup attestation: proxy edge
   (Oathkeeper `jwt` authenticator, `trusted_issuers`+`jwks_urls`+`target_audience` di-pin) yang
   menyuntik `X-Appcheck-Jti` ke upstream, dan upstream hard-fail `401` tanpa header itu
   (`create/device-account`, `phone/code-appcheck`). Token-nya RS256 milik Google, audience = proyek
   vendor → **tak bisa dipalsukan, jangan di-grind.** Buktikan bentuknya sekali (kirim `Appcheck: undefined`
   / junk / tanpa header → `401`), catat, lanjut.
2. **CAPTCHA yang MENOLAK otomasi secara server-side** (`ERR:服务端forbidden` dari GeeTest v3) — ini
   BUKAN IP-ban. Terukur: identik di IP residensial langsung **dan** di IP WAF baru; solver sudah benar
   (IoU 0.80–0.83, trajektori eased+jitter). Rotasi IP/UA/profil = buang waktu operator + jatah OTP.
   Dua probe diagnostik cukup → lompat ke handoff manusia.
3. **Handoff manusia yang benar itu SATU gerakan + satu kode** — bukan \"suruh operator daftar sendiri\".
   Skrip Playwright (browser yang KAMU luncurkan, `headless=False`) mengisi semua field, submit, lalu
   menunggu operator menggeser slider di jendela itu, dan menulis status ke disk supaya kelihatan di mana
   berhenti; setelah itu skrip polling `evidence/otp.txt` dan mengirim OTP-nya sendiri. Sesi login tetap
   di profil yang kamu bisa baca.
   **Kembali ke operator juga sah saat gerbangnya deteksi-automasi yang tak bisa dilewati** — itu bukan
   melanggar §G, itu §G yang berbunyi \"kembali HANYA kalau butuh keputusan bukan milikmu\" diterapkan pada
   gerbang yang secara teknis bukan milikmu. Yang WAJIB: katakan apa yang kamu sudah coba + hasil
   terukurnya, dan minta **tepat satu** aksi (geser slider, kirim kode) — bukan job deskripsi.
   Detail permukaan auth + taktik: skill `saas-test-account-provisioning`
   → `references/attestation-gated-auth-surface.md`.

### I. `deep-audit-mode.py arm` mencetak perintah yang GAGAL kalau disalin mentah

`arm <url> --scope "<prosa deskripsi scope>"` menyimpan prosa, lalu MANDATORY FIRST ACTION-nya
mencetak `audit-pipeline-orchestrator.py <url> --scope "<prosa yang sama>"`. Orchestrator meneruskan
`--scope` ke `scope_checker.py --domain`, yang mengharapkan **daftar domain**, bukan kalimat →
`❌ SCOPE GATE BLOCKED: ... BUKAN dalam scope (<prosa>)`, nol request terkirim. Terukur 2026-10-12.
Pilih satu: **(a) buang `--scope`** (tanpa profile = allow-all, sesuai RULE 30 — paling sering benar),
atau **(b) isi daftar domain** (`--scope "target.com,target-corp.com"`). Jangan tempel prosa.

### J. RELAUNCH/RESUME: pakai `--scope` yang MEMUAT host aktual, dan jangan percaya notifikasi launch lama

Dua kegagalan berurutan saat me-relaunch run yang mati (terukur 2026-10-13, `www.gkb.ch`):

1. **Resume dengan `--scope` apex-only langsung HARD-BLOCK.** `--target https://www.gkb.ch
   --scope "gkb.ch"` → `❌ SCOPE GATE BLOCKED: www.gkb.ch BUKAN dalam scope (gkb.ch)`, nol request
   terkirim. `scope_checker.py --domain` membandingkan **host aktual**, bukan apex. Saat me-relaunch
   target yang sudah ada, salin daftar scope dari run sebelumnya **plus** host itu sendiri:
   `--scope "www.gkb.ch,gkb.ch,*.gkb.ch"` → `✅ SCOPE GATE PASSED (URL)`. Baca scope dari
   `run-meta.json` / tracker run lama dulu; jangan mengarang dari domain apex.
2. **Notifikasi `Background process ... exited` menunjuk LAUNCH YANG ITU, bukan state sekarang.**
   Launch pertama gagal (scope gate) dan notifikasinya baru tiba beberapa menit kemudian —
   sesudah launch kedua sukses dan jalan. Kalau ditelan mentah, laporan jadi "prosesnya mati"
   padahal ada 11 proses hidup. Sebelum bicara apa pun: **cek proses hidup + mtime artefak
   terbaru**, lalu pastikan `session_id` yang dibicarakan memang launch terakhir. Launch baru =
   `session_id` baru; yang lama sudah mati sejak awal dan bukan berita.

Bukti yang dipakai untuk memastikan launch kedua benar-benar jalan (semua bisa dijalankan ulang):
`tail -N <log>` menunjukkan `✅ SCOPE GATE PASSED` → `STEP 1: Running FORCE FULL EXECUTION` →
`STEP 1.4a: Executing PAYLOAD VARIANTS`, plus `find <dir> -newermt "-6 minutes"` yang terus
menambah evidence, plus `psutil` menghitung proses `audit-pipeline-orchestrator.py` yang memuat
nama target.

*Juga:* reaper orphan orchestrator memiliki **daftar nama yang bisa basi** — `amass.exe` duduk
197 MB dengan parent MATI selama berjam-jam karena `amass`/`httpx`/`whatweb`/`naabu`/`nikto`/
`katana` tidak ada di tuple-nya. Detail + tuple yang benar: skill `hermes-ops`.

### K. Dua gerakan kejujuran untuk temuan API: differential batas-auth, dan "kode ini TER-DEPLOY?"

Untuk temuan pada API/service (GraphQL, REST, apa pun yang punya sederajat resource):

1. **Differential batas-auth** — kirim TANPA kredensial ke (a) field target, (b) **sibling** di tipe
   & sesi yang sama yang MEMANG menuntut auth, (c) field tak-ada pada dokumen yang sama. Hanya
   `(a) 200 + data` membuktikan **eksekusi**; `(b) Unauthorized` yang membuktikan ada gerbang auth
   yang **sengaja tak dipasang** di target; `(c) GRAPHQL_VALIDATION_FAILED` mematikan hipotesis
   "cache/catch-all yang membalas 200 ke semua". Tambah 12 putaran untuk membuktikan **tak ada
   throttle**. Satu probe sendirian = nol bukti.
2. **Kode TER-DEPLOY** — grep **konstanta UNIK** jalur kode itu di bundle produksi, bukan token
   generik. `Math.random` ada di setiap polyfill (4 hit palsu); alphabet `jkmnpqrtuvwxyz` dari
   `generateCode()` → 0 hit di 13 chunk. **Absennya konstanta BUKAN temuan** — katakan bundle tidak
   mengonfirmasi, dan temuan berdiri di analisis source + perilaku live saja. Konstanta SEBELAH
   (`createWithdrawLink` di chunk lain) hanya membuktikan fiturnya ADA, bukan cara secret dibuat.

Batas yang wajib ditulis apa adanya: `null` untuk nilai yang ditebak = **reachability**, BUKAN
pembacaan objek milik orang lain. Tulis *"lookup dapat dijangkau tanpa sesi dan tanpa rate limit"*,
JANGAN *"akses tanpa autentikasi ke withdraw link"*. Satu kata overclaim mengubah temuan yang
bertahan menjadi retraksi. Resep lengkap + tabel mentah: `references/auth-boundary-and-deployed-code-verification.md`.

### L. STATUS CODE ≠ EVIDENCE — 4 lookalikes yang WAJIB dibunuh sebelum mengklaim "data exposure"

Operator, 2026-10-13: *"jgn kasih 500-403-400-200, tp kasih sy bukti kalau itu ad impact kerasnya, spt data leak, idor, bola, ato rce, dsb nya, jadi harus buktikan ada sesuatu yg didapat dari temuan tsb dan berimpact negatif"*.

Sebuah respons baru disebut BUKTI kalau membawa sesuatu yang penyerang **belum** punya. Empat bentuk ini tampak seperti temuan dan bukan — semuanya terukur di satu sesi:

1. **SPA catch-all.** Setiap path menjawab `200` dengan shell yang **byte-identik**: `bcap.apnic.foundation` 606 B untuk `/`, `/api`, `/actuator/health`, `/v3/api-docs`; `app-qawolf.coderabbit.ai` 14 654 B untuk `/api/subscriptions`, `/version`, `/healthz`. Diskriminator: tembak 2–3 path yang **tak berhubungan** lalu bandingkan **panjang byte**; identik ⇒ app-shell, bukan API. Route asli hanya ada di bundle JS — berhenti menebak path.
2. **Regex kata kunci di atas HTML bukan "hard data".** Run yang sama mencetak `<<< DATA` untuk shell itu karena `"(id|email|name|token)":` cocok dengan **komentar di dalam JS**. Syarat: `json.loads()` sukses **dan** kontainernya tak-trivial (list len > 1 / ada key record). Jangan pernah regex di atas body HTML.
3. **Bucket pihak-ketiga yang namanya sama dengan target** — resep lengkap di reference bawah. Ringkas: baca **satu objek NON-PII** dari bucket dan sebutkan **produk/domain siapa** yang muncul di dalamnya; cek **namespace** XML (GCS `doc.s3.amazonaws.com` vs AWS `s3.amazonaws.com/doc`); nama bucket bisa ada di **dua cloud sekaligus** (yang satu 200, yang lain 404 `NoSuchBucket`). Nama yang mirip ≠ kepemilikan. Kalau isi objek membuktikan pemilik lain → **DROP**, jangan kirim ke VDP target.
4. **Pesan error generik yang dibaca sebagai oracle.** `{"message":"Email does not exist"}` tampak seperti user-enumeration; 15 email (2 jelas palsu + 13 kandidat nyata termasuk `csirt@`/`helpdesk@`/`admin@`) balas **1 body unik / 1 panjang / 1 status = NO ORACLE** — itu anti-enumeration yang BEKERJA. **Oracle enumerasi tak bisa dibuktikan tanpa kontrol POSITIF** (akun yang kamu pastikan ada). Tanpa kontrol → **retraksi**, jangan lapor. Pola retraksi jujurnya: sebut hipotesisnya, sebut angka yang membantahnya, tarik.

Detail + resep repro: `references/data-exposure-lookalikes-and-bucket-ownership.md` (termasuk **S3 key path JANGAN di-URL-encode** — `/` jadi `%2F` mengubah 200 menjadi 404 dan hampir membuat saya menyimpulkan "objek tak terjangkau"; **reachability objek ber-nama KYC dibuktikan dengan `HEAD` + `Range: bytes=0-3` magic bytes tanpa mengunduh dokumennya**; **deteksi populasi placeholder** via hash duplikat + nama file stok; dan jebakan MSYS `naabu -list <(sed …)` ⇒ `[FTL] open /dev/fd/63` → tulis file nyata, jangan process-substitution).

## ➕ RULES BODY — dipindah ke references/rules-body/ (SKILL.md <100k)

SKILL.md tidak boleh >100k karakter. Isi aturan lengkap DIPINDAH (bukan dihapus) ke berkas
di bawah. MUAT berkas yg relevan SEBELUM mengerjakan fase itu — daftar di bawah memuat
pemicu supaya kamu tahu kapan harus membuka.

| berkas | ukuran | pemicu (muat kalau kamu sedang…) |
|---|---|---|
| `references/rules-body/body-01.md` | 29,376 char | menyusun/menjalankan pipeline 0A-0F, orkestrasi, urutan gerbang |
| `references/rules-body/body-02.md` | 29,723 char | mengedit banyak berkas, sweep 40-file, jebakan silent-failure |
| `references/rules-body/body-03.md` | 25,286 char | menilai hasil gerbang, kandidat, atau menyimpulkan temuan |
| `references/rules-body/body-04.md` | 26,691 char | melaporkan (report/PDF/email), format deliverable |
| `references/rules-body/body-05.md` | 19,136 char | aturan rinci lanjutan |

### references/rules-body/body-01.md
- ## ⚡ GLOBAL MANDATE (operator, 2026-10-07) — tiap target, ta
- ## ⛔ RULE DEEP-AUDIT MODE (operator, 2026-10-10) — OUTER GAT
- ### WAJIB: setiap fase (KHUSUS 0C EXPLOIT) meninjau ULANG & 
- ### Siklus temuan (WAJIB)
- ## PHASE PIPELINE (0A→0F)
- ## ⛔ RULE 0c — Prove every check can FAIL, or it is decorati
- ### ⛔ Corollary 2 — prove the FAILURE happened before you ex
- ## CORE RULES (inline — enforcement-critical)
- ## ⛔ RULE 0: RULES DON'T FORCE ANYTHING — SCRIPTS DO
- ## ⛔ RULE 0: Honest Reporting — NO Overclaiming
- ## ⛔ RULE 0C: Impact-First — Not Volume
- ## ⛔ RULE 0B: Don't Skip, Don't Delete — Complete Missing It
- ## ⛔ RULE 1: Exploit-First Mindset
- ## ⛔ RULE 2: Loading ≠ Executing
- ## ⛔ RULE 30: SCOPE — NEVER Ask the User (Auto-Detect, Else 
- ### ⛔ RULE 30b: a policy that bans automated tools does NOT 
- ## ⛔ RULE 31: Patch-Verify Loop — Never Trust a Patch "Succe
- ### RULE 31b — two silent-failure traps that bit 40-file edi
- ## ⛔ RULE 3: Timeout = Retry, Not Skip — **SUPERSEDED 2026-1
- ## ⛔ RULE 4: Reload After Compression
- ## ⛔ RULE 5: Verification Log Before COMPLETE
- ## ⛔ RULE 7: Self-Check Every 5 Tool Calls
- ## ⛔ RULE 8: Track Every Ref File Execution
- ## ⛔ RULE 9: Proven ≠ Theoretical — NEVER Overclaim
- ## ⛔ RULE 10: Minimum Severity Threshold for Reporting
- ## ⛔ RULE 19: Minimum 3 Bypass Attempts Before "Blocked" Cla

### references/rules-body/body-02.md
- ## ⛔ MECHANICAL ENFORCEMENT
- ### Orchestrator pipeline (single-brain — enforced, not advi
- ### ⛔ ERROR = REWORK, NEVER SKIP (user rule: "jgn dskip, bal
- ### PoC payload classification (do not misread as lazy skipp
- ### ⛔ Tracker Limitation — log ≠ refs/tools
- ## ⛔ RULE 25: References MUST Be USED — Not Just Loaded (C6)
- ## ⛔ RULE 24: Candidate Review SOP — Temuan = CANDIDATE, 3x 
- ## ⛔ RULE 39: The Gate Must Be FAIL-CLOSED — a fail-open gat
- ## ⛔ RULE 39b: A gate must never score its OWN echo — unwrap
- ## ⛔ RULE 41: A gate must not block on a CORRECT outcome — a
- ## ⛔ RULE 40: Target the CANONICAL host — a bare-host 301 tu
- ## ⛔ RULE 42: A terse continuation names no target — reconst
- ## Config Requirements
- ### Track web3 WAJIB memuat `defi-exploit-forensics-in-pipel
- ### Aturan yang berlaku ke SETIAP track (dari run web3 nyata

### references/rules-body/body-03.md
- ### ⛔ Checklish aset WAJIB track-aware — kalau tidak, target
- ### ⛔ Tool yang exit≠0 karena MENEMUKAN isu bukan "error"
- ## ➕ Additive companion — `autonomous-exploration` (optional
- ## ➕ Runtime execution policy (2026-10-10)
- ## ➕ The "failure that pretends to be a result" family — IND
- ## ⚡ GLOBAL MANDATE (operator, 2026-10-07) — tiap target, ta
- ## ⛔ RULE DEEP-AUDIT MODE (operator, 2026-10-10) — OUTER GAT
- ### WAJIB: setiap fase (KHUSUS 0C EXPLOIT) meninjau ULANG & 
- ### Siklus temuan (WAJIB)
- ## PHASE PIPELINE (0A→0F)
- ## ⛔ RULE 0c — Prove every check can FAIL, or it is decorati
- ### ⛔ Corollary 2 — prove the FAILURE happened before you ex
- ## CORE RULES (inline — enforcement-critical)
- ## ⛔ RULE 0: RULES DON'T FORCE ANYTHING — SCRIPTS DO
- ## ⛔ RULE 0: Honest Reporting — NO Overclaiming
- ## ⛔ RULE 0C: Impact-First — Not Volume
- ## ⛔ RULE 0B: Don't Skip, Don't Delete — Complete Missing It
- ## ⛔ RULE 1: Exploit-First Mindset
- ## ⛔ RULE 2: Loading ≠ Executing
- ## ⛔ RULE 30: SCOPE — NEVER Ask the User (Auto-Detect, Else 
- ### ⛔ RULE 30b: a policy that bans automated tools does NOT 
- ## ⛔ RULE 31: Patch-Verify Loop — Never Trust a Patch "Succe

### references/rules-body/body-04.md
- ### RULE 31b — two silent-failure traps that bit 40-file edi
- ## ⛔ RULE 3: Timeout = Retry, Not Skip — **SUPERSEDED 2026-1
- ## ⛔ RULE 4: Reload After Compression
- ## ⛔ RULE 5: Verification Log Before COMPLETE
- ## ⛔ RULE 7: Self-Check Every 5 Tool Calls
- ## ⛔ RULE 8: Track Every Ref File Execution
- ## ⛔ RULE 9: Proven ≠ Theoretical — NEVER Overclaim
- ## ⛔ RULE 10: Minimum Severity Threshold for Reporting
- ## ⛔ RULE 19: Minimum 3 Bypass Attempts Before "Blocked" Cla
- ## ⛔ MECHANICAL ENFORCEMENT
- ### Orchestrator pipeline (single-brain — enforced, not advi
- ### ⛔ ERROR = REWORK, NEVER SKIP (user rule: "jgn dskip, bal
- ### PoC payload classification (do not misread as lazy skipp
- ### ⛔ Tracker Limitation — log ≠ refs/tools
- ## ⛔ RULE 25: References MUST Be USED — Not Just Loaded (C6)
- ## ⛔ RULE 24: Candidate Review SOP — Temuan = CANDIDATE, 3x 
- ## ⛔ RULE 39: The Gate Must Be FAIL-CLOSED — a fail-open gat

### references/rules-body/body-05.md
- ## ⛔ RULE 39b: A gate must never score its OWN echo — unwrap
- ## ⛔ RULE 41: A gate must not block on a CORRECT outcome — a
- ## ⛔ RULE 40: Target the CANONICAL host — a bare-host 301 tu
- ## ⛔ RULE 42: A terse continuation names no target — reconst
- ## Config Requirements
- ### Track web3 WAJIB memuat `defi-exploit-forensics-in-pipel
- ### Aturan yang berlaku ke SETIAP track (dari run web3 nyata
- ### ⛔ Checklish aset WAJIB track-aware — kalau tidak, target
- ### ⛔ Tool yang exit≠0 karena MENEMUKAN isu bukan "error"
- ## ➕ Additive companion — `autonomous-exploration` (optional
- ## ➕ Runtime execution policy (2026-10-10)
- ## ➕ The "failure that pretends to be a result" family — IND
- ## ➕ STANDING: deep-dive proaktif + verifikasi 3x (2026-10-1

## ⛔ REFERENCE DOKUMEN (`references/*.md`) — baca sesuai konteks


Aturan yang tidak masuk `references/rules/` tinggal di sini. **Baca yang relevan; jangan dilewatkan.**

| kapan dibaca | file |
|---|---|
| **WAJIB sebelum menutup laporan apa pun** — kebijakan runtime penuh: run tanpa batas, stall = WARN bukan kill (`toolguard.py`), gagal → auto-perbaiki → **jalankan ulang** (`autofix.py`), **DILARANG jatuh ke curl**, GENTLE saat vendor larang scanner, kadens distilasi, keluarga **"failure that pretends to be a result"** (§8 budget-netral, §9 AV quarantine, §10 ledger menuntut ISI, §11 field-name salah, §12 daftar guard), dan **§13 STANDING: deep-dive proaktif + verifikasi 3x**, **§14 STANDARD DELIVERABLE: draft Gmail + PDF PoC ber-gate impact-terbukti (`final-deliverable.py`), 3x-per-properti (`property-sweep.py`)** | `references/runtime-execution-policy-2026-10-10.md` |
| **menyatakan `FALSIFIED` / "aman" / "tidak vulnerable" / menyerah pada kandidat** — komplemen RULE 18, bukan duplikat. RULE 18 mengatur sisi POSITIF (jangan bilang *informational* terlalu cepat); gerbang ini mengatur sisi NEGATIF (jangan menyimpulkan MATI tanpa bukti). Beban bukti setara dua sisi · default ragu = `INCONCLUSIVE` (bukan FALSIFIED) · FALSIFIED wajib lolos 7 gerbang: ladder tuntas · ≥3 variasi · **steelman ditulis DULU** · bukti mitigasi dari EKSEKUSI nyata + ≥1 upaya bypass · evidence tier `Observed` (yang `Prepared` → INCONCLUSIVE) · klasifikasi root-cause gagal-reproduce (a) vuln memang tak ada = boleh FALSIFIED, (b) tooling/resource = WAJIB INCONCLUSIVE, (c) env beda = WAJIB INCONCLUSIVE · cross-framing dua arah. Plus gate per-TAHAP Recon→ThreatModel→Hipotesis→Validasi dgn `RECON GAP` dibawa eksplisit. Format verdict per-verdict wajib + jeda sanity-check operator sebelum CONFIRMED naik ke laporan. | `references/anti-premature-falsification-gates.md` |
| **mau tahu host-nya sebenarnya APA sebelum menembakkan payload** — peran host + enumerasi endpoint nyata (`deep-endpoints.py`): `signed-redirector`/`cdn-origin`/`app`/`api`/`static-site`/`redirector`, plus kelas uji **per peran** | `references/runtime-execution-policy-2026-10-10.md` §13.1 |
| **sebelum menyimpulkan temuan ATAU "0 temuan"** — 3 putaran independen dari awal (`reverify.py` sweep/http/probe); kandidat tak bereproduksi = UNSTABLE, tak boleh dilaporkan | `references/runtime-execution-policy-2026-10-10.md` §13.2 |
| **kamu baru mengedit kode pipeline** / gejala "tool error" untuk SEMUA tool, atau sebuah fix "tidak berefek" — `ast.parse` lewat tapi runtime tetap salah | `references/silent-failure-static-guards.md` — 3 guard di `hermes-health-audit.py` (`import_fail`, `unbound_name_fail`, `budget_arith_fail`) + cara menulis scope-walk closure-aware (versi naif = **37 false positive**, guard berisik lebih buruk daripada tidak ada) + tabel gejala→diskriminator 1 baris. **Praktik yang menangkap ketiganya: jalankan sekali di target-dir nyata — bukan `ast.parse`, bukan `import`** |
| **0A/0B selalu** — phase model, fresh-run, reset tracker | `references/audit-pipeline-phases-and-fresh-run.md` |
| **0C semua track** — checklist aset per fase (WAJIB) | `references/phase-execution-mandate.md` |
| **0E/0F** — siklus temuan (find→3x→candidate→re-validasi) | `references/candidate-lifecycle.md` |
| **0B/0C/0E/0F — track web3/Solidity** — tx-hash exploit forensics | `references/defi-exploit-forensics-in-pipeline.md` |
| **0C track web3 — menjalankan slither/aderyn/myth/echidna/medusa** pada source hasil recovery | skill **`onchain-source-recovery`** → bagian "Making a recovered source ACTUALLY analysable" (5 jebakan: file salah terpilih, remappings, `src="."` stack overflow, `out/build-info` wajib, `offline=true` memblokir solc) |
| **re-run setelah memperbaiki pipeline sendiri** | `references/multi-session-resume-2026-09-26.md` → "Rerunning after you FIX a bug" (dua state store wajib dibersihkan) |
| **0C track web3** — triage label severity tool statis EVM | `references/evm-and-recon-triage-2026-10-01.md` |
| **0D GATE** — fail-open finding gate | `references/finding-gate-fail-open-2026-10-07.md` |
| **0E/0F** — mechanical 7-question triage gate (`triage_gate.py`, E5) + a gate scoring its own echo (unwrap/scaffold scrub) + condition→skill router | `references/mechanical-triage-gate-and-self-echo.md` |
| **menulis ledger 0C/0D dengan tangan** (skema list vs dict, `evidence_file` path absolut & ≥100 B, vocabulary status yang diterima CHECK 2b, urutan `asset-coverage --init`/`--derive`, N/A-BLOCKED saat policy melarang scanner, **§7 gate baca DIR ENGAGEMENT tapi orchestrator TULIS ke `poc-plans/` → sync dulu + `asset-coverage` di-derive ulang dari `tools-usage.json` jadi edit coverage tak nyangkut**, **§8 gate yang diperbaiki tangan berhenti di artefak 0E/0F → RESUME orchestrator**, **§9 lokasi asli `asset-coverage.py` (di dalam skill, bukan `~/…/scripts/`) + script langkah 0C TIDAK punya `--help` (memanggilnya = MENJALANKAN run) + `execute-references.py` mengabaikan argumen target (pakai index cache) + `--mark` yang kena 0 entri karena beda HURUF BESAR/KECIL + `refs_web3` sah di-N/A saat tak ada korpus penyerang yang bisa ditembakkan + urutan perbaikan yang terbukti**) | `references/gate-artefact-schema-and-status-contract.md` |
| **0D GATE gagal berulang** — REWORK spiral, log ditulis sekali di akhir | `references/gate-rework-and-log-persistence.md` |
| **gate FAIL lalu rework menjalankan step yang SALAH** (mis. `poc-variant-usage.json missing` tapi log `re-running execute-variants.py` — substring dispatcher) · **C5/C6b tak pernah kelar** (sstimap/dalfox diulang per-repo, `timeout_cap=None`) · **scope gate tolak `www.` utk `--scope <bare-domain>`** · kandidat `impact-verify confirmed=` yang ternyata FP (SSTI control-test / open-redirect relative-Location / DOM-XSS marker-title) | `references/pipeline-rework-and-candidate-fp-fixes.md` |
| **0D HARD BLOCK 3× dengan pesan IDENTIK, REWORK tak menolong** — gate baca DIR ENGAGEMENT tapi orchestrator TULIS ke `poc-plans/` (fix = `AUDIT_ENGAGEMENT_DIR`) · **CHECK 2b memblokir pada ENTRI `FAILED`/`FAILED_USAGE`** (nuclei exit −1 = OOM-kill, linkfinder 429 → terbaca "wrong CLI") → resep jujur: re-run tool nyata (host lain yang in-scope kalau yang utama 429) → evidence berheader `# TOOL EVIDENCE:` (**`nuclei -o` menulis 0 byte saat 0 temuan** → gate butuh ≥1 byte) → koreksi entri `EXECUTED`+bytes (backup `.bak_gatefix_*`) → `asset-coverage.py --derive` → `verify-tool-usage.py` 13/13 → resume; **+ konvensi argumen 3 script yang berbeda** (`verify-tool-usage.py` ABS dir · `audit-checkpoint.py` NAMA RELATIF · `asset-coverage.py` ada di `scripts/` SKILL, bukan `~/…/scripts/`); **+ jangan telan "impact survivor" pipeline mentah** (sqlmap "not injectable" & 19 baris `[429]` dua-duanya tampak "notable") | `references/gate-toolchain-honesty-fixes-2026-10-12.md` §5 |
| **0D gagal 2× dengan pesan IDENTIK lalu nyaris HARD BLOCK** · **ledger menolak bukti tulisan-tangan** (`timestamp … predates the run`) · **gate HIJAU tapi sebagian tool tak pernah jalan** (`FUZZ_ONLY`/`SKIP_WITH_REASON`) · operator minta *"semua tool dipanggil, jgn dilewati"* | `references/gate-rederive-tz-and-fuzz-only-2026-10-12.md` — 3 cacat terukur: (1) `run_step5_tools()` re-run tool TAPI tak pernah `--derive` ulang → gate baca ledger BASI, pesan sama tiap attempt, HARD BLOCK tanpa 0E/0F (fix = derive setelah rework; bukti: 1× `--derive` → `49 ok / 0 fail`); (2) `_ts()` menormalkan stamp tz-aware ke **UTC** padahal `run-meta.started_at` **naive local** → bukti manual 02:49+07 (19:49Z) dianggap "mendahului" run 23:41 → `USED→NOT_RUN` (fix di `_ts` = local-naive **dan** tulis `# TS:` TANPA offset — `date -Iseconds` justru menambahkannya); (3) `force-full-execution` menulis `FUZZ_ONLY` (`no verified CLI invocation`) yang `--derive` petakan ke **N/A "documented skip"** → CHECK 12 LOLOS walau ~11 tool manifest belum pernah fire (terukur: ssrfmap/graphqlmap/jwt_tool/sstimap/smuggler/sslscan/subjack/linkfinder/secretfinder/cloud_enum/kube-hunter). **+ prosedur gap-close** (jalankan tool nyata → evidence `# TOOL EVIDENCE:` → update baris ledger → `--derive` → re-verify) **+ cara membuat tool resolvable** (`shutil.which` butuh ekstensi → wrapper shebang DAN `.cmd`; PATH `execute_code` ≠ PATH pipeline → cek final dari `terminal`; wordlist ffuf diprobe di `0B-recon/common.txt`; `byp4xx` di-`go build`; `jwt_tool` butuh `~/.jwt_tool/jwtconf.ini` tulis-tangan + token sebagai ARG STRING + `-rh` agar benar-benar terkirim) **+ sync dir: copy PARSIAL → 3 kegagalan guard yang khas** **+ `[STALL-WARN]` biasanya alarm palsu** (phase field hanya maju per-step; log di-block-buffer oleh `tee`; bukti = mtime evidence; MSYS PID ≠ WINPID → `ps -W` kolom 4) **+ resep SOAP/WSDL legacy** (`.wsdl` shell → `wsdl:import …?wsdl=<name>.wsdl`; buktikan origin memproses via `500 soap:Fault` sebelum uji; `403 Cloudflare` = vector DIBLOKIR EDGE, bukan "aman"; XInclude tanpa DTD = bypass WAF yang dicoba lebih dulu) |
| **tool menyerang HOST YANG SALAH** (proses dalfox/nuclei command line menunjuk domain pihak ketiga) — 3 cacat berantai, DIPERBAIKI 2026-10-10: wordlist path tanpa leading slash (`host.env` → DNS gagal, 46/100 probe hangus), `_param_url` pakai tes substring (`host in u.split("/")[2]`) sehingga `host///host-lain` LOLOS, crawl recon menambah URL absolut pihak ketiga tanpa filter scope. Bandingkan dgn **ROOT DOMAIN**, bukan host penuh (kalau tidak subdomain in-scope ikut tertolak); `urlparse` SENDIRI tak cukup — host kedua hidup di path, perlu guard `"//" in rest`. | `references/url-scope-bugfix-2026-10-10.md` |
| **6 kelas lain: deteksi ≠ bukti** — `http_probe` menandai probe "interesting" hanya dari `status not in (404,403,401) and size>0`; itu **tak bisa** membedakan halaman yg menggemakan kata `passwd` dari LFI yg BENAR-BENAR membaca file, 200 utk `{{7*7}}` dari SSTI yg mengevaluasi jadi `49`, respons apa pun dari SSRF yg memanggil canary, atau halaman lambat dari blind-SQLi yg benar-benar `sleep`. Stage **0C-C2d `impact-verify`** membuktikan 6 kelas: SSRF (callback OOB), LFI (signature isi file), SSTI (evaluasi aritmetika 49 **dan** 56 — dua jawaban benar berbeda), XXE (callback entity), open-redirect (host di `Location:`), blind-SQLi (differential waktu). **Dua bug nyata ketemu lewat testing:** (1) open-redirect terbaca "tidak ada" karena fetcher mengikuti redirect → off-site gagal → `status=None`, fix = `http_get_noredirect`; (2) SSRF palsu muncul karena callback itu buatan KLIEN KITA sendiri yg mengikuti redirect → probe SSRF sekarang wajib `noredirect`, 3xx dicatat terpisah sebagai `redirect_only`. Jebakan: test-target yg fetch URL ke dirinya sendiri WAJIB `ThreadingHTTPServer` (single-thread = deadlock, terukur `fetch failed: TimeoutError`); XXE butuh POST. | `references/impact-verification-stage-2026-10-10.md` |
| **RCE / command-injection — "kandidat" vs "terbukti jalan"** — pipeline bisa **DETEKSI** (nuclei tag `cmd-injection,rce`, 104 payload cmdi) tapi tak pernah **MEMBUKTIKAN eksekusi**; dan mapping 0C `"cmdi": ["gobuster","ffuf"]` SALAH TOTAL — keduanya directory brute-forcer, fuzz PATH (`/FUZZ`), tak bisa inject command ke parameter (terukur: `ffuf-cmdi.txt` = bruteforce nama file berlabel cmdi → hasil 0 by construction). Stage **0C-C2c `rce-verify`** membuktikan eksekusi via **3 channel independen** + kontrol inert: (1) differential waktu vs baseline benign — floor `0.6 × sleep`, BUKAN `sleep × ratio` (versi salah bikin hit 3.08s terbaca False), (2) callback OOB canary lokal (`curl`/`certutil`/`iwr`), (3) signature output perintah (`uid=...gid=`, `[fonts]`, `Windows IP Configuration`). **WAJIB payload Unix DAN Windows** (`;` vs `&`/`|`; `ping -n N` pengganti `sleep`) — di host Windows `; sleep 3` = 0 delay sedangkan `| sleep 3` = 3.16s. Verdict: `CONFIRMED` (OOB/output) / `PARTIAL_TIME_ONLY` (blind, ≥2 time) / `NOT_CONFIRMED`; kontrol kotor = warning, bukan lolos. | `references/rce-verification-stage-2026-10-10.md` |
| **XSS pada SPA / hasil "bersih" dari scanner server-side** — `plugins.jetbrains.com` punya **0 dari 123 URL ber-parameter**, jadi dalfox muter 53 menit tanpa ada yg bisa di-inject; hasil bersihnya **false negative by construction**, bukan bukti aman. Stage **0C-C2b `dom-xss`** (`dom-xss-test.py`, Playwright/Chromium) inject via query+hash+path, pasang sink hook SEBELUM navigasi, dan hanya mencatat HIT kalau payload **DITERJEMAHKAN** (MutationObserver lihat node baru / `window.onerror` / canary `127.0.0.1` benar-benar di-fetch). `payload-present-in-dom` = konteks, BUKAN hit. Wajib buktikan **dua arah**: benign → 0 hit, app rentan → ada hit. Jebakan: `page.evaluate` yg throw BUKAN bukti XSS (versi pertama menghitungnya sbg hit → 10 FP); Camofox path-mismatch → pakai Playwright. **MELEMAHKAN 2026-10-12 (terukur, 2 run): hook `mark()` menyala untuk SETIAP node IMG/SCRIPT/SVG baru — setiap halaman yang render via JS menghasilkannya, jadi `interpreted:true` = FALSE POSITIVE yang dijamin (148 "hit" di spectrocoin.com, 47 di antaranya halaman asli SpectroCoin yg tetap bukan XSS; sisanya `title:"Just a moment..."` = halaman challenge Cloudflare). Diskriminator 2 baris sebelum melaporkan apa pun: buang `title == "Just a moment..."`, dan buang yang `reason`-nya hanya `dom-sink:mutated-node:*`; hit sah BUTUH canary benar-benar di-fetch / `window.onerror` / DOM berubah KARENA payload. Perlakukan `dom-xss-findings.json` sebagai triage input, bukan temuan.** | `references/dom-xss-stage-2026-10-10.md` |
| **Rekon tampak "sukses" tapi endpoint hilang** — `deep-recon: urls.txt 27 -> 123` gagal senyap waktu root-domain dihitung dgn one-liner salah (menghasilkan tuple → `'list' object has no attribute 'split'`), sehingga **104 endpoint nyata tak pernah masuk cakupan** dan seluruh 0C menembak 27 URL saja. Hitung root domain dgn langkah eksplisit + `isinstance(str)` check; jalankan **pre-restart checker** (`pre_restart_check.py`) yg menguji SEMUA lapis fix sebelum restart, bukan sesudah. | `references/url-scope-bugfix-2026-10-10.md` |
| **SEBELUM restart pipeline panjang** — operator: *"kenapa banyak bug muncul, gkberes2 auditnya"*. Anti-pola yg bikin itu: **temukan bug → fix → restart 4 jam → temukan bug berikutnya**. Terukur: **5 restart, 10 bug, ~20 jam**, tetap tak sampai 0F. Semua fix BENAR; METODENYA salah — run penuh adalah detektor bug termahal yg ada, dan pipeline 7-lapis punya permukaan besar utk kelas cacat ini. Jawabannya: **`pipeline-contract-audit.py`** (5 detik, exit 1 kalau ada HIGH) = prasyarat restart, bukan pelengkap sesudahnya. **10 bug itu SATU kelas**: *nilai/aturan/klaim dideklarasikan di satu lapis, lalu diabaikan/dibuang/ditinggalkan buktinya di lapis berikutnya, tanpa ada yg mengecek jarak.* Hanya 2 dari 10 bug "logic"; 8 adalah **pelanggaran kontrak antar-lapis** — sebabnya uji per-lapis tak pernah menemukannya. **+ cara menulis auditor: ukur KODE bukan teks** — versi pertama 13 finding, **11 false positive** (komentar BUGFIX yg mendeskripsikan bug ikut cocok regex; `DORK_TIMEOUT` cuma di docstring; `taskkill` DI DALAM `except TimeoutExpired:` itu justru FIX; `taskkill`/`powershell`/`wmic` itu utility singkat) → pakai `ast`, lihat 8 baris KE BELAKANG, kecualikan utility. Guard berisik lebih buruk daripada tidak ada. **+ dua lapis timeout JANGAN dicampur**: C1 per-tool (SLOW_FUZZ=1200s, lain 600s, SC 1800s) vs C6 per-clue (60s) — dalfox 8 menit di C1 itu NORMAL. | `references/whole-chain-contract-audit.md` |
| **mengamati run** — jangan vonis "mati" dari `tail` log | `references/run-observation-discipline.md` |
| **menjalankan batch fuzzer manual (ffuf dll) di samping pipeline** — satu `-w` per placeholder (gabung wordlist, cek 5 URL pertama dari JSON) · kalibrasi throughput dgn run kecil non-`-s` SEBELUM batch besar · `-maxtime` supaya hasil pasti tertulis · **jangan baca liveness Go tool dari counter I/O `wmic`** (flat ≠ mati) | `references/pipeline-rework-and-candidate-fp-fixes.md` §7 |
| **tool jalan jauh melewati timeout-nya** (dalfox 44 min vs cap 1200 s) / "apakah tool ini masih sehat?" — CPU-delta menjawab *hidup*, BUKAN *dalam budget*; hitung `now − StartTime` vs cap `SLOW_FUZZ`, kill out-of-band lalu biarkan `TIMEOUT` tercatat jujur; **`force-full-execution.py` kena bug `subprocess.run(shell=True,timeout=)` yang sama seperti tool_router — "fires once" bukan sifat aman**; + reklaim RAM saat peringatan 0A muncul (camoufox+Chrome = 1.3 GB) | `references/pipeline-tool-timeout-budget.md` §7 |
| **operator bilang "macet"/"powershellnya beku"** — satu tool muter (sstimap di asset statis dsb) memblokir pipeline; kill 1× malah respawn (autofix `max_attempts=3` di atas toolguard yg tak pernah kill) → kill sampai attempt habis; + `bytes_seen:0` itu artefak redirect `> file`. **Juga**: run yang SUDAH mati (jendela host ditutup) → relaunch **DETACHED** + auto-resume dari `trackers/audit-pipeline-<slug>.json` & file penanda sub-fase (jangan restart 0A); unstick lebih bersih = jalankan sub-step-nya sendiri lalu relaunch; relaunch mati ~10 detik **tanpa traceback** = OOM RAM <1.2 GB, bukan bug; cara membuktikan TAK ada drift curl (grep `curl` menyesatkan = komentar + `grpcurl`); **TIGA penyebab freeze yang penampakannya sama**: (a) tool muter, (b) **runner milik ORCHESTRATOR sendiri** tanpa timeout (`_account_mandated_tools()`: `trufflehog filesystem .` / `gitleaks detect --source .` / `interactsh-client -n 1 -v` → freeze 0D abadi + mati EXIT 1 tanpa traceback) → Popen+`stdin=DEVNULL`+timeout+`taskkill /T`+status `TIMEOUT` direkam jujur, (c) **DUA instance** di target-dir sama → artefak sub-fase korup (7/15 vektor) dan karena resume meng-SKIP sub-fase yang file penandanya ADA, C3 terkunci selamanya → **karantina** ke `_QUARANTINE/`+manifest (jangan hapus), lalu cabang REWORK gate yang menjalankan ulang. Diskriminator 1 perintah: `scripts/pipeline-proc-triage.py` (CPU-delta → BLOCKED vs LOOPING, anak per parent-PID, mtime evidence, kadens autofix, RAM). **Kontrak status producer↔gate**: status baru (`TIMEOUT`) wajib diakui `verify-tool-usage.py` (kalau tidak → `UNACCOUNTED statuses (gate blind spot)`), sementara `asset-coverage.py` **sengaja** menolak `TIMEOUT` → pakai cap **per-tool** utk scanner lama (nuclei 900/nikto 420/kube-hunter 600) supaya scan asli tak jadi TIMEOUT palsu; dan karena entri yang sudah tercatat di-SKIP selamanya, entri `TIMEOUT` yang keliru **dikarantina** (jangan diubah jadi EXECUTED). Closure manifest baru menulis `tools-usage.json` di **AKHIR** loop → jangan kill di tengah 0D. **Cara menyodorkan bukti hidup ke operator**: CPU parent datar itu NORMAL (induk menunggu anak) — tunjukkan anak + delta CPU anak + mtime artefak + timestamp log, beri one-liner `while true; do date +%T; tail -n 3 <dir>/orchestrator.log; sleep 5; done` | `references/unstick-frozen-pipeline-tool-loop.md` + `scripts/launch-pipeline-detached.py` + `scripts/pipeline-proc-triage.py` |
| **sebelum menyatakan KESIMPULAN apa pun tentang artefak** (run mati? temuan ada? RULE 0 dilanggar? patch aman?) — tabel klaim→bukti otoritatif; 8 kali salah-ucap dalam satu sesi | `references/artifact-claim-verification.md` |
| **gate 0D/0F gagal padahal run SELESAI — 18 cacat gate** (SC tool analisis file salah, manifest minta korpus yang tak ada, skill 0E dituntut di 0D, log ditulis sekali di akhir, recon web untuk target kontrak) | `references/gate-defects-2026-10-08.md` |
| **sebelum MENGKLAIM apa pun ke operator** — "run mati", "X hilang", "ini melanggar aturan", "target tidak terpengaruh": jalankan cek yang membantahnya DULU (8 klaim prematur dalam 1 sesi; satu hampir membatalkan temuan valid, satu lagi melaporkan run yang sudah `EXIT 0` sebagai MATI — kesalahan yg SAMA terulang padahal sudah dicatat). Cek-verifikasi yg FAIL lebih dulu menuduh VERIFIER-nya (case/whitespace/escaping) | `references/claim-discipline-verify-before-assert.md` |
| **0D GATE** — designing a gate that fails for the RIGHT reason (track-awareness, artefacts nothing writes, exit codes that lie, REWORK making it worse, **gate vs producer VOCABULARY mismatch**) | `references/gate-design-and-track-awareness.md` |
| **gate memblokir dengan aset yang keliatannya wajar** — bandingkan nama yang diminta gate vs field yang benar-benar ditulis producer sebelum menyalahkan run | `references/gate-design-and-track-awareness.md` §6b |
| **0D HARD BLOCK 3× gara-gara `poc-execution.json` = `[]`, atau FINAL GATE FAILED cuma karena `REPORT-survivors.md` absen** (2 run penuh, 2026-10-17) — rework TIDAK memperbaiki keduanya | `references/gate-block-repair-recipes-2026-10-17.md` — diskriminator 1 menit (`poc-plan.json` `repos_matched:0` + `wc -c` = 2 byte), fix di PRODUCER (`track-poc-execution.py` kini tulis `NO_POC_MATCHED` untuk plan 0-match), jebakan **resume me-SKIP 0C** (tulis ledger jujur berbasis bukti plan dulu; jangan fabrikasi), regenerasi `REPORT-survivors.md` via `finding_gate.py … --report …` (rc=0 walau 0 survivor), dan wajib baca **`passed-findings.json` — bukan `survivors.json`** saat bilang "ada/0 temuan" (survivor impact-gate bisa FP: varian SSRF dgn body identik homepage lolos regex proof lalu dibatalkan triage) |
| **gate memblokir padahal run-nya BENAR** — penolakan yang benar (0 temuan) tak meninggalkan artefak, gate menuntut artefak yang tak bisa ada di fase itu, atau dua komponen membaca bar yang berbeda | `references/terminal-state-and-phase-appropriate-gates.md` |
| **skill 0D vs 0E** — mandat yang mustahil dipenuhi di 0D (`loaded-skills.txt` vs `late-skills.txt`), dan auto-evidence skill dari artefak yang ia naungi | `references/terminal-state-and-phase-appropriate-gates.md` §1, §4 |
| **CHECK 13 gagal terus pada skill web yang JELAS sudah dipakai** (`hunt-idor/hunt-auth-bypass/hunt-xss/hunt-sqli/hunt-ssrf`) | `references/autofill-skill-rules-gap-web-hunt-skills.md` — **dua ronde**: (1) `rules` dict tanpa KEY → `applied` mustahil true; (2) KEY sudah ada tapi menuntut `skill-evidence/<skill>.md` yang **tak ada penulisnya** → tetap mustahil. JANGAN edit `skill-usage.json` (di-regenerate tiap run); perbaiki PRODUCER-nya |
| **gate menuntut artefak yang TAK ADA yang menulis** — gate FAIL berulang dgn REWORK yang tak bisa memperbaiki apa pun (cakupan tampak kurang padahal run benar) | `references/phantom-requirements.md` — prosedur diskriminator: `grep -rn "<nama>" scripts/` (hits hanya di gate = phantom) + **bandingkan dgn run lama yang pernah lulus 0F** (tak punya ledger/artefak = syarat itu belum pernah terpenuhi siapa pun). **Empat kasus terukur**: ledger 0B (13 aset, 0 direkam) · `skill-evidence/` · `subs.txt`/`live.txt` wajib NON-KOSONG (mustahil di host CDN/apex: subfinder 0 → httpx tak pernah bikin `live.txt`; **seed host target = mencatat fakta, bukan fabrikasi**) · manifest 0C ~55 tool vs force-exec yang merekam subset. **Tiga bentuk producer yang bisa dipakai ulang**: record-what-ran / account-the-manifest / derive-from-artefacts — invariannya sama: tak ada yg ditandai USED tanpa eksekusi |
| **gate bilang bukti "filler / fabricated" padahal file-nya JELAS ada** (`ls` melihatnya, `stat()` melihatnya, tapi `--derive` bilang marker hilang) | `references/unreadable-evidence-and-av-quarantine.md` — "exists" ≠ "readable": AV lokal bisa membuat file **bisa dibuat + di-stat tapi `open()` gagal `OSError EINVAL`** (nama/konten tool brute-force spt `patator` → terkunci; `os.listdir`/`find` bahkan **tak melihatnya**, `ls` melihat). Diskriminator 1 baris: `open(p,'rb').read()`. JANGAN simpulkan "tool gagal" atau "gate rusak" — keduanya salah. Fix di PRODUCER: nama netral utk tool sensitif (identitas di DALAM file) + **probe-baca setelah tulis** + re-point entri ledger lalu `--derive` lagi |
| **kandidat 0E menumpuk SAMPAH / skor HIGH dari file yang bukan temuan** (agregator menelan seluruh pohon run: ledger, `*-usage.json`, `*-index.json`, `skill-evidence/`, output-nya sendiri) | `references/aggregator-ingest-scope-and-false-positives.md` — 3 cacat + fix 3 lapis. (1) `rglob("*")` + skip-list 8 nama → tambah `EXCLUDE_DIRS` **dan** `EXCLUDE_NAME_RE` (regex, bukan daftar). (2) `NOTABLE_KW` cocok dgn **NAMA TEMPLATE nuclei di dalam file indeks** → `references-index.json` dapat skor **HIGH "333 notable"** tanpa satu request pun; aturan: kandidat butuh **respons**, bukan kata kunci — line harus `(status HTTP + URL)` ATAU marker vuln, dan **path file bukan respons**. (3) agregator menilai **output-nya sendiri** → duplikat + dokumen yang sudah disaring masuk lagi; pola sama dgn gate-menilai-echo. Terukur: **151 → 2 kandidat** (dua-duanya bukti nyata). |
| **laporan NEGATIF: jujur tapi belum layak kirim** (operator minta review; 851 B, tak ada alasan per-kandidat & tak ada ringkasan cakupan) | `references/negative-report-substance.md` — RULE 41 menjamin hasil negatif **ADA**; ini soal membuatnya **BERGUNA**. Seluruh data yang kurang sudah ada di disk (`review-candidates.json`, `gated.json`, `*-usage.json`, `asset-coverage.json`). Bentuk wajib: hasil → sebab → **cakupan** (per kelas, angka + nama artefak) → **kandidat & alasan tiap penolakan** → **batas/N-A**(dikelompokkan per alasan) → indeks bukti. `N/A` **bukan** cakupan. **+ §"Consumer↔producer contract"** — dua mis-read yang gagal SENYAP saat membangun laporan dari artefak: (a) field NAME salah (`reasons` list ditulis producer, dibaca `reason` scalar → tiap baris jadi `(no reason recorded)`, seolah gate tak pernah menjelaskan); (b) container SHAPE salah (`len(dict)` menghitung KEY, bukan baris → laporan negatif mencetak `cleared validation 4` padahal **0** = over-claim lewat pintu belakang). Baca output producer dulu (`print(list(json.load(...)[0].keys()))`), sadari bentuknya, dan assert funnel monoton-turun sebelum menulis. |
| **0B/0C/0D — setiap kali mengubah gate, manifest, atau classifier status tool** | `references/track-aware-gates-and-run-lifecycle.md` |
| **sebelum menyimpulkan sebuah run "mati" / berhenti di tengah** | `references/track-aware-gates-and-run-lifecycle.md` §7 — **BUKTIKAN DULU run-nya memang berakhir**: tanpa baris `=== EXIT ===` ia masih JALAN. Log yg tak bertambah saat disampling (apalagi lewat `\| tee`) bukan mayat. §7 versi lama pernah salah menyimpulkan "dibunuh RAM" padahal run-nya SELESAI dan gate yang memblokir — jangan ulangi |
| **gate FAIL lalu REWORK, atau jumlah kegagalan NAIK antar attempt** | `references/track-aware-gates-and-run-lifecycle.md` §8 — REWORK bisa menghapus artefak yang ia sendiri butuhkan; bandingkan HIMPUNAN kegagalan, bukan cuma jumlahnya |
| **Windows / MSYS** (＋ **heredoc menulis ulang KONTEN**: escaped-newline di dalam f-string jadi baris baru sungguhan → `SyntaxError: unterminated f-string`; pakai `chr(10)` lalu `py_compile` setelah generate — **PowerShell inline di dalam heredoc gagal SENYAP**: keluaran kosong/exit 1 ≠ "tak ada proses", pakai `wmic … /format:csv` + `csv.reader`, urutan kolom `Node,CommandLine,Name,ProcessId`) — jebakan path & invokasi tool, **termasuk saat MENULIS run-script** (heredoc tak dikutip = tool jalan tanpa target tapi rc=0), dan **mengutip SEGMEN path = spasi hilang** (`/d/data/"hermes/bug-bounty"/x` → tree hantu; gejala: `No such file or directory` pada file yang jelas sudah ditulis) | `references/msys-path-and-tool-invocation-traps.md` |
| **sebuah fix yang sudah kamu terapkan "tidak berefek"** / dua skill berbeda soal perilaku satu tool | `references/toolkit-copy-drift-and-bundle-sync.md` — toolkit ada **3 salinan**; bundle berisi `finding_gate.py` **v1 fail-OPEN** sementara live **v2 fail-closed**, dan SKILL.md menyuruh menjalankan yang BASI. `%LOCALAPPDATA%\hermes\scripts\` = sumber kebenaran; jalankan `bundle-sync.py sync` di sesi yang sama dgn tiap edit |
| **track web3 ATAU setiap kali gate memblokir** — enforcement track-aware + jebakan yg bikin pipeline "COMPLETE" padahal tidak menganalisis apa pun | `references/track-aware-enforcement-and-pipeline-traps.md` |
| **vendor larang scanner** | `references/vendor-forbidden-scanner-adaptation.md` |
| **resume antar-sesi** | `references/multi-session-resume-2026-09-26.md` |
| **patch pipeline "sudah saya pasang" tapi perilakunya tak berubah** — blok berkunci `if path.exists()` (path salah tulis → tak ada efek, tak ada error, `py_compile` lolos) | `references/gate-rederive-tz-and-fuzz-only-2026-10-12.md` §1b — bukti tunggal = **grep baris log milik patch itu di run berikutnya**; ambil path dari blok tetangga yang sudah benar; **loop/penolong pengaman membuat patch tampak "terverifikasi" padahal bukan** |
| **target SPA / host-role `static-site`** — `deep-recon` hanya mengisi 4–6 URL sehingga 15 varian + 15 business-logic + 52 reference menembak app-shell | `references/gate-rederive-tz-and-fuzz-only-2026-10-12.md` §7 — ekstrak endpoint API dari bundle (`main.<hash>.js`, `gen-cfg.js`) lalu **append ke `urls.txt`** (tuas tunggal; C2/C3/C4/C5/C6 membaca `urls.txt` saat step-nya mulai → tak perlu restart). Cek liveness host dulu — `exchange.`/`pro.` ternyata 302 ke apex, bukan produk |
| **"failure that pretends to be a result" — INDEX keluarga** (hollow coverage dari marker `[200]` di `urls.txt`/`live.txt` · scope leak payload ke host pihak-ketiga · ledger stale karena `--derive` jalan SEBELUM closure manifest menulis `tools-usage.json` · **run bilang `COMPLETE`/`33/33` tapi report lebih tua dari bukti → fase-complete itu CACHE, fix producer TIDAK menggugurkannya; paksa fase hilir jalan ulang dengan menulis ulang `completed_phases`+`current` — backup + `_QUARANTINE/manifest.json` dulu, jangan hapus state**) | `references/coverage-lies-and-report-quality.md` |
| **operator kirim lanjutan singkat tanpa sebut target** ("nggak ada temuan ya / teruskan cek sampai tuntas") di sesi baru — rekonstruksi engagement dari disk (state.db `sessions`+`messages`, mtime `_progress/`, `TRIAGE.md`, `findings.json`) lalu `deep-audit-mode.py guard` sebagai alat-kebenaran tercepat; `guard BLOCKED (tools-usage.json not found)` = BUKTI klaim "0 temuan" sebelumnya belum pernah ter-gate | `references/engagement-identification-from-terse-operator-message.md` |


## FULL RULE INDEX (references/rules/) — muat sesuai fase


Setiap aturan yang tidak inline di bawah tersimpan di sini. **0C WAJIB memuat ulang semua ini** (rule + payload/cookbook/exploit-book) sebelum mengklaim COMPLETE.

| file | section |
|---|---|
| `01-section.md` |  |
| `02-rule-0-rules-dont-force-anything-scripts-do.md` | ⛔ RULE 0: RULES DON'T FORCE ANYTHING — SCRIPTS DO |
| `03-rule-0-honest-reporting-no-overclaiming.md` | ⛔ RULE 0: Honest Reporting — NO Overclaiming |
| `04-rule-0c-impact-first-not-volume.md` | ⛔ RULE 0C: Impact-First — Not Volume |
| `05-rule-0b-dont-skip-dont-delete-complete-missing-items.md` | ⛔ RULE 0B: Don't Skip, Don't Delete — Complete Missing Items |
| `06-rule-1-exploit-first-mindset.md` | ⛔ RULE 1: Exploit-First Mindset |
| `07-rule-2-loading-executing.md` | ⛔ RULE 2: Loading ≠ Executing |
| `08-rule-2b-use-the-right-tool-not-just-curl.md` | ⛔ RULE 2b: Use the RIGHT tool — not just curl |
| `09-pipeline-change-checklist-run-this-after-every-edit-to-a-pip.md` | Pipeline change checklist — run this after EVERY edit to a pipelin |
| `10-rule-30-scope-never-ask-the-user-auto-detect-else-allow-all.md` | ⛔ RULE 30: SCOPE — NEVER Ask the User (Auto-Detect, Else Allow-All |
| `11-rule-31-patch-verify-loop-never-trust-a-patch-succeeded.md` | ⛔ RULE 31: Patch-Verify Loop — Never Trust a Patch "Succeeded" |
| `12-rule-32-multi-topic-parallel-audits-isolation-the-other-topi.md` | ⛔ RULE 32: Multi-Topic Parallel Audits — Isolation & the "Other To |
| `13-rule-2f-long-scans-go-to-the-background-not-into-subagents.md` | ⛔ RULE 2f: LONG SCANS GO TO THE BACKGROUND — NOT INTO SUBAGENTS |
| `14-rule-3-timeout-retry-not-skip.md` | ⛔ RULE 3: Timeout = Retry, Not Skip |
| `15-rule-4-reload-after-compression.md` | ⛔ RULE 4: Reload After Compression |
| `16-rule-5-verification-log-before-complete.md` | ⛔ RULE 5: Verification Log Before COMPLETE |
| `17-rule-6-max-15-context-per-finding.md` | ⛔ RULE 6: Max 15% Context Per Finding |
| `18-rule-7-self-check-every-5-tool-calls.md` | ⛔ RULE 7: Self-Check Every 5 Tool Calls |
| `19-rule-8-track-every-ref-file-execution.md` | ⛔ RULE 8: Track Every Ref File Execution |
| `20-rule-9-proven-theoretical-never-overclaim.md` | ⛔ RULE 9: Proven ≠ Theoretical — NEVER Overclaim |
| `21-rule-10-minimum-severity-threshold-for-reporting.md` | ⛔ RULE 10: Minimum Severity Threshold for Reporting |
| `22-rule-11-craft-cms-specific-testing.md` | ⛔ RULE 11: Craft CMS Specific Testing |
| `23-rule-15-user-mandated-audit-hardrules-all-7-non-negotiable.md` | ⛔ RULE 15: User-Mandated Audit Hardrules (ALL 7 — NON-NEGOTIABLE) |
| `24-rule-16-memory-format-compact-no-numbers-no-emojis.md` | ⛔ RULE 16: Memory Format — Compact, No Numbers, No Emojis |
| `25-rule-17-solidity-tool-windows-quirks.md` | ⛔ RULE 17: Solidity Tool Windows Quirks |
| `26-rule-17b-by-design-filter-dont-report-intentional-behavior.md` | ⛔ RULE 17b: By-Design Filter — Don't Report Intentional Behavior |
| `27-rule-18-anti-premature-classification-mandatory.md` | ⛔ RULE 18: Anti-Premature-Classification (MANDATORY) |
| `28-rule-19-minimum-3-bypass-attempts-before-blocked-claim.md` | ⛔ RULE 19: Minimum 3 Bypass Attempts Before "Blocked" Claim |
| `29-rule-28-pipeline-output-findings-triage-before-reporting.md` | ⛔ RULE 28: Pipeline Output != Findings — Triage Before Reporting |
| `30-rule-33-resume-an-engagement-from-its-log-never-re-derive-sc.md` | ⛔ RULE 33: Resume an ENGAGEMENT from its log — never re-derive sco |
| `31-rule-34-when-there-is-no-fuzzable-url-the-authenticated-api-.md` | ⛔ RULE 34: When there is NO fuzzable URL — the authenticated API h |
| `32-rule-35-scanner-output-triage-the-fp-classes-that-keep-burni.md` | ⛔ RULE 35: Scanner-output triage — the FP classes that keep burnin · **estate-scan triage + re-verifikasi** (contoh terukur: nuclei 42 host/3.546 template/282k request → 651 match = 624 info/7 low/0 high; wajib split per severity+template-id; **re-request tiap hit non-info** karena temuan bisa sudah hilang — `expired-ssl` di host yang deployment-nya sudah dihapus = bukan temuan baru; host kedua dengan cacat SAMA = addendum ke laporan yang sudah terkirim, bukan laporan baru; **aturan kalibrasi: derivable ≠ disclosure** — endpoint "bocor" tanpa auth yang isinya bisa diturunkan/publik = informational → DROP (terukur: `/api/v1/identity` balas 200 untuk alamat apa pun + tanpa rate limit, tapi `ownerServers()` on-chain = 0 dan alamat PS yang dikembalikan tak punya code → record DERIVED, bukan kebocoran infrastruktur); probe auth-vs-validasi pakai body INVALID (`422` field-required = validasi jalan, `401/403` = ada gerbang auth) supaya tak pernah menembak write nyata) → `references/estate-scan-triage-and-reverification.md` |
| `33-rule-36-all-tools-all-variants-on-an-auth-gated-target-curlp.md` | ⛔ RULE 36: "All tools, all variants" on an AUTH-GATED target — cur |
| `34-mechanical-enforcement.md` | ⛔ MECHANICAL ENFORCEMENT |
| `35-rule-12-execute_code-shutil-not-persistent.md` | ⛔ RULE 12: execute_code shutil Not Persistent |
| `36-rule-13-target-surface-prioritization-high-value-first.md` | ⛔ RULE 13: Target Surface Prioritization — High-Value First |
| `37-rule-14-cloudflare-bot-protection-dont-fake-results.md` | ⛔ RULE 14: Cloudflare Bot Protection — Don't Fake Results |
| `38-rule-20-pipeline-integrity-audit-run-when-user-asks-cek-semu.md` | ⛔ RULE 20: Pipeline Integrity Audit (run when user asks "cek semua |
| `39-rule-25-references-must-be-used-not-just-loaded-c6.md` | ⛔ RULE 25: References MUST Be USED — Not Just Loaded (C6) |
| `40-rule-24-candidate-review-sop-temuan-candidate-3x-cek-lowhigh.md` | ⛔ RULE 24: Candidate Review SOP — Temuan = CANDIDATE, 3x Cek, Low→ |
| `41-rule-26-poc-repos-extract-techniques-not-just-execute-1-c6b.md` | ⛔ RULE 26: PoC Repos → Extract TECHNIQUES, Not Just Execute 1% (C6 |
| `42-rule-27-multi-session-resume-per-phase-state-never-restart-f.md` | ⛔ RULE 27: Multi-Session Resume — Per-Phase State, Never Restart f |
| `43-rule-23-unified-pipeline-hard-won-fixes-findings-quality-bar.md` | ⛔ RULE 23: Unified Pipeline Hard-Won Fixes + Findings Quality Bar |
| `44-rule-21-poc-execution-plan-generation-fix-windows-path-resol.md` | ⛔ RULE 21: POC Execution Plan Generation Fix (Windows path resolut |
| `45-rule-22-tool-detection-on-windows-use-shutilwhich-explicit-p.md` | ⛔ RULE 22: Tool Detection on Windows — Use shutil.which + Explicit |
| `46-per-tool-timeout-values-tool_routerroute_and_run-defaults.md` | Per-Tool Timeout Values (tool_router.route_and_run defaults) |
| `47-rule-36-evm-static-tool-severity-labels-are-not-findings-tri.md` | ⛔ RULE 36: EVM static-tool SEVERITY LABELS ARE NOT FINDINGS — tria |
| `48-rule-37-a-delegated-subagent-that-times-out-at-600s-has-stil.md` | ⛔ RULE 37: A delegated subagent that times out at 600s has still W |
| `49-rule-38-enumerated-hosts-and-spa-routes-need-a-differential-.md` | ⛔ RULE 38: Enumerated hosts and SPA routes need a DIFFERENTIAL — m |
| `50-config-requirements.md` | Config Requirements |
| `51-companion-reference-poc-technique-atlas-additive-never-overr.md` | Companion Reference — `poc-technique-atlas` (additive, never overr |

---


## ⛔ REFERENCE DOKUMEN (`references/*.md`) — baca sesuai konteks


Aturan yang tidak masuk `references/rules/` tinggal di sini. **Baca yang relevan; jangan dilewatkan.**

| kapan dibaca | file |
|---|---|
| **WAJIB sebelum menutup laporan apa pun** — kebijakan runtime penuh: run tanpa batas, stall = WARN bukan kill (`toolguard.py`), gagal → auto-perbaiki → **jalankan ulang** (`autofix.py`), **DILARANG jatuh ke curl**, GENTLE saat vendor larang scanner, kadens distilasi, keluarga **"failure that pretends to be a result"** (§8 budget-netral, §9 AV quarantine, §10 ledger menuntut ISI, §11 field-name salah, §12 daftar guard), dan **§13 STANDING: deep-dive proaktif + verifikasi 3x**, **§14 STANDARD DELIVERABLE: draft Gmail + PDF PoC ber-gate impact-terbukti (`final-deliverable.py`), 3x-per-properti (`property-sweep.py`)** | `references/runtime-execution-policy-2026-10-10.md` |
| **menyatakan `FALSIFIED` / "aman" / "tidak vulnerable" / menyerah pada kandidat** — komplemen RULE 18, bukan duplikat. RULE 18 mengatur sisi POSITIF (jangan bilang *informational* terlalu cepat); gerbang ini mengatur sisi NEGATIF (jangan menyimpulkan MATI tanpa bukti). Beban bukti setara dua sisi · default ragu = `INCONCLUSIVE` (bukan FALSIFIED) · FALSIFIED wajib lolos 7 gerbang: ladder tuntas · ≥3 variasi · **steelman ditulis DULU** · bukti mitigasi dari EKSEKUSI nyata + ≥1 upaya bypass · evidence tier `Observed` (yang `Prepared` → INCONCLUSIVE) · klasifikasi root-cause gagal-reproduce (a) vuln memang tak ada = boleh FALSIFIED, (b) tooling/resource = WAJIB INCONCLUSIVE, (c) env beda = WAJIB INCONCLUSIVE · cross-framing dua arah. Plus gate per-TAHAP Recon→ThreatModel→Hipotesis→Validasi dgn `RECON GAP` dibawa eksplisit. Format verdict per-verdict wajib + jeda sanity-check operator sebelum CONFIRMED naik ke laporan. | `references/anti-premature-falsification-gates.md` |
| **mau tahu host-nya sebenarnya APA sebelum menembakkan payload** — peran host + enumerasi endpoint nyata (`deep-endpoints.py`): `signed-redirector`/`cdn-origin`/`app`/`api`/`static-site`/`redirector`, plus kelas uji **per peran** | `references/runtime-execution-policy-2026-10-10.md` §13.1 |
| **sebelum menyimpulkan temuan ATAU "0 temuan"** — 3 putaran independen dari awal (`reverify.py` sweep/http/probe); kandidat tak bereproduksi = UNSTABLE, tak boleh dilaporkan | `references/runtime-execution-policy-2026-10-10.md` §13.2 |
| **kamu baru mengedit kode pipeline** / gejala "tool error" untuk SEMUA tool, atau sebuah fix "tidak berefek" — `ast.parse` lewat tapi runtime tetap salah | `references/silent-failure-static-guards.md` — 3 guard di `hermes-health-audit.py` (`import_fail`, `unbound_name_fail`, `budget_arith_fail`) + cara menulis scope-walk closure-aware (versi naif = **37 false positive**, guard berisik lebih buruk daripada tidak ada) + tabel gejala→diskriminator 1 baris. **Praktik yang menangkap ketiganya: jalankan sekali di target-dir nyata — bukan `ast.parse`, bukan `import`** |
| **0A/0B selalu** — phase model, fresh-run, reset tracker | `references/audit-pipeline-phases-and-fresh-run.md` |
| **0C semua track** — checklist aset per fase (WAJIB) | `references/phase-execution-mandate.md` |
| **0E/0F** — siklus temuan (find→3x→candidate→re-validasi) | `references/candidate-lifecycle.md` |
| **0B/0C/0E/0F — track web3/Solidity** — tx-hash exploit forensics | `references/defi-exploit-forensics-in-pipeline.md` |
| **0C track web3 — menjalankan slither/aderyn/myth/echidna/medusa** pada source hasil recovery | skill **`onchain-source-recovery`** → bagian "Making a recovered source ACTUALLY analysable" (5 jebakan: file salah terpilih, remappings, `src="."` stack overflow, `out/build-info` wajib, `offline=true` memblokir solc) |
| **re-run setelah memperbaiki pipeline sendiri** | `references/multi-session-resume-2026-09-26.md` → "Rerunning after you FIX a bug" (dua state store wajib dibersihkan) |
| **0C track web3** — triage label severity tool statis EVM | `references/evm-and-recon-triage-2026-10-01.md` |
| **0D GATE** — fail-open finding gate | `references/finding-gate-fail-open-2026-10-07.md` |
| **0E/0F** — mechanical 7-question triage gate (`triage_gate.py`, E5) + a gate scoring its own echo (unwrap/scaffold scrub) + condition→skill router | `references/mechanical-triage-gate-and-self-echo.md` |
| **menulis ledger 0C/0D dengan tangan** (skema list vs dict, `evidence_file` path absolut & ≥100 B, vocabulary status yang diterima CHECK 2b, urutan `asset-coverage --init`/`--derive`, N/A-BLOCKED saat policy melarang scanner, **§7 gate baca DIR ENGAGEMENT tapi orchestrator TULIS ke `poc-plans/` → sync dulu + `asset-coverage` di-derive ulang dari `tools-usage.json` jadi edit coverage tak nyangkut**, **§8 gate yang diperbaiki tangan berhenti di artefak 0E/0F → RESUME orchestrator**, **§9 lokasi asli `asset-coverage.py` (di dalam skill, bukan `~/…/scripts/`) + script langkah 0C TIDAK punya `--help` (memanggilnya = MENJALANKAN run) + `execute-references.py` mengabaikan argumen target (pakai index cache) + `--mark` yang kena 0 entri karena beda HURUF BESAR/KECIL + `refs_web3` sah di-N/A saat tak ada korpus penyerang yang bisa ditembakkan + urutan perbaikan yang terbukti**) | `references/gate-artefact-schema-and-status-contract.md` |
| **0D GATE gagal berulang** — REWORK spiral, log ditulis sekali di akhir | `references/gate-rework-and-log-persistence.md` |
| **gate FAIL lalu rework menjalankan step yang SALAH** (mis. `poc-variant-usage.json missing` tapi log `re-running execute-variants.py` — substring dispatcher) · **C5/C6b tak pernah kelar** (sstimap/dalfox diulang per-repo, `timeout_cap=None`) · **scope gate tolak `www.` utk `--scope <bare-domain>`** · kandidat `impact-verify confirmed=` yang ternyata FP (SSTI control-test / open-redirect relative-Location / DOM-XSS marker-title) | `references/pipeline-rework-and-candidate-fp-fixes.md` |
| **0D HARD BLOCK 3× dengan pesan IDENTIK, REWORK tak menolong** — gate baca DIR ENGAGEMENT tapi orchestrator TULIS ke `poc-plans/` (fix = `AUDIT_ENGAGEMENT_DIR`) · **CHECK 2b memblokir pada ENTRI `FAILED`/`FAILED_USAGE`** (nuclei exit −1 = OOM-kill, linkfinder 429 → terbaca "wrong CLI") → resep jujur: re-run tool nyata (host lain yang in-scope kalau yang utama 429) → evidence berheader `# TOOL EVIDENCE:` (**`nuclei -o` menulis 0 byte saat 0 temuan** → gate butuh ≥1 byte) → koreksi entri `EXECUTED`+bytes (backup `.bak_gatefix_*`) → `asset-coverage.py --derive` → `verify-tool-usage.py` 13/13 → resume; **+ konvensi argumen 3 script yang berbeda** (`verify-tool-usage.py` ABS dir · `audit-checkpoint.py` NAMA RELATIF · `asset-coverage.py` ada di `scripts/` SKILL, bukan `~/…/scripts/`); **+ jangan telan "impact survivor" pipeline mentah** (sqlmap "not injectable" & 19 baris `[429]` dua-duanya tampak "notable") | `references/gate-toolchain-honesty-fixes-2026-10-12.md` §5 |
| **0D gagal 2× dengan pesan IDENTIK lalu nyaris HARD BLOCK** · **ledger menolak bukti tulisan-tangan** (`timestamp … predates the run`) · **gate HIJAU tapi sebagian tool tak pernah jalan** (`FUZZ_ONLY`/`SKIP_WITH_REASON`) · operator minta *"semua tool dipanggil, jgn dilewati"* | `references/gate-rederive-tz-and-fuzz-only-2026-10-12.md` — 3 cacat terukur: (1) `run_step5_tools()` re-run tool TAPI tak pernah `--derive` ulang → gate baca ledger BASI, pesan sama tiap attempt, HARD BLOCK tanpa 0E/0F (fix = derive setelah rework; bukti: 1× `--derive` → `49 ok / 0 fail`); (2) `_ts()` menormalkan stamp tz-aware ke **UTC** padahal `run-meta.started_at` **naive local** → bukti manual 02:49+07 (19:49Z) dianggap "mendahului" run 23:41 → `USED→NOT_RUN` (fix di `_ts` = local-naive **dan** tulis `# TS:` TANPA offset — `date -Iseconds` justru menambahkannya); (3) `force-full-execution` menulis `FUZZ_ONLY` (`no verified CLI invocation`) yang `--derive` petakan ke **N/A "documented skip"** → CHECK 12 LOLOS walau ~11 tool manifest belum pernah fire (terukur: ssrfmap/graphqlmap/jwt_tool/sstimap/smuggler/sslscan/subjack/linkfinder/secretfinder/cloud_enum/kube-hunter). **+ prosedur gap-close** (jalankan tool nyata → evidence `# TOOL EVIDENCE:` → update baris ledger → `--derive` → re-verify) **+ cara membuat tool resolvable** (`shutil.which` butuh ekstensi → wrapper shebang DAN `.cmd`; PATH `execute_code` ≠ PATH pipeline → cek final dari `terminal`; wordlist ffuf diprobe di `0B-recon/common.txt`; `byp4xx` di-`go build`; `jwt_tool` butuh `~/.jwt_tool/jwtconf.ini` tulis-tangan + token sebagai ARG STRING + `-rh` agar benar-benar terkirim) **+ sync dir: copy PARSIAL → 3 kegagalan guard yang khas** **+ `[STALL-WARN]` biasanya alarm palsu** (phase field hanya maju per-step; log di-block-buffer oleh `tee`; bukti = mtime evidence; MSYS PID ≠ WINPID → `ps -W` kolom 4) **+ resep SOAP/WSDL legacy** (`.wsdl` shell → `wsdl:import …?wsdl=<name>.wsdl`; buktikan origin memproses via `500 soap:Fault` sebelum uji; `403 Cloudflare` = vector DIBLOKIR EDGE, bukan "aman"; XInclude tanpa DTD = bypass WAF yang dicoba lebih dulu) |
| **tool menyerang HOST YANG SALAH** (proses dalfox/nuclei command line menunjuk domain pihak ketiga) — 3 cacat berantai, DIPERBAIKI 2026-10-10: wordlist path tanpa leading slash (`host.env` → DNS gagal, 46/100 probe hangus), `_param_url` pakai tes substring (`host in u.split("/")[2]`) sehingga `host///host-lain` LOLOS, crawl recon menambah URL absolut pihak ketiga tanpa filter scope. Bandingkan dgn **ROOT DOMAIN**, bukan host penuh (kalau tidak subdomain in-scope ikut tertolak); `urlparse` SENDIRI tak cukup — host kedua hidup di path, perlu guard `"//" in rest`. | `references/url-scope-bugfix-2026-10-10.md` |
| **6 kelas lain: deteksi ≠ bukti** — `http_probe` menandai probe "interesting" hanya dari `status not in (404,403,401) and size>0`; itu **tak bisa** membedakan halaman yg menggemakan kata `passwd` dari LFI yg BENAR-BENAR membaca file, 200 utk `{{7*7}}` dari SSTI yg mengevaluasi jadi `49`, respons apa pun dari SSRF yg memanggil canary, atau halaman lambat dari blind-SQLi yg benar-benar `sleep`. Stage **0C-C2d `impact-verify`** membuktikan 6 kelas: SSRF (callback OOB), LFI (signature isi file), SSTI (evaluasi aritmetika 49 **dan** 56 — dua jawaban benar berbeda), XXE (callback entity), open-redirect (host di `Location:`), blind-SQLi (differential waktu). **Dua bug nyata ketemu lewat testing:** (1) open-redirect terbaca "tidak ada" karena fetcher mengikuti redirect → off-site gagal → `status=None`, fix = `http_get_noredirect`; (2) SSRF palsu muncul karena callback itu buatan KLIEN KITA sendiri yg mengikuti redirect → probe SSRF sekarang wajib `noredirect`, 3xx dicatat terpisah sebagai `redirect_only`. Jebakan: test-target yg fetch URL ke dirinya sendiri WAJIB `ThreadingHTTPServer` (single-thread = deadlock, terukur `fetch failed: TimeoutError`); XXE butuh POST. | `references/impact-verification-stage-2026-10-10.md` |
| **RCE / command-injection — "kandidat" vs "terbukti jalan"** — pipeline bisa **DETEKSI** (nuclei tag `cmd-injection,rce`, 104 payload cmdi) tapi tak pernah **MEMBUKTIKAN eksekusi**; dan mapping 0C `"cmdi": ["gobuster","ffuf"]` SALAH TOTAL — keduanya directory brute-forcer, fuzz PATH (`/FUZZ`), tak bisa inject command ke parameter (terukur: `ffuf-cmdi.txt` = bruteforce nama file berlabel cmdi → hasil 0 by construction). Stage **0C-C2c `rce-verify`** membuktikan eksekusi via **3 channel independen** + kontrol inert: (1) differential waktu vs baseline benign — floor `0.6 × sleep`, BUKAN `sleep × ratio` (versi salah bikin hit 3.08s terbaca False), (2) callback OOB canary lokal (`curl`/`certutil`/`iwr`), (3) signature output perintah (`uid=...gid=`, `[fonts]`, `Windows IP Configuration`). **WAJIB payload Unix DAN Windows** (`;` vs `&`/`|`; `ping -n N` pengganti `sleep`) — di host Windows `; sleep 3` = 0 delay sedangkan `| sleep 3` = 3.16s. Verdict: `CONFIRMED` (OOB/output) / `PARTIAL_TIME_ONLY` (blind, ≥2 time) / `NOT_CONFIRMED`; kontrol kotor = warning, bukan lolos. | `references/rce-verification-stage-2026-10-10.md` |
| **XSS pada SPA / hasil "bersih" dari scanner server-side** — `plugins.jetbrains.com` punya **0 dari 123 URL ber-parameter**, jadi dalfox muter 53 menit tanpa ada yg bisa di-inject; hasil bersihnya **false negative by construction**, bukan bukti aman. Stage **0C-C2b `dom-xss`** (`dom-xss-test.py`, Playwright/Chromium) inject via query+hash+path, pasang sink hook SEBELUM navigasi, dan hanya mencatat HIT kalau payload **DITERJEMAHKAN** (MutationObserver lihat node baru / `window.onerror` / canary `127.0.0.1` benar-benar di-fetch). `payload-present-in-dom` = konteks, BUKAN hit. Wajib buktikan **dua arah**: benign → 0 hit, app rentan → ada hit. Jebakan: `page.evaluate` yg throw BUKAN bukti XSS (versi pertama menghitungnya sbg hit → 10 FP); Camofox path-mismatch → pakai Playwright. **MELEMAHKAN 2026-10-12 (terukur, 2 run): hook `mark()` menyala untuk SETIAP node IMG/SCRIPT/SVG baru — setiap halaman yang render via JS menghasilkannya, jadi `interpreted:true` = FALSE POSITIVE yang dijamin (148 "hit" di spectrocoin.com, 47 di antaranya halaman asli SpectroCoin yg tetap bukan XSS; sisanya `title:"Just a moment..."` = halaman challenge Cloudflare). Diskriminator 2 baris sebelum melaporkan apa pun: buang `title == "Just a moment..."`, dan buang yang `reason`-nya hanya `dom-sink:mutated-node:*`; hit sah BUTUH canary benar-benar di-fetch / `window.onerror` / DOM berubah KARENA payload. Perlakukan `dom-xss-findings.json` sebagai triage input, bukan temuan.** | `references/dom-xss-stage-2026-10-10.md` |
| **Rekon tampak "sukses" tapi endpoint hilang** — `deep-recon: urls.txt 27 -> 123` gagal senyap waktu root-domain dihitung dgn one-liner salah (menghasilkan tuple → `'list' object has no attribute 'split'`), sehingga **104 endpoint nyata tak pernah masuk cakupan** dan seluruh 0C menembak 27 URL saja. Hitung root domain dgn langkah eksplisit + `isinstance(str)` check; jalankan **pre-restart checker** (`pre_restart_check.py`) yg menguji SEMUA lapis fix sebelum restart, bukan sesudah. | `references/url-scope-bugfix-2026-10-10.md` |
| **SEBELUM restart pipeline panjang** — operator: *"kenapa banyak bug muncul, gkberes2 auditnya"*. Anti-pola yg bikin itu: **temukan bug → fix → restart 4 jam → temukan bug berikutnya**. Terukur: **5 restart, 10 bug, ~20 jam**, tetap tak sampai 0F. Semua fix BENAR; METODENYA salah — run penuh adalah detektor bug termahal yg ada, dan pipeline 7-lapis punya permukaan besar utk kelas cacat ini. Jawabannya: **`pipeline-contract-audit.py`** (5 detik, exit 1 kalau ada HIGH) = prasyarat restart, bukan pelengkap sesudahnya. **10 bug itu SATU kelas**: *nilai/aturan/klaim dideklarasikan di satu lapis, lalu diabaikan/dibuang/ditinggalkan buktinya di lapis berikutnya, tanpa ada yg mengecek jarak.* Hanya 2 dari 10 bug "logic"; 8 adalah **pelanggaran kontrak antar-lapis** — sebabnya uji per-lapis tak pernah menemukannya. **+ cara menulis auditor: ukur KODE bukan teks** — versi pertama 13 finding, **11 false positive** (komentar BUGFIX yg mendeskripsikan bug ikut cocok regex; `DORK_TIMEOUT` cuma di docstring; `taskkill` DI DALAM `except TimeoutExpired:` itu justru FIX; `taskkill`/`powershell`/`wmic` itu utility singkat) → pakai `ast`, lihat 8 baris KE BELAKANG, kecualikan utility. Guard berisik lebih buruk daripada tidak ada. **+ dua lapis timeout JANGAN dicampur**: C1 per-tool (SLOW_FUZZ=1200s, lain 600s, SC 1800s) vs C6 per-clue (60s) — dalfox 8 menit di C1 itu NORMAL. | `references/whole-chain-contract-audit.md` |
| **mengamati run** — jangan vonis "mati" dari `tail` log | `references/run-observation-discipline.md` |
| **menjalankan batch fuzzer manual (ffuf dll) di samping pipeline** — satu `-w` per placeholder (gabung wordlist, cek 5 URL pertama dari JSON) · kalibrasi throughput dgn run kecil non-`-s` SEBELUM batch besar · `-maxtime` supaya hasil pasti tertulis · **jangan baca liveness Go tool dari counter I/O `wmic`** (flat ≠ mati) | `references/pipeline-rework-and-candidate-fp-fixes.md` §7 |
| **tool jalan jauh melewati timeout-nya** (dalfox 44 min vs cap 1200 s) / "apakah tool ini masih sehat?" — CPU-delta menjawab *hidup*, BUKAN *dalam budget*; hitung `now − StartTime` vs cap `SLOW_FUZZ`, kill out-of-band lalu biarkan `TIMEOUT` tercatat jujur; **`force-full-execution.py` kena bug `subprocess.run(shell=True,timeout=)` yang sama seperti tool_router — "fires once" bukan sifat aman**; + reklaim RAM saat peringatan 0A muncul (camoufox+Chrome = 1.3 GB) | `references/pipeline-tool-timeout-budget.md` §7 |
| **operator bilang "macet"/"powershellnya beku"** — satu tool muter (sstimap di asset statis dsb) memblokir pipeline; kill 1× malah respawn (autofix `max_attempts=3` di atas toolguard yg tak pernah kill) → kill sampai attempt habis; + `bytes_seen:0` itu artefak redirect `> file`. **Juga**: run yang SUDAH mati (jendela host ditutup) → relaunch **DETACHED** + auto-resume dari `trackers/audit-pipeline-<slug>.json` & file penanda sub-fase (jangan restart 0A); unstick lebih bersih = jalankan sub-step-nya sendiri lalu relaunch; relaunch mati ~10 detik **tanpa traceback** = OOM RAM <1.2 GB, bukan bug; cara membuktikan TAK ada drift curl (grep `curl` menyesatkan = komentar + `grpcurl`); **TIGA penyebab freeze yang penampakannya sama**: (a) tool muter, (b) **runner milik ORCHESTRATOR sendiri** tanpa timeout (`_account_mandated_tools()`: `trufflehog filesystem .` / `gitleaks detect --source .` / `interactsh-client -n 1 -v` → freeze 0D abadi + mati EXIT 1 tanpa traceback) → Popen+`stdin=DEVNULL`+timeout+`taskkill /T`+status `TIMEOUT` direkam jujur, (c) **DUA instance** di target-dir sama → artefak sub-fase korup (7/15 vektor) dan karena resume meng-SKIP sub-fase yang file penandanya ADA, C3 terkunci selamanya → **karantina** ke `_QUARANTINE/`+manifest (jangan hapus), lalu cabang REWORK gate yang menjalankan ulang. Diskriminator 1 perintah: `scripts/pipeline-proc-triage.py` (CPU-delta → BLOCKED vs LOOPING, anak per parent-PID, mtime evidence, kadens autofix, RAM). **Kontrak status producer↔gate**: status baru (`TIMEOUT`) wajib diakui `verify-tool-usage.py` (kalau tidak → `UNACCOUNTED statuses (gate blind spot)`), sementara `asset-coverage.py` **sengaja** menolak `TIMEOUT` → pakai cap **per-tool** utk scanner lama (nuclei 900/nikto 420/kube-hunter 600) supaya scan asli tak jadi TIMEOUT palsu; dan karena entri yang sudah tercatat di-SKIP selamanya, entri `TIMEOUT` yang keliru **dikarantina** (jangan diubah jadi EXECUTED). Closure manifest baru menulis `tools-usage.json` di **AKHIR** loop → jangan kill di tengah 0D. **Cara menyodorkan bukti hidup ke operator**: CPU parent datar itu NORMAL (induk menunggu anak) — tunjukkan anak + delta CPU anak + mtime artefak + timestamp log, beri one-liner `while true; do date +%T; tail -n 3 <dir>/orchestrator.log; sleep 5; done` | `references/unstick-frozen-pipeline-tool-loop.md` + `scripts/launch-pipeline-detached.py` + `scripts/pipeline-proc-triage.py` |
| **sebelum menyatakan KESIMPULAN apa pun tentang artefak** (run mati? temuan ada? RULE 0 dilanggar? patch aman?) — tabel klaim→bukti otoritatif; 8 kali salah-ucap dalam satu sesi | `references/artifact-claim-verification.md` |
| **gate 0D/0F gagal padahal run SELESAI — 18 cacat gate** (SC tool analisis file salah, manifest minta korpus yang tak ada, skill 0E dituntut di 0D, log ditulis sekali di akhir, recon web untuk target kontrak) | `references/gate-defects-2026-10-08.md` |
| **sebelum MENGKLAIM apa pun ke operator** — "run mati", "X hilang", "ini melanggar aturan", "target tidak terpengaruh": jalankan cek yang membantahnya DULU (8 klaim prematur dalam 1 sesi; satu hampir membatalkan temuan valid, satu lagi melaporkan run yang sudah `EXIT 0` sebagai MATI — kesalahan yg SAMA terulang padahal sudah dicatat). Cek-verifikasi yg FAIL lebih dulu menuduh VERIFIER-nya (case/whitespace/escaping) | `references/claim-discipline-verify-before-assert.md` |
| **0D GATE** — designing a gate that fails for the RIGHT reason (track-awareness, artefacts nothing writes, exit codes that lie, REWORK making it worse, **gate vs producer VOCABULARY mismatch**) | `references/gate-design-and-track-awareness.md` |
| **gate memblokir dengan aset yang keliatannya wajar** — bandingkan nama yang diminta gate vs field yang benar-benar ditulis producer sebelum menyalahkan run | `references/gate-design-and-track-awareness.md` §6b |
| **0D HARD BLOCK 3× gara-gara `poc-execution.json` = `[]`, atau FINAL GATE FAILED cuma karena `REPORT-survivors.md` absen** (2 run penuh, 2026-10-17) — rework TIDAK memperbaiki keduanya | `references/gate-block-repair-recipes-2026-10-17.md` — diskriminator 1 menit (`poc-plan.json` `repos_matched:0` + `wc -c` = 2 byte), fix di PRODUCER (`track-poc-execution.py` kini tulis `NO_POC_MATCHED` untuk plan 0-match), jebakan **resume me-SKIP 0C** (tulis ledger jujur berbasis bukti plan dulu; jangan fabrikasi), regenerasi `REPORT-survivors.md` via `finding_gate.py … --report …` (rc=0 walau 0 survivor), dan wajib baca **`passed-findings.json` — bukan `survivors.json`** saat bilang "ada/0 temuan" (survivor impact-gate bisa FP: varian SSRF dgn body identik homepage lolos regex proof lalu dibatalkan triage) |
| **gate memblokir padahal run-nya BENAR** — penolakan yang benar (0 temuan) tak meninggalkan artefak, gate menuntut artefak yang tak bisa ada di fase itu, atau dua komponen membaca bar yang berbeda | `references/terminal-state-and-phase-appropriate-gates.md` |
| **skill 0D vs 0E** — mandat yang mustahil dipenuhi di 0D (`loaded-skills.txt` vs `late-skills.txt`), dan auto-evidence skill dari artefak yang ia naungi | `references/terminal-state-and-phase-appropriate-gates.md` §1, §4 |
| **CHECK 13 gagal terus pada skill web yang JELAS sudah dipakai** (`hunt-idor/hunt-auth-bypass/hunt-xss/hunt-sqli/hunt-ssrf`) | `references/autofill-skill-rules-gap-web-hunt-skills.md` — **dua ronde**: (1) `rules` dict tanpa KEY → `applied` mustahil true; (2) KEY sudah ada tapi menuntut `skill-evidence/<skill>.md` yang **tak ada penulisnya** → tetap mustahil. JANGAN edit `skill-usage.json` (di-regenerate tiap run); perbaiki PRODUCER-nya |
| **gate menuntut artefak yang TAK ADA yang menulis** — gate FAIL berulang dgn REWORK yang tak bisa memperbaiki apa pun (cakupan tampak kurang padahal run benar) | `references/phantom-requirements.md` — prosedur diskriminator: `grep -rn "<nama>" scripts/` (hits hanya di gate = phantom) + **bandingkan dgn run lama yang pernah lulus 0F** (tak punya ledger/artefak = syarat itu belum pernah terpenuhi siapa pun). **Empat kasus terukur**: ledger 0B (13 aset, 0 direkam) · `skill-evidence/` · `subs.txt`/`live.txt` wajib NON-KOSONG (mustahil di host CDN/apex: subfinder 0 → httpx tak pernah bikin `live.txt`; **seed host target = mencatat fakta, bukan fabrikasi**) · manifest 0C ~55 tool vs force-exec yang merekam subset. **Tiga bentuk producer yang bisa dipakai ulang**: record-what-ran / account-the-manifest / derive-from-artefacts — invariannya sama: tak ada yg ditandai USED tanpa eksekusi |
| **gate bilang bukti "filler / fabricated" padahal file-nya JELAS ada** (`ls` melihatnya, `stat()` melihatnya, tapi `--derive` bilang marker hilang) | `references/unreadable-evidence-and-av-quarantine.md` — "exists" ≠ "readable": AV lokal bisa membuat file **bisa dibuat + di-stat tapi `open()` gagal `OSError EINVAL`** (nama/konten tool brute-force spt `patator` → terkunci; `os.listdir`/`find` bahkan **tak melihatnya**, `ls` melihat). Diskriminator 1 baris: `open(p,'rb').read()`. JANGAN simpulkan "tool gagal" atau "gate rusak" — keduanya salah. Fix di PRODUCER: nama netral utk tool sensitif (identitas di DALAM file) + **probe-baca setelah tulis** + re-point entri ledger lalu `--derive` lagi |
| **kandidat 0E menumpuk SAMPAH / skor HIGH dari file yang bukan temuan** (agregator menelan seluruh pohon run: ledger, `*-usage.json`, `*-index.json`, `skill-evidence/`, output-nya sendiri) | `references/aggregator-ingest-scope-and-false-positives.md` — 3 cacat + fix 3 lapis. (1) `rglob("*")` + skip-list 8 nama → tambah `EXCLUDE_DIRS` **dan** `EXCLUDE_NAME_RE` (regex, bukan daftar). (2) `NOTABLE_KW` cocok dgn **NAMA TEMPLATE nuclei di dalam file indeks** → `references-index.json` dapat skor **HIGH "333 notable"** tanpa satu request pun; aturan: kandidat butuh **respons**, bukan kata kunci — line harus `(status HTTP + URL)` ATAU marker vuln, dan **path file bukan respons**. (3) agregator menilai **output-nya sendiri** → duplikat + dokumen yang sudah disaring masuk lagi; pola sama dgn gate-menilai-echo. Terukur: **151 → 2 kandidat** (dua-duanya bukti nyata). |
| **laporan NEGATIF: jujur tapi belum layak kirim** (operator minta review; 851 B, tak ada alasan per-kandidat & tak ada ringkasan cakupan) | `references/negative-report-substance.md` — RULE 41 menjamin hasil negatif **ADA**; ini soal membuatnya **BERGUNA**. Seluruh data yang kurang sudah ada di disk (`review-candidates.json`, `gated.json`, `*-usage.json`, `asset-coverage.json`). Bentuk wajib: hasil → sebab → **cakupan** (per kelas, angka + nama artefak) → **kandidat & alasan tiap penolakan** → **batas/N-A**(dikelompokkan per alasan) → indeks bukti. `N/A` **bukan** cakupan. **+ §"Consumer↔producer contract"** — dua mis-read yang gagal SENYAP saat membangun laporan dari artefak: (a) field NAME salah (`reasons` list ditulis producer, dibaca `reason` scalar → tiap baris jadi `(no reason recorded)`, seolah gate tak pernah menjelaskan); (b) container SHAPE salah (`len(dict)` menghitung KEY, bukan baris → laporan negatif mencetak `cleared validation 4` padahal **0** = over-claim lewat pintu belakang). Baca output producer dulu (`print(list(json.load(...)[0].keys()))`), sadari bentuknya, dan assert funnel monoton-turun sebelum menulis. |
| **0B/0C/0D — setiap kali mengubah gate, manifest, atau classifier status tool** | `references/track-aware-gates-and-run-lifecycle.md` |
| **sebelum menyimpulkan sebuah run "mati" / berhenti di tengah** | `references/track-aware-gates-and-run-lifecycle.md` §7 — **BUKTIKAN DULU run-nya memang berakhir**: tanpa baris `=== EXIT ===` ia masih JALAN. Log yg tak bertambah saat disampling (apalagi lewat `\| tee`) bukan mayat. §7 versi lama pernah salah menyimpulkan "dibunuh RAM" padahal run-nya SELESAI dan gate yang memblokir — jangan ulangi |
| **gate FAIL lalu REWORK, atau jumlah kegagalan NAIK antar attempt** | `references/track-aware-gates-and-run-lifecycle.md` §8 — REWORK bisa menghapus artefak yang ia sendiri butuhkan; bandingkan HIMPUNAN kegagalan, bukan cuma jumlahnya |
| **Windows / MSYS** (＋ **heredoc menulis ulang KONTEN**: escaped-newline di dalam f-string jadi baris baru sungguhan → `SyntaxError: unterminated f-string`; pakai `chr(10)` lalu `py_compile` setelah generate — **PowerShell inline di dalam heredoc gagal SENYAP**: keluaran kosong/exit 1 ≠ "tak ada proses", pakai `wmic … /format:csv` + `csv.reader`, urutan kolom `Node,CommandLine,Name,ProcessId`) — jebakan path & invokasi tool, **termasuk saat MENULIS run-script** (heredoc tak dikutip = tool jalan tanpa target tapi rc=0), dan **mengutip SEGMEN path = spasi hilang** (`/d/data/"hermes/bug-bounty"/x` → tree hantu; gejala: `No such file or directory` pada file yang jelas sudah ditulis) | `references/msys-path-and-tool-invocation-traps.md` |
| **sebuah fix yang sudah kamu terapkan "tidak berefek"** / dua skill berbeda soal perilaku satu tool | `references/toolkit-copy-drift-and-bundle-sync.md` — toolkit ada **3 salinan**; bundle berisi `finding_gate.py` **v1 fail-OPEN** sementara live **v2 fail-closed**, dan SKILL.md menyuruh menjalankan yang BASI. `%LOCALAPPDATA%\hermes\scripts\` = sumber kebenaran; jalankan `bundle-sync.py sync` di sesi yang sama dgn tiap edit |
| **track web3 ATAU setiap kali gate memblokir** — enforcement track-aware + jebakan yg bikin pipeline "COMPLETE" padahal tidak menganalisis apa pun | `references/track-aware-enforcement-and-pipeline-traps.md` |
| **vendor larang scanner** | `references/vendor-forbidden-scanner-adaptation.md` |
| **resume antar-sesi** | `references/multi-session-resume-2026-09-26.md` |
| **patch pipeline "sudah saya pasang" tapi perilakunya tak berubah** — blok berkunci `if path.exists()` (path salah tulis → tak ada efek, tak ada error, `py_compile` lolos) | `references/gate-rederive-tz-and-fuzz-only-2026-10-12.md` §1b — bukti tunggal = **grep baris log milik patch itu di run berikutnya**; ambil path dari blok tetangga yang sudah benar; **loop/penolong pengaman membuat patch tampak "terverifikasi" padahal bukan** |
| **target SPA / host-role `static-site`** — `deep-recon` hanya mengisi 4–6 URL sehingga 15 varian + 15 business-logic + 52 reference menembak app-shell | `references/gate-rederive-tz-and-fuzz-only-2026-10-12.md` §7 — ekstrak endpoint API dari bundle (`main.<hash>.js`, `gen-cfg.js`) lalu **append ke `urls.txt`** (tuas tunggal; C2/C3/C4/C5/C6 membaca `urls.txt` saat step-nya mulai → tak perlu restart). Cek liveness host dulu — `exchange.`/`pro.` ternyata 302 ke apex, bukan produk |
| **"failure that pretends to be a result" — INDEX keluarga** (hollow coverage dari marker `[200]` di `urls.txt`/`live.txt` · scope leak payload ke host pihak-ketiga · ledger stale karena `--derive` jalan SEBELUM closure manifest menulis `tools-usage.json` · **run bilang `COMPLETE`/`33/33` tapi report lebih tua dari bukti → fase-complete itu CACHE, fix producer TIDAK menggugurkannya; paksa fase hilir jalan ulang dengan menulis ulang `completed_phases`+`current` — backup + `_QUARANTINE/manifest.json` dulu, jangan hapus state**) | `references/coverage-lies-and-report-quality.md` |
| **operator kirim lanjutan singkat tanpa sebut target** ("nggak ada temuan ya / teruskan cek sampai tuntas") di sesi baru — rekonstruksi engagement dari disk (state.db `sessions`+`messages`, mtime `_progress/`, `TRIAGE.md`, `findings.json`) lalu `deep-audit-mode.py guard` sebagai alat-kebenaran tercepat; `guard BLOCKED (tools-usage.json not found)` = BUKTI klaim "0 temuan" sebelumnya belum pernah ter-gate | `references/engagement-identification-from-terse-operator-message.md` |


## FULL RULE INDEX (references/rules/) — muat sesuai fase


Setiap aturan yang tidak inline di bawah tersimpan di sini. **0C WAJIB memuat ulang semua ini** (rule + payload/cookbook/exploit-book) sebelum mengklaim COMPLETE.

| file | section |
|---|---|
| `01-section.md` |  |
| `02-rule-0-rules-dont-force-anything-scripts-do.md` | ⛔ RULE 0: RULES DON'T FORCE ANYTHING — SCRIPTS DO |
| `03-rule-0-honest-reporting-no-overclaiming.md` | ⛔ RULE 0: Honest Reporting — NO Overclaiming |
| `04-rule-0c-impact-first-not-volume.md` | ⛔ RULE 0C: Impact-First — Not Volume |
| `05-rule-0b-dont-skip-dont-delete-complete-missing-items.md` | ⛔ RULE 0B: Don't Skip, Don't Delete — Complete Missing Items |
| `06-rule-1-exploit-first-mindset.md` | ⛔ RULE 1: Exploit-First Mindset |
| `07-rule-2-loading-executing.md` | ⛔ RULE 2: Loading ≠ Executing |
| `08-rule-2b-use-the-right-tool-not-just-curl.md` | ⛔ RULE 2b: Use the RIGHT tool — not just curl |
| `09-pipeline-change-checklist-run-this-after-every-edit-to-a-pip.md` | Pipeline change checklist — run this after EVERY edit to a pipelin |
| `10-rule-30-scope-never-ask-the-user-auto-detect-else-allow-all.md` | ⛔ RULE 30: SCOPE — NEVER Ask the User (Auto-Detect, Else Allow-All |
| `11-rule-31-patch-verify-loop-never-trust-a-patch-succeeded.md` | ⛔ RULE 31: Patch-Verify Loop — Never Trust a Patch "Succeeded" |
| `12-rule-32-multi-topic-parallel-audits-isolation-the-other-topi.md` | ⛔ RULE 32: Multi-Topic Parallel Audits — Isolation & the "Other To |
| `13-rule-2f-long-scans-go-to-the-background-not-into-subagents.md` | ⛔ RULE 2f: LONG SCANS GO TO THE BACKGROUND — NOT INTO SUBAGENTS |
| `14-rule-3-timeout-retry-not-skip.md` | ⛔ RULE 3: Timeout = Retry, Not Skip |
| `15-rule-4-reload-after-compression.md` | ⛔ RULE 4: Reload After Compression |
| `16-rule-5-verification-log-before-complete.md` | ⛔ RULE 5: Verification Log Before COMPLETE |
| `17-rule-6-max-15-context-per-finding.md` | ⛔ RULE 6: Max 15% Context Per Finding |
| `18-rule-7-self-check-every-5-tool-calls.md` | ⛔ RULE 7: Self-Check Every 5 Tool Calls |
| `19-rule-8-track-every-ref-file-execution.md` | ⛔ RULE 8: Track Every Ref File Execution |
| `20-rule-9-proven-theoretical-never-overclaim.md` | ⛔ RULE 9: Proven ≠ Theoretical — NEVER Overclaim |
| `21-rule-10-minimum-severity-threshold-for-reporting.md` | ⛔ RULE 10: Minimum Severity Threshold for Reporting |
| `22-rule-11-craft-cms-specific-testing.md` | ⛔ RULE 11: Craft CMS Specific Testing |
| `23-rule-15-user-mandated-audit-hardrules-all-7-non-negotiable.md` | ⛔ RULE 15: User-Mandated Audit Hardrules (ALL 7 — NON-NEGOTIABLE) |
| `24-rule-16-memory-format-compact-no-numbers-no-emojis.md` | ⛔ RULE 16: Memory Format — Compact, No Numbers, No Emojis |
| `25-rule-17-solidity-tool-windows-quirks.md` | ⛔ RULE 17: Solidity Tool Windows Quirks |
| `26-rule-17b-by-design-filter-dont-report-intentional-behavior.md` | ⛔ RULE 17b: By-Design Filter — Don't Report Intentional Behavior |
| `27-rule-18-anti-premature-classification-mandatory.md` | ⛔ RULE 18: Anti-Premature-Classification (MANDATORY) |
| `28-rule-19-minimum-3-bypass-attempts-before-blocked-claim.md` | ⛔ RULE 19: Minimum 3 Bypass Attempts Before "Blocked" Claim |
| `29-rule-28-pipeline-output-findings-triage-before-reporting.md` | ⛔ RULE 28: Pipeline Output != Findings — Triage Before Reporting |
| `30-rule-33-resume-an-engagement-from-its-log-never-re-derive-sc.md` | ⛔ RULE 33: Resume an ENGAGEMENT from its log — never re-derive sco |
| `31-rule-34-when-there-is-no-fuzzable-url-the-authenticated-api-.md` | ⛔ RULE 34: When there is NO fuzzable URL — the authenticated API h |
| `32-rule-35-scanner-output-triage-the-fp-classes-that-keep-burni.md` | ⛔ RULE 35: Scanner-output triage — the FP classes that keep burnin · **estate-scan triage + re-verifikasi** (contoh terukur: nuclei 42 host/3.546 template/282k request → 651 match = 624 info/7 low/0 high; wajib split per severity+template-id; **re-request tiap hit non-info** karena temuan bisa sudah hilang — `expired-ssl` di host yang deployment-nya sudah dihapus = bukan temuan baru; host kedua dengan cacat SAMA = addendum ke laporan yang sudah terkirim, bukan laporan baru; **aturan kalibrasi: derivable ≠ disclosure** — endpoint "bocor" tanpa auth yang isinya bisa diturunkan/publik = informational → DROP (terukur: `/api/v1/identity` balas 200 untuk alamat apa pun + tanpa rate limit, tapi `ownerServers()` on-chain = 0 dan alamat PS yang dikembalikan tak punya code → record DERIVED, bukan kebocoran infrastruktur); probe auth-vs-validasi pakai body INVALID (`422` field-required = validasi jalan, `401/403` = ada gerbang auth) supaya tak pernah menembak write nyata) → `references/estate-scan-triage-and-reverification.md` |
| `33-rule-36-all-tools-all-variants-on-an-auth-gated-target-curlp.md` | ⛔ RULE 36: "All tools, all variants" on an AUTH-GATED target — cur |
| `34-mechanical-enforcement.md` | ⛔ MECHANICAL ENFORCEMENT |
| `35-rule-12-execute_code-shutil-not-persistent.md` | ⛔ RULE 12: execute_code shutil Not Persistent |
| `36-rule-13-target-surface-prioritization-high-value-first.md` | ⛔ RULE 13: Target Surface Prioritization — High-Value First |
| `37-rule-14-cloudflare-bot-protection-dont-fake-results.md` | ⛔ RULE 14: Cloudflare Bot Protection — Don't Fake Results |
| `38-rule-20-pipeline-integrity-audit-run-when-user-asks-cek-semu.md` | ⛔ RULE 20: Pipeline Integrity Audit (run when user asks "cek semua |
| `39-rule-25-references-must-be-used-not-just-loaded-c6.md` | ⛔ RULE 25: References MUST Be USED — Not Just Loaded (C6) |
| `40-rule-24-candidate-review-sop-temuan-candidate-3x-cek-lowhigh.md` | ⛔ RULE 24: Candidate Review SOP — Temuan = CANDIDATE, 3x Cek, Low→ |
| `41-rule-26-poc-repos-extract-techniques-not-just-execute-1-c6b.md` | ⛔ RULE 26: PoC Repos → Extract TECHNIQUES, Not Just Execute 1% (C6 |
| `42-rule-27-multi-session-resume-per-phase-state-never-restart-f.md` | ⛔ RULE 27: Multi-Session Resume — Per-Phase State, Never Restart f |
| `43-rule-23-unified-pipeline-hard-won-fixes-findings-quality-bar.md` | ⛔ RULE 23: Unified Pipeline Hard-Won Fixes + Findings Quality Bar |
| `44-rule-21-poc-execution-plan-generation-fix-windows-path-resol.md` | ⛔ RULE 21: POC Execution Plan Generation Fix (Windows path resolut |
| `45-rule-22-tool-detection-on-windows-use-shutilwhich-explicit-p.md` | ⛔ RULE 22: Tool Detection on Windows — Use shutil.which + Explicit |
| `46-per-tool-timeout-values-tool_routerroute_and_run-defaults.md` | Per-Tool Timeout Values (tool_router.route_and_run defaults) |
| `47-rule-36-evm-static-tool-severity-labels-are-not-findings-tri.md` | ⛔ RULE 36: EVM static-tool SEVERITY LABELS ARE NOT FINDINGS — tria |
| `48-rule-37-a-delegated-subagent-that-times-out-at-600s-has-stil.md` | ⛔ RULE 37: A delegated subagent that times out at 600s has still W |
| `49-rule-38-enumerated-hosts-and-spa-routes-need-a-differential-.md` | ⛔ RULE 38: Enumerated hosts and SPA routes need a DIFFERENTIAL — m |
| `50-config-requirements.md` | Config Requirements |
| `51-companion-reference-poc-technique-atlas-additive-never-overr.md` | Companion Reference — `poc-technique-atlas` (additive, never overr |

---

