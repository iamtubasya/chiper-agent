# Reverse Index — CSRF

**Cara pakai:** cocokkan fitur yang ditemukan recon dengan kolom kiri.
Satu baris cocok = probe WAJIB sebelum kelas ini boleh ditandai N/A.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| form aksi sensitif (ganti email/password) | kirim tanpa token, dari origin lain | CSRF vulnerability with no defenses |
| API dengan cookie-based auth | cek SameSite + apakah token diperiksa server | CSRF vulnerability with no defenses |
| endpoint yang hanya cek Content-Type | CSRF lewat simple request (form-encoded) | CSRF vulnerability with no defenses |

## PoC corpus terkait (2 repo)

- `0xcc12138_wavlink-nu516u1-csrf-command-injection-`
- `AlexMihailEngineer_CVE-2026-11784-Optimole-CSRF`

## Lab PortSwigger: csrf (1 lab)

- CSRF vulnerability with no defenses (`lab-no-defenses`)
