# Reverse Index — Clickjacking

**Cara pakai:** cocokkan fitur yang ditemukan recon dengan kolom kiri.
Satu baris cocok = probe WAJIB sebelum kelas ini boleh ditandai N/A.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| halaman aksi sensitif tanpa X-Frame-Options | iframe + overlay | Basic clickjacking with CSRF token protection · Clickjacking with fo |
| form dengan CSRF token | clickjacking tetap bisa (token ikut terkirim) | Basic clickjacking with CSRF token protection · Clickjacking with fo |
| aksi satu klik (hapus, transfer) | prefilled form input | Basic clickjacking with CSRF token protection · Clickjacking with fo |

## PoC corpus terkait (0 repo)


## Lab PortSwigger: clickjacking (5 lab)

- Basic clickjacking with CSRF token protection (`lab-basic-csrf-protected`)
- Clickjacking with form input data prefilled from a URL parameter (`lab-prefilled-form-input`)
- Clickjacking with a frame buster script (`lab-frame-buster-script`)
- Exploiting clickjacking vulnerability to trigger DOM-based XSS (`lab-exploiting-to-trigger-dom-based-xss`)
- Multistep clickjacking (`lab-multistep`)
