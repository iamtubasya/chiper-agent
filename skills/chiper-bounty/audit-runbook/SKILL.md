---
name: audit-runbook
version: 1.0.0
author: adapted from toma's SOP (bbskills-pack-20261015)
description: Enforced audit SOP — phases, differential, ledger.
metadata:
  hermes:
    tags: [bug-bounty, methodology, pipeline, sop, differential]
---

# Audit Runbook — enforced SOP (adapted 2026-10-16)

**Provenance:** diadaptasi dari SOP "toma" (bbskills-pack-20261015), phase-label-nya
di-remap ke pipeline `audit-pipeline-orchestrator.py` milik operator (0A→0F) supaya
dua sistem tidak tabrakan. Konten inti (3 hukum, tabel evidence, account factory)
dipertahankan apa adanya.

## ⚠️ Mapping WAJIB — jangan pakai label fase dari sumber asli

| Fase sumber (toma) | Fase kita (pipeline) | catatan |
|---|---|---|
| 0A Scope Gate | **0A** + 0A-SCOPE | sama |
| 0B Recon | **0B** | sama |
| 0C Hunt per class | **0C (C1..C6b)** | sama |
| **0D Deep-Dive** | **bagian dari 0C** (`0C-DEEP`) | ❌ **0D kita = verify-tool-usage, BUKAN deep-dive** |
| *(tidak ada)* | **0D verify-tool-usage** | usage-JSON = gate keras (auto-rework) |
| 0E Candidate Review | **0E** | = RULE 24 |
| 0F Report | **0F** | sama |

## Three laws

1. **Differential testing.** Setiap cek membanding dua state: valid vs invalid,
   auth vs anon, user A vs user B, before vs after. Satu response = bukan apa-apa;
   **SELISIH = temuan**. (Tekan ini yang nangkep heise.de H-01.)
2. **Ordered.** Fase berurutan, punya entry/exit criteria — no skipping ahead.
3. **Verified usage.** Tiap skill/tool wajib ninggalin evidence di disk.
   Tanpa bukti = tidak dikerjakan. "Skip" hanya boleh dengan alasan N/A tertulis.

- **`geo-block-proxy-ops`** — lewati geo-block/VPN saat mendaftar akun uji: CloakBrowser (proxy+geoip+timezone+locale konsisten), WARP, tangga eskalasi, dan disiplin etika (data sendiri, jangan identitas palsu). Skrip: `scripts/geo_session.py`. Fase 0A (policy) → 0B (level blokir) → 0C (daftar).

- **`signup-block-ops`** — tangga eskalasi saat pendaftaran akun uji terblokir (email verif → CAPTCHA → SMS → invite → IP/rate → approval): 7 langkah, 3 percobaan beda sebelum N/A. Fase 0A → 0B → 0C.

- **`hint_store.py`** — koreksi operator jadi ARTEFAK persistens (konsep Cairn). Hint global + per-target; gate memblokir aksi yang bertentangan (kill proses, skip tool). Dibaca orchestrator di awal pipeline. Tambah: `python hint_store.py add --content "..." --action protect_process --pattern X`

## Phase 0A — SCOPE GATE (before any request)

**Wajib baca `redteam-mindset` lebih dulu** — safe hands (defend-aware) + exploiter's
head (pantang menyerah) harus jalan bersamaan sebelum probe pertama.

- Baca `security.txt` → record Contact, Policy, Expires. Buka Policy/Disclosure.
- Record: tipe program (bounty/VDP/none), reward, scope allow/blocklist,
  safe-harbor sentence, rules.
- Tidak ada scope tertulis → **jangan asumsi allow-all**: authorization = artifact,
  bukan assertion. Tanpa artifact → passive-only + inquiry program, lalu target berikut.
  *(Cross-ref: `recon-scope-triage` — soft-404 & ownership triage.)*
- **Scope yang DIENUMERASI ≠ wildcard.** Banyak VDP modern menulis scope sebagai daftar host
  eksplisit ("the docs.proton.me web app", "api.protonvpn.ch") alih-alih wildcard. Konsekuensinya:
  host yang resolve tapi TIDAK disebut = OUT, walaupun satu domain dengan yang in-scope dan
  walaupun terlihat seperti produk yang sama. Contoh nyata (Proton 2026-10-25): `meet.proton.me`,
  `sheets.proton.me`, `verify.proton.me` resolve & 200, `scribe.proton.me` NXDOMAIN — keempatnya
  tidak ada di daftar, jadi tidak disentuh. Tulis di COVERAGE sebagai `OUT-OF-SCOPE (not listed in
  VDP)` supaya tidak terbaca sebagai "belum diuji".
  - Subdomain hasil enumerasi (`subfinder`) juga hanya **intel**: masuk daftar scan hanya kalau
    cocok dengan baris scope. 150 subdomain ditemukan ≠ 150 target sah.
  - Sebaliknya, kalau policy memakai wildcard (`*.x.com`), **apex** tidak otomatis in-scope —
    lihat `audit-pipeline-operations` untuk bentuk argumen `--scope` yang benar.
