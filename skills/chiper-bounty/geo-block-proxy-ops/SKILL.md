---
name: geo-block-proxy-ops
version: 1.0.0
author: RESEARCHER_NAME
description: >-
  Get past geo-blocks, VPN walls and registration gates during authorized testing.
  Covers the tool matrix (CloakBrowser geoip/proxy, Camoufox, WARP, proxychains),
  fingerprint consistency rules, and the escalation ladder when signup is blocked.
metadata:
  hermes:
    tags: [security, proxy, geo-block, vpn, registration, fingerprint, bug-bounty]
---

# Geo-Block & Proxy Ops — mendaftar akun saat target memblokir wilayah

**Tesis:** geo-block bukan temuan keamanan — itu **penghalang operasional**. Tugasmu
melewatinya secara sah (kamu punya izin menguji target), lalu tetap menguji.

---

## 1. Matriks alat (status host, terverifikasi 2026-10-22)

| alat | bisa apa | status | kapan dipakai |
|---|---|---|---|
| **CloakBrowser** | `proxy` + `timezone` + `locale` + `geoip` — **semua sekaligus** | ✅ terpasang | **pilihan utama** — fingerprint konsisten |
| **Camoufox** | stealth Firefox; geoip via konfigurasi | ✅ terpasang | alternatif; bot-detection lebih baik |
| **WARP (Cloudflare)** | VPN penuh sistem | ✅ `warp-cli` ada | kalau target blokir di level IP/negara |
| **proxychains** | SOCKS/HTTP per-perintah | ❌ belum | untuk `curl`/tool CLI |
| **browser_exec** | CDP biasa | ✅ | kalau tak ada geo-block |

**Kenapa CloakBrowser utama:** dia mengubah **proxy + zona waktu + locale + geoip
bersamaan**. Kalau cuma ganti IP (VPN) tapi timezone tetap `Asia/Jakarta` dan locale
`en-US`, itu **inkonsistensi** — mudah dideteksi. Konsistensi = lolos.

---

## 2. Aturan konsistensi fingerprint (WAJIB)

Saat mendaftar akun dari wilayah yang berbeda, **semua sinyal harus menunjuk ke wilayah
yang sama**:

| sinyal | harus cocok dengan |
|---|---|
| IP address | negara target |
| `timezone` | zona waktu negara target |
| `locale` / `Accept-Language` | bahasa negara target |
| `geoip` (browser API) | negara target |
| alamat yang diisi di form | negara/daerah target |
| nomor telepon (kalau diminta) | format negara target |

**Aturan praktis:** kalau target di Jerman, pakai IP Jerman + `Europe/Berlin` +
`de-DE` + alamat Jerman. **Jangan** IP Jerman dengan timezone Jakarta.

---

## 3. Alur kerja

### Langkah 1 — cek jenis blokirnya
```bash
# a. blokir IP/negara (HTTP 403 dengan pesan geo)
curl -s -o /dev/null -w "%{http_code}\n" https://target.com/signup
# b. blokir di level DNS (NXDOMAIN dari lokasi kamu)
dig +short target.com
# c. blokir hanya di halaman pendaftaran (aplikasi lain bisa)
curl -s https://target.com/signup | grep -iE "not available|region|country"
```
**Penting:** tentukan **level** blokirnya. DNS-level butuh VPN; aplikasi-level cukup
proxy browser.

### Langkah 2 — pilih alat sesuai level

| level blokir | alat |
|---|---|
| DNS / IP negara | **WARP** (sistem penuh) |
| Halaman/aplikasi | **CloakBrowser** dengan `proxy` + `geoip` + `timezone` + `locale` |
| Bot-detection (Cloudflare/DataDome) | **CloakBrowser** atau **Camoufox** + proxy residensial |
| Hanya butuh nomor telepon asing | layanan SMS sekali-pakai (lihat catatan etika) |

### Langkah 3 — jalankan dengan fingerprint konsisten
```python
from cloakbrowser import launch

b = launch(
    headless=True,
    proxy="http://user:pass@de-proxy:8080",     # IP negara target
    geoip=True,                                  # browser API ikut negara proxy
    timezone="Europe/Berlin",                    # zona waktu sama
    locale="de-DE",                              # bahasa sama
)
p = b.new_page()
p.goto("https://target.com/signup")
```
**Verifikasi konsistensi sebelum lanjut:**
```bash
# cek IP & geo terdeteksi
curl -s https://ipinfo.io   # via proxy yang sama
# cek timezone & locale di browser
#   p.evaluate("() => Intl.DateTimeFormat().resolvedOptions().timeZone")
#   p.evaluate("() => navigator.language")
```

