# Reverse Index — Cross-Site Scripting

**Cara pakai:** cocokkan fitur yang ditemukan recon dengan kolom kiri.
Satu baris cocok = probe WAJIB sebelum kelas ini boleh ditandai N/A.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| field yang dirender balik (nama, komentar, profil) | marker unik 8+ char, cek posisi & konteks HTML | — |
| upload gambar/dokumen (SVG, HTML) | SVG dengan <script> atau event handler | — |
| parameter URL yang masuk ke halaman (redirect, next, url) | reflected XSS via parameter tersebut | — |
| halaman dengan DOM sink (innerHTML, document.write) | source→sink di JS bundle | — |
| fitur AI/chat yang render output model | XSS lewat output handler yang tidak escape | Exploiting LLM APIs with excessive agency · Exploiting vulnerabiliti |

## PoC corpus terkait (8 repo)

- `0xashfaq_-HelpDeskZ-v2.0.2---Stored-Cross-Site-Scripting-XSS-`
- `AnandJogawade_CVE-2026-48849-Roundcube-Webmail-Stored-XSS`
- `Ant1sec-ops_Hospital-management-Systemv4.0-Stored-XSS`
- `Beesco00_CVE-2024-52794-Discourse-Stored-XSS`
- `ColdFusionX_CVE-2024-46878-TikiCMS-XSS`
- `ColdFusionX_CVE-2024-46879-TikiCMS-XSS`
- `FUNFACTOR1_pocket-android-xss-0click-cve`
- `FraMarcuccio_CVE-2025-29094-Multiple-Stored-Cross-Site-Scripting-XSS`
