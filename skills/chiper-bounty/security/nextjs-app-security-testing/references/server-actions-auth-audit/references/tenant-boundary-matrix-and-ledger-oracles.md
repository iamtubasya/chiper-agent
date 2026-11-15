# Multi-tenant boundary matrix + ledger oracles

Reusable method for answering one question properly: **"can tenant B reach tenant A's data — read or
write?"** — with negative results that stand up, and with the oracles needed to know what actually
happened. Distilled from an authorized multi-round engagement on a hardened MTD bookkeeping SaaS
(Next.js App Router + form/JS server actions + a Bearer API + a per-object export endpoint).

## 0. Set up two independent tenants + one anonymous client

```
A = the account under test (however you were granted it — cookie session and/or Bearer API key)
B = a second, INDEPENDENT tenant you created yourself (register a fresh account)
C = no credentials at all
```

Harvest A's object ids from its own surfaces (page HTML, API list, export links) and B's from its own.
Then run every row below **in both directions** (B→A and A→B) — direction matters: a firm/admin plan
may have extra reach that a plain account does not, and vice versa.

Note: an API key and a browser session can belong to DIFFERENT accounts. Confirm the identity of each
before drawing conclusions (`GET /api/v1/me` → accountId; account export → plan/createdAt).

## 1. The matrix (cheap, run all of it before claiming "scoped")

| # | Vector | Expected-safe result |
|---|---|---|
| 1 | B requests A's object pages `/app/<noun>/{A_id}` (with and without query params) | 404 |
| 2 | A's API key requests B's objects `/api/v1/<noun>/{B_id}` | 404 + explicit code (`*_not_found`) |
| 3 | **Per-object EXPORT endpoint** `/api/properties/{id}/export?format=pdf\|xlsx&taxYear=` with A's ids from B (and vice versa) | 404, identical body to a random id |
| 4 | Aggregate exports: account export, firm/clients CSV | own data only; a non-firm account gets a header-only CSV, not an error |
| 5 | Header tenant overrides (`X-Account-Id`, `X-User-Id`, `X-Client-Id`, `X-Organisation-Id`, `X-Firm-Id`, `X-Tenant-Id`, `accountId`, `X-Account`) | response byte-identical to the un-overridden call (headers ignored) |
| 6 | Query-param tenant overrides (`accountId`, `clientId`, `userId`, `sourceId`, `includeShared`, `all`, `debug`, `raw`) | ignored |
| 7 | Pagination/limit abuse (`limit=1e9`, negative, huge offset, duplicated params) | validated (`limit must be 1..200`) or ignored |
| 8 | Unauthenticated requests to every object path | 307 → /login, or 401 |
| 9 | Unauthenticated "id spaces" (`/api/og/{id}`, `/api/img/…`, `/api/blog-image/{slug}`, `/api/staticmap?q=`) fed tenant UUIDs | 404 / generic image — content slugs only, no tenant data |
| 10 | Value injection in validated params (`taxYear=1900`, `../../etc/passwd`, `?format=../x`) | 400 `bad tax year`; format coerced to the whitelist |
| 11 | Path variants: uppercase UUID, `{uuid}`, no-dash, `;` matrix param, `../`, `%2f`, double-encoded `%252e`, `%00`, trailing slash | 404/400 (uppercase UUID may legitimately 200 — case-insensitive lookup is fine if still own-scoped) |
| 12 | Method/rewrite tricks: `POST` + `X-HTTP-Method-Override`, `X-Original-URL`, `X-Rewrite-URL`, `X-Forwarded-Host` | 405, or own data with the header ignored |
| 13 | **Cache check**: repeat an authenticated GET, then request the SAME URL with no cookie | `CF-Cache-Status: DYNAMIC` and 307 — if instead you get the authenticated file back, that is a real finding |
| 14 | Existence oracle: compare bodies for (own id / foreign valid id / random id) | byte-identical 404s ⇒ no existence disclosure, no enumeration oracle |

Rows 3, 13 and 14 are the ones most often skipped and the ones that produce the strongest negative
evidence. Row 3 is the highest-value read path (it returns the whole ledger as a file).

## 2. Oracles: how to know a write actually landed

- **Per-object export** (`/api/properties/{id}/export?format=pdf&taxYear=all`) — the ledger as
  PDF/XLSX. This is the truth for "did a row appear/disappear". The page UI only renders the SELECTED
  tax year, so rows in another year look like "0 entries".
- **Account export** (`/api/account/export`) — plan, users, clients, businesses, properties,
  submissions; confirms which tenant a change belongs to.
- **The other tenant's own session** — read B's export after a B-targeted write.
- **File size deltas** are a fast tripwire: the same export byte-size before/after (±1 byte from the
  generated-date) means nothing changed.

Parsing pitfall: the export's category/description columns contain commas, dots and mid-word ellipses
(`Other property i...`, `Rent, rates, insu...`). A strict
`(\d{2}/\d{2}/\d{4})\s+([A-Za-z ]+?)\s+(\S+)\s+([-+]?£[\d.,]+)` regex silently misses those rows and
produces false "0 rows" readings — count rows with a loose pattern (`\d{2}/\d{2}/\d{4}`) for
present/absent decisions, and only tighten it when you need the amounts.

## 3. Feeding an AI-categorisation / review queue on purpose

When the queue is empty ("Nothing to review") but you need to test its confirm action:

1. Upload a tiny CSV (3 rows, mixed signs, vague descriptions) through the app's import UI.
2. In the column-mapping step set the per-value category selects (`cat-key-*`) to **"Review later"** —
   that is the option that routes a row into the queue instead of auto-categorising it.
3. Assign the destination object, continue to preview, import.
4. The queue now lists the row with its hidden `txnId`, a `category` select and a **Confirm** button —
   that is the confirm action under test.
5. Pending rows do NOT appear in the ledger export until confirmed; they appear after.

## 4. Cleanup after driving the UI (do this before you write the report)

- Entries created via the UI may live in a **different tax year than the page's default filter** — set
  the tax-year selector to "All time" before hunting for the delete buttons, otherwise the row
  controls are not rendered at all and it looks like the delete control does not exist.
- Row actions are usually `button[aria-label="Delete entry"]` → click → confirm with an inline
  **Yes** button (same form), then re-check the export.
- "Undo import" buttons did NOT fire from `evaluate(click())` in headless (no POST captured); deleting
  the rows individually worked reliably. If a batch-level undo will not fire, delete the entries.
- Import batch *records* commonly have no delete control — they remain as disclosed residue. Note them
  explicitly (ids + that they are empty) in the deliverable instead of quietly leaving them.
- Final hygiene pass: both tenants' exports (row counts + byte sizes), the review queue state, the
  API key still valid (`/api/v1/me` → 200), and any share/role objects still intact.

## 5. Outcome shape that makes the negative result credible

Report per action:

| action | foreign target | server response | positive control |
|---|---|---|---|
| addTransaction | propertyId → B | `That property could not be found.` | own property: entry created |
| updateTransaction | txnId → B | `That entry could not be found.` | own entry: amount changed |
| deleteTransaction | txnId → B | no-op (foreign untouched) | own entry: deleted |
| review Confirm | txnId → B | no-op (item still queued) | own id: item confirmed, queue emptied |

Without the control column, "no-op" is indistinguishable from "my request never reached the server".
