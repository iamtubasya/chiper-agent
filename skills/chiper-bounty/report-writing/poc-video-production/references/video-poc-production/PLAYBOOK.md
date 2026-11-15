---
name: video-poc-production
description: "Produce a video proof-of-concept (screen recording + live HTTP evidence) when a triager or vendor asks for a 'video PoC' with a report. Covers the three routes (re-runnable exploit / CLI-API / static PDF), the capture-to-MP4 pipeline (curl transcripts, PIL terminal frames, Playwright browser recording, ffmpeg composite + concat), and the verification step that catches truncated segments and letterboxed frames before you ship."
version: 1.0.0
author: RESEARCHER_NAME
license: MIT
metadata:
  hermes:
    tags: [video, poc, ffmpeg, playwright, evidence, bug-bounty, report]
---

# Video PoC production

Dipakai ketika triager/vendor minta **"video PoC"** untuk laporan yang sudah ada. Terjadi pada
Todoist DCR 2026-10. Vendor sering minta video setelah laporan teks masuk, jadi ini kerjaan
lanjutan — bukan bikin temuan baru.

## Prinsip yang tidak bisa ditawar

1. **Semua isi video harus berasal dari capture nyata.** Output terminal = respons HTTP mentah dari
   perintah yang ditampilkan di frame itu. Kalau tidak bisa menjalankan ulang, jangan mengarang.
2. **Bahasa Inggris.** Artefak eksternal wajib Inggris (caption, kartu judul, komentar).
3. **Redact rahasia asli.** `client_secret`, token, API key → tampilkan `xxxx...[REDACTED, N chars]`.
   Nilai yang jadi bukti demo boleh tampil; kredensial hidup tidak.
4. **Jangan lakukan interaksi korban.** Berhenti di titik terakhir yang aman (mis. halaman login).
   Tulis di kartu penutup: "No victim account was created or used."
5. **Domain reserved, bukan infra nyata.** `*.example.com`, `*.test`, `attacker.test` — jangan pakai
   domain yang benar-benar kamu kontrol, nanti dianggap infra penyerang sungguhan.
6. **Catat state yang kamu buat.** Setiap klien/akun/objek yang lahir untuk rekaman harus dilaporkan
   ke user untuk di-revoke, beserta ID-nya.

## Tiga rute — pilih yang paling kuat

Tanyakan: **eksploitasinya bisa dijalankan ulang sekarang?**

| Rute | Kapan | Hasil |
|---|---|---|
| **A. Browser nyata** | target web, ada UI/redirect yang perlu dilihat | Playwright rekam native → bukti hidup. Paling meyakinkan. |
| **B. HTTP/CLI nyata** | eksploitasi lewat API/CLI | Render gaya terminal dari transkrip curl nyata + highlight. |
| **C. PDF statis saja** | tidak bisa diulang, cuma ada PDF | Halaman PDF di-render + zoom/pan + caption. **Ini slideshow, bukan PoC** — bilang ke user bahwa triager sering menganggapnya kurang. |

**⛔ TERMINAL SEGMEN: rekam terminal ASLI, jangan frame render.** Operator menegaskan dua kali
(2026-10-16, korreksi langsung): *"buat pakai terminal asli, karna ini nampak di render, bakal d
tolak videonya."* Frame terminal yang di-PIL dari transkrip nyata (walau isinya output sungguhan)
**ditolak triager** karena kelihatan dirender — jadi rute B (render sintetis) itu untuk kartu
judul/komentar saja, BUKAN untuk segmen bukti terminal. Untuk segmen bukti, gunakan **rute E**
(mintty nyata + keystroke nyata, lihat `report-writing/poc-video-production` Route E): window
`mintty` dari Git for Windows, `-o ThemeFile=monokai-dimmed`, `PS1='$ '` lewat `--rcfile`, isi grid
`-s COLSxROWS`, `SendInput` unicode 75ms±jitter + `VK_RETURN`, lalu **gulir via scrollbar (drag
thumb)** — mintty mengabaikan wheel event sintetis dan Shift+PageUp. Panaskan interpreter dulu
(`python3 -c "pass"`, baru `clear`) sebelum `ffmpeg` mulai, dan **QA-gate tiap take dengan OCR**
(invert teks terang-di-gelap → tesseract) menegaskan string disclosure benar-benar ada di frame;
ulangi rekaman kalau gagal. Render = kartu; terminal = rekaman jendela nyata.

