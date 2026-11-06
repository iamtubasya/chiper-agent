---
name: probe-validation
version: 1.0.0
author: RESEARCHER_NAME
license: MIT
description: "Prove a probe fires: negative controls, coverage sanity gates, debugging 0-hit sweeps."
metadata:
  hermes:
    tags: [security, validation, lab, exploit, proof, methodology]
---

# Probe Validation — "endpoint hidup" ≠ "vuln terbukti"

Dipakai saat memverifikasi bahwa sebuah kelas bug **benar-benar bisa dieksploitasi** di lab
atau target: kalibrasi probe sampai menyala, dan buktikan hasilnya bukan artefak environment.

**Aturan inti: setiap probe butuh kontrol yang hasilnya BERBEDA kalau vuln tidak ada.**
Tanpa kontrol, `500`/`200`/`403` hanyalah kebisingan.

## When to Use

- Lab/container sudah UP dan kamu harus membuktikan tiap **kelas** benar-benar menyala.
- Sebuah probe membalas 200/500/403 dan kamu hampir mencatatnya sebagai temuan.
- Kamu butuh menyatakan "kelas X belum teruji" secara jujur (negative + coverage).
- Kamu memverifikasi ulang temuan lama sebelum dilaporkan.

## 0. Alur 4 ronde (pola yang terbukti)

```
Ronde 1  probe naif -> catat mana yang cuma "200 OK"
Ronde 2  perbaiki akar masalah (kalibrasi parameter, identifier sendiri)
Ronde 3  rangkai jadi chain + metrik impact (bukan status code)
Ronde 4  tutup loop: state berubah? kontrol gagal? selebihnya RETRACT
```

Jangan lapor sebelum ronde 4. Laporkan prosesnya (ronde apa memperbaiki apa) —
operator sering minta "proses kamu gimana", bukan hanya tabel hasil.

## 1. Kontrol benign untuk sink berbasis network (aturan paling mahal)

Sink yang bergantung koneksi keluar — SSRF, webhook, image proxy, email, OOB callback —
**wajib** dites dengan kontrol benign lebih dulu.

Kalau pesan blokir **identik** untuk semua target, termasuk URL eksternal tak berbahaya,
maka blokir terjadi pada **koneksi**, bukan pada validasi target.

```
Diagnostik:  semua payload diblok sama persis  ->  curiga env/filter infra
             kontrol benign lolos              ->  filter bereaksi ke target = sinyal nyata
             kontrol benign juga diblok        ->  INCONCLUSIVE / RETRACT
```

Contoh nyata (Juice Shop 20.3.0 di Docker): 13 payload SSRF (`127.0.0.1`, `2130706433`,
`0177.0.0.1`, `[::1]`, `[::ffff:127.0.0.1]`, `127.1`, `0`, `0.0.0.0`, `nip.io`,
`172.17.0.1`, nama service Docker, `169.254.169.254`, `metadata.google.internal`) semua
membalas `500 Blocked illegal activity by ::ffff:172.17.0.1`. Terlihat sempurna.
Kontrol benign (PNG publik) dibalas **pesan sama** → itu NAT/egress Docker, **bukan SSRF**.
Probe ditarik, bukan dilaporkan.

## 2. Kalibrasi, jangan tembak

| uji | yang dikalibrasi | sinyal kalibrasi yang benar |
|---|---|---|
| UNION SQLi | jumlah kolom | error `SELECTs to the left and right ... same number of result columns`; cari n yang 200 |
| LFI / traversal | depth `../` | sweep 2..8; depth salah = 200 tapi kosong, depth benar = isi file |
| rate-limit | jumlah attempt | 50–100x, catat 429 pertama (~25–30 umum) |
| race | concurrency + metrik objek | delta jumlah order/token/saldo |
| boolean/blind | sampel per state | >=8 sampel, cek separation min>max (buang sampel pertama) |

Catat angka kalibrasinya di bukti ("9 gagal, 10 sukses, 11 gagal") — itu yang membedakan
kalibrasi dari keberuntungan.

## 2a. Artefak pengukuran yang MEMALSUKAN negatif (ronde-0, sebelum apa pun)

Sebelum menyimpulkan "0 temuan", pastikan **alat ukurmu** tidak sedang memotong datanya.
Ini kelas false negative yang paling mahal karena terlihat seperti hasil bersih.

**Kasus nyata (Deeper Chain, 2026-10-28).** Untuk membuang modul test dari file Rust:

```python
body = re.split(r"#\[cfg\(test\)\]", src)[0]   # SALAH
```

Pallet FRAME mendeklarasikan modul test di **header** file:

```rust
#[cfg(test)] mod mock;
#[cfg(test)] mod tests;
```

Jadi split pertama memotong file **138 KB / 39 extrinsic** menjadi **903 byte**. Semua grep
setelahnya balik 0 hit, dan run tampak seperti negatif bersih. Bug O(N) yang dicari ada di
file itu — hampir terlewat sepenuhnya.

Aturan:

```python
m = list(re.finditer(r"#\[cfg\(test\)\]", src))
body = src[:m[-1].start()] if m else src        # occurrence TERAKHIR, bukan pertama
assert len(body) > 0.5 * os.path.getsize(path), "tertruncate di header - baca ulang file"
```

**Gerbang umum:** setiap kali negatif bergantung pada "tidak ditemukan", bandingkan ukuran
data yang kamu pindai dengan ukuran aslinya. Rasio >2x curiga; >10x hampir pasti salah.
Sebutkan di COVERAGE berapa byte/baris yang benar-benar dibaca.

**Varian lain dari kelas yang sama:**

| artefak | cara memalsukan | gerbang |
|---|---|---|
| split/parsing | regex memotong di header, file 150x lebih kecil | bandingkan `len(body)` vs `getsize` |
| hitungan `ls -la` | kolom ke-5 = bytes, bukan jumlah file | pakai `wc -l` |
| kotak masuk | "8 pesan terakhir" → email target di luar jendela | cari per kriteria (`from:`), bukan recency |
| endpoint kontrol | semua address balik nilai sama → RPC mock | sertakan kontrol yang jawabannya sudah diketahui |

## 2b. "0 hits" = debug the PROBE, not the target

Kalau scanner balik 0 temuan padahal PoC Python-mu menyala di endpoint yang sama, tersangka
pertama adalah **probe**, bukan target. Jangan menyimpulkan "target aman" dari output kosong.

**Diagnostik wajib sebelum menuduh target** — pakai template yang PASTI cocok:

```yaml
# probe-reach.yaml — satu-satunya tujuan: "apakah scanner benar-benar sampai ke service?"
http:
  - raw:
      - |
        POST /vulnerable/path HTTP/1.1
        Host: {{Hostname}}
        Content-Type: application/x-www-form-urlencoded

        param=value
    matchers:
      - type: word
        part: body
        words: ["<kata yang pasti ada di halaman mana pun>"]
```

Kalau ini juga 0 → masalah koneksi/host/cookie, bukan matcher. Kalau ini 200 → baru
curigai matcher. Tanpa langkah ini, `0 hits` tidak bisa dibedakan dari `scan tidak jalan`.

Kasus nyata: `nuclei -u http://localhost:4280` → 0 hits; `nuclei -u http://127.0.0.1:4280`
→ hit. `localhost` resolve ke `::1` sedangkan service hanya bind IPv4. Hampir menyimpulkan
"DVWA aman" dari probe yang tidak pernah mendarat.

## 2c. Uji falsifiabilitas probe: PAIRED test (teknik terkuat)

Cara membuktikan sebuah probe **mentransfer** (bukan cuma menyala di lab yang kamu tulis):
jalankan template **identik** ke target dan **jalur kode patched**-nya. Yang berubah hanya
kode target, bukan probe.

