# Reverse Index — NoSQL Injection

**Cara pakai:** cocokkan fitur yang ditemukan recon dengan kolom kiri.
Satu baris cocok = probe WAJIB sebelum kelas ini boleh ditandai N/A.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| API dengan JSON body ke MongoDB | {"$ne": null} di field password | Detecting NoSQL injection · Exploiting NoSQL operator injection to b |
| parameter yang masuk ke query operator | $where / $regex injection | Detecting NoSQL injection · Exploiting NoSQL operator injection to b |
| login yang terima object (bukan string) | kirim array/object, bandingkan response | Detecting NoSQL injection · Exploiting NoSQL operator injection to b |
| endpoint dengan filter dinamis | extract data via operator injection | Detecting NoSQL injection · Exploiting NoSQL operator injection to b |

## PoC corpus terkait (5 repo)

- `BiiTts_CVE-2026-54350-Budibase-NoSQL-Injection`
- `CadGoose_MongoBleed-CVE-2025-14847-Fully-Automated-scanner`
- `Ermensonx_CVE-2025-14857-MongoBleed`
- `ExploreIO_CVE-2026-79483-FastGPT-NoSQL-Injection`
- `FurkanKAYAPINAR_CVE-2025-14847-MongoBleed-Exploit`

## Lab PortSwigger: nosql-injection (3 lab)

- Detecting NoSQL injection (`lab-nosql-injection-detection`)
- Exploiting NoSQL operator injection to bypass authentication (`lab-nosql-injection-bypass-authentication`)
- Exploiting NoSQL operator injection to extract unknown fields (`lab-nosql-injection-extract-unknown-fields`)
