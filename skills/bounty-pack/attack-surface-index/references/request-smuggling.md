# Reverse Index — HTTP Request Smuggling

**Cara pakai:** cocokkan fitur yang ditemukan recon dengan kolom kiri.
Satu baris cocok = probe WAJIB sebelum kelas ini boleh ditandai N/A.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| front-end proxy + back-end beda parser | CL.TE / TE.CL probe | HTTP request smuggling, basic CL.TE vulnerability · HTTP request smu |
| HTTP/2 di front-end | H2.CL / H2.TE downgrade | HTTP request smuggling, basic CL.TE vulnerability · HTTP request smu |
| Transfer-Encoding yang tidak standar | obfuscating TE header | HTTP request smuggling, basic CL.TE vulnerability · HTTP request smu |

## PoC corpus terkait (1 repo)

- `George0Papasotiriou_CVE-2026-1010-WebSocket-Connection-Smuggling-via-Malformed-Upgrade-Header`

## Lab PortSwigger: request-smuggling (3 lab)

- HTTP request smuggling, basic CL.TE vulnerability (`lab-basic-cl-te`)
- HTTP request smuggling, basic TE.CL vulnerability (`lab-basic-te-cl`)
- HTTP request smuggling, obfuscating the TE header (`lab-obfuscating-te-header`)
