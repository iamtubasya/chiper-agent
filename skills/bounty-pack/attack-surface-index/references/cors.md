# Reverse Index — CORS Misconfiguration

**Cara pakai:** cocokkan fitur yang ditemukan recon dengan kolom kiri.
Satu baris cocok = probe WAJIB sebelum kelas ini boleh ditandai N/A.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| API dengan Access-Control-Allow-Origin dinamis | reflect origin + credentials | CORS vulnerability with basic origin reflection · CORS vulnerability |
| endpoint yang percaya Origin null | sandbox iframe → null origin | CORS vulnerability with basic origin reflection · CORS vulnerability |
| subdomain yang bisa di-XSS | CORS trust subdomain → chain | CORS vulnerability with basic origin reflection · CORS vulnerability |

## PoC corpus terkait (1 repo)

- `AdityaBhatt3010_CVE-2026-27579-CORS-Misconfiguration-Leading-to-Authenticated-Data-Exposure`

## Lab PortSwigger: cors (3 lab)

- CORS vulnerability with basic origin reflection (`lab-basic-origin-reflection-attack`)
- CORS vulnerability with trusted null origin (`lab-null-origin-whitelisted-attack`)
- CORS vulnerability with trusted insecure protocols (`lab-breaking-https-attack`)