- Evidence: `PHASE0.md` — pemahaman bisnis: fund flow, data flow, user roles,
  trust boundaries, hunting angles turunan dari flow itu. Tanpa PHASE0.md = belum boleh hunting.
- Exit: `PHASE0.md` ada + scope verdict tertulis.

- **`attack-flows`** — 3 alur end-to-end siap jalan: (1) dangling domain → takeover → OAuth/ATO, (2) zombie/undocumented API → authz bolong → database/produksi, (3) polimerisasi temuan (1 celah → pola → klasifikasi). Tiap langkah sebut skill + depth target. Fase 0B → 0C → 0E → 0F.

- **`attack-flows-db-web3`** — 2 alur tambahan: (4) menyerang lapisan DATABASE lewat 8 vektor (SQLi/NoSQLi/IDOR/GraphQL/gRPC/actuator/datastore/file leak) sampai RCE, (5) web3: bytecode → decompile → analisa 12 kelas bug → PoC Foundry. Fase 0B → 0C → 0E → 0F.

## Phase 0B — RECON (ordered; tiap langkah meninggalkan file)

| # | Action | Tools | Evidence |
|---|---|---|---|
| 1 | Subdomain enum | subfinder, amass, crt.sh | `subs.txt`, `live.txt` (httpx) |
| 2 | URL/JS harvest | katana, gau, waybackurls | `urls.txt`, `js.txt` |
| 3 | Endpoint extraction | grep JS `/api/`, fetch paths | `endpoints.txt` |
| 4 | Vuln scan baseline | nuclei (template relevan) | `nuclei.txt` |
| 5 | Exposed files | ffuf `.git`/`.env` paths — **sha-compare every hit against a random nonsense path on the same host first.** SPA front-ends answer 200 with a byte-identical index for `.env`, `.git/config`, `actuator/*`, `Dockerfile` and `.well-known/*`; `-fc 404` does not save you because the SPA serves 200, and a real 404 only appears under `/api/*`. Measured 2026-10-25: 7 hosts × 80 words → 66–70 "hits" per host, every one a soft-404. | `exposed/` |
| 6 | Smuggling probe | `smuggler` (di `~/go/bin`, PATH) — atau honest N/A | `smuggling.txt` |
| 7 | Scope ranking | **`scripts/scope_checker.py`** (pengganti `scope_narrower.py` sumber) | `targets-ranked.txt` |

**Ukuran run scanner (terukur 2026-10-31):** `-tags cve` sendirian = 4.583 template → puluhan ribu
request, dan hampir semua program minta jangan. Fingerprint dulu, lalu jalankan tag yang cocok
(`aspnet,iis,dotnet,angularjs,jquery` = 45; `exposed-panels,backup,swagger,graphql` = 88). Run yang
terlalu lambat: **kill dan ganti dengan run terbatas yang benar-benar selesai** — jangan laporkan
sweep parsial sebagai coverage. `-stats` + log `Requests: X/Y (100%)` adalah artefak yang membuat
klaim "0 temuan" jujur.

Exit: semua file ada, atau N/A-with-reason tercatat.

**Lanjutan wajib:** buka `attack-surface-index` — petakan setiap fitur yang ditemukan
recon ke probe pertama per kelas (RCE / IDOR-BOLA / ATO). Satu baris cocok = probe
wajib sebelum kelas itu boleh ditandai N/A.

- **`hunt-data-exposure`** — gejala "database bocor dari endpoint": routing ke 8 mekanisme, probe per datastore, disiplin bukti (count + 1 record, redaksi PII). Fase 0C-C2/C3.

- **`exploit-depth`** — tangga L0→L5: setiap sinyal (200/403/500/timing) wajib diturunkan sampai impact terbukti. Termasuk tangga eskalasi per kelas (403→6 bypass, 500→oracle, 200 kosong→headers/timing) dan aturan adjacent-gate (1 temuan → uji semua sejenis). Fase 0C + 0E + 0F.

