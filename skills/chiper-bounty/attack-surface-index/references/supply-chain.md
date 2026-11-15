# Reverse Index — Supply Chain

**Cara pakai:** cocokkan fitur yang ditemukan recon dengan kolom kiri.
Satu baris cocok = probe WAJIB sebelum kelas ini boleh ditandai N/A.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| dependency lockfile (package-lock, Cargo.lock) | cargo-audit / npm audit → advisory | — |
| CI/CD workflow (.github/workflows) | workflow injection + secret exfiltration | — |
| paket internal yang dipublikasi | dependency confusion | — |
| install script (postinstall) | arbitrary code saat npm install | — |

## PoC corpus terkait (0 repo)

