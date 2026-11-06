# Data-exposure lookalikes & third-party bucket ownership

Sumber: sesi 2026-10-13 (estate `apnic.net` + `blink-staging` S3/GCS). Semua angka di bawah terukur,
bukan contoh karangan. Dipakai bersama §L di SKILL.md.

Aturan operator yang memicu berkas ini: *"jgn kasih 500-403-400-200, tp kasih sy bukti kalau itu ad
impact kerasnya, spt data leak, idor, bola, ato rce, dsb nya, jadi harus buktikan ada sesuatu yg
didapat dari temuan tsb dan berimpact negatif"*.

---

## 1. SPA catch-all — 200 untuk SEMUA path

| host | path diuji | hasil |
|---|---|---|
| `bcap.apnic.foundation` (nginx/1.24.0) | `/`, `/pdms-web`, `/api`, `/actuator/health`, `/swagger-ui.html`, `/v3/api-docs`, `/login` | **606 B identik, 200** (kecuali `/api` = 404 0 B) |
| `app-qawolf.coderabbit.ai` | `/api/health`, `/api/version`, `/api/subscriptions`, `/api/reviews`, `/healthz`, `/version` | **14 654 B identik, 200** |

**Diskriminator 2 request:** kalau dua path yang tak berhubungan balas panjang byte yang sama →
app-shell. Route asli hanya ada di bundle JS (`/assets/revalidated/main-<hash>.js`), dan bundle itu
memakai *dynamic import* (`import("./chunk-<hash>.js")`) sehingga daftar endpoint harus dibaca dari
chunk, bukan dari string literal di main.js.

Bentuk chunk CodeRabbit yang informatif (pola nama = peta fitur, pakai ini sebagai hipotesis uji):
```
startup-dependencies~main~SsoOAuthCallback~index~AzureDevOpsTenantLogin~ClerkCallback~Gerri~<hash>.js
startup-dependencies~main~SsoOAuthCallback~index~VSCodeExtensionAuth~CLITokenAuth~AzureDevO~<hash>.js
startup-dependencies~main~ChangeStackLoginRedirect~SsoOAuthCallback~index~VSCodeExtensionAu~<hash>.js
```
⇒ kandidat kelas uji: `SsoOAuthCallback` (open redirect / code interception), `CLITokenAuth`
(penerbitan token tanpa sesi web), `AzureDevOpsTenantLogin` (tenant confusion).

## 2. Regex "hard data" di atas HTML = false positive yang dijamin

Run pertama mencetak `<<< DATA` untuk shell SPA karena pola `"(id|email|name|token|key)":` cocok
dengan **komentar di dalam bundle** (`// Ca…`). Aturan:
```python
try:
    j = json.loads(body); items = len(j) if isinstance(j, list) else len(j.get('data') or j)
except Exception:
    items = None          # bukan JSON ⇒ TIDAK BISA jadi hard-data
hard = items is not None and items > 1        # atau key record eksplisit
```

## 3. Reachability objek "KYC" tanpa mengunduh dokumennya

Objek yang namanya mengandung `driving_licence_user` bisa dibuktikan **tersedia publik** tanpa
mengambil isinya:

```bash
curl -sI "https://<bucket>.s3.amazonaws.com/571/driving_licence_user/<file>.jpg"
# HTTP/1.1 200 OK | Content-Length: 2268156 | Content-Type: image/jpeg | ETag "68efe2…"
curl -s -r 0-3 "<url>" | xxd | head -1      # ffd8ffe0 = JPEG asli, bukan placeholder
curl -sI "<url-tidak-ada>"                   # kontrol: 404  ⇒ per-objek, bukan blanket cache
```

Catatan jujur yang WAJIB ditulis saat melaporkan: objek yang namanya KYC **belum tentu** berisi KYC.
Bukti: 96 sampel dari 8 keluarga dokumen → hanya **76 hash unik**, dengan `operational_driving_licence/
download_1658378998.jpeg` muncul **6×** dan `bank_statement_photo/nature3jpg_*.jpg` 3× (nama stok).
Satu PDF di folder `driving_licence_user` **asli** (bukan placeholder) terbukti dari metadata internal:
```
title/subject = "ACT Drivers License" | author = "CamScanner" | producer = "intsig.com pdf producer"
2 halaman × embedded JPEG (1876×1164, 1960×1208)
```
⇒ cara membedakan scan asli dari template: `pdftotext` + `pymupdf` (`page.get_images()`), cek
`author/producer` (CamScanner/scan app) dan jumlah gambar tertanam. Nama file `DmmyPDF1`, `samplepdf`,
`NETCCLogo1`, `pexels-*`, `nature*`, `icon`, `download*`, `images*` = placeholder.