- **`exploit-chain-graph`** — 57 kelas: primitif → teknik pengembangan → eskalasi ke skill mana → depth target. Setiap sinyal positif WAJIB dibuka graf ini sebelum kelas ditutup. Fase 0C + 0C-C7 (chain_builder) + 0E.

- **`lead_escalation.py`** (C7-E4) — kembangkan tiap kandidat sampai batas paling dalam: kelas → primitif → eskalasi → probe konkret (ato/rce/data-exposure/idor/auth-bypass/business-logic). Terukur batch1: 122 kandidat → 21 unik → rencana eskalasi. Tanpa ini, sinyal positif berhenti di 'ada yang menarik' → 0 lolos 0E. Metrik: `verify_claims.py` (fase, tool coverage, kelas, verdict jujur).

## Phase 0C — HUNT (per kelas, urut nilai bisnis)

**Pra-jual WAJIB:** buka `howtohunt-checklist` dulu — pastikan surface kelas itu ADA
di target. Kalau tidak ada, catat `N/A: <alasan>` di LEDGER (jangan skip diam-diam),
baru lanjut ke kelas berikutnya. Tiap kelas: load skill → jalankan differential → simpan evidence.

| Class | Skill | Core differential |
|---|---|---|
| Auth/session | hunt-auth-bypass, hunt-session | valid vs invalid creds; pre vs post-login; concurrent session |
| Password reset | hunt-forgot-password | valid vs invalid email (response + timing); token entropy/expiry |
| IDOR/BOLA | hunt-idor — **dua identitas dari Account Factory SOP** | user A object vs user B replay |

**Detail wajib untuk baris di atas:** `references/authz-negative-proof.md` — cara membuktikan NEGATIF
pada authz/kripto (objek nyata vs endpoint kosong, ID tetangga, oracle info-only, matriks input SRP,
jebakan "422 ≠ rate-limit", kuota yang teksnya menipu).
| Price/logic | hunt-business-logic | tampered vs original (server recompute?) |
| Paywall/entitlement | (0C-DEEP) | anon vs free vs paid body |
| XSS stored | hunt-xss | canary payload vs plain text |
| SSRF | hunt-ssrf | OOB callback vs no-callback |
| SQLi | hunt-sqli | true vs false boolean; time differential |
| OAuth/OIDC | hunt-oauth | state/nonce binding; redirect_uri manipulation |
| Rate limit | hunt-brute-force | burst vs single; seed bagus di bawah load |
| GraphQL | graphql-audit | persisted vs ad-hoc; introspection on/off |
| API misconfig | hunt-api-misconfig | anon vs authenticated role boundary |
| AI/LLM endpoint (SSRF via tool schema) | hunt-llm-ai → `references/tool-schema-ssrf.md` | `$ref`/`$schema`/`image_url` pointing at OAST vs benign URL, WITH the tool object's mandatory `description` field; callback source-IP vs own egress |
| PHP runtime (CVE-2026-109618/9) | **hunt-php2shell** | OOM multipart fatal vs clean request; PHPSESSID value vs `[a-zA-Z0-9,-]{26}` charset (leaked heap = non-conforming bytes) |

**Tambahan untuk target WEB3 (pakai kalau scope on-chain; kalau tidak ada surface-nya,
catat `N/A: <alasan>` — lihat `howtohunt-checklist` kelas 11-19):**

| Class | Skill | Core differential |
|---|---|---|
| Smart account / modular authz | hunt-aa-modular | `installModule` dengan address attacker vs allowlist registry |
| Signed approval replay | hunt-permit2-signature | signature identik di-submit dua kali / di fork / recipient berbeda |
| AMM hooks / pool | hunt-amm-hooks | pool dengan hook attacker vs hook terdaftar; fee mutasi mid-swap |
| Restaking / LRT | hunt-restaking-lrt | slash dengan attestation fabric vs on-chain-verifiable task |
| Intent / solver / attestor | hunt-intent-settlement | `solve()` dengan solver arbitrary vs allowlist |
| Oracle / sequencer uptime | hunt-oracle-l2 | uptime down sebelum grace vs sesudah grace; `updatedAt` lampau |
| Vault inflation | hunt-vault-inflation | mint 1 wei → donate → victim deposit; single-party vs multi-party |
| Upgradeability / diamond | hunt-diamond-proxy | `diamondCut`/`upgradeTo` dari non-owner; selector duplikat |

