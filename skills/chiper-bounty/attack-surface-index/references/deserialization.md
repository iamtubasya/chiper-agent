# Reverse Index — Insecure Deserialization

**Cara pakai:** cocokkan fitur yang ditemukan recon dengan kolom kiri.
Satu baris cocok = probe WAJIB sebelum kelas ini boleh ditandai N/A.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| endpoint yang terima serialized data (Java/.NET/pickle) | gadget chain via ysoserial | — |
| cookie/state ter-encode (base64 besar) | decode → coba gadget | — |
| API dengan object graph (PHP unserialize, Ruby Marshal) | phar:// / object injection | — |
| cache/session store yang bisa ditulis | plant serialized payload | — |

## PoC corpus terkait (4 repo)

- `AdityaBhatt3010_React2Shell-CVE-2025-55182-The-Deserialization-Bug-That-Broke-the-Web`
- `CypherHippie_CVE-2026-34486---unauthenticated-RCE-via-Java-deserialization`
- `Dhananjayasj_CVE-2025-24813-Apache-Tomcat-Partial-PUT-Deserialization-RCE-`
- `Gelcon_PoC-ModbusMechanic-3.0-Insecure-Deserialization-and-RCE`