### Langkah 4 — daftar akun (disiplin)

```
✓ Pakai email sekali-pakai yang kamu kuasai (mail.tm / disposables)
✓ Isi form dengan data yang KONSISTEN dgn wilayah proxy
✓ Simpan kredensial ke identities/<label>.json (identity_harness)
✗ JANGAN pakai data orang lain / identitas palsu yang meyakinkan
✗ JANGAN akun yang melanggar ToS target (baca policy dulu)
```

**Catatan etika & hukum:** kamu boleh membuat akun uji dengan **data milikmu sendiri**
(email + nama samaran). Jangan memalsukan identitas orang nyata, jangan pakai kartu
kredit orang lain, dan jangan lakukan kalau policy target melarang pendaftaran dari
wilayah tersebut — kalau melanggar, tandai surface itu `not-tested` dengan alasan.

### Langkah 5 — verifikasi & lanjut audit
```bash
# setelah akun jadi, capture sesi untuk harness
python identity_harness.py capture --label a \
  --url https://target.com/login --data 'u=...&p=...'
# lalu lanjut audit seperti biasa (0C)
```

---

## 4. Tangga eskalasi kalau masih terblokir

```
1. Ganti proxy (negara sama, IP beda)          — IP proxy mungkin sudah dikenal
2. Ganti tipe proxy (datacenter -> residensial) — target blokir datacenter
3. WARP penuh (bukan cuma browser)              — blokir di level DNS/Sistem
4. Camoufox instead of CloakBrowser             — fingerprint beda
5. Tambah delay + perilaku manusia              — bot-detection, bukan geo
6. Coba brand saudara di platform yang sama    — mail.com geo-block ≠ GMX/WEB.DE; kebijakan per merek bisa beda
7. Catat N/A dengan alasan                      — jangan memalsukan hasil
```

**Aturan:** tiga pendekakan berbeda sebelum menyimpulkan "terblokir". Kegagalan teknis
= rework, bukan N/A (lihat `redteam-mindset`).

Kalau UI-nya bail-out (redirect ke halaman bantuan) tapi API-nya masih balik 2xx,
blokirnya level UI — teknik route-abort biar JS context tetap hidup ada di
`bot-protected-target-testing` → `references/keep-page-context-for-api-testing.md`.

---

## 4b. United Internet mail platform (mail.com / GMX / WEB.DE) — kasus khusus

- **Blokir geo tingkat edge, seluruh path**: dari negara yang tidak diizinkan, setiap
  path di `signup.mail.com` balik 403 (platform-mesh), dan `register-service.mail.com`
  ada tapi 404. Cookie consent tidak menolong — blokir murni berbasis IP.
- **Wizard GMX/WEB.DE bisa dibuka dari mana saja** (`register.gmx.net`,
  `register.web.de`) tapi step terakhir butuh **verifikasi mTAN SMS** — jangan pakai
  nomor HP operator tanpa izin eksplisit; layanan SMS bayar butuh approval budget.
- **Anti-automation per-IP lintas ketiga brand**: setelah ~10 kali mulai registrasi,
  wizard bail ke `hilfe.<brand>.net/kundenservice/flexreg.html` dan endpoint
  `/aliases` balik `denial-error`. Budget **~1 flow registrasi berguna per 30–60 menit
  per IP** — jadwalkan validasi 3x di sekitar cooldown itu (loop retry tiap ~20 menit),
  dan perlakukan "blocked" sebagai kondisi normal, bukan perubahan temuan.
- Free proxy list ~96% mati dan mail.com blok IP datacenter; relay Vercel tidak
  menembus kebijakan geo. Detail lengkap platform + API map: skill
  `hunt-united-internet-mail`.

## 5. Yang TIDAK boleh dilakukan

| jangan | kenapa |
|---|---|
| Pakai identitas orang nyata | pemalsuan identitas — masalah hukum |
| Pakai kartu kredit orang lain | penipuan |
| Akun massal / bot pendaftar | melanggar ToS hampir semua target |
| Bypass verifikasi KYC dengan data palsu | bisa ban + masalah regulasi |
| Lewati blokir yang **secara eksplisit** dilarang policy | habiskan engagement |

