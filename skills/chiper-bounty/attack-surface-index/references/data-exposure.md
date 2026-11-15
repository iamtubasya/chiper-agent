# Reverse Index — Data Exposure (database leak dari endpoint)

**Cara pakai:** cocokkan gejala di kolom kiri. Satu baris cocok = probe WAJIB sebelum
kelas ini boleh ditandai N/A. Kelas lengkap: `hunt-data-exposure`.

| Gejala di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| collection endpoint (`/api/users`, `/api/orders`) | fetch **UNAUTHENTICATED** dulu — primitive termurah | Insecure direct object references · Unprotected admin functionality |
| endpoint ber-id numerik/uuid | swap id A→B, bandingkan body | User ID controlled by request parameter |
| `/graphql` atau `/api/graphql` | introspection → query objek orang lain | Accessing private GraphQL posts · Accidental field exposure |
| port 27017/9200/6379/5984 terbuka | baca metadata + count + 1 record (JANGAN dump) | — |
| parameter yang masuk ke query DB | `'` + bandingkan error & waktu | SQL injection vulnerability in WHERE clause |
| `.sql` / `.bak` / `.git` / `heapdump` | baca struktur, cari kredensial | Information disclosure in version control history |
| field sensitif ikut keluar (`role`, `isAdmin`) | tambahkan field ke body yang sah | — |
| endpoint versi lama (`/v1/`, `/internal/`) | bandingkan dgn versi aktif | — |
| endpoint zombie (fitur dimatikan, sisa integrasi) | anon control + uji authz; lihat `attack-flows` alur 2 | — |

## PoC corpus terkait (dari 2.223 repo)

Lihat `security/poc-technique-atlas/references/` untuk daftar per kelas:
`idor-bola.md` · `sqli.md` · `nosql.md` (MongoBleed CVE-2025-14847) ·
`info-disclosure.md` · `api-misconfig.md` · `cloud.md`.

## Disiplin pasca-temuan (WAJIB)

- Ambil **count + min 10 record** (atau semua kalau <10) — JANGAN dump seluruh koleksi
- **Redaksi PII** di laporan (masking email/telepon)
- Catat request/response + timestamp + marker unik
- Laporkan lewat kanal policy, jangan hubungi korban langsung
