# SSRF lewat LLM tool-definition (JSON-Schema `$ref`) — kelas vektor baru

Ditemukan & dikonfirmasi 2026-10-25 di Proton Lumo (`POST /api/ai/v1/chat/completions`),
dilaporkan sebagai Medium, unauthenticated, blind SSRF dengan boolean oracle.

## Kenapa ini sering kelewat

Auditor memetakan permukaan LLM sebagai "chat" (prompt injection, jailbreak) dan lupa bahwa
**payload `tools` adalah input parser di sisi server**, bukan sekadar prompt. Backend yang
resolve JSON Schema remote (`$ref`) akan melakukan HTTP GET **sebelum** model dipanggil.

Pemicu: endpoint bergaya [OI] (OpenAI-compatible) yang menerima `tools[].function.parameters`.

## Payload minimal

```http
POST /api/ai/v1/chat/completions HTTP/1.1
Host: <target-llm-host>
Accept: application/json
Content-Type: application/json
x-pm-appversion: web-lumo@1.3.0        # WAJIB di Proton; tanpa ini 400 Code 5002

{"model":"lumo-lite","max_tokens":4,"stream":false,
 "messages":[{"role":"user","content":"hi"}],
 "tools":[{"type":"function","function":{"name":"t","description":"d",
   "parameters":{"$ref":"https://<collaborator>/poc.json"}}}]}
```

Catatan: `description` **wajib**. Tanpa itu body gagal validasi
`IncomingToolSpec` dan **tidak ada fetch** — ini justru kontrol negatif yang berguna.

## Oracle: bukan "JSON valid", tapi "JSON SCHEMA valid"

Semua di bawah ini remote mengembalikan HTTP 200; bedanya isi, bukan status:

| dokumen remote | API | bacaan |
|---|---|---|
| objek JSON biasa (`httpbin.org/json`) | 200 | diterima sebagai schema kosong |
| base64 schema asli `{type:object,properties:{...}}` | 200 | valid |
| base64 `{"not":"a schema"}` (`not` harus schema) | **500** | schema tidak valid |
| `/html`, `/xml`, `/image/png` | 500 | bukan JSON |
| body kosong (`/status/200`,`204`,`404`,`500`) | 500 | tak ada body |

**Uji refleksi:** selipkan marker unik di dalam schema remote. Kalau marker **tidak** muncul di
respons → murni boolean oracle, **bukan** read primitive. Jangan klaim "arbitrary file read".

## Bukti bahwa ini server-side, bukan klien

Dari log collaborator mentah, header request hanya `Host` + `Accept: */*`
(**tidak ada cookie/Authorization yang diteruskan**), dan source IP adalah egress target
(beberapa address berbeda), bukan IP peneliti. Ini dua klaim yang harus dibuktikan terpisah:
(a) request datang dari infra target, (b) tanpa kredensial apa pun.

## Matriks eskalasi (dan batas jujurnya)

| target | tanda |
|---|---|
| loopback port tertutup | gagal cepat ~1–2 s (TCP RST) |
| RFC1918 terfilter | menggantung sampai connect timeout ~30 s |
| metadata cloud (AWS/GCP/Alibaba/Oracle) | biasanya 30 s / gagal cepat → **tidak ada kredensial** |
| DNS internal cluster | tidak resolve |

Selisih RST vs timeout = **oracle host/port internal** yang bisa dipakai attacker tanpa auth.
Kalau metadata terfilter dan DNS internal tidak resolve, ceiling-nya **blind SSRF**, bukan
credential theft — tulis apa adanya, jangan naikkan severity tanpa bukti.

Redirect: arahkan `$ref` ke URL 302 yang menuju collaborator. Kalau hop akhir tercatat
(plus header `Referer` dari hop pertama) → fetcher mengikuti redirect → allowlist first-hop bisa
dilewati.

## Pertanyaan yang wajib dijawab sebelum lapor

1. Apakah fetch terjadi tanpa auth? (kirim ulang tanpa `Authorization`/cookie/`x-pm-uid`)
2. Apa yang dikirim ke target? (cek raw request di collaborator — header apa saja)
3. Apakah mengikuti redirect?
4. Oracle-nya apa persisnya (status remote? validitas JSON? validitas schema?)
5. Ada refleksi isi? Kalau tidak, sebut "boolean oracle" dan jangan lebih.
6. Endpoint lain di API yang juga resolve `$ref`? Uji: endpoint feedback/upload/importer
   yang menerima string sering **tidak** fetch — itu hasil negatif yang memperkuat laporan
   ("primitif terbatas pada satu endpoint").

## Permukaan lain yang layak dicek (pola sama)

- `$schema` di dalam `parameters` (beberapa validator ikut fetch)
- `$ref` di JSON Schema untuk structured output / response_format
- spec OpenAPI yang di-upload user (server mem-parse lalu resolve referensi eksternal)
- tool/plugin manifest yang menyebut URL remote (MCP-style)
- import "from URL" di fitur dokumen/importer

## Anti-pola

- Jangan pakai `curl` sebagai bukti utama; pakai collaborator (interactsh) + raw log.
- Jangan laporkan "SSRF" hanya karena ada parameter URL — tanpa callback = tidak ada bukti.
- Jangan klaim brute-force/rate-limit dari request yang ditolak di tahap **validasi parameter**
  (mis. ephemeral SRP acak) — itu belum pernah jadi tebakan sungguhan.
