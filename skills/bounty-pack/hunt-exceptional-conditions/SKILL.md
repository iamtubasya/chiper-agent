---
name: hunt-exceptional-conditions
description: "Hunt mishandling of exceptional conditions — feed an endpoint malformed/unexpected input (wrong type, broken JSON, oversized field, null byte) and make it fail OPEN or leak internals: a verbose stack-trace / framework error page that discloses ORM internals, server file paths, library versions, or a language traceback. Use on any input-accepting endpoint (JSON APIs, forms, query params). Medium-High when the leak exposes internal structure that arms a deeper attack."
report_count: 0
sources: hackerone_public
---

# HUNT-EXCEPTIONAL-CONDITIONS — Verbose Errors / Fail-Open (A10:2025)

## What actually pays

Well-built apps catch errors and return a clean, generic message. A broken app,
when handed input it didn't expect, throws an unhandled exception and renders a
**developer error page** straight to the client — leaking the stack trace, the
ORM/query internals, server-side file paths, and framework/library versions.
That disclosure is the finding (and it arms SQLi/RCE/path attacks next).

## Recon

Any endpoint that parses input is a candidate; the richest are:

```
JSON APIs that expect typed fields:  POST /api/* with {numbers, ids, enums}
Endpoints with numeric/id path or query params:  /item/{id}, ?page=, ?quantity=
Search / filter / sort params
File or content-type sensitive uploads
```

## Attack — send what the code didn't anticipate

Take a known-good request and break ONE assumption at a time:

- **Wrong type:** a field the app expects to be a number/string is sent as an
  array or object — `{"rating":"x","comment":[1,2,3]}`, `{"quantity":{}}`.
- **Malformed body:** truncated/!invalid JSON, an unterminated string, a stray
  brace, a wrong/missing Content-Type.
- **Boundary/oversized:** a very long string, a huge/negative/overflow number.
- **Null byte / control chars** embedded in a value.

```
POST /api/Feedbacks   {"rating":"notanumber","comment":[1,2,3]}
GET  /item/' OR /item/%00   (also exercises the error path)
```

Watch the RESPONSE BODY, not just the status: a 500 (or even a 200/400) whose
body contains a stack trace or framework error page is the signal.

## What counts as a leak (the success signal)

A finding is confirmed when the response body contains a cross-framework error-disclosure signature:

- **Node/Express + Sequelize:** `SequelizeDatabaseError`, `node_modules/sequelize`,
  a JS stack with internal paths.
- **PHP:** `<b>Warning</b> ... /var/www/.../file.php on line N`.
- **Python:** `Traceback (most recent call last)`, `werkzeug.exceptions`.
- **Java:** `at com.app.Foo(Foo.java:42)` stack frames.
- **.NET:** `Server Error in '/' Application`, a `[System.XxxException: ...]` YSOD.

A clean JSON error (`{"error":"Invalid input"}`) with no internals is NOT a
finding — that's correct handling. Disclosure of internal structure is.

## Validation discipline

- Capture the exact leaked artifact (path, ORM class, version, stack frame) —
  that's the evidence. "It returned 500" alone is not disclosure.
- Note what the leak enables next (e.g. a disclosed SQL error → hunt-sqli; a
  disclosed absolute path → hunt-lfi).

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Null/empty/oversized: kirim `null`, `""`, 10 MB string | Crash & DoS aplikasi |
| 2 | Unicode & normalisasi: homoglyph, zero-width, RTL override | Filter bisa dilewati |
| 3 | Type juggling: `"0e123"` vs `"0e456"`, `true` vs `1` | Perbandingan longgar |
| 4 | Nilai negatif & batas: `-1`, `MAX_INT+1`, `0.999999999` | Overflow & off-by-one |
| 5 | State tidak konsisten: hapus resource lalu pakai referensi lama | Use-after-delete |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis
N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Gate 0 Validation

1. **Apa yang bisa dilakukan penyerang SEKARANG?** "Penyerang bisa membuat layanan tidak responsif dengan mengirim satu request berisi string 10 MB ke `/api/search`."
2. **Apa yang hilang dari korban?** Ketersediaan. Ukur dampaknya (waktu respons, kegagalan) dan bandingkan dengan baseline.
3. **Bisa direproduksi 10 menit dari nol?** Sertakan request dan pengukuran sebelum/sesudah. Kalau hanya memperlambat, nyatakan demikian.

## Eskalasi wajib (jangan berhenti di kelas ini)

**Primitif:** picu penanganan error tak terduga

**Teknik pengembangan:** malformed input -> stack trace; race pada cleanup; partial write

**Eskalasi ke:** `hunt-rce` · `hunt-info-disclosure`

**Depth target:** L2 -> L4

Satu temuan di kelas ini WAJIB menyebut eskalasi berikutnya (atau alasan primitif habis).
Lihat `exploit-chain-graph` + `exploit-depth` (L0-L5). `depth_gate.py` memblokir temuan
yang buktinya cuma status code.

## Runnable probes

Commands you can paste. `<TARGET>`/`<RPC>` are placeholders — fill them
from recon, do not guess endpoints.

