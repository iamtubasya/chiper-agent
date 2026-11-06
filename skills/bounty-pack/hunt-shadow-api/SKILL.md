---
name: hunt-shadow-api
description: "Hunt shadow / zombie / undocumented API surface (OWASP API9 Improper Inventory Management) — enumerate the full API version history (v1/v2/beta/legacy paths, header- and subdomain-based versioning), pull and diff every reachable OpenAPI/Swagger spec (including ones only findable via the Wayback Machine), and behaviorally diff old vs. current versions for auth/rate-limit/validation regressions rather than just response-shape differences. Distinct from hunt-api-misconfig, which owns exploitation once you have a spec or endpoint (mass assignment, JWT, OData, Swagger-chain attacks); distinct from hunt-subdomain, which owns host-level discovery. This skill owns the version-inventory and behavioral-diff workflow itself. Use when the target has versioned API paths, multiple specs, a changelog referencing deprecated endpoints, or a mobile app whose hardcoded backend calls look older than the current web app's."
sources: owasp_api_top10_2023, portswigger_research, public_research
report_count: 0
---

## OWASP API9 — Improper Inventory Management (Shadow / Zombie APIs)

As an API evolves, old versions and internal/staging routes routinely stay reachable without
receiving the same security fixes as the current version — because nobody tracks that they
still exist. The bug is rarely in one endpoint; it's in the **delta** between what an old
version enforces and what the current version enforces on the same operation.

### When to use

Trigger when:
- Versioned paths are visible (`/v1/`, `/v2/`, `/api/2023-01-01/`) or `Accept`/`X-API-Version`
  headers are in play.
- A changelog, release notes, or deprecation notice references removed/old API behavior.
- A mobile APK/IPA (via `apk-redteam-pipeline` / `ios-redteam-pipeline`) hardcodes endpoints
  that look like an older backend version than the current web app calls.
- Multiple OpenAPI/Swagger specs are discoverable, or `info.version` in one spec implies others
  exist.

DO NOT use for single-version APIs with no version history — there's nothing to diff; go
straight to `hunt-api-misconfig` for direct exploitation of the one surface that exists.

---

## Stage 1 — Enumerate the Full Version Surface

```bash
# Path-based versioning
for v in v1 v2 v3 v4 beta alpha internal legacy old 2022-01-01 2023-01-01 2024-01-01; do
  curl -s -o /dev/null -w "%{http_code} /api/$v/\n" "https://$TARGET/api/$v/"
done

# Header-based versioning
curl -s -H "X-API-Version: 1" https://$TARGET/api/users
curl -s -H "Accept: application/vnd.company.v1+json" https://$TARGET/api/users

# Subdomain-based versioning
for sub in api api-v1 api-v2 apiv1 apiv2 legacy-api old-api internal-api staging-api; do
  curl -s -o /dev/null -w "%{http_code} $sub\n" "https://$sub.$TARGET/"
done
```

A `200`/`401`/`403` on an old version path (anything but `404`/connection-refused) means the
version is still live and worth carrying into Stage 3, even if it demands auth.

---

## Stage 2 — Pull Every Reachable Spec, Not Just the Linked One

```bash
for path in openapi.json swagger.json v1/swagger.json v2/swagger.json v3/api-docs \
            api-docs.json swagger/v1/swagger.json .well-known/openapi.json; do
  curl -s -o /dev/null -w "%{http_code} /$path\n" "https://$TARGET/$path"
done

# Wayback Machine — a DEPRECATED version's spec often stays indexed after the live link is removed
curl -s "http://web.archive.org/cdx/search/cdx?url=$TARGET/*swagger*&output=json&collapse=urlkey"
curl -s "http://web.archive.org/cdx/search/cdx?url=$TARGET/*openapi*&output=json&collapse=urlkey"
```

### Stage 2b — The initializer chain: when EVERY conventional spec path is 404

A host can `404` on every path in the loop above and still ship a Swagger UI. Probe the **UI**,
not the spec, then read the real spec URL out of the UI's own bootstrapping file:

```bash
for p in swagger-ui/ swagger-ui/index.html swagger-ui/swagger-initializer.js \
         swagger/index.html swagger.json docs/index.html; do
  curl -s -o /dev/null -w "%{http_code} /$p\n" "https://$HOST/$p"
done
grep -oE '"url":\s*"[^"]*"' swagger-initializer.js   # -> the real spec path, often non-standard
```

`swagger-initializer.js` is where `SwaggerUIBundle({ url: "…" })` gets its spec location; a
dockerised Spring/Go service routinely edits only that line, so `/v3/api-docs` can 404 while
`/api-doc/openapi.json` answers 300 KB. Also probe the neighbouring spec names once you know the
service stacks one (`/api-doc/openapi.json`, `/api-docs`, `/spec`, `/openapi.yaml`).

**Worked case (0.xyz, 2026-10-14).** `ffuf -fc 404` over `common.txt` against `api.<target>` returned
**0 results**, and the host was written up in the draft report as "dormant / every path 404".
A later `nuclei` run's `swagger-api` template hit `/swagger-ui/swagger-ui.js` → initializer →
`"url": "/api-doc/openapi.json"` → a **72-path OpenAPI spec** that documented an entire privileged
surface: `/v0/internal/api-keys` CRUD, `/v0/internal/referrals`, `/v0/internal/announcements`
CRUD, `/v0/internal/analytics/users`, and `/v0/internal/smoketest` ("run with the funded local
wallet"). Everything except 12 ops was anonymous-inherited.

Two generalisations to carry forward:

- **`404` on a generic wordlist is not evidence of dormancy.** Deep UI paths are absent from
  `common.txt`/`raft` directory lists because they are assets, not directories. State coverage as
  "`N` wordlists × `M` paths, no hit" — never as "the service is empty".
- **Content-match scanners and content-length fuzzers are complementary, not redundant.** ffuf
  answers "does this wordlist entry hit"; nuclei's templates answer "does this path serve a known
  artifact". `-fc 404` additionally makes ffuf blind to a `200` with an unexpected body shape.
  Run both, and re-run the first after the second names a path family.

Once a spec is in hand, prefer `jq -r '.paths | keys[]'` over any further fuzzing: the spec is the
authoritative inventory **and** it carries the auth model (`components.securitySchemes`,
per-operation `security`). A global `security: [{}, {ApiKeyAuth}, {BearerAuth}]` with 12 operations
override-narrowed to `[{ApiKeyAuth}, {BearerAuth}]` tells you exactly which routes to probe bare and
which are gated — before you send a single request. Scan the spec's own text for stray secrets too
(`bearer`, `eyJ…`, internal hostnames): a clean one is a stated negative worth having.

When more than one spec resolves (a current one and an archived/old one), diff the endpoint
inventories directly:
```bash
jq -r '.paths | keys[]' v1-swagger.json | sort > /tmp/v1_paths.txt
jq -r '.paths | keys[]' v2-swagger.json | sort > /tmp/v2_paths.txt
comm -23 /tmp/v1_paths.txt /tmp/v2_paths.txt   # in v1 only — candidates for "still live but forgotten"
```
For every path in that diff, confirm it's still reachable against the v1 base URL. A route
documented only in the old spec that still returns something other than `404` is a zombie-
endpoint candidate — carry it into Stage 3.

---

## Stage 3 — Behavioral Diff Between Old and Current Version

For each operation that exists in **both** versions, compare security-relevant behavior, not
response shape. Response shape differences are Informational; behavioral security regressions
are the finding.

- **Auth strength.** Does the old version accept no token, an expired token, or a lower-
  privilege token that the current version rejects?
  ```bash
  curl -s -H "Authorization: Bearer $EXPIRED_TOKEN" https://$TARGET/api/v1/users/me -w '\n%{http_code}\n'
  curl -s -H "Authorization: Bearer $EXPIRED_TOKEN" https://$TARGET/api/v2/users/me -w '\n%{http_code}\n'
  ```
- **Rate limiting.** Burst the same number of requests against both versions' equivalent
  endpoint; a missing `429` on the old version means rate-limiting was added later and never
  backported.
- **Input validation.** Send the identical injection/oversized/malformed payload to both; the
  old version accepting what the new one rejects means hardening happened forward-only —
  chain into whichever injection class the payload targets (`hunt-sqli`, `hunt-idor`, etc.).
- **Field exposure.** Does the old version's response body include fields — internal IDs, other
  users' data, internal notes, PII — that the current version has since redacted?

---

## Stage 4 — Deprecated / Internal Routes Never Referenced by the Current UI

- Grep JS bundles for API calls no visible UI flow triggers (`/internal/`, `/admin/`, `/debug/`,
  `/_internal/`, `/test/`, `/staging/`) — reuse `hunt-source-leak`'s JS-bundle grep patterns for
  this specifically.
- Check `robots.txt` / `sitemap.xml` for disallowed API paths — a self-inflicted disclosure.
- Mobile-app endpoint inventories (via `apk-redteam-pipeline` / `ios-redteam-pipeline`) very
  often reference an older backend version than the current web app calls. Treat every
  APK/IPA-sourced endpoint as a version-diff candidate against the live web API.

---

## False-Positive Gate

- A version difference alone (different response shape, cosmetic field renaming) is
  Informational. The finding is a **security-relevant regression** — auth, rate-limit, or
  validation that got weaker going backward in version history.
- Confirm the old endpoint is not simply an alias/proxy to the current implementation before
  claiming a behavioral difference — send a payload that would actually behave differently
  under old vs. new logic, not just compare a version string in the response body.
- A `200` on a path that just serves a static "this API version is deprecated, use v2" message
  is not a finding — confirm the underlying operation still executes.

---

## Severity Table

| Finding | Severity |
|---|---|
| Old version bypasses auth entirely where current version requires it | Critical |
| Old version missing rate-limit present on current version | Medium–High (chain via `hunt-brute-force`) |
| Old version leaks extra fields (PII, internal IDs) vs. current | Medium–High |
| Old version accepts payloads the current version now validates/sanitizes | High (chain to the underlying injection class) |
| Version is reachable but behaviorally identical to current | Informational |

---

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Diff versi: `/api/v1/` vs `/api/v2/` — endpoint lama masih hidup? | Zombie API |
| 2 | JS bundle: grep `/api/`, endpoint, parameter tersembunyi | Permukaan tak terdokumentasi |
| 3 | Mobile API: intercept aplikasi mobile untuk endpoint internal | API khusus mobile |
| 4 | Route deprecated: `/old/`, `/legacy/`, `/internal/` | Authz lebih lemah |
| 5 | Parameter tak terdokumentasi: tambah `debug`, `admin`, `internal` | Fitur tersembunyi |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis
N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Gate 0 Validation

1. **Apa yang bisa dilakukan penyerang SEKARANG?** "Penyerang bisa memanggil `/api/v1/admin/users` yang masih aktif tanpa auth" — tunjukkan data yang dikembalikan.
2. **Apa yang hilang dari korban?** Data atau aksi pada endpoint tak terdokumentasi. Sebutkan endpoint spesifik.
3. **Bisa direproduksi 10 menit dari nol?** Sertakan request dan respons.

## Eskalasi wajib (jangan berhenti di kelas ini)

**Primitif:** akses endpoint tak terdokumentasi

**Teknik pengembangan:** versi lama tanpa patch; endpoint internal tanpa auth

**Eskalasi ke:** `hunt-idor` · `hunt-auth-bypass` · `hunt-data-exposure`

**Depth target:** L2 -> L4

Satu temuan di kelas ini WAJIB menyebut eskalasi berikutnya (atau alasan primitif habis).
Lihat `exploit-chain-graph` + `exploit-depth` (L0-L5). `depth_gate.py` memblokir temuan
yang buktinya cuma status code.

## Related Skills & Chains

- **`hunt-api-misconfig`** — owns exploitation once a spec or endpoint is in hand (mass
  assignment, JWT attacks, OData, Swagger-chain attacks). This skill hands it a sharper target:
  "here's a zombie endpoint with weaker validation than the current one."
- **`hunt-subdomain`** — owns host/subdomain-level discovery (`api-v1.target.com` as its own
  host, potential takeover). This skill owns what happens once you're inside a given host's
  version surface.
- **`hunt-source-leak`** — JS-bundle grep for internal/undocumented calls; reused here
  specifically for version-diffing rather than secret extraction.
- **`apk-redteam-pipeline`** / **`ios-redteam-pipeline`** — mobile builds routinely hardcode an
  older API version; every mobile-sourced endpoint is a version-diff candidate.
- **`hunt-brute-force`** — a rate-limit regression found here is only a complete finding once
  chained to actual brute-forceable impact (login, OTP, enumeration).

## 2026 sweep (dork pass 2026-10-26 — advisori + riset kategori)

- **CVE-2026-5022 — API endpoint auth bypass.** Endpoint API yang tidak menerapkan pemeriksaan autentikasi yang dimiliki endpoint lain pada aplikasi yang sama.
  Lesson: authz yang tidak konsisten antar-endpoint adalah pola #1 kelas ini. Cara menemukannya: **petakan semua endpoint dari JS bundle + dokumentasi, lalu bandingkan mana yang mengembalikan 401 dan mana yang tidak** — yang tidak, padahal seharusnya iya, adalah kandidat.
- **Kategori Zombie API (riset 2026: saaspentest.io, ox.security, ammune.ai).** Endpoint yang dulu terdokumentasi dan digarap, lalu **deprecated di atas kertas tapi tetap berjalan di produksi**. Karena deprecated, endpoint itu kehilangan patch keamanan, update skema, dan review akses — sementara tetap berjalan di atas library lama.
  Lesson: cari penanda versi dan siklus hidup di path: `/api/v1/`, `/api/v2/`, `/old/`, `/legacy/`, `/internal/`, `/deprecated/`, `/beta/`, `/v1/`. **Endpoint v1 yang masih hidup setelah v3 rilis adalah target prioritas** — ia berjalan di atas library lama DAN biasanya lolos dari review authz terakhir.
- **Kategori Shadow API.** Endpoint tak terdokumentasi yang **melewati API gateway dan WAF sama sekali** karena tidak pernah masuk inventaris. Penyerang yang menemukannya berinteraksi dengan "hantu arsitektur masa lalu" — tanpa aturan gateway modern.
  Lesson: sumber terbaik untuk menemukan shadow API adalah **bundle JS aplikasi mobile dan SPA** (grep `fetch`/`axios`/base URL), bukan dokumentasi. Endpoint khusus mobile paling sering tidak terdokumentasi dan paling lemah authz-nya.

**Metode deteksi yang bekerja:** (1) diff `urls.txt` hasil `gau`/`waymore` (arsip historis) terhadap endpoint yang benar-benar hidup — arsip memuat endpoint yang sudah dihapus dari UI tapi mungkin masih hidup; (2) grep bundle JS untuk string `/api/`; (3) fuzz dengan wordlist versi (`v1`, `v2`, `internal`, `legacy`) di atas path yang sudah diketahui.


## Critical severity anchor (kelas ini bisa Critical — syaratnya)

| Kondisi | Severity |
|---|---|
| Shadow endpoint yang melewati gateway DAN tidak punya authz | Critical |
| Shadow endpoint dengan authz lebih lemah dari versi resmi | High-Critical |
| Shadow endpoint hanya ekspos data publik | Info |
| Endpoint arsip yang masih hidup tapi sudah dihapus dari UI | Medium-High |

**Kalibrasi wajib:** "endpoint tidak terdokumentasi" BUKAN temuan. Temuan adalah endpoint yang
**melewati kontrol keamanan** (gateway, WAF, authz) yang versi resminya punya.

## 2026 sweep

- **Bundle JS mobile & SPA sebagai sumber utama** — grep `fetch`/`axios`/base URL. Endpoint khusus
  mobile paling sering tidak terdokumentasi dan paling lemah authz-nya.
- **Diff arsip vs live** — `gau`/`waymore` memuat endpoint yang sudah dihapus dari UI tapi mungkin
  masih hidup.
- **Version fuzz** — `v1`, `v2`, `internal`, `legacy` di atas path yang sudah diketahui.
- **API gateway path mismatch** — gateway memfilter `/api/v2/*` tapi `/api/v1/*` atau
  `/internal/api/*` lolos.
