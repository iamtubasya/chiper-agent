---
name: hunt-data-exposure
version: 1.0.0
author: RESEARCHER_NAME
description: >-
  Database / dataset leak from an endpoint: route the symptom to its mechanism, probe
  per datastore, and prove it with minimal evidence. Use when recon shows a collection
  endpoint, an exposed datastore port, a dump file, or a GraphQL schema that returns
  data it should not.
metadata:
  hermes:
    tags: [security, data-exposure, database, leak, idor, bola, bug-bounty]
---

# Data Exposure — database leak dari endpoint

**Kelas tujuan, bukan primitif.** "Database bocor" adalah *gejala*. Tugas pertama adalah
menentukan **mekanismenya**, karena itu yang menentukan severity, cara membuktikan, dan
cara melaporkan.

## 1. Routing — gejala → mekanisme

| # | Mekanisme | Ciri di recon | Kelas induk | Severity |
|---|---|---|---|---|
| 1 | **Unauthenticated collection read** | `/api/users`, `/api/orders` balas 200 tanpa cookie | IDOR/BOLA | Critical |
| 2 | **IDOR on object** | butuh auth, tapi id orang lain kebaca | IDOR/BOLA | High–Critical |
| 3 | **GraphQL BOLA-by-resolver** | `/graphql` introspection aktif, mutation tanpa `@auth` | GraphQL | High |
| 4 | **Datastore exposed** | port 27017/9200/6379/5984 terbuka tanpa auth | Cloud misconfig | Critical |
| 5 | **SQLi → dump** | error-based / boolean / time-based di parameter | SQL Injection | Critical |
| 6 | **File leak** | `.sql`, `.bak`, `.old`, `heapdump.hprof`, `.git` | Info Disclosure | Medium–High |
| 7 | **Mass assignment** | field sensitif (`role`, `isAdmin`, `balance`) ikut keluar | API Misconfig | Medium–High |
| 8 | **Shadow / undocumented API** | endpoint lama/versi (`/v1/`, `/internal/`) masih hidup | Shadow API | Medium |

**Aturan:** tentukan mekanisme SEBELUM menulis laporan. "Database bocor" tanpa mekanisme
= laporan ditolak triage.

## 2. Probe per mekanisme (urutan nilai bisnis)

### Mekanisme 1 — collection endpoint tanpa auth (termurah, severity tertinggi)
```bash
# 1. anon control DULU — tanpa cookie sama sekali
curl -s -o /dev/null -w "%{http_code} %{size_download}\n" https://T/api/users
# 2. bandingkan dgn versi ber-auth
curl -s -H "Cookie: session=A" -o /dev/null -w "%{http_code} %{size_download}\n" https://T/api/users
# 3. ambil count + minimal 10 record sebagai bukti (JANGAN dump semua)
curl -s "https://T/api/users?limit=10" | python3 -c "import sys,json; d=json.load(sys.stdin); print('count:', len(d)); print(json.dumps(d[:2], indent=1))"
```
**Sinyal:** anon 200 + body >100 byte = **primitive termurah**. Kalau anon 200 tapi body
kosong/redacted, itu BUKAN akses — lanjut ke mekanisme 2.

**Minimum bukti: 10 record.** Satu record bisa jadi akun tes, seed, atau artefak.
10 record yang berbeda (email/id/timestamp berbeda) membuktikan eksposur **sistemik**.
Kalau total data <10, ambil **semua** — jumlah sedikit itu sendiri bagian dari temuan.

### Mekanisme 2 — IDOR pada objek
```bash
# pakai identity_harness supaya terukur
python identity_harness.py diff --label-a a --label-b b \
  --urls https://T/api/orders/1 https://T/api/users/1 https://T/api/me
```
Sinyal otomatis: `BOTH-200-DIFFERENT-BODY` (B melihat data A) · `ANON-READABLE`.