```bash
# 0) baseline — record the healthy response to compare against
curl -sS -o base.out -w 'base %{http_code} %{size_download} %{time_total}\n' https://<TARGET>/api/search

# 1) NULL / EMPTY / OVERSIZED — the crash class
for v in '' 'null' '0'; do
  curl -sS -o /dev/null -w "empty=$v %{http_code} %{time_total}\n" \
    -X POST https://<TARGET>/api/search -H 'Content-Type: application/json' -d "{\"q\":$([ -z "$v" ] && echo 'null' || echo "\"$v\"")}"
done

# 2) TYPE CONFUSION — send an array where a string is expected, and vice versa
curl -sS -X POST https://<TARGET>/api/search -H 'Content-Type: application/json' \
  -d '{"q":["a","b"]}' -o t1.out -w 'array %{http_code}\n'
curl -sS -X POST https://<TARGET>/api/search -H 'Content-Type: application/json' \
  -d '{"q":{"$ne":null}}' -o t2.out -w 'object %{http_code}\n'
diff <(head -c 400 base.out) <(head -c 400 t1.out) >/dev/null && echo 'identical -> no signal'

# 3) NUMERIC BOUNDARIES
for n in -1 0 2147483648 9223372036854775808; do
  curl -sS -o /dev/null -w "n=$n %{http_code} %{time_total}\n" \
    "https://<TARGET>/api/items?limit=$n"
done

# 4) UNICODE / NORMALISATION — filter bypass via homoglyph and zero-width
curl -sS 'https://<TARGET>/search?q=%E2%80%8Bzsx1' -o u1.out -w 'zwsp %{http_code}\n'
curl -sS 'https://<TARGET>/search?q=%D0%B0dmin' -o u2.out -w 'cyrillic-a %{http_code}\n'

# 5) USE-AFTER-DELETE — create, delete, then use the old reference
ID=$(curl -sS -X POST https://<TARGET>/api/items -H "Authorization: Bearer $TOK" -d '{"name":"x"}' | jq -r '.id')
curl -sS -X DELETE "https://<TARGET>/api/items/$ID" -H "Authorization: Bearer $TOK" -o /dev/null -w 'del %{http_code}\n'
curl -sS "https://<TARGET>/api/items/$ID" -H "Authorization: Bearer $TOK" -o /dev/null -w 'after-del %{http_code}\n'
```

**Proof bar:** an exceptional input must produce a *consequence* — data leak in the
error, a 500 that reveals internals, or a measurable availability hit. A 500 with a
generic body is robustness, not a finding.

---

## 2026 sweep (dork pass 2026-10-26 — advisori terverifikasi)

- **CVE-2026-18649 / CVE-2026-20404 / CVE-2026-23842 — DoS / resource exhaustion (dari atlas lokal, kategori report-only).**
  Lesson: kelas ini **report-only** — jangan jalankan terhadap target nyata. Yang bisa dilaporkan: ReDoS pada regex input pengguna, algorithmic complexity pada endpoint pencarian/sort, dan entity expansion pada parser XML (yang sekaligus adalah XXE kalau entity eksternal resolve).
- **CVE-2026-31431 / CVE-2026-42533 — nginx pre-auth heap buffer overflow.** Kondisi eksepsional (input tak terduga) yang menyebabkan kebocoran memori, bukan hanya crash.
  Lesson: **kondisi eksepsional yang menyebabkan kebocoran data jauh lebih berharga daripada yang menyebabkan crash.** Uji input tak terduga sambil memantau apakah respons membocorkan sesuatu, bukan hanya apakah tetap hidup.

**Probe inti:** null/empty/oversized, Unicode & normalisasi (homoglyph, zero-width, RTL override), type juggling (`"0e123"` vs `"0e456"`, `true` vs `1`), nilai negatif & batas (`-1`, `MAX_INT+1`), dan state tidak konsisten (hapus resource lalu pakai referensi lama).


## Critical severity anchor (kelas ini bisa Critical — syaratnya)

| Kondisi | Severity |
|---|---|
| Input tak terduga → kebocoran memori / data sensitif di respons | Critical |
| Input tak terduga → RCE (buffer overflow, deserialization) | Critical |
| Input tak terduga → bypass authz (state tidak konsisten) | High-Critical |
| Input tak terduga → crash / DoS | Medium |
| Input tak terduga → hanya error message berbeda | Info |

**Kalibrasi wajib:** **kondisi eksepsional yang menyebabkan kebocoran data jauh lebih berharga
daripada yang menyebabkan crash** (CVE-2026-31431 / CVE-2026-42533, nginx pre-auth heap overflow).
Uji sambil memantau apakah respons membocorkan sesuatu, bukan hanya apakah tetap hidup.

## 2026 sweep

- **CVE-2026-31431 / CVE-2026-42533 (nginx)** — pre-auth heap buffer overflow via kondisi
  eksepsional. Kebocoran memori, bukan hanya crash.
- **Type juggling** — `"0e123" == "0e456"` di PHP, `true == 1`, `null == 0`. Uji perbandingan yang
  membandingkan input attacker dengan nilai terkontrol.
- **Unicode normalisasi** — homoglyph, zero-width, RTL override yang membuat dua string berbeda
  dianggap sama oleh satu lapisan dan berbeda oleh lapisan lain.
- **State tidak konsisten** — hapus resource lalu pakai referensi lama (stale ID setelah delete).
