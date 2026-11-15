# Extracting the real API surface from a minified front end

When scanners cannot reach the API, the bundle tells you what the API is. Mine it deliberately.

## 0. Get the bundles
Fetch them **through the page** (see the Akamai playbook — curl/ctx.request return the
challenge page instead):

    js = pg.evaluate("""async (urls) => {
        const out = {};
        for (const u of urls) { const r = await fetch(u, {credentials:'include'});
                                  out[u] = await r.text(); }
        return out; }""", script_urls)
    for u, t in js.items():
        assert len(t) > 1000, "challenge page, not a bundle"     # the silent failure

Prefer **capturing the script URLs from a live page load** (`page.on("request")` filtered to
`resource_type == "script"`), then scroll to trigger lazy chunks. A regex over the initial HTML
misses chunks the app loads on interaction.

## 1. Next.js: read `__NEXT_DATA__`
`runtimeConfig` is build-time public env and names the internal services directly.

    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    d = json.loads(m.group(1))
    d["runtimeConfig"]     # API hosts, search endpoints, token brokers, public API keys
    d["buildId"]           # needed for /_next/data/<buildId>/<route>.json
    d["assetPrefix"]       # where static assets actually live (often a CDN path)

Also: `gssp`/`appGip` tell you whether pages are SSR (data arrives in HTML, so you may not
need the API at all) or fully client-rendered (the API is the only source and may be protected).

Treat `runtimeConfig` as *public* config. Finding a Google Maps / analytics / search key is
normal and not a finding. Look for a **server** secret instead; if none exists, say so.

## 2. GraphQL: operation names survive minification
Documents are tagged template literals. Extract names, then read the query text that follows
each name, then the fragments.

    ops = re.findall(r'(?:query|mutation)\s+([A-Za-z_]\w{2,40})\s*(?:\([^)]*\))?\s*\{', js)
    for m in re.finditer(r'query\s+' + name, js):  print(js[m.start(): m.start()+2500])

Triage the names, they are the bug list:
  - `*ForGuest`, `get*ByHash`, `get*ByToken` → unauthenticated-reachable; check what the
    fragment returns before deciding anything
  - `create*`, `update*`, `link*`, `merge*`, `delete*` → mutation surface; check authz
  - anything `send*`, `*TaxInvoice`, `*Refund`, `*Credit` → money/irreversible
  - `*ForUser`/`*ForCustomer` with a client-supplied id argument → IDOR candidates

**The fragment's field list is the blast radius.** `orderTotal` alone is a privacy nit;
`shippingAddress { address1, city, firstName, lastName, postalCode, province }` is PII
exposure and changes how you score the endpoint.

## 3. Always trace the call site
The query definition tells you the shape; the call site tells you the threat model. A query
taking `$hash: String!` is unremarkable — everyone's does. What matters is where `hash` comes
from. Worked example from a real bundle:

    // definition — looked scary
    query GetOrderForGuestByHash($hash: String!) { getOrderByHash(hash: $hash) { ...F } }

    // call site — decided the verdict
    v = readQueryParam(window.location.search);   // ?hash= straight off the URL
    query({variables: {hash: v}});
    // ...and elsewhere: var r = window.crypto.randomUUID(); setCookie(VISITOR_ID, r, +1y)

So: the secret is the token in the confirmation-email link, generated with a CSPRNG — a
conventional magic-link design — and *not* attacker-derivable from the order number. Recording
that reasoning explicitly is what separates a finding from a false alarm.

Trace these in the same way:
  - which header/param a token-broker endpoint trusts
  - what generates a client-supplied identifier
  - whether a "feature flag" is a real server gate or only a client-side hide
  - whether a field posted by the client is ever used for a security decision

## 4. Soft-404s silently corrupt enumeration
If unknown API paths return `200` with a multi-megabyte HTML shell, every wordlist hit looks
real. Detect by content-type + size:

    if "text/html" in ct and len(body) > 500_000:   # not an endpoint
        continue
    if len(body) < 5_000 and "html" not in ct:      # a real API response
        print(path, r.status, body[:200])

Without this you will "discover" dozens of fake endpoints and waste a day chasing them.

## 5. Second-jurisdiction endpoints in the bundle
A build often ships another market's config (`REACT_APP_*_ENDPOINT_NZ`, `.co.uk`, etc.).
That is a different company/legal entity unless the program says otherwise. Extract it (it
tells you about the architecture) but **do not send traffic**. Enumerating the scope
boundaries this way is what keeps an engagement in-bounds.

## 6. Route discovery without the sitemap
`robots.txt` `Disallow` lines are a gift for route shape (`/bag`, `/delivery/*`, `/checkout`,
`/payment`, `/track-my-order*?*`, `*/undefined*`). They are not an authorization boundary —
they govern crawlers, not researchers — so a user-facing route listed there is still testable
under the program. Use the *shape* of the list to decide what to try first.
