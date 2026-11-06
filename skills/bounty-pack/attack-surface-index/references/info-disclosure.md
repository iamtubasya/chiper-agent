# Reverse Index — Information Disclosure

**Cara pakai:** cocokkan fitur yang ditemukan recon dengan kolom kiri.
Satu baris cocok = probe WAJIB sebelum kelas ini boleh ditandai N/A.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| .git / .env / backup exposed | baca config, cari kredensial | — |
| error/stack trace verbose | ekstrak path, versi, internal host | — |
| JS bundle / source map | endpoint & kunci tersembunyi | — |
| debug endpoint (/actuator, /_debug) | heapdump, env, config | — |

## PoC corpus terkait (1 repo)

- `AdityaBhatt3010_CVE-2026-27579-CORS-Misconfiguration-Leading-to-Authenticated-Data-Exposure`
