# Reverse Index — Prototype Pollution

**Cara pakai:** cocokkan fitur yang ditemukan recon dengan kolom kiri.
Satu baris cocok = probe WAJIB sebelum kelas ini boleh ditandai N/A.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| JS bundle dengan merge/extend/assign | pollusi __proto__ lewat JSON body | — |
| API yang terima nested JSON | constructor.prototype pollution | — |
| query string yang di-parse jadi object | __proto__[x]=y via URL | — |

## PoC corpus terkait (1 repo)

- `BiiTts_CVE-2026-44789-n8n-PrototypePollution-RCE`