**Rute D (browser chrome, tervalidasi 2026-10):** kalau buktinya ada di *browser chrome* —
terutama panel **DevTools Network** (request headers tanpa Authorization) — Playwright tidak bisa
merekamnya (DevTools adalah view WebUI terpisah, tidak pernah masuk `record_video`). Untuk kasus itu
rekam jendela browser ASLI: `ffmpeg -f gdigrab`, koordinat klik dibaca dari DOM (shadow-root piercing)
dan divalidasi dengan *self-checking click*, input dikirim via ctypes `SendInput` (ingat: struct
`INPUT` x64 harus 40 byte union — keyboard struct yang dibuat sendiri gagal diam-diam). Resolusi
desktop1366×768 → crop baris taskbar lalu `increase`+`crop` ke kanvas 1920×1080. Resep lengkap +
helper siap pakai ada di skill kembar `report-writing/poc-video-production`:
`skills/report-writing/poc-video-production/references/windows-screen-recording.md` dan `skills/report-writing/poc-video-production/scripts/win32_input.py` (juga catatan: verifier bawaan
punya region model sendiri — expected boundary harus dihitung dari *perubahan tag*, bukan awal
segmen, karena dua segmen bertag sama menyatu jadi satu span).

## Pipeline

```
1. capture   → jalankan perintahnya, simpan headers+body ke file (jangan ketik ulang!)
2. render    → frame PIL 1920x1080 (kartu + terminal + band komentar) → pipe ke ffmpeg
3. composite → rekaman Playwright + overlay address bar asli + caption → mp4
4. concat    → semua segmen, fps disamakan
5. VERIFY    → sampling piksel per timestamp (wajib, lihat bawah)
```

Skrip kerja lengkap ada di `references/video-poc-pipeline.md` — salin dan sesuaikan.

## Pitfall yang benar-benar kejadian

**Playwright merekam viewport saja — tanpa address bar.** Padahal untuk temuan OAuth/redirect,
"domainnya tetap target.com" adalah inti argumennya. Solusi: rekam viewport, lalu composite
address bar sendiri dengan URL **asli** hasil `page.url()` / header `Location`. Jangan mengarang URL.

**Campur fps merusak timeline concat.** Rekaman Playwright keluar 25 fps; segmen PIL 30 fps. Setelah
concat, segmen browser terpotong jadi ~8 detik dan kartu penutup melebar jadi 20 detik — total durasi
tetap benar, jadi kelihatan sehat kalau tidak diverifikasi. Paksa `fps=30` di setiap segmen DAN
`-r 30 -fps_mode cfr` saat concat.

**`-vsync` sudah dihapus di ffmpeg 9.x.** Pakai `-fps_mode cfr`.

**MemoryError saat render frame PIL.** 1920x1080 RGB = 6,2 MB per frame; 500 frame = 3 GB dan box
6 GB akan mati. Render sebagai **generator**, tulis tiap frame langsung ke stdin ffmpeg
(`-f rawvideo -pix_fmt rgb24`), jangan pernah menampung list frame.

**Koordinat `overlay` relatif ke rantai saat itu, bukan ke canvas.** Menaruh bar di `y=0` setelah
`scale+pad` akan menimpa bagian atas video, bukan duduk di atasnya. Bikin canvas eksplisit dulu
(`color=c=0x0D1117:s=1920x1080:d=1[bg]`), baru `[bg][base]overlay=0:BAR_H`.

**Letterbox/pillarbox merusak kualitas.** `force_original_aspect_ratio=decrease` + `pad` menyisakan
bar gelap (21% di kasus nyata). Pakai `increase` + `crop` supaya halaman mengisi penuh.