**Kalau policy target melarang pendaftaran dari wilayahmu:** tandai surface
`not-tested`, sebutkan alasan, dan lanjut ke surface lain. Itu **bukan** kegagalan —
itu kepatuhan.

---

## 6. Sambungan ke pipeline

```
0A  baca policy — apakah mendaftar akun uji diizinkan?
0B  recon — cek level blokir (DNS/IP/aplikasi)
0C  daftar akun via CloakBrowser/WARP → capture sesi → identity_harness
0C  lanjut audit seperti biasa
0D  gate: N/A harus menyebut alat apa yang sudah dicoba
```

Skill terkait: `disposable-auth-identity` (bootstrap akun) ·
`identity_harness.py` (capture sesi) · `redteam-mindset` (3 percobaan) ·
`bot-protected-target-testing` (Cloudflare/DataDome) · `exploit-depth` (L0-L5).

## 7. Proxy untuk tool CLI (pengganti proxychains)

`proxychains` **tidak tersedia** di Windows (butuh LD_PRELOAD — Linux only). Tapi tool
modern (`curl`, `nuclei`, `ffuf`, `sqlmap`, `httpx`, `requests`) **semua hormati env
proxy**, jadi env-var adalah cara yang benar di sini.

```bash
# sekali jalan
python proxy_run.py --proxy http://user:pass@host:8080 -- nuclei -u https://target.com

# rotasi dari daftar (tiap percobaan proxy beda)
python proxy_run.py --list proxies.txt --rotate -- ffuf -u https://T/FUZZ -w w.txt

# cek IP sebelum & sesudah (verifikasi proxy benar-benar jalan)
python proxy_run.py --proxy http://host:8080 --check

# kelola daftar
python proxy_run.py --add "http://user:pass@de-host:8080" --tag DE
python proxy_run.py --list-proxies
```

**Catatan:** `NO_PROXY` otomatis diisi `localhost,127.0.0.1` supaya lab Docker
(juice-shop :3000, dvwa :4280) tidak lewat proxy.

### 7a. Berburu proxy gratis — urutan yang tidak buang waktu

Dua tahap. **Jangan** langsung tembak target dengan ribuan proxy.

**Tahap 1 — filter geo dulu (murah).** Timeout 6s, 120 worker, tes ke
`https://api.country.is/`, simpan yang `country == "US"`. Dari ~7.3k daftar mentah
hasilnya biasanya **<10 kandidat** — kalau tahap 1 tidak memfilter, tahap 2 membuang
24 menit untuk nol hasil.

**Tahap 2 — baru tes ke target** dengan kandidat itu saja.

Sumber dengan metadata uptime (jauh lebih baik dari daftar buta):

```bash
curl -s "https://proxylist.geonode.com/api/proxy-list?limit=200&page=1&sort_by=lastChecked&sort_type=desc&country=US&filterUpTime=90" -o geonode.json
# -> data[].ip / .port / .upTime / .lastChecked
```

**Jebakan hasil palsu — `200` dengan body kecil BUKAN lolos.** Sebagian proxy balas
`200` dengan 0–3 byte (respons kosong milik proxy sendiri), bukan halaman target.
Selalu bandingkan `size_download` dengan ukuran respons yang kamu sudah kenal —
halaman blokir Akamai `Access Denied` ≈ 365 byte. Entri `200 / size 3` di
`proxies_good.json` adalah noise; verifikasi ulang sebelum percaya.

**Jebakan throughput.** 7.3k proxy × 12s timeout ÷ 60 worker ≈ 24 menit. Pakai
timeout 6s + 120 worker (≈6 menit), dan jalankan via `terminal(background=true,
notify_on_complete=true)` supaya tidak memblokir turn.

## 8. SPA bail-out navigation: keep the JS context alive (measured 2026-10-25, GMX flexreg)

Saat menguji API registrasi lewat browser, wizard sering **redirect client-side ke
halaman bantuan** (mis. `hilfe.gmx.net/kundenservice/flexreg.html`) setelah beberapa
step API. Navigasi itu **menghancurkan execution context** — `page.evaluate()`
berikutnya gagal dengan `NetworkError` / `Execution context was destroyed`, padahal
cookie flow (reg-flow-data0/1, chunks-flow-data) sudah ke-set dan API-nya masih
melayani (captcha-verification & personal-info tetap 204 walau UI sudah bail).

Fix (Playwright/Camoufox) — blok navigasi bail-out SEBELUM mengisi form:

