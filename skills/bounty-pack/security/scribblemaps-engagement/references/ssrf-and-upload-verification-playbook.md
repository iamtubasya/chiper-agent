# Server-side fetch + upload verification playbook

Class-level techniques proven 2026-10-31 (Scribble Maps). Applies to any target where the
server fetches a caller-supplied URL (SSO metadata import, webhooks, avatar/OG-image fetch,
connectors) or stores a caller-supplied file.

## A. SSRF: prove it, then prove its limits before writing a word of the report

1. **OOB first.** Start `interactsh-client -v -o oob.txt` in the background, read the domain
   from the log (`[a-z0-9]{25,40}\.oast\.[a-z]+`), then fire the request. Confirm **both** a DNS
   interaction and an HTTP interaction, and note the source IPs — the resolver IP and the
   egress IP are usually different (measured: DNS 20.42.77.69, HTTP 13.72.78.248, Azure).
2. **Repeat 3x with distinct path tags** so each run maps to one interaction. Identical
   timestamps per run = reproducible, not a fluke.
3. **Find the oracle.** Compare error strings for a URL that returns 200 versus one that
   returns 401/404/timeout. Measured pair:
   `"Failed to parse metadata XML"` (fetched 200) vs `"Could not fetch the metadata"` (failed).
   That pair is an external host/port reachability oracle and belongs in the report.
4. **Try to break the private-address filter — and report the result either way.** Test at
   minimum: `127.0.0.1`, `[::1]`, `[::ffff:127.0.0.1]`, `[::ffff:a9fe:a9fe]` (link-local IPv6),
   `2130706433` (decimal), `0x7f000001` (hex), `017700000001` (octal), `127.1` (short form),
   `0.0.0.0`, `169.254.169.254`, `10.0.0.1`, `192.168.1.1`, `240.0.0.1`, plus hostnames that
   resolve to private ranges (`localtest.me`, `127.0.0.1.nip.io`, `10.0.0.1.nip.io`,
   `192.168.0.1.nip.io`). If all are blocked, **say so** — a public-only SSRF is Low-Medium,
   and claiming internal access you did not achieve is what gets a report downgraded.
5. **Check whether the fetch carries credentials.** Point the URL at auth-required endpoints
   on the *same* domain (`/api/account`, `/api/users`). If they return 401 to the fetch, no
   cookie is replayed — a genuinely good negative worth stating.
6. **Note the stated limits** (HTTPS-only, no redirects, timeout, size cap). They tell you the
   vendor thought about abuse, which sets the realistic severity.
7. **Unproven is unproven.** If a path (e.g. domain-verification file fetch) returns the same
   error for a private-resolving hostname as for a non-resolving one, internal reachability is
   **not demonstrated**. Write that sentence; do not infer it from timing.

## B. Stored XSS via upload: verify execution in a real browser before claiming it

An SVG/HTML payload being stored and served verbatim is **not** a finding by itself.

1. Upload the payload, then fetch the stored URL and read the headers:
   `Content-Type`, `Content-Security-Policy`, `X-Content-Type-Options`,
   `Content-Disposition`, `Access-Control-Allow-Origin`.
2. **`CSP: ...; sandbox` without `allow-scripts` plus `X-Content-Type-Options: nosniff`
   defeats it.** Measured: an SVG with `<script>alert(1)</script>` was stored and served as
   `image/svg+xml`, and Chrome logged
   *"Blocked script execution in '...svg' because the document's frame is sandboxed and the
   'allow-scripts' permission is not set."*
3. Confirm with a real browser, not by reasoning: navigate to the URL, capture
   `console` + `pageerror`, and also test `<img>` / `<object>` embedding from a neutral page.
   `imgLoaded: load` + `scriptRan: false` is the negative.
4. Also check the **filename is randomised** on store (measured: `probe.svg` ->
   `/user/overlay/2026/10/31/qWAmIi.svg`) — that kills path traversal via filename, and it is
   worth one line in the coverage doc.
5. Clean up uploaded test files through the product's own remove endpoint.

## C. Same route, different host — the cheapest authz differential there is

When one app is served from several hostnames (`www.` / `api.` / `team.`), the authorisation
filter is frequently wired into only some of them. Fire the **identical** request at each host
and compare. Measured: `GET /api/maps/paidsample/raw` -> `200` + 16,908 bytes on
`www.scribblemaps.com`, `401 application/problem+json` on `api.scribblemaps.com`. That single
pair turned a "maybe by design" observation into a demonstrable control bypass, and it costs
two requests.

Corollary for multi-tenant apps: a cross-tenant attempt that returns the SPA's login HTML
instead of JSON proves nothing. Build the **control** first (give the second identity its own
tenant/team so the session has valid context), then retry — otherwise the negative is
worthless and the positive is unprovable.