**Vision tool belum tentu bisa QA hasil render.** Kalau tidak bisa melihat gambar, verifikasi
deterministik: ambil teks DOM dari halaman (Playwright `inner_text`), dan statistik piksel
(komposisi terang/gelap, bbox logo, densitas tepi). Itu lebih dapat dipercaya daripada vision.

**⛔ `gdigrab` WAJIB dibatasi durasi (`-t <dur>`), jangan di-stop manual.** Ini yang paling sering
merusak rekaman. Kalau `ffmpeg -f gdigrab` dibiarkan berjalan lalu di-`kill` (atau dikirimi
SIGINT/SIGTERM dari shell MSYS/Git-Bash), **moov atom tidak pernah ditulis** dan file MP4 hasilnya
korupsi total — `ffprobe` menjawab `moov atom not found` dan **tidak bisa di-repair** dengan
`ffmpeg -i corrupt.mp4 -c copy fixed.mp4` (input-nya sendiri yang gagal dibuka). Satu jam rekaman
hilang.

Cara benar — biarkan ffmpeg **selesaikan sendiri**:

```bash
ffmpeg -hide_banner -loglevel warning -f gdigrab -framerate 15 -draw_mouse 1 \
       -t 300 -i desktop -vf "scale=1280:720" \
       -c:v libx264 -pix_fmt yuv420p -preset ultrafast -movflags +faststart \
       -y F1-screen-recording.mp4
```

`-t 300` = 5 menit lalu exit bersih. Ukur dulu berapa lama siklus PoC-mu butuh (fetch → solve →
submit), lalu set `-t` sedikit di atasnya. Kalau ternyata butuh lebih lama, ambil **dua klip** dan
concat — jangan pernah memperpanjang rekaman yang sudah jalan.

Kalau terpaksa harus menghentikan lebih awal, hentikan proses Windows-nya secara eksplisit, bukan
lewat sinyal bash:

```bash
MSYS_NO_PATHCONV=1 /c/Windows/System32/taskkill.exe /F /PID <pid>
```

(`taskkill` biasa dari MSYS gagal dengan `Invalid argument/option - '//F'` karena MSYS mengubah
`/F` jadi path — `MSYS_NO_PATHCONV=1` mematikan konversi itu. Tapi tetap: korupsi moov sudah terjadi
sebelum taskkill jalan, jadi ini hanya untuk membersihkan proses, bukan untuk menyelamatkan file.)

Setelah build, **selalu** verifikasi sebelum menganggap rekaman ada:

```bash
ffprobe -v error -show_entries format=duration,size \
        -show_entries stream=codec_name,width,height -of default=noprint_wrappers=1 out.mp4
```

Durasi harus mendekati `-t` yang diminta (300s → ~300.000000) dan `codec_name=h264`. Kalau muncul
`moov atom not found`, file itu tidak ada — rekam ulang, jangan coba repair.

**Dimensi ganjil bikin encode gagal diam-diam.** `gdigrab` desktop 1264×693 → `yuv420p` butuh
genap. Tambahkan `-vf "pad=ceil(iw/2)*2:ceil(ih/2)*2"` (atau `scale=1280:720` yang sudah genap).
Gejalanya `libx264 ... Could not open encoder before EOF` dan file 0 byte.

**Rekam browser ASLI, bukan slideshow.** Kalau buktinya adalah widget/CAPTCHA/alur login, rekam
jendela browser sungguhan (`gdigrab` + SeleniumBase/CDP mengendarai halaman, mouse cursor asli via
`-draw_mouse 1`). Kartu PIL berannotasi bagus sebagai pengantar, tapi **bukan** pengganti rekaman —
vendor bisa menolaknya sebagai fabricated. Kalau hanya punya slideshow, katakan terus terang ke user
sebelum dikirim.

### VERIFY juga KONTEST-nya, bukan hanya pikselnya

Verifikasi piksel menangkap video rusak. Ia **tidak** menangkap video yang bagus tapi menjelaskan
hal yang salah. Dua kegagalan nyata (do.de ALTCHA PoW, 2026-10-26) yang keduanya ditemukan vendor:

