# Reverse Index — File Upload

**Cara pakai:** cocokkan fitur yang ditemukan recon dengan kolom kiri.
Satu baris cocok = probe WAJIB sebelum kelas ini boleh ditandai N/A.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| upload avatar / dokumen / import | extension ganda + MIME spoof + polyglot | Remote code execution via web shell upload · Web shell upload via Co |
| upload yang diproses server (resize, parse) | upload ke path yang bisa dieksekusi | Remote code execution via web shell upload · Web shell upload via Co |
| upload di admin panel | webshell langsung | Remote code execution via web shell upload · Web shell upload via Co |
| upload via API (multipart) | content-type mismatch + .htaccess upload | Remote code execution via web shell upload · Web shell upload via Co |

## PoC corpus terkait (3 repo)

- `Avento_CVE-2024-45507_Behinder_Webshell`
- `Eyodav_OpenPLC-Insecure-File-Upload`
- `FraMarcuccio_CVE-2025-29093-Arbitrary-File-Upload`

## Lab PortSwigger: file-upload (6 lab)

- Remote code execution via web shell upload (`lab-file-upload-remote-code-execution-via-web-shell-upload`)
- Web shell upload via Content-Type restriction bypass (`lab-file-upload-web-shell-upload-via-content-type-restriction-bypass`)
- Web shell upload via path traversal (`lab-file-upload-web-shell-upload-via-path-traversal`)
- Web shell upload via obfuscated file extension (`lab-file-upload-web-shell-upload-via-obfuscated-file-extension`)
- Remote code execution via polyglot web shell upload (`lab-file-upload-remote-code-execution-via-polyglot-web-shell-upload`)
- Web shell upload via race condition (`lab-file-upload-web-shell-upload-via-race-condition`)
