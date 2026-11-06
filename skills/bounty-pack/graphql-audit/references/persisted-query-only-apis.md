# Persisted-query-only GraphQL APIs (no introspection, no arbitrary ops)

Some large SPAs expose a GraphQL endpoint that **rejects every arbitrary operation** and
only answers pre-registered (persisted) queries keyed by an opaque id. Naive probing looks
like a dead end; it is not.

Case study: Tripadvisor `POST https://www.tripadvisor.com/data/graphql/ids` (2026-10).

## 1. Detect

```bash
curl -s -X POST "$B" -H 'content-type: application/json' -H "User-Agent: ...bugcrowd..." \
  -d '{"query":"{__typename}"}' -w '\n%{http_code}\n'
# 200 {"errors":[{"message":"Arbitrary operations not available to untrusted clients"}]}
```
- `GET` → `405 Method not allowed`.
- Introspection / arbitrary doc / field-suggestion probes all return the *same* generic
  "arbitrary operations not available" error — so §1–§3 oracles in the parent skill do
  **not** apply here. That message is itself the signal: an allowlist of persisted ids exists.

Do NOT read "arbitrary operations blocked" as "no attack surface". The surface is every
allowlisted query, callable with **attacker-chosen variables**.

## 2. Harvest the query ids from the app's own traffic

The ids and the variable shapes only exist in the app's requests, so capture them:

- Python + `websocket-client`: attach to the page target, `Network.enable`,
  `Page.navigate` a data-rich page, then read `Network.requestWillBeSent` and print
  `request.postData` for URLs matching `graphql`.
  NOTE: a JS `fetch`/`XHR` monkey-patch injected before load **missed these calls** in the
  session (framework pre-bound its fetch). `Network.enable` caught all 11. Prefer the
  protocol domain over in-page hooks for this.
  See `browser-cdp-auth-audit` → "Capturing the app's own API calls".

Observed wire format — a **batched JSON array**, one object per operation:
```json
[{"variables":{"userId":"7704590F6F24262FA899A73571B6E1C0"},
  "extensions":{"preRegisteredQueryId":"afb52b3d56ec64e7"}}]
```
Ids are 16-hex (`preRegisteredQueryId`). Harvest them by page: a hotels listing yielded
`e61c41aba1e70583` (search), `25f9ddb1ce629144` (location by id), `afb52b3d56ec64e7`
(userId→trips), `7b2d1f78e3dc76a4` (experiment+userId), telemetry, config, etc.

## 3. Replay and mine variables for BOLA/IDOR

Replay from inside the real authenticated page (in-page `fetch`, so cookies + DataDome
clearance apply). Store the result on `window` and read it in a separate `Runtime.evaluate`
(awaitPromise on a non-invoked arrow returns `{}` — see parent skill trap #0):

```js
window.__r=null;
fetch('/data/graphql/ids',{method:'POST',headers:{'content-type':'application/json'},
  body:JSON.stringify([{variables:{userId:'7704590F6F24262FA899A73571B6E1C0'},
    extensions:{preRegisteredQueryId:'afb52b3d56ec64e7'}}])})
 .then(r=>r.text().then(t=>window.__r={s:r.status,t:t.slice(0,900)}));
// next call: JSON.stringify(window.__r)
```

For each query, swap the object id in `variables` for a value you do not own. Evidence of a
missing ownership check = a normal result (not an auth error) for a foreign id.

## 4. Pitfalls that stop you declaring a false IDOR

1. **Input-format validation ≠ authorization.** A malformed id (`"1"`, all-zeros, wrong
   length) returns a *generic error* (`Error #243441195 …`), which is **validation**, not an
   authz decision. Only a well-formed foreign id returning *data* proves anything.
2. **Two empty results prove nothing.** Own userId → `{"tripCount":{"trips":[]}}`;
   random valid 32-hex userId → also `{"tripCount":{"trips":[]}}`. Both empty is
   **INCONCLUSIVE** — it cannot distinguish "server ignores the id and returns the caller's
   data" (safe) from "server returns any user's data" (BOLA), because the caller has no data
   to leak. You need a foreign id that is *known to be populated*. Say so; do not infer.
3. **Check the feature is in scope before investing.** On Tripadvisor the userId→trips query
   reaches the **Trips** feature, which the brief lists OOS (`*.tripadvisor.*/Trips`). A
   proven BOLA on an OOS feature is not reportable. Confirm the feature against the program
   brief *before* building the PoC.
4. Send a batch of probes in one request (the array format allows it) — cheaper and matches
   the app's own shape.

## 5. Honest reporting when it is a control, not a bug

`{"errors":[{"message":"Arbitrary operations not available to untrusted clients"}]}` is a
**working security control**. Document it as a verified negative in the engagement log; do
not dress it up as a finding.

## 6. Variant: path-encoded Apollo APQ (`/<Operation>/<sha256>` in the URL)

Some SPAs don't POST a query id — they **GET** it, with the operation name and the query hash in
the **PATH** and the variables in the query string:

    GET /api/pub/gql/<skin>/<Operation>/<sha256>?variables={"userId":"..."}
    GET /api/auth/gql/<skin>/<Operation>/<sha256>?mutation=1&variables={"onAirId":"..."}   # authed / writes

Case study: radiosunshine / sunshine.ch (CH Media), 2026-10. The logged-in SPA's own traffic
exposed `…/FavouriteStreams/61974670…?variables={"userId":"459caee0-…"}`,
`…/Page/84a80e76…?variables={"prefix":"default","path":"/"}`,
`…/UserProfile/0674295d…` (auth gql), and `…/MarkFavouriteStream/<hash>?mutation=1&variables={"onAirId":"…"}`
(a write — mutate nothing you do not own).

### Find the shape when live probing 404s
`POST /api/pub/gql/<skin>` (no suffix) returns the edge's plain `404` — the route only exists
**with** the suffix, so blind probing never finds it and it *looks* internal-only. Harvest it from
the archive corpus instead:

    waymore -i target.ch -mode U -oU urls.txt         # passive: Wayback / CommonCrawl / URLScan
    grep -oE '/api/[a-z]+/gql/[^ ?]+' urls.txt | sort -u

Same lesson as §2 (the shape lives in the app's own traffic): when the live page is a JS-rendered
SPA you can't scrape it with curl, and a CDP/`performance` capture needs a logged-in session — so
the archive corpus is the cheapest source. Do this BEFORE writing off an `/api/*` namespace.

### Behaviour
- Unknown hash → `200 {"errors":[{"message":"PersistedQueryNotFound"}]}` — the endpoint is
  **allowlist-locked** to the app's registered operations. A `?query=` / `&query=` override is
  **ignored** (still `PersistedQueryNotFound`).
- Variables are attacker-chosen and are the entire surface: swap ids for BOLA, swap
  `prefix`/`path` for hidden content, add `limit`/`offset` for over-fetch.

### Schema leak from a STALE persisted query (introspection off)
When a registered query references a field the schema has since renamed, the persisted-query
validation error leaks the schema — no introspection needed:

    {"errors":[{"message":"Cannot query field \"sponsor\" on type \"INewsArticle\". Did you mean \"sponsors\"?","locations":[{"line":73,"column":7}]}]}
    {"errors":[{"message":"Variable \"$cityId\" of required type \"String!\" was not provided."}]}

Read the error for **type names, sibling field names, and required variable names/types**, then
feed variables to the ops that DO resolve. That is the §1 field-suggestion oracle for free.