### Mekanisme 3 — GraphQL BOLA
```
# introspection dulu (buka schema)
{ __schema { types { name fields { name } } } }
# lalu query objek orang lain dengan sesi sendiri
query { user(id: "VICTIM_ID") { email phone } }
```
Cek juga: mutation tanpa `@auth` directive, dan **subscription yang bisa didengar anon**.

### Mekanisme 4 — datastore exposed (port, bukan HTTP)
| datastore | port | probe read-only |
|---|---|---|
| MongoDB | 27017 | `mongosh --eval "db.stats()" --host T` |
| Elasticsearch | 9200 | `curl https://T:9200/_cat/indices` |
| Redis | 6379 | `redis-cli -h T INFO keyspace` |
| CouchDB | 5984 | `curl https://T:5984/_all_dbs` |
| S3 / bucket | 443 | `aws s3 ls s3://BUCKET --no-sign-request` |

**Aturan aman:** baca **metadata + count + minimal 10 record** (atau **SEMUA** kalau
datanya <10 — kalau cuma ada 3, itu sendiri adalah temuan). JANGAN dump seluruh koleksi.

### Mekanisme 5 — SQLi → dump
Pakai `hunt-sqli` (111 baris teknik + 3 lab). Target: `information_schema`, jumlah baris,
**minimal 10 baris contoh** sebagai bukti — bukan seluruh tabel. Kalau tabel <10 baris,
ambil semua dan sebutkan jumlahnya.

### Mekanisme 6 — file leak
```
/.git/config            → kredensial & remote
/.env                   → secret
/dump.sql / backup.sql  → struktur + data
/actuator/heapdump      → heap dump (bisa mengandung session & token)
/.DS_Store / .bak / .old
```
Pakai `hunt-source-leak` (301 baris).

### Mekanisme 7 — mass assignment
```bash
# tambahkan field sensitif ke body yang sah
curl -X PUT https://T/api/me -d '{"name":"x","role":"admin","isAdmin":true}'
# cek apakah field tersimpan / ikut keluar di response
```

### Mekanisme 8 — shadow API
Pakai `hunt-shadow-api` (196 baris) + `hunt-spa-api` — endpoint versi lama yang lupa dimatikan.

## 3. Disiplin pasca-temuan (WAJIB)

| boleh | tidak boleh |
|---|---|
| Ambil **count** (`COUNT(*)`, `_count`, `total`) | Download seluruh koleksi |
| Ambil **1 record contoh** sebagai bukti | Eksfil data PII massal |
| Catat **request/response + timestamp + marker unik** | Menyimpan data korban di disk |
| **Redaksi PII** di laporan (masking email/telepon) | Menempelkan data asli ke report |
| Laporkan lewat kanal policy | Menghubungi korban langsung |

**Kenapa ini menguntungkan kamu:** laporan dengan `count + 1 record ter-redaksi` lebih
cepat ditriage daripada laporan dengan 50MB dump. Yang pertama terbukti; yang kedua
membuat tim hukummu tersangkut.

## 4. Gate 0 — sebelum lapor

1. **Mekanisme teridentifikasi** (salah satu dari 8 di atas)
2. **Bukti differential** — anon vs auth, atau A vs B (bukan single response)
3. **Volume disebut** — count nyata, bukan "banyak sekali"
4. **Minimal 10 record** diambil sebagai bukti (atau semua kalau total <10) — 1 record
   bisa jadi akun tes/seed/artefak; 10 record berbeda membuktikan eksposur sistemik
5. **PII ter-redaksi** di laporan
6. **Reproduksi 10 menit** dari sesi bersih
7. **Dampak konkret** — data siapa, bisa dipakai untuk apa (ATO? spam? phishing?)

## 5. Skill & alat pendukung

