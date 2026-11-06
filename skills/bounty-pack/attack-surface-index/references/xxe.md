# Reverse Index — XXE

**Cara pakai:** cocokkan fitur yang ditemukan recon dengan kolom kiri.
Satu baris cocok = probe WAJIB sebelum kelas ini boleh ditandai N/A.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| endpoint yang terima XML / SOAP | DOCTYPE + ENTITY → baca /etc/hostname | Exploiting XXE to perform SSRF attacks · Exploiting XXE using extern |
| upload SVG / DOCX / XLSX | XXE via file upload (SVG dengan ENTITY) | Exploiting XXE to perform SSRF attacks · Exploiting XXE using extern |
| API dengan Content-Type application/xml | XInclude kalau DOctype diblokir | Exploiting XXE to perform SSRF attacks · Exploiting XXE using extern |
| integrasi SAML / WS-Federation | XXE lewat assertion XML | Exploiting XXE to perform SSRF attacks · Exploiting XXE using extern |

## PoC corpus terkait (3 repo)

- `AT190510-Cuong_CVE-2025-65482-XXE-`
- `BigMancer_Jinhe-OA-XXE-Vulnerability`
- `George0Papasotiriou_CVE-2026-11112-XXE-via-SVG-Image-Upload`

## Lab PortSwigger: xxe (4 lab)

- Exploiting XXE to perform SSRF attacks (`lab-exploiting-xxe-to-perform-ssrf`)
- Exploiting XXE using external entities to retrieve files (`lab-exploiting-xxe-to-retrieve-files`)
- Exploiting XInclude to retrieve files (`lab-xinclude-attack`)
- Exploiting XXE via image file upload (`lab-xxe-via-file-upload`)
