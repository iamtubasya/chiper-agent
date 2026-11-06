# Cross-tenant data-access matrix — "can I read another user's ledger?"

Template + verified results from Quarterwise (2026-10-01), run because the operator asked directly:
*"from the user-data side, can you get leaked data, or other users' ledger data?"* This is a named
pass, not a BOLA hunt: the deliverable is a matrix of what held.

## Tenants and credentials — what you need

| Role | Credential | Why |
|---|---|---|
| A — first tenant | Bearer API key (`/api/v1/me` → `accountId` + `plan`) | survives a dead browser session |
| B — second, INDEPENDENT tenant | `qw_session` cookie of another account you own | the only way to prove horizontal isolation |
| C — nobody | none | unauth baselines |

Prove the credentials are different tenants before you start: `/api/v1/me` for the key,
`/api/account/export` for the cookie (`users[].email`, `plan`). Same tenant = the whole matrix is
meaningless. Harvest B's own object ids from `/app`, `/app/imports`, `/app/review`,
`/app/account*`, and one `/app/sources/<own-uuid>` (`re.findall(uuid_regex, html)`).

## The 17 vectors

| # | Vector | Quarterwise result |
|---|---|---|
| 1 | B → A object pages: `/app/sources/{A}` (+`?ty=`), `/app/clients/{A}`, `/app/imports/{A}` ×5 | all **404** |
| 2 | A (API key) → B sources: `/api/v1/sources/{B}/transactions` | **404** `source_not_found` ("No source with that id on this account.") |
| 3 | **`/api/properties/{id}/export?format=pdf\|xlsx&taxYear=`** (full ledger export) | own **200** real file; A's 3 sources, client's source, random uuid → **404**; unauth **307**; API key **307** (session-only) |
| 4 | `taxYear` / `format` injection (`1900`, `../../etc/passwd`, `../x`) | `400 bad tax year`; format whitelisted (still xlsx) |
| 5 | Header tenant spoofing: `X-Account-Id`, `X-User-Id`, `X-Client-Id`, `X-Organisation-Id`, `X-Firm-Id`, `X-Tenant-Id`, `accountId`, `X-Account` | all **ignored** (identical own response) |
| 6 | Query-param tenancy: `accountId`, `clientId`, `userId`, `sourceId`, `includeShared`, `all`, `debug`, `raw` | all **ignored** |
| 7 | `/api/v1/sources/{id}/transactions` param abuse (`limit=1e9/-5/offset=-1/99999`) | `limit` validated 1–200 (`422` outside); unknown params ignored |
| 8 | `/api/account/export` as B | own data only (`plan`, `createdAt`, `users`, `clients`, `businesses`, `properties`, `submissions: []`) |
| 9 | `/app/clients/export.csv` as a NON-firm account | **200 with a header-only CSV** — scoped, not a leak |
| 10 | Server action "Save settings" + foreign `propertyId` (B's session) | `"Only the owner can change these settings."` |
| 11 | Server action "Ownership share" (Form 17) + foreign `propertyId` | `"That property could not be found."` |
| 12 | Server action "Delete property" + random `propertyId` | `"Only the property owner can delete a property."` |
| 13 | Unauth `/app/*`, `/api/account/export`, `/api/documents/{id}` | **307** → /login |
| 14 | Unauth id spaces `/api/og/{id}/{b64}.png`, `/api/img/{areas,guides,tools}/{slug}`, `/api/blog-image/{slug}` with tenant uuids | **404** "Not found" — content slugs, not user objects |
| 15 | `/api/staticmap?q={uuid}` unauth | 200 generic PNG map, no tenant data |
| 16 | Artifact content check: parse the export for foreign markers | only the requesting tenant's own email/property/entries |
| 17 | Share revocation | the shared source no longer appears in the owner's `/api/v1/sources` and 404s directly → revocation works |

## Existence-oracle test (do this explicitly)

```
A's source id     -> 404 {"error":"not found"}   21 bytes
client's source   -> 404 {"error":"not found"}   21 bytes
random uuid       -> 404 {"error":"not found"}   21 bytes
API: all three    -> 404 {"error":{"code":"source_not_found","message":"No source with that id
                     on this account."}}
```

Byte-identical bodies across the three id classes = no oracle. A different body/length/message for
"exists but not yours" IS reportable (enumeration), even when no data leaks.

## Artifact verification (turns "scoped" into evidence)

```python
r = S.get(f"{BASE}/api/properties/{SELF}/export?format=pdf&taxYear=all", timeout=45)
import pymupdf; d = pymupdf.open(stream=r.content, filetype="pdf")
txt = "\n".join(p.get_text() for p in d)
assert not [t for t in ["<other tenant name>", "<other uuid>"] if t in txt]
# XLSX: unzip in memory, concatenate the XML parts, scan for foreign names/uuids
```

Header checks that matter on the same response: `content-type`, `content-disposition` filename
(carries the property's own slug), `%PDF` / `PK` magic bytes — a 200 with the wrong magic byte is a
different endpoint behaviour than a 200 with the file.

## Write-path ownership, HTTP-only

Override the hidden id on a REAL form and submit with the attacker's session:

```python
# Playwright route (robust): locate the form carrying the field, override, then requestSubmit()
form = pg.locator("[name='propertyId']").first.locator("xpath=ancestor::form[1]")
form.locator("[name='propertyId']").first.evaluate("(e,v)=>{e.value=v;e.dispatchEvent(new Event('input',{bubbles:true}))}", FOREIGN)
form.evaluate("f=>f.requestSubmit()")
pg.wait_for_timeout(4000)          # read page.on("response") → the 1:{"error":"..."} segment
```

Form indices shift per page (`$ACTION_4` settings / `$ACTION_5` delete / `$ACTION_6` share on one
source page), so enumerate forms and print each one's field names + action id before firing.
Use a RANDOM uuid when probing a destructive action; use a foreign-but-real id only for
non-destructive settings, and only where you own the target account.

## Honest gaps to state in the write-up

- **Login throttled:** `POST /login` → **504 after 60.21 s** + `retry-after: 120` (Cloudflare), so no
  fresh sessions. Everything session-dependent was run through one pre-existing valid cookie
  (`GET /app` → 200) plus the API key. Say so; do not imply you re-tested what you could not.
- **Session-only paths not re-driven:** firm/client pages, import-confirm, review queue, billing —
  all need a Pro session. List them as coverage gaps rather than "clean".
- **`nextCursor` tampering untested** because one tenant has no transactions and the other has no
  API key (free plan). Say that instead of scoring it.
- **Intermittent 500s** (`/app/file`, `/app/year-end`, digest-only error page) during a high-volume
  pass = likely your own throttling footprint; unverified, needs a clean-IP retest.

## Hygiene

No writes succeeded in this pass (every write attempt was refused by an ownership check), the only
requests that reached application state were two telemetry POSTs to an open `/api/collect`
(discarded payloads, body `accountId` not honoured). Re-verify state afterwards from the
authoritative side — `/api/v1/sources` transaction counts per source, and the second tenant's own
property page still 200 with its original name.
