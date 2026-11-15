# Reverse Index — Open Redirect

**Cara pakai:** cocokkan fitur yang ditemukan recon dengan kolom kiri.
Satu baris cocok = probe WAJIB sebelum kelas ini boleh ditandai N/A.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| parameter redirect / next / return / url | ganti ke domain eksternal, ikuti 302 | — |
| login/logout dengan return URL | redirect setelah auth → token di URL | — |
| OAuth callback | redirect_uri manipulation → token theft | Authentication bypass via OAuth implicit flow · Forced OAuth profile |
| halaman dengan link eksternal | open redirect → phishing / SSRF filter bypass | — |

## PoC corpus terkait (0 repo)