**Aturan web3 di 0C:** setiap kelas wajib lewat `onchain-finding-verification` (fork PoC +
attacker P&L + negative control) sebelum naik ke 0E. Ledger web2 (sqlmap/dalfox/ffuf/nuclei/
katana) adalah **N/A** untuk scope contract-only — bukan "tidak dijalankan".

Exit: tiap kelas punya ledger row (tested + evidence, atau alasan N/A).

## Phase 0C-DEEP — DEEP-DIVE (bagian dari 0C, BUKAN fase terpisah)

Pilih 1–2 flow nilai tertinggi (money flow, auth). Per flow:
1. Baca SEMUA JS bundle flow itu; daftar tiap endpoint + parameter.
2. Map state machine (guest → registered → paid → admin); test tiap transisi,
   terutama downgrade & langkah yang dilewati.
3. Invariant checklist: price/quantity/currency/discount tamper, race resource
   terbatas, replay callback/webhook, entitlement confusion.
4. Chain pass: masukan primitive terkonfirmasi → goal impact;
   tandai tiap link **PROVEN / PARTIAL / UNPROVEN** (manual; `chain_builder.py`
   hanya kalau tersedia — jangan gagal kalau gak ada).

Exit: `deepdive/<flow>/` berisi endpoint map + invariant test log.

## Phase 0C-C7 — AGGREGATE + CHAIN (penutup 0C, sejak 2026-10-18)

**Harus di EKOR 0C, setelah C1..C6b selesai** — karena tugasnya mengumpulkan kandidat
dari SELURUH sub-fase, lalu mengembangannya jadi chain attack. Ditaruh di tengah 0C
akan menghasilkan chain parsial; ditaruh di 0E membuat 0E campur (eksploitasi +
review).

Urutan: `aggregate-findings.py` → `weaponize-gate.py` (chain_class HEAD/LINK/
STANDALONE + severity + weaponization) → `chain_builder.py` (susun chain, tiap link
**PROVEN / PARTIAL / UNPROVEN**).

Output: `findings.json` · `weaponized-findings.json` · `chains.json`.

## Phase 0D — VERIFY (usage-JSON = sumber kebenaran)

Pipeline menulis **usage-JSON** per step; `verify-tool-usage` meng-block kalau
ngawur (tulis-di-akhir = HARD BLOCK). Ini gate keras utama.
`LEDGER.md` (tabel `| Phase | Skill/Tool | Invoked? | Evidence file | Result |`)
= tampilan manusia yang dirender dari usage-JSON — **bukan sistem paralel**.
Invoked?=yes wajib punya path evidence nyata; Invoked?=no wajib alasan N/A.
Laporan akhir: "X/Y skill dipakai" + daftar semua N/A beserta alasannya.

### Aturan ledger (append-only, sejak 2026-10-18)

`tools-usage.json` adalah **ledger kumulatif**, bukan snapshot. Rework TIDAK lagi
menimpa riwayat:

| kelas rework | pemicu | perilaku |
|---|---|---|
| **REWORK-EXTEND** | validasi ulang kandidat, verifikasi tambahan, permintaan baru | **APPEND** — dihitung pekerjaan berbeda, bukti bertambah |
| **REWORK-ERROR** | fail, stall, hung, timeout, exit≠0 | boleh reset entri fase itu — run lama tidak valid |

Audit trail lengkap per attempt: `tools-usage.attempts.json`
(ts, phase, reason, class, entries, ledger_total). Helper: `scripts/usage_ledger.py`.

Efek: audit yang butuh 3 putaran validasi menghasilkan **3× bukti**, bukan 1 bukti
yang ketimpa. CHECK 12 jadi lebih kuat, bukan lebih lemah.

## Phase 0E — CANDIDATE REVIEW (RULE 24)

**Pra-jual WAJIB (sejak 2026-10-26):** sebelum CEK-1, buka
**`report-gotchas`** → `references/class-gotchas.md` pada kelas yang diklaim
kandidat itu. Cek PoC terhadap **minimum proof** kelas tersebut. Kalau belum
memenuhi → kandidat BELUM jadi temuan; tulis apa yang akan membuktikannya,
jangan lanjut ke 7-Question Gate. Skill ini aditif: ia punya bar proof
per-kelas + detektor AI-slop; `triage-validation` tetap punya keputusan
(7-Question Gate, NEVER SUBMIT list, chain table, CVSS).