```python
await page.route('**hilfe.gmx.net**', lambda route: asyncio.ensure_future(route.abort()))
```

Halaman tetap di origin wizard, context hidup, fetch API bisa lanjut. Pola umum:
blok redirect ke domain bantuan/error apa pun (`**/hilfe.**`, `**/error**`,
`**/bailout**`) selama sesi testing API. Catatan: anti-automation level API tetap
bisa menolak endpoint tertentu (mis. `denial-error` setelah probing berulang) —
itu beda lapisan dari bail-out UI; tunggu cooldown (~30-60 menit, satu flow per
window) daripada mengubah pendekatan.

## 9. Tangga diagnosa blokir egress (WAJIB dijalankan berurutan)

Saat target utama balik 403 dan kamu tidak yakin penyebabnya, **jangan langsung
minta proxy residential**. Jalankan 5 anak tangga ini; tiap anak tangga memisahkan
satu hipotesis. Kasus nyata: Kohl's (Bugcrowd) — 403 di semua anak tangga.

| # | Uji | Cara | Hasil Kohl's | Kesimpulan yang boleh diambil |
|---|---|---|---|---|
| 1 | Geo murni | request langsung dari box | 403 `AKA_GEO=ID` | geo-block terkonfirmasi |
| 2 | Datacenter US | proxy HTTP/SOCKS US | 403 `AKA_GEO=US` | **bukan geo** — reputasi IP |
| 3 | TLS/bot fingerprint | Chrome asli (Playwright) + proxy US | 403 | bukan fingerprint — IP-range ACL |
| 4 | Tor exit US | 40 sirkuit dirotasi | 403 `AKA_GEO=US` | Tor exit list diblokir |
| 5 | Egress cloud bersih | reader/fetcher publik (r.jina.ai) | 403 | **datacenter/cloud diblokir menyeluruh** |

Aturan baca hasil:
- `AKA_GEO=ID` + 403 → geo-block.
- `AKA_GEO=US` + 403 → **bukan** geo. Jangan bilang "target blokir negara saya".
- Kalau anak tangga 2–5 semua 403, satu-satunya jalan adalah **IP US residential**.
  Sebutkan blokirnya sebagai "IP-range ACL (datacenter + cloud + Tor)", bukan
  "WAF" atau "bot detection" — triage butuh akurasi.

**Deteksi geo Tor salah kaprah:** `api.country.is` melaporkan exit Tor sebagai
`country: "T1"`. Kalau kamu gate `if cc != "US": skip`, **semua exit US valid
terbuang**. Pakai cookie/header geo milik target sendiri (Akamai: `AKA_GEO` di
`Set-Cookie`) sebagai sumber kebenaran, bukan layanan geo pihak ketiga.

## 10. Tor di Windows — versi & sumber build

- Bundle expert **Tor 14.0.1 / 15.0.4 membawa tor 0.4.8.x dan TIDAK BISA dipakai**
  di jaringan Tor saat ini. Gejalanya persis:
  `At least one protocol listed as required in the consensus is not supported by
  this version of Tor... The missing protocols are: Desc=3 Microdesc=3`
  lalu tor menggantung di `Bootstrapped 40% (loading_keys)` selamanya.
- **Butuh tor >= 0.4.9.** Ambil dari channel dist (bukan archive):
  `https://dist.torproject.org/torbrowser/<ver>/tor-expert-bundle-windows-x86_64-<ver>.tar.gz`
  Cek daftar versi dulu: `curl -s https://dist.torproject.org/torbrowser/ | grep -oE 'href="[0-9][^"]*/"'`
  (archive.torproject.org/tor-package-archive/ hanya memuat rilis lama).
- `ExitNodes {us}` + `StrictNodes 1` **membutuhkan database GeoIP**. Bundle expert
  menaruh `data/geoip` + `data/geoip6` sebagai **saudara** folder `tor/`, bukan di
  dalamnya — pakai path absolut di torrc:
  `GeoIPFile D:/path/to/data/geoip` dan `GeoIPv6File D:/path/to/data/geoip6`
- Rotasi sirkuit tanpa stem: kirim `AUTHENTICATE` + `SIGNAL NEWNYM` ke ControlPort
  lewat socket, lalu tunggu ~7 detik sebelum request berikutnya.
- `MaxCircuitDirtiness`/`NewCircuitPeriod` rendah supaya exit berubah sendiri.

Detail kasus + skrip: `references/akamai-egress-block.md`
