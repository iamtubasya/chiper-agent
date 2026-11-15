# Reverse Index — Web Cache Poisoning

**Cara pakai:** cocokkan fitur yang ditemukan recon dengan kolom kiri.
Satu baris cocok = probe WAJIB sebelum kelas ini boleh ditandai N/A.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| CDN / reverse proxy di depan app | unkeyed header → poison cache | — |
| halaman yang reflect header (X-Forwarded-Host) | kirim header, cek apakah ter-cache | — |
| halaman dengan query param mempengaruhi body | cache key excludes param → poison | — |

## PoC corpus terkait (1 repo)

- `George0Papasotiriou_CVE-2026-11101-HTTP-Cache-Poisoning-via-Unkeyed-Query-Parameter`
