# CORS Misconfiguration Variant Matrix — every ACAO shape + proof bar

Katalog eksekusi cepat untuk `hunt-cors`. Detail + browser PoC tetap di SKILL.md; di sini semua
varian reflection shape dipetakan jadi tabel satisfied-condition + proof bar. Additive-only.

**Prinsip utama (dari SKILL.md):** reflection saja = Informational. Yang bayar = **credentialed
read** — `Access-Control-Allow-Origin: <attacker>` **DAN** `Access-Control-Allow-Credentials: true`
dengan cara yang membuat browser BENAR-benar mengirim cookie ke attacker origin.

---

## A. ACAO reflection shape matrix

| # | Server mengembalikan | Exploitable untuk credentialed theft? | Catatan |
|---|---|---|---|
| A1 | `Access-Control-Allow-Origin: *` | **TIDAK** | browser blok credential read dengan wildcard |
| A2 | `ACAO: https://evil.com` (reflect arbitrary) + `ACAC: true` | **YA — Critical** | attacker origin baca credentialed response |
| A3 | `ACAO: https://evil.com` **tanpa** `ACAC` | TIDAK | no creds, hanya baca non-auth data |
| A4 | `ACAO: null` + `ACAC: true` | **YA** | null-origin trust (sandboxed iframe, data:) |
| A5 | `ACAO: https://target.com.evil.com` (prefix/substring) | YA | regex `startsWith("target.com")` bypass |
| A6 | `ACAO: https://eviltarget.com` (suffix) | YA | regex `endsWith("target.com")` bypass |
| A7 | `ACAO: https://target.com, https://evil.com` (multi-item) | bervariasi | lihat §B — header HYPER yang keliatan crown-jewel |
| A8 | `ACAO: https://sub.target.com` | YA (jika sub takeover) | chain `hunt-subdomain` |
| A9 | `ACAO: http://target.com` (insecure/scheme-lowered) | YA | trusted HTTP origin → MitM/pollution |
| A10 | `ACAO: https://target.com%60.evil` (encoded/unicode) | YA | URL parser confusion |

---

## B. Malformed / multi-item ACAO (header yang keliatan crown jewel tapi sering false)

`Access-Control-Allow-Origin: https://attacker.com, https://target.com` atau
`...: attacker.com target.com` (space-separated) — browser modern (Chrome/Firefox) **menolak**
multi-value ACAO. Tapi beberapa proxy/CDN/http-library menormalkannya beda. Selalu cek dengan
**browser sungguhan** (bukan `curl`), karena `curl` tidak memodelkan CORS preflight/same-origin.

**Rule:** reflection di `curl` ≠ exploitable. Bukti PAYABLE = PoC HTML yang di-load dari attacker
origin dan BENER-bener membaca `responseText`.

---

## C. Pre-flight (OPTIONS) gating bypass — the write-CSRF-adjacent

```bash
# cek preflight mengizinkan method/header yang seharusnya diblok
curl -s -X OPTIONS https://<TARGET>/api/admin/users \
  -H "Origin: https://evil.com" -H "Access-Control-Request-Method: DELETE" \
  -H "Access-Control-Request-Headers: X-Custom-Auth" -i
```

| Cek | Vulnerable jika |
|---|---|
| `Access-Control-Allow-Methods` berisi `PUT`/`DELETE`/`PATCH` | attacker origin bisa issue write authed |
| `Access-Control-Allow-Headers` berisi custom auth header | attacker bisa set `Authorization`/`X-Api-Key` |
| `Access-Control-Allow-Credentials: true` | ...dan ACAO reflect attacker |

**Kill-signal:** attacker origin melakukan **write** terautentikasi (bukan cuma read).

---

## D. Vary / cache interaction (CORS + cache poisoning)

`Vary: Origin` absen + response cacheable → ACAO stiker menempel ke cache → poisoning. Cross-ref
`hunt-cache-poison` / `hunt-host-header` Phase 2.

---

## E. postMessage origin-check weakness (sibling surface)

```javascript
// weak checks to flag (from SKILL.md):
event.origin.indexOf("target.com") > -1     // "target.com.evil.com" lolos
event.origin.endsWith("target.com")         // "eviltarget.com" lolos
event.origin.startsWith("https://target")   // "https://target.evil.com" lolos
// no check at all
```

**Proof bar:** demo event.origin jahat mengirim data/aksi ke handler yang nerima.

---

## F. Fingerprint quick-ref (sweep cepat)

1. `curl -s -D - -o /dev/null -H "Origin: https://evil.com" https://<TARGET>/api/...` → baca ACAO/ACAC.
2. `-H "Origin: null"` → cek null-trust.
3. `-H "Origin: https://target.com.evil.com"` → cek prefix/regex.
4. `-X OPTIONS` dengan `Access-Control-Request-*` → cek preflight methods/headers.
5. Browser PoC (wajib) — `curl` tidak pernah jadi bukti CORS.

## Refusal-pattern

- `ACAO: *` tanpa ACAC → **bukan** credentialed theft, jangan lapor High.
- Reflection `curl` tanpa browser PoC → Informational, bukan Critical.
- ACAO multi-item yang browser tolak → false positive (cek browser nyata dulu).