1. **Screenshot dari run yang berbeda.** Laporan mendeskripsikan widget berakhir di state
   `expired`, tapi screenshot yang dilampirkan menunjukkan state **`Verified`** — diambil dari run
   sebelumnya di sesi yang sama. Vendor: *"F1-widget-expired.png shows the widget in the 'Verified'
   state, rather than the reported 'Verification expired' state."**
   Aturan: **satu artefak = satu run = satu nama file yang menyebut run-nya**
   (`F1-run3-widget-expired.png`, bukan `F1-widget-expired.png`). Baca state DOM dan screenshot
   **dalam tool call yang bersamaan**, dan sebelum submit buka lagi setiap gambar sambil membaca
   paragraf laporan di sebelahnya.

2. **Timestamp dari loop polling, bukan dari sistem.** Laporan klaim token "expired 66 s sebelum
   widget selesai", diturunkan dari `Date.now()` saat agent polling DOM — 127 s setelah klik karena
   jarak antar-panggilan observasi. Vendor hitung ulang dari `expiresAt` challenge + waktu klik dan
   menunjukkan masih ada ~61 s validity saat klik. Angkanya artefak instrumen, bukan sifat target.
   Aturan: **pakai field jam milik sistem** (`expiresAt`, `issuedAt`, header `Date`, `solution.time`
   di dalam payload). Kalau terpaksa pakai jam sendiri, tulis basis pengukurannya ("as read at
   16:23:37") dan sertakan nilai mentahnya supaya triager bisa menghitung ulang.

## VERIFY — langkah yang tidak boleh dilewati

Build sukses ≠ video benar. Extract frame di timestamp yang diketahui dan ukur:

- **band komentar ada di setiap segmen** → bright piksel di strip bawah
- **typing animation jalan** → ink di body naik bertahap
- **segmen browser full-frame** → tidak ada strip gelap di kiri/kanan
- **transisi segmen tepat** → bandingkan dengan akumulasi durasi segmen

Kasus nyata: build melaporkan sukses, tapi segmen browser cuma 8 detik dan ada pillarbox 21%.
Keduanya ketangkap hanya karena sampling piksel.

## Spesifikasi deliverable

MP4 · H.264 (`libx264`) · `-pix_fmt yuv420p` · 1920x1080 · 30 fps · `-movflags +faststart` ·
**tanpa audio** (kecuali diminta narasi) · durasi 60-120 detik · caption Inggris menyatu di video
(bukan file .srt terpisah, supaya jalan di player apa pun).

`faststart` penting: portal vendor sering streaming, bukan download.

## Struktur video yang terbukti

```
0:00  kartu judul       judul, target, endpoint, severity, peneliti, tanggal
0:05  langkah 1         aksi utama (registrasi/request) → respons sukses, highlighted
0:20  kontrol A         bukti hal yang seharusnya menghalangi memang tidak ada / salah jenis error
0:27  langkah 2         aksi lanjutan
0:37  kontrol B         kontrol positif yang ada tapi sia-sia (kalau ada)
0:46  browser nyata     konsekuensi yang bisa dilihat mata
1:01  kartu penutup     dampak + pernyataan tidak ada akun korban dipakai
```

Band komentar di bawah layar di **setiap** segmen — ini yang user minta eksplisit ("buatkan komentar
di dalam video bisa?"). Kalau tidak diminta pun, tambahkan: triager menonton tanpa audio.

## Kalau langkah di video berbeda dari laporan PDF

Ini yang paling penting: **jangan diamkan.** Kalau saat produksi video ketemu bahwa langkah di
laporan tidak akurat (host salah, endpoint berubah, klaim yang tidak terbukti), hasilkan tiga hal:

1. Video yang mengikuti jalur **yang benar-benar jalan**.
2. Ringkasan langkah terkoraksi (plain text, siap tempel ke submission) — jelaskan apa yang berubah
   dan mengapa, plus tabel perbandingan.
3. PDF versi baru dengan seksi terbuka "Correction to the previous submission" + tegaskan apakah
   koreksinya mengubah kerentanan atau tidak.

Jangan sembunyikan perbedaan itu; kalau triager mereproduksi langkah lama dan gagal, laporan bagus
bisa ditolak. Lihat `references/correcting-a-submitted-report.md`.
