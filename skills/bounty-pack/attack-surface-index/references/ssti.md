# Reverse Index — Server-Side Template Injection

**Cara pakai:** cocokkan fitur yang ditemukan recon dengan kolom kiri.
Satu baris cocok = probe WAJIB sebelum kelas ini boleh ditandai N/A.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| template editor / email template / CMS theme | {{7*7}} dan ${7*7} — beda engine beda payload | — |
| parameter yang masuk ke pesan error/notifikasi | SSTI di pesan yang dirender server-side | — |
| form builder / custom field | shortcode/template interpolation | — |
| fitur export (PDF/HTML dari template) | SSTI di template export | — |

## PoC corpus terkait (4 repo)

- `AT190510-Cuong_CVE-2025-64087-SSTI-`
- `AT190510-Cuong_CVE-2026-38165-SSTI-`
- `Andriesces_SelectCours-_Sever-side-Template-injection`
- `George0Papasotiriou_CVE-2026-11104-Python-SSTI-via-Jinja2-attr-Filter-Bypass`