## 4. Kepemilikan bucket pihak-ketiga — tes 3 langkah

Bucket bernama sama dengan target belum tentu milik target. Terukur pada `blink-staging` (bocor
**60 000+ key listing**, termasuk folder bernama `drivers_licence_user`, `bank_statement_photo`,
`customer_signature` — yang tampak persis seperti KYC exposure):

1. **Objek non-PII yang diunduh menyebutkan bisnis siapa.** `/var/www/html/blink/backend/uploads/
   jobs170/terms_and_condition/terms_and_condition.pdf` = *"Solar PV Sale and Installation Agreement —
   Clean Energy Council Limited"*; lalu `additional_attachment_email1430/Retailerpermissionupdatesspv_*.txt`
   = *"register STC … retailer … installation job summary"* + kalimat *"installation done **blink** can
   perform after installation"*. ⇒ pemilik = produk bernama "Blink" **untuk solar/STC Australia**
   (`blinkecosystem.com.au`), BUKAN Blink Technologies (Bitcoin, Próspera) yang sedang diaudit.
2. **Namespace XML memisahkan cloud.** Listing GCS ber-`xmlns='http://doc.s3.amazonaws.com/2006-03-01'`;
   listing AWS ber-`xmlns="http://s3.amazonaws.com/doc/2006-03-01/"`. Bucket yang sama bisa ada di dua
   cloud: `blink-staging` **200 di keduanya**, sementara `blink-web`/`blink-dev` cuma ada di GCS
   (AWS balas `404 NoSuchBucket`) — dan listing lama saya sempat mencampur keduanya sebagai satu bucket.
3. **Kontrol bucket sejenis.** `blink` → `403 AccessDenied` (bukan terbuka) sementara `blink-staging` →
   `200` listing; jadi yang bocor memang salah konfigurasi, bukan default platform.

Konsekuensi: temuan ini **DROP** dari laporan target (aturan "menyerang pihak ketiga di luar scope =
engagement hangus"), dan yang dicatat hanya *excluded — third-party bucket, owner = <produk lain>*.
Kalau pemiliknya dicari untuk disclosure tersendiri: urlscan (`domain:<bucket-host>`), GitHub code
search & grep.app untuk nama field upload yang khas, landing page di dalam bucket, `?location/?acl/?policy`
(403 di kasus ini) — semua bisa nol hasil, dan itu jawaban yang sah.

## 5. Jebakan operasional yang muncul di sesi yang sama

- **`naabu -list <(sed …)` gagal `[FTL] Could not run enumeration: open /dev/fd/63`** (process
  substitution tidak jalan untuk exe native di MSYS). Tulis file nyata (`sed … > hosts.txt`) lalu
  `naabu -list hosts.txt`. `httpx`/`katana` dengan `<(...)` punya mode gagal senyap yang sama.
- **S3 key JANGAN di-URL-encode.** `%2F` dianggap bagian dari nama key ⇒ `404 NoSuchKey`; dengan path
  biasa objek yang sama balas `200`. Ini sempat membuat kesimpulan "objek KYC tidak terjangkau" yang
  salah dan harus diretraksi.
- **Hitung ulang penuh sebelum menyimpulkan "60 000+ key"**: paginasi 118 halaman `max-keys=1000`
  = 117 706 key, `complete=True`; file enumerasi 8,4 MB. Jalankan di background dengan log progres —
  loop inline 180 s timeout.
- **Orchestrator menimpa bukti recon Anda.** `recon-evidence/recon-subfinder.txt` (5 027 baris) ditulis
  ulang menjadi 9 baris oleh langkah `_recon_record_usage` milik orchestrator yang menulis file dengan
  nama sama. Simpan hasil recon Anda di **direktori terpisah** (`D:/data/hermes/<target>-recon/`) dan
  salin hanya setelah pipeline selesai.