Tiap temuan = CANDIDATE. Setelah semua fase: review satu-satu, severity naik.
- **CEK-1 VALID**: bug nyata? Buang by-design / spekulatif / info-only.
- **CEK-2 REPRODUCIBLE**: evidence file ≥100B. Tidak ada file = REJECT.
- **CEK-3 IMPACT**: siapa dirugikan, apa yang hilang? Tanpa sinyal dampak = REJECT.
Hanya READY → draft + PDF. Evidence: `CANDIDATES.md` per verdict.
*(Cross-ref `triage-validation` 7-Question Gate + `audit-execution-discipline` RULE 24/27.)*

### RULE 24b — POC ≠ TEMUAN (dikoreksi operator, 2026-10-25)

Scanner mengeluarkan "POC" per-(URL,parameter), bukan per-vulnerabilitas. Jangan pernah menjumlah
POC sebagai jumlah temuan. Kesalahan nyata yang ditolak operator: melaporkan "3 POC dalfox" sehingga
terbaca sebagai 3 temuan, padahal ketiganya satu parameter yang sama dan semuanya **false positive**,
dan temuan sebenarnya cuma 1.

Aturan hitung yang harus dipakai di status/laporan:
```
TEMUAN   : <jumlah kelas/vuln unik yang lolos 0E>
POC/alert: <jumlah mentah dari scanner>  →  sebut eksplisit "N POC, M false positive"
NEGATIF  : <jumlah kelas yang diuji & terbukti bersih, dengan file bukti>
UNTESTED : <jumlah kelas yang tidak bisa diuji + alasannya>
```
Kalau satu parameter memunculkan 3 POC, tulis **"3 POC pada 1 parameter"**, bukan "3 temuan".
Sebelum menyebut angka "temuan", jalankan: apakah tiap item punya impact berbeda dan lolos CEK-1/2/3?
Kalau tidak, itu satu kandidat atau nol.

### RULE 24c — Disproof wajib sebelum membuang ATAU menerima scanner hit

Tiga pola yang terbukti (2026-10-25, Proton) dan harus dipakai ulang:

| Scanner | Klaim | Cara disprove | Hasil nyata |
|---|---|---|---|
| **dalfox** | `[POC] ...?ref=xss` | kirim canary + payload XSS + tanpa-param; bandingkan **panjang body** dan cari refleksi di **body & header**; cek bundle untuk sink DOM | body identik 8205 B di semua varian, `ref` hanya `params.append()` ke URL redirect → FALSE POSITIVE |
| **ffuf** | `.env`, `.git/config`, `actuator/*` = 200/403 | ambil SHA-256 body hit, bandingkan dengan path acak (`/zz-nonexistent-<rand>`) | semua identik = **soft-404 SPA catch-all**; 404 asli hanya di `/api/*` |
| **sqlmap/ghauri** | "not injectable" | cek status HTTP: `400`/`401` = request tidak pernah valid → **hasil tidak sah**, ulangi dengan header wajib (`Accept`, `x-pm-appversion`, cookie `AUTH-<uid>`) | run pertama 400 → dibuang; run dengan header benar baru boleh disebut NEGATIVE |

Aturan: **hasil negatif hanya sah kalau request-nya diterima server.** `400`/`401`/`403` di seluruh
run = bukti tooling salah, bukan bukti target aman. Dan counterpart: klaim positif hanya sah setelah
disproof manual — jangan kirim "CONFIRMED" milik scanner ke laporan.

### RULE 24e — Authz negatif butuh identitas penyerang yang BERKONTEKS (terukur 2026-10-31, Scribble Maps team app)

Gejala: uji BOLA lintas-tenant dari akun B dapat balasan `200` berisi **HTML halaman login** (bukan
JSON, bukan 403). Itu **bukan** "authz menolak" — itu "sesi tidak punya konteks tenant", dan kamu tidak
bisa membedakan keduanya dari respons saja.

Pola yang benar (4 langkah, jangan dipotong):
1. Beri akun penyerang **konteks sah dulu** — di sini: buat team sendiri untuk akun B, supaya sesinya
   punya tenant aktif.
2. Ulangi request yang sama persis.
3. Bandingkan dengan **kontrol owner** (akun A pada record-nya sendiri) yang harus balik JSON nyata —
   ini membuktikan endpoint-nya hidup dan bukan routing yang salah.
4. Baru simpulkan: balasan HTML/guard + record tidak berubah = authz menolak (negatif yang sah).

Tanpa langkah 1–3, kalimat "cross-tenant ditolak" adalah klaim yang tidak terbukti, dan BOLA akan
salah ditandai NEGATIF.

### RULE 24f — Dua jebakan probing yang memakan waktu (terukur 2026-10-31)

