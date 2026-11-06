# Harvesting the API surface from client bundles when the API is unreachable

Use when the API host is blocked (challenge/geo) but the storefront and its JS bundles are
reachable. Zero live requests to the API, and it turns a dead session into a ranked target
list for the next session that has a usable egress.

## Why this works
A GraphQL/SPA frontend ships every operation it can perform: operation name, argument
signatures, and the full selection set (including every PII field it can receive). That is a
complete map of the attack surface, minus the schema's hidden parts — and it is exactly what
you need to prioritise once you can talk to the API.

## Recipe

1. **Find the bundles the app actually loads.** `page.on("request")` filtered on
   `resource_type == "script"` and a `.js` suffix, while driving the real UI. Static HTML
   parsing misses lazily-loaded chunks.
2. **Download them through the page, not through an HTTP client.**
   `page.evaluate` running `fetch(url)` uses the browser's own TLS/fingerprint and the page's
   cookies. `context.request.get()` and curl both got 403 where in-page `fetch` got 200 —
   the edge was fingerprinting the client. Same lesson as the parent SKILL.md.
3. **Extract operations with a regex over the bundle text.**
   ```python
   re.finditer(r'(?:query|mutation)\s+([A-Za-z_][A-Za-z0-9_]{2,45})\s*\(([^)]{0,300})\)?\s*\{', t)
   ```
   Bundled GraphQL documents are template literals (`gql\`query Foo($x: String!) {...}\``), so
   the operation name and the `$args` list fall out cleanly. Fragments show up as
   `fragment <Name> on <Type> {` — grep those separately to get the returned field list.
4. **Also harvest:** `https?://host/path` literals, `"/api/..."` / `"/graphql"` strings,
   webpack chunk maps (`{<id>:"<hash>",...}` → reconstruct `/static/js/<id>.<hash>.chunk.js`),
   and `manifest.json` / `asset-manifest.json` for the chunk list.

## What to look for in the harvested operations
Rank by "does this take an object reference that the server might not ownership-check":

| Signature shape | Why it matters |
|---|---|
| `($uuid: String!)` on a status/lookup query, e.g. `getCustomerSubscriptionStatus($onepassUUID)` | classic BOLA by object reference |
| `($id: String!, $version: Long!, $actions: [...])` on a mutation, e.g. `updateMyBag(...)` | cart/object write by id |
| `($ids: [Int!]!)` | integer IDs → enumerable, then BOLA |
| `($token: String!)` on an account action, e.g. `linkAccountsV2($token)` | account-linking ATO class |
| an **optional** token/ hash next to a required object id, e.g. `SendTaxInvoice($orderType!, $orderId!, $hash: String)` | the optional token suggests a weaker path exists when it is omitted |
| `getOrderByHash($hash: String!)` fed straight from a query param | bearer-token lookup; the question is only whether the hash is guessable |

For the Kmart case this produced 20 operations and a ranked six-item BOLA list — including an
order-tracking lookup returning `shippingAddress{address1, firstName, lastName, postalCode,
province}`, and a `hash` query parameter that the page passed straight into `getOrderByHash`.

## Discipline
Harvested operations are **leads, not findings**. Nothing here is reportable until you execute
against the live API and observe the server's own answer. Write them down as "untested, ranked"
so the next session does not mistake the list for a result — and so a negative report does not
silently claim coverage it never had.