```
target sama · template sama · sesi sama · hanya jalur kode berbeda

security=low         4 hits   <- kode rentan
security=medium      0 hits
security=high        0 hits
security=impossible  0 hits   <- fix sesungguhnya
=> DISCRIMINATING: probe menyala di kode rentan, DIAM di kode yang diperbaiki
```

Ini yang membedakan "probe jalan" dari "probe cuma menyala". Kalau probe menyala di versi
patched juga, probe itu **false positive** — perbaiki matcher-nya, jangan lapor.

Cari oracle patched yang tersedia: modul security-level pada app rentan (DVWA `low` vs
`impossible`), versi library lama vs baru, endpoint lama vs hasil rewrite, branch fix di repo.

**Batas kejujuran:** untuk kelas yang kontrolnya kamu tulis sendiri (lab buatan sendiri),
paired test hanya membuktikan konsistensi internal — **bukan** transfer. Nyatakan itu
eksplisit, dan hanya klaim transfer untuk kelas yang benar-benar diuji pada kode pihak ketiga.

## 2d. Sink blind: matcher yang diam itu BENAR

Untuk SSRF/webhook/email blind, content matcher yang tidak menyala adalah **perilaku yang
benar**, bukan kegagalan probe. Satu-satunya bukti sah adalah OOB.

```
endpoint balas {"queued":true} tanpa body  <- tidak ada yang bisa di-match
interactsh mencatat DNS + HTTP, User-Agent: python-requests/2.32.3
=> server-side fetch terbukti (bukan browser peneliti)
```

Kontrol: kirim host OOB yang sama ke endpoint ber-allowlist → harus ditolak. Kalau
allowlist menolak tapi sink rentan tetap memanggil, itu bukti berpasangan.

## 2e. Memindahkan PoC Python → template scanner (jebakan transport)

PoC yang jalan di Python sering mati saat dipindah ke templates. Periksa berurutan:

| gejala | penyebab | perbaikan |
|---|---|---|
| 0 hits di semua path | `localhost` → IPv6, service IPv4-only | pakai `127.0.0.1` |
| payload injeksi tidak sampai | `%3B` di-encode ulang oleh scanner | tulis `;` literal di body |
| regex tidak pernah cocok | `\\d` di YAML single-quote ≠ `\d` | pakai kelas karakter `[0-9]` |
| sesi hilang, semua 401/login page | nama cookie case-sensitive (`PHPSESSID`) | samakan persis |
| template gagal senyap | variabel `{{var}}` tidak didefinisikan | hapus, atau isi via `-V var=` |
| semua word "match" | `-mc 200` pada sink yang selalu 200 | filter body/ukuran |

Yang terakhir itu yang paling sering: **sink proxy membalas 200 bahkan saat upstream 404**,
jadi `-mc 200` mencocokkan segalanya. Kontrolnya: satu word yang dijamin tidak ada
(`nope-xyz`) — kalau ikut "match", filter-mu salah. Ganti ke filter ukuran body 404
(`-fs <size>`) atau tanda tangan isi yang unik.

## 2f. Negative assertion tanpa POSITIVE CONTROL = test yang tidak membuktikan apa pun
`assert!(!verify(...))` berdiri sendiri **tidak membuktikan apa-apa**: verifier yang selalu balik `false`
lolos semua assertion macam itu. Setiap negatif butuh **positive control yang dibangun dari konstruksi
yang sama, di test yang sama** — input jujur yang WAJIB verify. Kalau positive control gagal, yang salah
adalah konstruksimu, bukan kodenya.

Terbukti 2026-10-27 pada settle lane Tacit (`cxfer-core`, test adversarial terhadap
`swap_batch_aggregate_identity` / `swap_blind_aggregate_kernel` asli). Dua test saya sendiri salah, dan
positive control yang menangkap keduanya:

| assertion saya | kenapa salah |
|---|---|
| "identitas sisi-A menolak receipt sisi-B yang digelembungkan 100x" | tidak bisa dan tidak seharusnya — jumlah sisi-A hanya melihat input dan output A; receipt B **tak terlihat** secara struktural. Guard sebenarnya ada di cek sisi-B. |
| "kernel menolak signature jelek" dengan `delta` ≠ nilai input | excess-nya jadi punya komponen `400·H` dan **tidak punya discrete log sama sekali**, jadi tak ada signature valid yang mungkin ada. Konstruksinya invalid, bukan verifier-nya. |

Keduanya akan terbaca sebagai "kode menolak" dan dikirim sebagai klaim NEGATIF palsu — cermin dari
over-claim biasa, dan sama salahnya.

Bentuk yang bekerja:

```rust
// POSITIVE CONTROL dulu: konstruksi jujur harus verify.
assert!(verify(&honest), "positive control gagal: verifier menolak input jujur");
// lalu tiap negatif, satu variabel per test
assert!(!verify(&delta_off_by_one), "...");
assert!(!verify(&receipt_inflated_100x), "...");
assert!(!verify(&wrong_blinding_excess), "...");
assert!(!verify(&sig_under_other_pool_or_chain), "...");   // replay lintas pool/deployment
```

Checklist untuk test adversarial atas rutin kripto/verifikasi apa pun:

1. positive control lolos lebih dulu — kalau tidak, **stop**, perbaiki konstruksi;
2. tiap negatif beda dari kontrol di **tepat satu** field;
3. sertakan negatif replay — signature sah di bawah `pool_id` / `chain_binding` / deployment lain;
4. sertakan off-by-one pada setiap angka yang dideklarasikan, bukan hanya inflasi 100x (100x bisa
   tertangkap guard overflow dan menyembunyikan lubang off-by-one);
5. tulis di catatan coverage bahwa kontrolnya ada — "test membuktikan X ditolak" tanpa kontrol bukan bukti.

Portabel ke semua stack: aturan yang sama berlaku untuk `assert` Python pada escaper regex, `vm.expectRevert`
Solidity, atau matcher nuclei yang harus tetap diam.

## 2h. Reproduksi N kali lewat JALUR YANG SAMA = 1 observasi, bukan N

"Sudah 3x, hasilnya sama" hanya berarti sesuatu kalau tiap ronde **berbeda mekanisme**.
Menjalankan skrip yang sama, dengan data yang sama, lewat kode yang sama, tiga kali, adalah
satu pengamatan yang diulang — bukan tiga bukti. Ini kebalikan dari §2c: di sana kamu
memvariasikan kode target; di sini kamu harus memvariasikan **jalur masukmu**.

**Kasus nyata (InterNACHI, 2026-10-30) — false positive yang lolos 2 ronde.**

Klaim awal: field `legal_name` di signup tersimpan dobel (`RESEARCHER_NAMERESEARCHER_NAME`).
Dua akun menunjukkan hasil identik → terlihat seperti 2x reproduksi.

```
akun 1  given=RESEARCHER_NAME  family=Susanto  legal="RESEARCHER_NAME"  -> "RESEARCHER_NAMERESEARCHER_NAME"  BUG
akun 3  given=""     family=BB3      legal="BB3 Legal"      -> " BB3BB3 Legal"               BUG
```

Ronde ke-3 menambahkan **kontrol yang berbeda mekanisme**: nilai di-inject langsung ke DOM
(`el.value = ...`) alih-alih diketik/di-`fill()`.

```
akun 5  given=Alpha  family=Beta  legal="Gamma Delta"  -> "Gamma Delta"   BENAR
```

Hasilnya: server menyimpan apa pun yang dikirim. Dobelnya berasal dari Alpine `@change`
handler di form (`if (infer_legal_name && !!family_name) legal_name = given_name + " " + family_name`)
yang mem-prefix input user. **Client-side UX bug, bukan integritas data.** Ditarik.

Aturan:

