# Data Exposure

_Database / dataset leak from an endpoint. Kelas tujuan (destination class), bukan
primitif — tentukan mekanismenya dulu. Extracted 2026-10-21 from hunt-data-exposure._

## 8 mekanisme

1. Unauthenticated collection read (IDOR/BOLA, Critical)
2. IDOR on object (High–Critical)
3. GraphQL BOLA-by-resolver (High)
4. Datastore exposed — MongoDB 27017 / Elasticsearch 9200 / Redis 6379 / CouchDB 5984 (Critical)
5. SQLi → dump (Critical)
6. File leak — .sql/.bak/.git/heapdump (Medium–High)
7. Mass assignment — role/isAdmin/balance (Medium–High)
8. Shadow / undocumented API (Medium)

## Teknik inti

- **Anon control dulu**: `curl -w "%{http_code} %{size_download}"` tanpa cookie, lalu
  bandingkan dengan versi ber-auth. Anon 200 + body >100B = primitive termurah.
- **Differential wajib**: single response bukan temuan. Pakai `identity_harness.py diff`.
- **Datastore read-only**: baca metadata + count + min 10 record (atau semua kalau <10).
  JANGAN dump seluruh koleksi.
- **Redaksi PII**: masking email/telepon di laporan.

## Gate sebelum lapor

Mekanisme teridentifikasi · bukti differential · volume disebut (count nyata) ·
PII ter-redaksi · reproduksi 10 menit · dampak konkret (data siapa, untuk apa).