| kebutuhan | alat |
|---|---|
| IDOR terukur | `identity_harness.py` (mode `diff`, `ids`) |
| Collection unauth | `curl` + bandingkan anon vs auth |
| Datastore | `mongosh` · `redis-cli` · `curl` (read-only) |
| SQLi | `hunt-sqli` + `sqlmap` |
| File leak | `hunt-source-leak` + `nuclei` exposures templates |
| Shadow API | `hunt-shadow-api` + `hunt-spa-api` |
| GraphQL | `hunt-graphql` + `graphql-audit` + `graphql-cop` |

## 6. Sumber

Atlas terkait: `security/poc-technique-atlas/references/` — `idor-bola.md` (104 baris) ·
`sqli.md` (111) · `auth-bypass.md` (97) · `nosql.md` (17, termasuk MongoBleed
CVE-2025-14847) · `info-disclosure.md` · `api-misconfig.md` · `cloud.md`.

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Error verbose: paksa 500 (tipe salah, null, oversized) → baca stack trace | Path + versi + query bocor |
| 2 | Endpoint debug/status: `/status`, `/health`, `/metrics`, `/debug` | Sering tanpa auth |
| 3 | Backup & source: `.bak`, `.old`, `.zip`, `.git/`, `web.config.bak` | Source & kredensial |
| 4 | API over-fetch: bandingkan field respons vs yang dipakai UI | Field sensitif ikut keluar |
| 5 | IDOR-adjacent: objek publik yang seharusnya butuh auth | Batas publik/privat yang salah |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis
N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Gate 0 Validation

1. **Apa yang bisa dilakukan penyerang SEKARANG?** "Penyerang tak terautentikasi bisa membaca stack trace di `/api/export` yang membocorkan connection string database."
2. **Apa yang hilang dari korban?** Data spesifik yang bocor: kredensial, PII, konfigurasi internal. Bukan "informasi sensitif".
3. **Bisa direproduksi 10 menit dari nol?** Sertakan request dan respons (disedit) yang menunjukkan kebocoran.

## Eskalasi wajib (jangan berhenti di kelas ini)

**Primitif:** baca dataset massal

**Teknik pengembangan:** PII -> phishing/credential stuffing; token -> ATO

**Eskalasi ke:** `hunt-ato` · `hunt-business-logic`

**Depth target:** L2 -> L5

Satu temuan di kelas ini WAJIB menyebut eskalasi berikutnya (atau alasan primitif habis).
Lihat `exploit-chain-graph` + `exploit-depth` (L0-L5). `depth_gate.py` memblokir temuan
yang buktinya cuma status code.

## 2026 sweep (dork pass 2026-10-26 — advisori terverifikasi)

- **CVE-2026-25049 — n8n: unauthenticated settings disclosure.** Endpoint pengaturan terbuka.
- **CVE-2026-31431 / CVE-2026-43284 — nginx "copy-fail" / "dirty-frag": kebocoran memori pra-auth.** Heap buffer overflow + information leak.
  Lesson: kebocoran pada proxy/web server berdampak lintas pengguna karena memegang traffic semua orang — termasuk header auth request lain.
- **CVE-2026-42533 — nginx: pre-auth heap buffer overflow + heap information leak.**
- **CVE-2026-102628 — Cadmos LTI: `APP_DEBUG=true` membocorkan seluruh `.env` plaintext.** Lihat `hunt-laravel`.

**Yang masih dibayar:** secret di **riwayat commit** (bukan cuma file aktif), source map lengkap, dan endpoint `/settings`/`/config` tanpa auth. Yang jarang: banner versi tanpa eksploit CVE yang bekerja, dan stack trace tanpa data sensitif.


## Critical severity anchor (kelas ini bisa Critical — syaratnya)

Database/dataset leak dari endpoint: minimal bukti = count + 1 record (redaksi PII). Kalibrasi: 'on-chain discoverable = not confidential' untuk data on-chain; endpoint kosong / array kosong = BUKAN leak, itu negative; kuota teks yang menipu — baca angka dalam error sebelum klaim DoS.