1. Sebelum menghitung "Nx reproducible", tulis **mekanisme tiap ronde**. Kalau semua ronde
   memakai skrip/harness/akun-flow yang sama persis, hitungannya tetap 1.
2. Ronde pembeda harus mengubah **jalur**, bukan cuma mengulang: inject-DOM vs ketik-manual,
   API vs UI, akun baru vs akun lama, browser vs HTTP client, jam berbeda, sesi bersih.
3. Untuk bug yang diduga **server-side**, kontrol wajib mengirim nilai yang sama lewat jalur
   yang tidak melewati klien. Kalau server tetap benar → bug ada di klien, dan itu bukan
   temuan keamanan.
4. Tulis hasil tiap ronde di bukti (jalur apa yang dipakai), supaya reviewer bisa melihat
   bahwa "3x" berarti tiga jalur, bukan tiga kali klik.

Saudara dari §4b: di sana kamu butuh **akun pengamat bersih**; di sini kamu butuh **jalur
masuk yang berbeda**. Keduanya menjawab pertanyaan yang sama — apakah yang saya ukur itu
perilaku sistem, atau perilaku alat ukur saya sendiri.

## 2i. Token sekali-pakai: satu token untuk N tes = N-1 NON-HASIL

Kalau probe-mu memakai **artefak sekali-pakai** (requestId, nonce, OTP, CSRF token, digest
tanda tangan, idempotency key), maka tes ke-2 dan seterusnya **tidak menguji apa pun** — server
membalas "sudah dipakai / kedaluwarsa", dan itu terbaca persis seperti penolakan yang benar.

**Kasus nyata (relay.link app-fees, 2026-10-30).** Matriks 10 tes memakai satu `requestId`.
Tes 2–10 semuanya membalas `inexistent or expired`. Dibaca naif: "10/10 ditolak, aman".
Kenyataannya **1 hasil nyata + 9 non-hasil**. Setelah tiap tes memakai digest baru, barulah
muncul verdict yang benar-benar berbeda (`Invalid signature`, `Could not process permit`, `500`).

Aturan:

```
untuk SETIAP kasus uji:
    minta artefak BARU  (POST prepare / GET nonce / dst)
    baru submit          -> hanya submit pertama untuk artefak itu yang sah
```

**Bedakan "kedaluwarsa" dari "ditolak".** `inexistent or expired` = artefak sudah hilang,
tes tidak pernah dievaluasi → ulangi. `Invalid signature` = server benar-benar memeriksa
tanda tanganmu → itu data. Hanya yang kedua boleh masuk tabel.

**Kontrol untuk kelas ini:** jalankan satu kasus **dua kali dengan artefak baru** — harus
memberi verdict sama. Kalau berbeda, kamu sedang mengukur urutan, bukan perilaku.

**Varian:** artefak sekali-pakai juga bisa **dihanguskan oleh percobaan yang gagal**. Kalau
submit pertama error 500, jangan asumsikan artefaknya masih hidup untuk tes berikutnya —
mint ulang.

Saudara dari §2a: di sana alat ukur memotong data; di sini alat ukur **kehabisan bahan bakar**
dan kamu membaca tangki kosong sebagai hasil pengukuran.

## 2j. Probe yang bergantung pada precondition: buktikan precondition-nya MENDARAT dulu

Sebagian probe hanya bermakna kalau state awalnya benar-benar terbentuk — device sudah terikat,
2FA sudah aktif, kode sudah terbit, langganan sudah ada. Kalau setup-nya gagal senyap, probe
menguji objek yang salah dan hasilnya **terbaca sebagai kebalikannya**.

Kasus nyata (DedSec CCTV, 2026-10-30). Probe device-lock melaporkan `200 NOT BLOCKED` — terlihat
seperti auth bypass lintas-PC. Penyebabnya: harness tidak pernah **mengikat** device lebih dulu,
jadi tidak ada binding yang bisa dilanggar. Setelah setup diperbaiki (binding pada PC-A, lalu login
dari PC-B):

```
bind PC-A          -> 200
login dari PC-B    -> 403     <- kontrol bekerja
login lagi PC-A    -> 200
body hwid=PC-C     -> 403     <- header menang atas body, tidak bisa pindah device
```

Aturan: setiap probe ber-precondition menulis **assert precondition** sebelum menguji target.
Kalau assert gagal, verdict-nya `INCONCLUSIVE` — bukan "bypass".

## 2k. Perilaku BENAR yang terbaca sebagai temuan karena threat model-nya tidak berlaku

Kelas false positive yang paling memalukan: probe "lolos" justru karena kontrol yang dicari memang
tidak seharusnya ada di sana. Menulisnya sebagai temuan berarti melaporkan desain, bukan cacat.

Terukur pada target yang sama: probe CSRF mengirim `PUT /account/email-preferences` dengan
`Origin: https://evil.com`, mendapat `200`, dan harness menandainya **"cross-origin accepted"**.
Itu salah. Endpoint-nya memakai **`Authorization: Bearer`**, bukan cookie — tidak ada ambient
credential yang ikut terkirim otomatis oleh browser, jadi tidak ada permukaan CSRF sejak awal.
`200` di sini adalah perilaku yang benar.

| probe | "lolos" berarti temuan HANYA kalau | kalau bukan, hasilnya |
|---|---|---|
| Origin/Referer cross-site | auth berbasis cookie/session | **tidak ada permukaan CSRF** — bukan temuan |
| clickjacking | endpoint mengubah state via cookie | header hilang tanpa dampak |
| CORS reflect | `allow_credentials: true` + cookie auth | refleksi tanpa credential = tidak berbahaya |
| `X-Forwarded-For` spoof | proxy tidak menimpa header | Caddy `header_up` menimpa → aman |
| host-header poisoning | link email dibangun dari request Host | `TrustedHostMiddleware` menolak → aman |

Sebelum mencatat "lolos": tulis dulu **mekanisme auth-nya** (cookie? bearer? mTLS?). Kalau
mekanismenya tidak memakai ambient credential, seluruh keluarga probe CSRF/CORS/clickjacking
tidak punya objek. Ini §5b versi positif: bukan "belum diuji", tapi **"tidak berlaku — sebutkan
alasannya"**.

### Varian khusus: menguji kode verifikasi yang dipakai guest/host

Saat menguji rutin yang dipakai oleh komponen trust-boundary (guest zkVM, verifier on-chain, kernel
conservation), tambahkan tiga sumbu yang sering terlewat:

- **skema ganda** — kalau ada dua fungsi yang menghasilkan nilai yang sama untuk tujuan sama (mis.
  `native_nullifier(nk, leaf)` vs `nullifier(leaf)`), buktikan keduanya **berbeda** dan bahwa jalur yang
  boleh dipakai hanya satu. Dua skema untuk satu note = double-spend.
- **domain binding** — signature/proof yang sah harus DITOLAK di bawah pool/chain/deployment lain.
- **kardinalitas** — untuk klaim "hanya pemilik yang bisa", uji seluruh ruang kecil (mis. 256 kandidat
  kunci) dan pastikan **tepat satu** yang lolos gate, bukan sekadar "yang salah ditolak".



| klaim | bukti lemah | bukti kuat |
|---|---|---|
| negative quantity / mass assignment | `POST` → 200 | `GET` ulang → nilai persisten + aksi lanjutan lolos |
| race | status code bervariasi | 0 → 12 order dari **satu** keranjang |
| upload → RCE | "upload sukses" | `GET /uploads/x.php?c=id` → `uid=33(www-data)` |
| cross-tenant write (invite/bind/share/BOLA) | `POST` → `code:0` / `200 success` | baca ulang state objek **dari akun ke-3 yang bersih**: id objek target benar-benar berubah (bukan id milik pemanggil) — lihat §4b |
| ATO | login → 200 | endpoint **admin-only** tembus dengan token itu |
| CSRF | form terkirim | pesan sukses + revert berhasil |
| stored XSS | payload terkirim | re-GET halaman, `<script>` masih mentah |
| SQLi | error/200 | baris data nyata (email, hash) dengan format tervalidasi |

