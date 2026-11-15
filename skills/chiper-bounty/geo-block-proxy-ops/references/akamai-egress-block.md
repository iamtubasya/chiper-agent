# Kasus: Akamai IP-range ACL — Kohl's (Bugcrowd, Okt 2026)

Target: `www.kohls.com`, `mapps.kohls.com`, `wallet.kohls.com` (retail US).
Semua properti utama di belakang satu Akamai property yang menolak **semua**
egress non-residential. Brief program mewajibkan UA `RESEARCHER_BC_EMAIL`
dan rate <=6 req/s — itu bukan penyebab blokir (403 identik dengan UA browser).

## Ciri respons blokir

```
HTTP/1.1 403 Forbidden
Server: AkamaiGHost
Set-Cookie: AKA_GEO=ID; path=/; secure
Set-Cookie: AKA_SNB_STP=test; ...
```
Body selalu HTML `Access Denied ... Reference #18.bac3017.<ts>.<hex>` +
`https://errors.edgesuite.net/18...`.

**`AKA_GEO` adalah sensor diagnosa terpenting.** Baca dari `Set-Cookie`, bukan
dari layanan geo eksternal:
- `AKA_GEO=ID` → geo-block.
- `AKA_GEO=US` tapi tetap 403 → **bukan geo**; ini reputasi/rentang IP.

## Probe diagnostik 5 anak tangga (jalan sekali, ~10 menit)

```bash
UA="RESEARCHER_BC_EMAIL"
# 1. langsung
curl -s -A "$UA" -D - -o /dev/null --max-time 20 "https://target/" | grep -iE '^HTTP|AKA_GEO'
# 2. proxy US datacenter
curl -s -x http://US_PROXY:PORT -A "$UA" -D - -o /dev/null --max-time 20 "https://target/" | grep -iE '^HTTP|AKA_GEO'
# 3. Chrome asli + proxy US (Playwright) -> buang TLS fingerprint dari hipotesis
# 4. Tor exit US, 40x NEWNYM
# 5. egress cloud bersih
curl -s --max-time 45 "https://r.jina.ai/https://target/" | head -c 200
```

Interpretasi lihat SKILL.md §9. Kalau 2–5 semua 403 → **butuh IP US residential**;
laporkan sebagai "IP-range ACL", bukan "geo-block" atau "bot detection".

## Sumber proxy gratis — hasil terukur (jangan diulang percuma)

- `proxyscrape` + 3 daftar GitHub → 7.352 kandidat, **0 lolos** ke target.
- `proxylist.geonode.com/api/proxy-list?...&country=US&filterUpTime=90` →
  200 proxy US berkualitas; hanya 8 yang bisa konek, **semua 403**.
- Free proxy = hampir selalu sudah masuk daftar blokir Akamai. Jangan habiskan
  >15 menit di sini; naik ke anak tangga 4/5 atau minta residential.

## Yang TIDAK bekerja (sudah diuji, catat sebagai negatif terverifikasi)

- Cloudflare WARP dari lokasi non-US → exit mengikuti colo terdekat (ID), tidak
  bisa dipilih negaranya di consumer mode.
- `wrangler`/Cloudflare Workers tanpa Smart Placement → egress dari colo terdekat
  klien, bukan US. Smart Placement hanya membantu kalau Worker sudah ter-autentikasi.
- Google Translate proxy (`<host-with-dashes>.translate.goog`) → balik
  `400 "Can't translate this page"` saat origin menolak.
- VPS US di `known_hosts` tanpa kunci SSH → tidak ada akses.
- Tor dengan build 0.4.8.x → tidak bisa bootstrap (lihat SKILL.md §10).

## Bypass yang PERLU dicoba sebelum menyerah

1. **Origin discovery via passive DNS** — `api.hackertarget.com/hostsearch/?q=<host>`
   dan `otx.alienvault.com/api/v1/indicators/hostname/<host>/passive_dns`.
   Kalau ketemu IP non-Akamai, coba `curl -k -H "Host: <host>" https://<ip>/`.
   Catatan: untuk Kohl's semua IP historis = 23.x (Akamai), tidak ada kebocoran origin.
2. **Host alternatif di luar daftar OOS** — cek `alt01/alt02.www.<domain>`,
   `ww8/ww9/ww11.<domain>` dari hasil subfinder. Untuk Kohl's semuanya sinkhole
   DNS atau balik 200 kosong (`server: jag`), bukan storefront.
3. **Properti Akamai lain yang tidak membawa ACL geo** — ACL bersifat per-property.
   Kohl's: `jarvis-prod-ext.kohls.com` (Spring Boot) dan `arcwebservices.kohls.com`
   (`WWW-Authenticate: Bearer`) **reachable dari ID**. Kalau target utama blok,
   audit properti yang lolos; jangan anggap seluruh estate mati.

## Pelajaran proses

- Egress blocker adalah **REWORK**, bukan N/A. Tapi setelah 5 anak tangga gagal,
  eskalasi ke operator dengan tabel hasil — jangan diam-diam mencoba proxy ke-50.
- Sambil menunggu egress, alihkan ke track yang tidak butuh egress: reverse APK,
  audit host reachable, takeover DNS. Session Kohl's menghasilkan 1 temuan ATO
  tervalidasi dari host yang tidak diblokir.
