# Reverse Index — CRLF Injection

**Cara pakai:** cocokkan fitur yang ditemukan recon dengan kolom kiri.
Satu baris cocok = probe WAJIB sebelum kelas ini boleh ditandai N/A.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| parameter redirect / url / next | %0D%0A + header palsu | — |
| form yang mengirim email | CRLF email header → BCC attacker | — |
| login/protokol negosiasi (telnet, SMTP) | CRLF → auth bypass | — |
| endpoint yang set cookie dari input | CRLF → Set-Cookie injection | — |

## PoC corpus terkait (1 repo)

- `George0Papasotiriou_CVE-2026-11113-SMTP-Header-Injection-in-Contact-Form`