- **Nilai query param WAJIB di-URL-encode.** Password `SmTest#2026` dikirim sebagai
  `?password=SmTest#2026` → karakter `#` memulai *fragment*, server hanya menerima `SmTest` → 401 palsu
  yang terbaca seperti "password salah". Pakai `urllib.parse.quote(v, safe="")`. Gejala khas: parameter
  yang "benar" selalu ditolak sementara nilai lain diterima.
- **sqlmap/ghauri kena WAF = run tidak sah; ulangi dengan header browser.** Run pertama 87× HTTP 403 →
  pesan akhir "not injectable" **dibuang**. Ulangi dengan `--random-agent --tamper=space2comment` plus
  `User-Agent` Chrome eksplisit → 0×403, baru boleh disebut NEGATIVE. Yang membedakan adalah **jumlah
  403 di log**, bukan pesan penutup sqlmap (perluasan RULE 24c).

### RULE 24d — "Tidak bisa" butuh tabel, bukan kalimat
Kalau menyatakan sesuatu BLOCKED (signup, akses, tool), sertakan tabel pendekatan + akar masalah
teknis. Satu percobaan gagal bukan blocked. Lihat `signup-block-ops` §0b untuk format yang diminta
operator.

## Phase 0F — REPORT

Satu temuan = satu draft email + satu PDF PoC lengkap. Draft tetap UNSENT kecuali
operator menyuruh kirim; inquiry program (tanya scope/status) pre-authorized.
*(Cross-ref `report-writing`, `bug-bounty-disclosure`.)*

**Kalau vendor punya portal submit (bukan email):** baca
`references/portal-submission-and-browser-automation.md` sebelum menyentuh endpoint submit-nya.
Isinya: resep Playwright + Chrome asli untuk lolos Turnstile, penanganan dialog
"logged in elsewhere", pola menahan browser terbuka untuk operator submit manual, dan —
paling penting — **jangan spam probe validasi di endpoint submit** karena itu memicu throttle
per-IP (429) yang kemudian memblokir submission asli. Satu payload tidak lengkap sudah cukup
untung mengungkap nama field berikutnya.

## Account Factory SOP (buat sendiri — jangan nanya user)

1. Coba temp-mail dulu (mail.tm API dsb); verifikasi inbox menerima.
2. Kalau target blokir disposable → Gmail plus-addressing
   (`RESEARCHER_USERNAME+<target><n>@gmail.com`); ambil OTP/link sendiri via gmail skill.
3. Jangan mengarang PII (nama/ID orang asli); kalau flow wajib nama asli →
   catat surface `not-tested` + alasan, jangan dipalsukan.
4. Dua akun untuk IDOR differential bila target mengizinkan (catat bila
   plus-address ternormalisasi jadi satu akun → batas single-identity).
5. Password: random kuat, simpan `creds.json` (0600) di audit workdir;
   jangan dipakai ulang antar target.
6. **Kalau self-provisioning memang mustahil, serahkan ke operator — jangan tulis N/A.**
   Sebagian target menaruh field signup di dalam iframe cross-origin
   (`.../challenge/v4/html?Name=email`) dan menaruh **honeypot** off-screen
   (`aria-hidden`, `x≈-1000`) di dokumen induk; API-nya menuntut
   `x-pm-human-verification-token` bertipe captcha (kosong → `422 Invalid token type`).
   Itu kontrol yang bekerja, bukan bug. Alurnya: buka Chromium *headed* + profil persisten
   lewat `terminal background=true`, beri operator URL dengan gerbang paling sedikit
   (`/<product>/signup?plan=free` biasanya menghapus seluruh langkah payment), tunggu selesai,
   lalu **panen cookie dari profil yang sama** dan **verifikasi identitas** sebelum dipakai.
   Catat di ledger: "account B dibuat manual oleh operator, <tanggal>".
   Resep + 6 pendekatan yang gagal: `signup-block-ops` §8–§9 dan
   `references/cross-origin-challenge-iframe-signup.md`.
7. **Bedakan "gagal membuat akun" dari "fitur tidak ada".** Identitas kedua yang tipenya
   external-address (bukan alamat provider) sering tidak bisa memakai produk tertentu
   (mis. Calendar minta `/setup-address`, Pass minta `/reauth`). Catat tipe akun di tabel
   identitas, supaya produk yang tak terprovision **tidak** dilaporkan sebagai "tidak ada temuan".
*(Cross-ref: `disposable-auth-identity`, `saas-test-account-provisioning`, `signup-block-ops`.)*
