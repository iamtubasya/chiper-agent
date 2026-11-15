# Apollo APQ graphql — the public endpoint whose shape is `<Op>/<sha256>` in the path

When an SSR SPA's shell advertises `apiPath` like
`/api/pub/gql/<client>,/api/pub/<other>/<client>,/api/auth/gql/<client>` and a naive
`POST /api/pub/gql/<client>` returns an **edge 404** (plain `openresty` page, not the app's JSON),
the public GraphQL is almost certainly **Apollo Automatic Persisted Queries (APQ)** exposed as a
**GET with the operation name and the query hash in the path**:

```
GET /api/pub/gql/<client>/<OperationName>/<sha256-of-the-query>?variables=<urlencoded JSON>
```

Proven on a live engagement (2026-10, Swiss broadcaster): `POST /api/pub/gql/radiosunshine` → openresty
404, but `GET /api/pub/gql/radiosunshine/BreakingNews/02b34de59decad886a548b152c22aafbf10061ae`
→ `200 application/json` with real data. The `/api/pub/<other>/<client>/<Op>/<hash>` sibling prefix
answered identically.

## Discovery — where the `<Op>/<hash>` pairs come from

You cannot guess a sha256. Two sources leak them:

1. **Archive/URL datasets.** `waymore` (and other Wayback/CommonCrawl-derived URL sets) contain the
   SPA's *own* historic calls, hashes included:
   ```bash
   waymore -i target.ch -mode U -oU wm.txt
   grep -oE 'https?://[^ ]*/api/pub/gql/[^ ]+' wm.txt | sed 's/?.*//' | sort -u
   # -> .../api/pub/gql/radiosunshine/NewsArticleTeaser/14bedb896fcc46ee2f04ea5f8ad92ac9682cce33
   ```
   (This is how the whole operation set surfaced: BreakingNews, Traffic, WeatherForecast,
   CurrentWeather, LastPlayed, ChameleonSongRefresh, NewsArticleTeaser, ….)
2. **The SSR state blob** (`window.__APOLLO_STATE__`) may reference operation strings; and the
   `window.app` config names the `apiPath` prefixes. Neither gives hashes — those come from archives.

## Behaviour to expect (and the checks that confirm APQ)

```bash
B=https://$TARGET/api/pub/gql/<client>
curl -s "$B/X/0000000000000000000000000000000000000000?variables=%7B%7D"
#   -> {"errors":[{"message":"PersistedQueryNotFound"}]}   <-- hash-locked; only registered ops run
curl -s "$B/X/0000...?query=%7B__typename%7D"               # a &query= override is IGNORED (same error)
curl -s -o /dev/null -w '%{http_code}\n' "$B"               # POST/GET to the bare base -> edge 404
```
So the endpoint is reachable and unauthenticated, but **you can only run the operations the server
already has** — arbitrary queries/introspection are not possible via APQ. Say so in the write-up
instead of over-claiming.

## The finding that *does* land: schema/type/variable disclosure via error messages

GraphQL validation errors are returned verbatim, and they leak the schema of the persisted query's
root types:

```
Cannot query field "sponsor" on type "INewsArticle". Did you mean "sponsors"?     # leaks type + fields
Variable "$cityId" of required type "String!" was not provided.                   # leaks var name + type
```

Technique: call every archived `<Op>/<hash>`, then
- add nothing → some return data, some return a "Variable … not provided" error that **names the
  required variable and its type**; re-call supplying it (`?variables={"cityId":"luzern"}`).
- a *stale* persisted query (the SPA's own query has since diverged) returns a "Cannot query field"
  error → that is a free schema-type + field-name enumeration.
- look for an ID-shaped mandatory variable (`contextId`, `id`) and vary it (`NewsArticle:<n>`) for
  IDOR on unpublished/unlisted content.

Severity framing: **unauthenticated public GraphQL endpoint reachable + schema/type/variable
disclosure (LOW)**. The APQ hash-lock is the control that stops it being worse.

## Related

- Cross-tenant/edge-routing nuance and the `window.app` / SSR-state extraction live in the parent
  SKILL.md §2b. That prefix-vs-namespace reasoning is what tells you the advertised path is
  internal-only and pushes you to hunt the real shape.
- `hunt-graphql` for the general GraphQL testing matrix (introspection, field suggestions, batching)
  once you have a query-capable endpoint — APQ-gated endpoints do not give you that.