Status code satu request tidak pernah cukup untuk klaim L5.

## 2g. Bug di resource/quota: buktikan di infra SENDIRI, dan ukur dengan counter bukan persentase

Kelas bug yang paling sering salah dibuktikan adalah **limit/kuota/hak istimewa yang diminta
oleh klien** (`cpus: 0`, `ram: 0`, `replicas: 0`, `tier: ""`). Nilai 0 adalah edge case klasik:
lolos type-check, diteruskan apa adanya, lalu ditafsirkan downstream sebagai "tanpa batas".
Tiga gerbang wajib, dan semuanya bisa dijalankan tanpa menyentuh host siapa pun.

### (a) Bukti source-level: jalankan modul ASLI, jangan reimplementasi

Kalau produknya open source, jangan menulis ulang validatornya di skrip sendiri — itu cuma
membuktikan skripmu. Muat modul upstream sungguhan dan stub hanya dependency beratnya
(DB, docker daemon, geo/HTTP call). Di Node cukup bajak `Module._load` sekali di awal, lalu
`require()` modul aslinya: fungsi validasinya benar-benar dieksekusi, termasuk semua `throw`.

Tiga jebakan yang memakan waktu nyata (Flux v8.21.1):

| Gejala | Sebab | Perbaikan |
|---|---|---|
| `Cannot find module 'axios'` | modul transitif belum di-install | fallback: kalau bare package tidak ketemu, kembalikan Proxy stub, bukan `throw` |
| `Cannot find module '../../config/userconfig'` | `config/default.js` me-require file user | `cp sampleUserConfig.js config/userconfig.js` |
| `Cannot read properties of undefined (reading 'scannedHeight')` | config buatan sendiri kurang lengkap | pakai **config asli** (`config/default.js`), jangan stub tulisan tangan |

**Dan inilah paired test-nya (§2c) tanpa perlu dua deployment:** cabang kode yang berbeda di
source yang sama sudah menjadi pasangan. Flux memvalidasi `cpu` di dua tempat —
`checkHWParameters` (punya minimum `cpu < 0.1`) dan `checkComposeHWParameters` (hanya cek total
*terlalu besar*). Call-site memilih berdasarkan versi spec:

```
appValidator.js:1389   if (version <= 3) checkHWParameters(...) else checkComposeHWParameters(...)
```

Jadi satu spec, dua jalur: cabang v<=3 **menolak** `cpu:0` ("CPU badly assigned"), cabang v>3
**meloloskan**. Itu diferensial yang menentukan — bukan sekadar "fungsi balik true". Sertakan
`file:line` call-site, bukan hanya nama fungsi: yang meyakinkan reviewer adalah bukti bahwa
pemeriksaan minimum itu *tidak pernah bisa dicapai* oleh spec versi baru.

### (b) Bukti runtime: bandingkan dengan kontrol berkuota yang NILAINYA DIKETAHUI

Reproduksi efek downstream-nya di mesin sendiri (Docker lokal, satu container). Kuncinya:
selalu jalankan **dua** container identik yang hanya berbeda di parameter yang diuji.

`docker stats --no-stream` **bukan** alat bukti di laptop/VM. Di Docker Desktop 2-core yang
sedang sibuk, container tanpa limit terbaca cuma ~32% CPU — angka itu mengukur host yang
kelaparan, bukan container. Yang valid adalah counter cgroup, karena enforcement kuota tidak
bergantung beban host:

```
/sys/fs/cgroup/cpu.max                 # "max 100000" = tanpa kuota ; "10000 100000" = 10% core
/sys/fs/cgroup/cpu.stat                # nr_periods / nr_throttled / throttled_usec
```

Hasil terukur (2026-10-28, `--cpus 0` vs `--cpus 0.1`, beban 8×`yes` 4 detik):

| | `cpu:0` (rentan) | `cpu:0.1` (kontrol) |
|---|---|---|
| `HostConfig.NanoCpus` | `0` | `100000000` |
| `cpu.max` | `max 100000` | `10000 100000` |
| cores_burned | 0.372 | **0.099** |
| `nr_periods` / `nr_throttled` | **0 / 0** | 372 / 346 |

Kontrol yang mentok **persis** di kuotanya (0.099 vs 0.1) adalah yang membuat pengukurannya
layak dipercaya — sekaligus membungkam "angkanya kecil, berarti tidak unlimited". `nr_periods=0`
pada yang rentan berarti scheduler tidak pernah mengevaluasi kuota sama sekali: `max` itu asli,
bukan kebetulan beban rendah. Tanpa baris kontrol, tabel ini tidak membuktikan apa pun.

### (c) Sajikan sebagai endpoint live yang membaca kernel per request

Angka di file teks selalu bisa dituduh ditulis tangan. Serve bukti dari dalam container yang
sama, baca `/sys/fs/cgroup/*` **pada setiap request**, dan ekspos ke publik:

- `busybox httpd` + CGI (`-h /www`, skrip di `cgi-bin/`) sudah cukup; tidak perlu framework.
- Fan-out dua panel (`/unlimited` = rentan, `/capped` = kontrol) lewat nginx sidecar dengan
  `proxy_pass` ke dua container; satu URL untuk vendor, dua jalur berdampingan.
- `cloudflared tunnel --url http://localhost:<port>` untuk URL publik tanpa akun. Kalau
  pre-check melaporkan QUIC FAIL, ulangi dengan `--protocol http2` — TCP-nya biasanya PASS.
- Tekankan di halaman bahwa nilai dibaca live dari cgroup, bukan dilampirkan.

Resep lengkap + seluruh perintahnya: `references/owned-infra-quota-proof.md`.

**Jangan** memakai node milik operator lain sebagai "target uji". Selain di luar scope
(`redteam-mindset`), laporanmu justru mati: vendor tidak bisa memverifikasi container di host
yang bukan miliknya, sementara keepalive/re-install loop terbaca sebagai evasion.



Untuk uji objek asing, kamu WAJIB tahu id milik sendiri; kalau tidak, `200` ambigu.

- Ambil id sendiri dari sumber otoritatif (JWT claim, response create, DB), bukan tebakan.
- Kontrol pembeda: **anon** ke objek sendiri → 401 membuktikan auth jalan; 200 untuk objek
  user lain = *authz gap* (BOLA). Kalau anon juga 200 → itu **auth hilang**, kelas temuan
  berbeda (dan severity berbeda) — jangan dicampur.

## 4b. Kode sukses ≠ perubahan state mendarat di objek yang dituju

Untuk operasi **WRITE** (invite, bind, share, transfer, tambah member, ubah setting, klaim kupon),
response `code: 0` / `success` adalah **klaim server**, bukan bukti efek. Server sangat sering
**mengabaikan id objek yang dikirim klien** dan memakai objek milik sesi sendiri. Yang membuktikan
temuan adalah **membaca ulang state objek target**, bukan membaca status code.

Kasus nyata (VeSync, 2026-10-28) — hampir jadi laporan Critical palsu:

```
POST /cloud/v1/homeManaged/homeSharedInvitation
{"homeId": <home MILIK AKUN LAIN>, "inviteeEmail": "<akun ketiga>"}
-> code 0 "request success"          <- terlihat seperti cross-tenant write (BOLA)

baca ulang homeList milik akun ketiga:
-> membership baru menempel di home MILIK PEMANGGIL, bukan di homeId yang dikirim
=> server mengabaikan homeId dari klien. TIDAK ada eskalasi. RETRACT.
```

Aturan:

1. Tulis dulu **efek yang dijanjikan** dalam bentuk baris konkret ("akun X harus muncul sebagai
   member di objek Y"), lalu baca objek itu **sebagai pengamat pihak ketiga**, bukan dari sudut
   pemanggil. Kalau kamu membaca dari sudut pemanggil, kamu melihat objeknya sendiri dan tidak
   akan pernah melihat bug ini maupun false positive-nya.
2. **Discriminator harus akun bersih** yang belum pernah berinteraksi dengan objek itu. Dua
   percobaan pertama saya terkontaminasi invite lama dari pemanggil yang sama, jadi state-nya
   sudah "kotor" sebelum tes dan hasilnya ambigu — saya butuh akun ke-5 baru untuk jawaban bersih.
3. Kalau pemanggil tidak bisa jadi pengamat (mis. invitee==caller ditolak
   `"you can not share it with yourself"`), itu justru petunjuk bahwa kamu butuh akun ke-3/ke-4,
   bukan alasan menutup lead.
4. Cocokkan **id objek** di post-state dengan target. Sama-sama `code 0` tapi id yang berubah
   adalah milik pemanggil = bukan bug.

Pola ini sepupu dari Body-Diff Rule: status code butuh diff **body**; write butuh diff **state**.
Dan lawannya juga berlaku — write yang mengembalikan error tetap bisa saja sudah mendarat
sebagian; baca state untuk kedua arah.

## 2l. Kontrol yang membalas body IDENTIK dengan target = parameter diabaikan, kontrol TIDAK SAH

Kontrol negatif baru sah kalau hasilnya **berbeda**. Kalau permintaan dengan parameter bogus
membalas body yang sama persis dengan permintaan sah, itu bukan "kontrol lolos" — itu bukti
bahwa **parameter tersebut tidak lagi diperiksa di jalur itu**, jadi kontrolnya tidak bisa
membedakan apa pun.

Terukur 2026-10-31, re-verify F1 first.org (`/_fcaptcha/api/score`, `signals:{}`):

```
siteKey=portal.first.org -> 200 {"success":false,"score":0.6,...,"wouldBlock":true}
siteKey=nope.invalid     -> 200 {"success":false,"score":0.6,...}      <- identik
```

Dibaca naif: "kontrol juga ditolak → fix berfungsi". Salah, kontrol itu tidak menguji apa pun.
Discriminator yang benar adalah **flip pra/pasca pada request yang sama**, yang hanya terlihat
kalau bukti lama disimpan:

```
2026-10-26  {"success":true,  "score":0.40,"token":"eyJzaX..."}     <- token diterbitkan
2026-10-31  {"success":false, "score":0.6, "wouldBlock":true,...}   <- token tidak ada
```

Saat re-verify, cetak body lama dan baru berdampingan. Kalau kontrol dan target sama-sama ditolak,
katakan eksplisit *"parameter ini tidak lagi dievaluasi di jalur ini, kontrol tidak informatif"* —
jangan dihitung sebagai kontrol yang hidup.

**Konsekuensi kedua (jangan over-claim arah sebaliknya):** kalau link pertama rantai sudah menolak
(tidak ada token terbit), link kedua menjadi **tidak dapat diuji oleh siapa pun**. Tulis "closed at
token issuance; endpoint downstream belum bisa dieksekusi" — bukan "endpoint downstream sudah
diperkuat". Menyebut seluruh rantai "hardened" dari bukti satu link adalah §5 versi optimis.

## 2l-bis. Classifier-mu adalah alat ukur: substring match di seluruh body = verdict palsu

Kelas artefak pengukuran yang paling sering lolos: **skrip probe sendiri** yang memutuskan verdict
dengan mencari kata di seluruh body. Markup halaman ikut ter-match, dan kamu membaca hasilnya
sebagai perilaku server.

Terukur 2026-10-31 (re-verify F1 first.org, `POST /auth/confirm`). Sembilan request berurutan
dinyatakan `REJECTED (captcha)` karena classifier mencari substring `"captcha"`. Kenyataannya
body memuat widget markup; pesan error sesungguhnya adalah:

```
class="s-msg s-msg-error">This request is expired or invalid. Please try sending this request again.
```

Itu **CSRF gagal**, bukan captcha. Artinya kesembilan tes itu **tidak pernah menguji apa pun** —
dan hasilnya terbaca sebagai "kontrol bekerja".

Dua cacat yang menyebabkannya, keduanya wajib dicek sebelum mempercayai verdict apa pun:

| cacat | gejala | perbaikan |
|---|---|---|
| token diambil dari halaman yang salah | `GET /auth/signup` → **404**, `csrf=""` di semua request | ambil token dari halaman yang **benar-benar menyajikan form** (`/auth/confirm`); dump `<form>` + `<input>` untuk memastikan |
| classifier substring di seluruh body | widget markup → `CAPTCHA` palsu | ekstrak **node error saja** (`s-msg-error`), jangan seluruh body |

```python
def err_msg(html):
    m = re.search(r'class="[^"]*s-msg[^"]*"[^>]*>(.*?)</', html, flags=re.S | re.I)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip() if m else ""

def classify(html):
    msg = err_msg(html).lower()
    if "expired or invalid" in msg:            return "CSRF_FAIL"      # paling awal
    if "additional verification" in msg:       return "CAPTCHA_FAIL"   # gate yang dituju
    if "more requests than allowed" in msg:    return "RATE_LIMIT"     # cabang ketiga
    if "check for an email sent to" in html.lower(): return "ACCEPTED"
    return "UNCLEAR" if not msg else "OTHER"
```

**Gerbang wajib:** setiap probe yang memakai token per-halaman harus punya
`assert csrf, "no CSRF token - semua verdict di bawah ini CSRF_FAIL, bukan tes"`. Tanpa assert itu,
kegagalan mengambil token menyamar sebagai penolakan yang benar — persis keluarga §2i (bahan bakar
habis dibaca sebagai hasil) tapi lewat jalur berbeda.

**Cabang ketiga jangan dilipat.** Di run yang sama, satu request membalas pesan rate-limit, bukan
captcha. Itu bukan "diterima" dan bukan "captcha ditolak". Laporkan hitungannya apa adanya
(`11 captcha, 1 rate-limited, 0 accepted`) — membulatkannya jadi `12/12 rejected` adalah
ketidakjujuran kecil yang membatalkan kredibilitas semua angka lain di laporan.

**Dan cek efek sampingnya dari LUAR probe.** Klaim "tidak ada email terkirim" tidak boleh
disimpulkan dari body respons. Query inbox-nya (`from:<domain>`, `to:<plus-address>`), kutip
query-nya, dan pastikan alamat itu memang bisa ditemukan sebelum menyimpulkan nol.

## 2m. Race: satu kali berhasil dari tiga ronde = BUKAN temuan

Race condition adalah kelas yang paling mudah menghasilkan false positive, karena hasilnya
**non-deterministik menurut definisinya**. Kalau kamu menerima hasil positif dari satu run,
kamu sedang mengukur keberuntungan, bukan kerentanan.

Terukur 2026-10-30 (DedSec CCTV). Tiga probe race, semuanya tampak positif di wave pertama:

| probe | wave-1 | validasi 3x | verdict |
|---|---|---|---|
| refresh-token rotation | 4 token dari 1 token | 1, 1, 1 token | FLAKY → buang |
| reset attempt-limit burn | "BURN BYPASSED" (kode benar lolos setelah 10 salah) | burned, burned, burned | FLAKY → buang |
| verify-email double-spend | 3 dari 8 request `200` | 1, 1 dari 8 | FLAKY → buang |

Ketiganya akan jadi laporan High palsu. Yang membatalkan: menjalankan **ulang dari state bersih
3x** dan mensyaratkan hasil konsisten.

Aturan:

1. **3 ronde, state bersih tiap ronde.** DB/akun/token baru per ronde — bukan mengulang di state
   sisa ronde sebelumnya (state sisa = mengukur urutan, bukan race).
2. **Syarat lolos = konsisten 3/3.** 1/3 atau 2/3 = `UNSTABLE`, tidak dilaporkan. Ini §5
   "tidak reproduksi 3x" diterapkan ke kelas yang paling butuh.
3. **Sertakan hitungan, bukan prosa.** "3/3 ronde: 8/8 request `200`" adalah bukti; "terjadi race" bukan.
4. **Kontrol anti-race:** jalankan request yang sama **seri** (satu per satu). Kalau seri juga
   memberi 2 token/2 order, itu bukan race — endpoint-nya memang menerbitkan berkali-kali.
5. **Thread nyata.** Pakai `threading` + `TestClient` per thread. Client tunggal yang dipakai
   bergantian men-serialisasi request dan menghasilkan 0 race — lalu terbaca sebagai
   "NOT BLOCKED"/"no race" padahal harness-nya yang salah (sama keluarganya dengan §2j).

```python
def fire(fn, n):
    out, lock = [], threading.Lock()
    def w(i):
        r = fn(i)
        with lock: out.append(r)
    ts = [threading.Thread(target=w, args=(i,)) for i in range(n)]
    [t.start() for t in ts]; [t.join() for t in ts]
    return out

verdicts = [run_once(round_no=i) for i in (1, 2, 3)]   # state bersih tiap ronde
confirmed = all(v > 1 for v in verdicts)
```

Kalau satu ronde gagal, tulis eksplisit: **"race tidak stabil (N/3), tidak dilaporkan"** —
itu hasil yang jujur, bukan kegagalan engagement.

## 2n. Timing oracle: bandingkan DELTA dengan SPREAD, bukan delta saja

Selisih median antar dua keadaan tidak membuktikan apa pun selama variance-nya lebih besar dari
selisih itu. Ini kesalahan paling umum saat mengklaim user-enumeration berbasis waktu.

Terukur 2026-10-30 (DedSec CCTV, `POST /auth/register`):

```
nonexistent : median 1652.83 ms  (min  776.71 / max 2987.86)
unverified  : median 1924.40 ms  (min  977.26 / max 3474.27)
verified    : median 2019.06 ms  (min  302.01 / max 3290.45)

delta verified-vs-new : +366 ms
spread (max-min)      :  2985 ms      <- 8x lebih besar dari delta
```

Delta 366 ms terlihat seperti oracle yang jelas. Tidak: distribusinya tumpang tindih total, jadi
satu request tunggal tidak bisa memprediksi keadaan akun. **Bukan oracle** — jangan lapor.

Aturan:

1. **Cetak min/max/median, bukan hanya median.** Tanpa spread, angka delta tidak bisa ditafsirkan.
2. **Gerbang: `delta > 3 x spread`** baru boleh disebut sinyal. Di bawah itu = `INCONCLUSIVE`.
3. **≥15 sampel, buang sampel pertama** (warm-up Argon2/JIT/pool koneksi).
4. **Kontrol positif wajib.** Ukur dua keadaan yang **pasti** berbeda secara struktur (endpoint
   yang memang membocorkan) dan pastikan harness-mu mendeteksi selisih itu. Harness yang tidak
   bisa mendeteksi beda yang diketahui tidak bisa dipakai membuktikan tidak-adanya beda.
5. **Baseline host ikut diukur.** Variance 3 detik pada endpoint ber-Argon2 berarti beban server
   mendominasi. Kalau begitu, timing bukan kanal di target ini — hentikan upaya, jangan mengulang
   dengan sampel lebih banyak.

## 2o. Probe auth: sebuah header SATU KARAKTER bisa memisahkan 401 dari 200 — dan polaritasnya wajib dicek

Kelas bypass termurah pada API berbasis SPA adalah middleware yang menganggap **"ada nilai"**
sebagai **"sesi valid"**. Ini tak terlihat oleh scanner karena respons tanpa kredensial adalah 401
yang bersih, dan hanya satu karakter yang memisahkan kedua keadaan.

**Probe-nya.** Untuk setiap endpoint yang balas `401`, kirim ulang dengan satu karakter non-kosong
di setiap nama header/cookie sesi yang bisa kamu temukan di bundle:

```python
T = {"x-session-token": "a"}          # satu karakter
st0, b0, _ = req(BASE + path)                      # 401
st1, b1, _ = req(BASE + path, hdr=T)               # 200 + data  <-- bypass
```

**Matriks nilai membuktikan ini uji kehadiran, bukan validasi lemah:**

| nilai | hasil |
|---|---|
| `""` (kosong) | 401 |
| `" "` (spasi) | 401 |
| `"a"`, `"0"`, `"."`, `"p0ZZZGARBAGE"`, 300 karakter, `{"a":1}`, `[1,2,3]` | **200** |

Kosong dan whitespace ditolak; semua nilai non-kosong lolos. Itu `if (token)` di tempat
`if (verify(token))`.

**Sweep nama header DAN cookie — dua jalur kode yang berbeda.** Terukur PubNub 2026-10-31,
34 nama disapu, tepat dua yang bekerja: `x-session-token: a` dan
`Cookie: __Host-PN-2-pnAdminToken=a`. `Authorization: Bearer a`, `x-auth-token`, `x-pn-token`,
`pnAdminToken`, `session`, `jwt`, `connect.sid` semuanya 401. **Ambil nama channel sesi dari
bundle SPA sebelum menebak** — grep yang sama yang menghasilkan peta `secure:!0`.

### Kontrol wajib #1 — IDOR horizontal sebelum klaim apa pun

Bypass yang membuka endpoint belum berarti apa-apa kalau endpoint itu tidak ter-scope ke pemanggil.
Untuk setiap endpoint yang terbuka, variasikan ID objek/akun dan hash responsnya:

```python
seen = {aid: (st, len(b), md5(b).hexdigest())
        for aid in ["627651", "1", "2", "100", "999999", "0"]}
uniq = len({v[2] for v in seen.values()})
# uniq == 1  -> tidak account-scoped -> TIDAK ada IDOR horizontal, katakan eksplisit
```

Body identik di semua ID berarti endpoint tidak ter-scope ke caller, jadi tidak ada IDOR yang bisa
diklaim. Menyatakan itu eksplisit adalah yang mencegah triager bertanya.

### Kontrol wajib #2 — cek POLARITAS, jangan hanya status code

Ini jebakan yang paling mahal di kelas ini. Sebuah endpoint bisa membalas **200 tanpa token** dan
**500 dengan token apa pun** — polaritas terbalik dari bypass. Itu **jalur kode rusak**, bukan
sinyal auth, dan tidak ada data di kedua keadaan.

Terukur pada host yang sama pada hari yang sama: satu endpoint berperilaku terbalik (200 tanpa
token, 500 dengan token) sementara endpoint lain di host yang sama justru terbuka tanpa auth dan
stabil 3x. **Uji polaritas tiap endpoint secara individual.** Aturannya:

```
200 tanpa token + 200 dengan token sampah  -> 200 sudah publik, bypass tidak membuktikan apa-apa
401 tanpa token + 200 dengan token sampah  -> BYPASS nyata, lanjut ke kontrol IDOR
200 tanpa token + 500 dengan token sampah  -> jalur rusak, BUKAN temuan
401 tanpa token + 500 dengan token sampah  -> jalur rusak, BUKAN temuan
```

`500` tidak pernah menjadi bukti apa pun kecuali bahwa handler-nya jalan — lihat §5 dan catatan
pitfall "generic 500 bukan information disclosure".

### Kontrol wajib #3 — bukti tulis dengan READ-BACK, dan perhatikan bentuk body

Untuk primitif tulis (publish/pesan/objek), `200 Sent` adalah klaim server. Buktinya adalah
**membacanya kembali** dari jalur baca yang sama, 3x:

```
run 1: publish -> 200 [1,"Sent","17934167610322324"]  read-back: ya
run 2: publish -> 200 [1,"Sent","17934167660586142"]  read-back: ya
run 3: publish -> 200 [1,"Sent","17934167714275400"]  read-back: ya
```

**Jebakan bentuk body menghasilkan negatif palsu.** Endpoint publish PubNub menolak
form-encoded `message=<json string>` dengan `400 [0,"Invalid JSON",...]` dan menerima **raw JSON
body** dengan `200 [1,"Sent",...]`:

```python
# SALAH - terbaca sebagai 400 dan disimpulkan "write diblokir"
req(url, "POST", {"message": json.dumps(payload)}, ctype="form")

# BENAR
req(url, "POST", {"text": "...", "type": "default"}, ctype="json")
```

Satu perubahan bentuk body adalah bedanya antara negatif dan High. **Sebelum mencatat "write
diblokir", ganti bentuk body dan ulangi.**

### Kontrol wajib #4 — asimetri read/write adalah diskriminator, bukan provenance

Pada keyset messaging, jangan simpulkan "baca tanpa auth = by design" sebelum menguji **tulis**-nya:

| keyset | baca history | publish | pembacaan |
|---|---|---|---|
| A | 200 readable | 200 Sent | demo keyset, tanpa PAM di mana pun → baca by design |
| B | **403 diblokir** | **200 Sent** | **PAM diterapkan untuk baca, tidak untuk tulis** |

Baris kedua adalah temuan. Kalau sebuah keyset **memang punya** Access Manager — baca storage-nya
menolak anonim dengan 403 — tapi jalur publish menerima mereka, vendor sudah membuat keputusan
otorisasi lalu gagal menerapkannya pada satu operasi. Itu bug, bukan default demo, dan bertahan
dari argumen "public subscribe key" karena key yang sama sudah digerbangi untuk baca.

**Jadi: sebelum membuang unauth keyset read sebagai by-design, uji tulis-nya.**

## 5. Anti over-claim

- Sink hidup ≠ sink bisa dieksploitasi. Laporkan "sink + filter bereaksi", jangan klaim bypass.
- Efek samping lab/env (NAT, container, proxy) tidak boleh masuk laporan.
- Tidak reproduksi 3x dengan sesi bersih = `UNSTABLE`, jangan lapor.
- Bedakan **PROVEN / PARTIAL / RETRACTED** di output. PARTIAL punya bukti untuk sebagian
  klaim saja (mis. pertanyaan security-question bocor, tapi takeover tidak diklaim).

## 5b. TIGA status, bukan dua: PROVEN / NEGATIVE / UNREACHABLE

Kesalahan taksonomi yang paling sering lolos ke laporan: menyebut host yang **tidak pernah bisa
dihubungi** sebagai "negative". Itu fabrikasi coverage. Ada tiga status, dan hanya satu yang
boleh disebut negatif:

| status | artinya | syarat | boleh masuk tabel coverage sebagai |
|---|---|---|---|
| **PROVEN** | kontrol menyala, efek terukur | ≥2 ronde bersih, artefak disimpan | temuan |
| **NEGATIVE** | probe **benar-benar mendarat**, kontrol berbeda hasilnya | respons diterima + kontrol pembeda jalan | "diuji, tidak rentan" |
| **UNREACHABLE** | koneksi tidak pernah terbentuk | `ConnectTimeout`, `SSLError`, `ConnectionError`, DNS mati | **"BELUM diuji"** — bukan negatif |

```python
# klasifikasi eksplisit di skrip probe, jangan biarkan exception jadi "bersih"
try:
    r = requests.get(u, timeout=12, verify=False)
    verdict = "NEGATIVE" if r.status_code in (401,403,404) else "CANDIDATE"
except (requests.exceptions.ConnectTimeout,
        requests.exceptions.SSLError,
        requests.exceptions.ConnectionError):
    verdict = "UNREACHABLE"        # JANGAN "NEGATIVE"
```

Kasus nyata (Telekom, 2026-10-29): `zot.tamarin.p5x4` (OCI registry) → ConnectTimeout;
`zipkin-uat.sdp` → ConnectTimeout; `zipkin-preview.sdp`, `zspi-sca-app`, `zspi-main-app` →
SSLError; `massenrecherche-vbs` → ConnectTimeout. Enam host, semuanya **firewalled atau
TLS-incompatible dari vantage point ini**. Ditulis sebagai `unreachable-from-here` di
`NEGATIVES.md`, dengan kalimat eksplisit *"NOT tested = NOT covered. Do not record as negative."*
Kalau digabung ke kolom negatif, tabel coverage akan berbohong tentang enam host sekaligus.

**Varian: scanner keluar 0 tapi prosesnya hidup.** `nuclei` yang menulis **0 baris jsonl**
sambil PID-nya masih berjalan 20+ menit bukan "0 temuan" — itu run yang belum selesai. Gerbang:

```bash
wc -l out.jsonl          # 0 baris?
ps -ef | grep -c "[n]uclei"   # proses masih ada?
# 0 baris + proses hidup = INCOMPLETE. Bunuh, jangan tunggu, jangan laporkan sebagai bersih.
```

Yang benar: jangan retry invokasi yang sama. Turunkan cakupan — `nuclei -u <satu-host>
-t http/exposures/configs/ -silent -jsonl` selesai <90 detik dan memberi hasil yang bisa
dipertanggungjawabkan, sedangkan `-tags` di atas seluruh template set adalah yang menggantung.

### 5c. Scanner balik 0: dua kontrol, dan cara membaca hasilnya

Sebelum sebuah `0` boleh masuk coverage, jawab dua pertanyaan terpisah — dan jangan gabungkan:

- **Kontrol A — engine-nya bisa match sama sekali?** `-tags tech` pada satu host yang pasti
  menyajikan service yang matchable. Wajib ≥1 hit.
- **Kontrol B — tag set yang dipakai benar-benar dieksekusi?** Jalankan tag set **real scan**
  pada **satu** host. Syarat: `Requests > 1000`, `Errors` di bawah beberapa persen, `Matched: 0`
  boleh diterima. Ini yang menangkap tag typo yang diam-diam men-select nol template.

| Kontrol A | Kontrol B | Real `Requests` | Real `Matched` | Verdict atas angka 0 |
|---|---|---|---|---|
| PASS | PASS | > 0 | 0 | **sah** |
| PASS | PASS | > 0 | ≥ 1 | **sah** — run memvalidasi dirinya sendiri |
| PASS | PASS | 0 | 0 | run rusak — target list kotor (lihat bawah) |
| FAIL | apa pun | apa pun | apa pun | buang, perbaiki invokasi |

**Baris kedua itu yang sering salah dibaca.** Kalau real scan menghasilkan `Matched: ≥1`, berarti
engine **benar-benar menembak selama run itu**. Scanner yang tidak mengirim apa pun tidak bisa
match apa pun — jadi angka 0 tetap sah untuk target/template yang tidak match, dan kontrol yang
tampak gagal itu murni bug kontrol. Terukur 2026-10-30 (`relay.link`, satu run):

```
CONTROL (-tags waf-detect, 13 host) -> Templates loaded: 1, 309 ms, Matched: 0    [INVALID]
REAL    (8 tag, 13 host)            -> Requests: 31702/38493, Matched: 1, Errors 997 (3.1%)
```

Kontrol itu **bukan kontrol**: satu template, 309 ms, tidak mungkin menguji pipeline tag.
Jangan buang run yang sehat hanya karena kontrol yang kamu tulis sendiri jelek.

**Jalankan dua kontrol sebagai invokasi terpisah**, bukan sebagai baris selipan di dalam skrip
scan. Kontrol yang ditanam dalam skrip panjang mewarisi host list dan tag string yang kebetulan
dibangun skrip itu — persis bagaimana "kontrol" satu-template 309 ms bisa tertulis di run yang
real scan-nya sehat.

**Target list kotor adalah penyebab tersembunyi `Requests: 0/0`.** `httpx -o` menulis
`URL [200] [tech]`, bukan URL murni; nuclei mem-parse tiap baris sebagai URL, gagal pada metadata
trailing, dan **membuang target tanpa error** — sementara `Targets loaded: 13` membuatnya terlihat
diterima. Gerbang:

```bash
grep -cE '^https?://[^ ]+$' targets.txt   # harus == wc -l targets.txt
awk '{print $1}' live.txt | grep -E '^https?://' | sort -u > live-urls.txt
```

`Matched: 0` dengan `Requests: 0/0` bukan target bersih — itu tidak ada scan sama sekali.

**Sebutkan penyelesaian, bukan hanya hasil.** `Requests: 31702/38493 (82%)` + `Scan completed in
52m` adalah run selesai, tapi 18% request terencana tidak pernah dieksekusi. Tulis "82% of planned
requests" di baris coverage, jangan "full scan".

**Kalimat penutup yang jujur** untuk coverage campuran:
`N proven, M tested-negative, K unreachable (belum diuji), L belum dijalankan` — bukan
"aman" dan bukan "0 temuan".

## 6. Format laporan yang diminta operator

Setelah verifikasi, sajikan:

1. **Proses** per ronde — apa yang gagal dan apa yang diperbaiki (bukan hanya hasil akhir).
2. **Tabel kelas → bukti nyata**, satu baris per kelas, kutip artefak aslinya
   (`uid=33`, hash md5, jumlah order, isi `/etc/passwd`).
3. **Yang DITARIK** secara eksplisit, beserta alasan kontrolnya.
4. **COVERAGE**: `diuji: ...` dan `BELUM diuji: ...` dengan alasan (app tidak expose, dll).
5. Skrip re-run agar hasil bisa direproduksi.

Jangan menutup dengan "aman/terkunci rapi" — tutup dengan angka: `N proven, M partial, K retracted`.

## 7. File pendukung

- `references/gate-self-test.md` — versi kelas yang sama untuk **GATE/harness**, bukan probe:
  **sweep seluruh toolkit dulu** (jangan perbaiki gate satu per satu saat gagal — bug konvensi itu
  sistematis), two-sided gate test (positive + 2 negatif), kenapa `BLOCKED`/`not found` untuk sesuatu
  yang ada itu **cacat gate**, readiness smoke-test yang membuat pipeline menghasilkan artefak (dan
  kenapa smoke test yang semua-hijau itu rusak), serta aturan "jangan melemahkan gate yang benar".

- `references/severity-matrix-verification.md` — **RESOLVED 2026-10-30: all four levels pass
  (4/4 matrix), but only after seven gate defects were fixed — before them the same matrix gave 0
  survivors.** Matriks uji 4-severity yang WAJIB dijalankan sebelum pakai pipeline di program yang
  membayar Low/Medium, syarat per level (Critical/High tanpa tambahan; Medium butuh `chain_analysis`
  atau `next_to_hunt`; Low harus terminal atau punya link bernama), 5 negative control yang harus
  tetap ditolak, tujuh cacat gate (symptom → fix), fixture shape yang membuat matriks bermakna, dan
  aturan: **melemahkan gate untuk memperbaiki false-negative tanpa menjalankan ulang negative control
  = mengganti gate rusak dengan karet stempel.** Harness: `audit-pipeline-operations/scripts/severity_gate_regression.py`.

- `references/substrate-pallet-audit-note.md` — versi kelas yang sama untuk audit **source
  code** (bukan web probe): artefak pengukuran yang memalsukan negatif di repo Rust/FRAME,
  dan cara membedakan "belum diuji" dari "tidak ada".

- `references/owned-infra-quota-proof.md` — resep lengkap §2g: clone upstream pinned, harness
  `Module._load` (3 jebakan config/stub), kerangka `file:line` call-site, diferensial dua
  container `--cpus 0` vs `--cpus 0.1` dengan counter cgroup, CGI + nginx + cloudflared untuk
  endpoint bukti publik, dan 8 pitfall nyata (pkill membunuh PID 1, `docker stats` menipu,
  `MSYS_NO_PATHCONV`, QUIC diblok → `--protocol http2`).

- `references/payment-callback-auth-probing.md` — kelas **payment callback / webhook auth**: cara
  menemukan route-nya (nama path = nama provider, bukan kata kamus), membaca skema auth dari pesan
  error ("Missing signature header" vs "Invalid signature" = nama header bocor), matriks forgery
  lengkap (HMAC/type-juggling/transport/oracle) yang WAJIB dijalankan penuh walau akhirnya ditolak,
  empat temuan Low/Medium yang tetap sah ketika kripto-nya kencang (DTO disclosure sebelum auth,
  oracle, guard tak konsisten antar controller, kanal QA live di produksi), dan aturan kejujuran
  khusus kelas ini (route located ≠ vuln; forge hanya ke `customer_uid` sendiri; berhenti di uji
  return-URL).

- `references/offchain-claim-signature-binding.md` — sisi **keluar**: endpoint yang memberi klien
  digest untuk ditandatangani lalu melepas dana (`/claim`, `/withdrawals/request`, `/execute`).
  Probe binding signature (minta claim wallet orang lain → tanda tangan dengan key sendiri →
  `400 Invalid signature` = terikat benar, `200` + steps = temuan S3/S4 — **jangan broadcast**),
  tell "recipient inversion" (request yang *benar* gagal sementara yang mencurigakan sukses),
  matriks penegakan API-key lengkap (≥8 varian; pesan `Missing` vs `Unauthorized` BUKAN oracle),
  urutan validasi-body vs auth (400 ≠ unauthenticated — pakai body schema-valid), aritmetika
  quote/appFees yang harus diverifikasi numerik, decode calldata vs nilai yang ditampilkan, dan
  probe namespace RPC node (`rpc_modules` → `admin_*`/`personal_*`/`debug_*`; RPC baca publik =
  by design).
- `references/juice-shop-dvwa-probe-recipes.md` — resep per-kelas yang sudah terbukti di
  Juice Shop 20.3.0 + DVWA 1.10 (payload, angka kalibrasi, trap token/field-name).
- `references/scanner-template-porting.md` — memindahkan PoC Python ke template nuclei/ffuf:
  reach test, jebakan `%3B`/`\\d`/cookie-case/`{{var}}`, kenapa `-mc 200` salah di sink
  proxy, uji paired low-vs-impossible, bukti OOB untuk sink blind, dan desain target
  internal-only agar bukti SSRF tidak bisa dipalsukan.

## 8. Skill terkait (jangan duplikasi isinya)

- `exploit-depth` — tangga L0→L5 dan eskalasi per kelas (hulu dari skill ini).
- `local-vuln-lab` — daftar lab dan cara menjalankannya.
- `triage-validation` — 7 pertanyaan sebelum menulis laporan.
- `evidence-hygiene` — cara menyimpan/menredaksi bukti.

## Absorbed playbooks (complete sub-packages under `references/`)
- `references/fuzzing-coverage-integrity/PLAYBOOK.md` — the two bugs that make ffuf lie (default
  matcher ignores HTTP 400; a leading slash in the wordlist doubles the path), the mandatory sanity
  gate that proves the harness can see a known-live endpoint, how auth level shifts status codes,
  and the three independent corroborations required before writing a negative.
