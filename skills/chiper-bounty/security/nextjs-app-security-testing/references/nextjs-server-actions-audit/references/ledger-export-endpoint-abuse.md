# Ledger-export endpoint — full abuse sweep, and the shared-property three-surface result

Session: quarterwise.co.uk, 2026-10-01. Read-only. Endpoint found by grepping the authed bundle
for the *bare* path prefix (see SKILL.md → "Authenticated crawl → route-handler inventory"):

```
/api/properties/{id}/export?format=pdf|xlsx&taxYear=<year|all>
```

It returns the full property ledger (dates, categories, descriptions, amounts, the account email) as
PDF or XLSX. Neither the anonymous crawl nor the OpenAPI document lists it. Ownership was already
proven scoped (own 200, foreign/random 404, unauth 307, API key 307 — it is session-only). The
second pass asked "can the scoped lookup be bypassed, or the response leak to someone else?" —
49 probes, nothing found. Keep the table: these are the cheap, high-yield variants for any
authenticated file-export route.

| Vector | Probes | Result |
|---|---|---|
| Shared-cache / auth-response leak | prime own export → same URL **without** cookie; with `Cache-Control: no-cache`; foreign id anon | `CF-Cache-Status: DYNAMIC` on every response; no-cookie → **307**; no public cache directives → a cached authenticated export is never served |
| CRLF / header injection via `format` & `taxYear` (they land in `Content-Disposition`) | `format=pdf%0d%0aX-Injected:%201`, `taxYear=all%0d%0a…`, `format=%0d%0aSet-Cookie:…` | no injected header; format coerced to the whitelist; bad taxYear → 400 |
| Content/template injection via `taxYear` (it IS reflected into the PDF) | `2026-27`, `ZZ<tY><script>alert(1)</script>`, `{{7*7}}`, `'; DROP--` | only the strictly valid value is accepted; the rest → `400 {"error":"bad tax year"}` |
| Uppercase UUID | `{UUID}.upper()` | 200 — lookup is case-insensitive, still own-scope only |
| Path/encoding variants | `{id}/export/` · `{{id}}` · no-dash uuid · `/EXPORT` · `{id};x` · `../{foreign}` · `{id}%2f..%2f{foreign}` · `%252e%252e%2f{foreign}` · `{id}%00` | 308 (trailing slash) · 404 · 404 · 404 · 404 · 404 · 404 · 404 · **400 Bad Request** (`%00`) |
| Extra / duplicate params | `&id=`, `&propertyId=`, `&sourceId=`, `;id=` · `format=pdf&format=xlsx` · `format=` · `taxYear=all&taxYear=1900` | foreign-id params ignored (own file returned) · duplicates take the FIRST value · empty → default xlsx |
| Alternate id spaces (type confusion) | account uuid · client uuid · import uuid · `1` · `0` · `all` · `*` · `me` · `null` · `undefined` · random — **including the caller's OWN account id** | all **404**, byte-identical `{"error":"not found"}` (21 bytes); own account id also 404 → no type confusion, no oracle |
| Method / rewrite headers | `POST` + `X-HTTP-Method-Override: GET` · `X-Original-URL: <foreign export URL>` · `X-Rewrite-URL: …` · `X-Forwarded-Host: evil` | 405 · own PDF (header ignored, no rewrite bypass) · own PDF · no effect |
| Range / conditional / defaults | `Range: bytes=0-99` · `If-None-Match: *` · `HEAD` · no query at all | 200 full file (no 206) · 200 (no 304) · 200 no body · defaults to **xlsx** |

Two mechanical notes: a 200 with the wrong magic bytes is a different behaviour than a 200 with the
file, so always assert `%PDF` / `PK` on the body rather than trusting `content-type`; and the
`content-disposition` filename carries the property's own slug — a useful cross-tenant marker when
you spot-check an accepted response.

## Shared-property result (same session, firm session)

One shared property, badge "Can view" — the three surfaces disagree:

| Surface | Result |
|---|---|
| `/app/sources/{shared}` (firm session) | **200** — "You are viewing <client>'s books as their adviser · Can view" |
| `/api/v1/sources` (Pro API key) | the shared property is **absent** from the list |
| `/api/properties/{shared}/export` | **404** — a sharee cannot export the client's ledger |
| `/app/sources/{unrelated tenant}` (firm session) | **404** — access is per-share, not blanket |
| UI on the shared page | renders **only the logout form** — no save/delete/share/record controls |

Then, aiming three write actions at the shared property with the firm session (zero-risk oracles —
wrong confirm name, invalid percent, identical values):

```
updateSourceSettingsAction -> "Only the owner can change these settings."
updateOwnerShare           -> "That property could not be found."     (gate runs before validation)
deletePropertyAction       -> "Only the property owner can delete a property."
control (own property, wrong confirm name) -> "The name you typed does not match this property."
```

The control proves the foreign cases were stopped at the **ownership** gate rather than the
typed-name check. Report the read-yes / write-no / unrelated-no shape; the three-surface
inconsistency is a separate informational item (the release note claimed the API docs explain how
shared properties appear; in practice the API lists none).

## Hygiene after both passes

Firm: 3 sources, all `transactionCount: 0`, `sharePercent: 100`. Shared client property still
readable by the firm (200). Second tenant: property intact, 11 entries, own export byte-identical
(6,213 B). Review queue unchanged. Every write attempt was refused at the ownership gate →
**zero state change**. Re-verify from the authoritative side (`/api/v1/sources` counts + the second
tenant's own page) rather than from the UI.
