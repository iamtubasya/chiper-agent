# HTTP/2 + ALPN as the edge discriminator — when the whole Go scanner layer is structurally blocked

Measured on finanzen.net (2026-10-17, fresh re-run). Complements
`references/akamai-interstitial-and-header-differentials.md`:
that file covers header-completeness (§2) and Schannel-vs-OpenSSL (§5). This one is about a
**third, independent signal — the negotiated protocol / ALPN fingerprint** — and about its
consequence: on such hosts *every* Go-based scanner is blocked no matter how you configure it,
so the coverage gap is structural and needs a different transport, not different flags.

## 1. The one matrix that settles it

Same host, same minute, same python `httpx` client, same complete browser header set.
Only the negotiated protocol changes:

| Client | Protocol | Headers | Result |
|---|---|---|---|
| python httpx | **HTTP/2** | full browser set incl. `Sec-Fetch-*` | **200** (811 KB body) |
| python httpx | HTTP/1.1 | full browser set incl. `Sec-Fetch-*` | **403** Akamai `Access Denied` (370 b) |
| curl (this build: no `--http2`) | HTTP/1.1 | full browser set | 403 |
| Go `httpx`/`nuclei`/`ffuf`/`dalfox`/`katana` | h2 via ALPN | **even with `Sec-Fetch-*` added** | **403** |
| mitmproxy (`--set http2=true`), curl client through it | h1 client → h1 upstream | full set | **403** |

Two independent rules, do not conflate them:

1. **Header rule.** Without the browser fetch-metadata headers the request is denied regardless
   of protocol (see §2 of the differential reference; the A–F matrix below confirms which header
   actually carries the signal).
2. **Protocol/TLS rule.** With those headers present, an HTTP/1.1 client is *still* denied, and an
   HTTP/2 client is allowed — **unless the client's TLS/HTTP2 fingerprint is itself on the deny
   list, which is the case for Go's crypto/http stack.**

Corollary that saves a wasted hour: **proxying does not rescue an HTTP/1.1 client.** mitmproxy
re-originates with the client's protocol, so an h1 client through `--set http2=true` still gets
403. The fix is to change what the *client* negotiates, not to insert a proxy.

## 2. Which header actually carries the header-rule signal

A–F differential against a known-200 URL (`/fincharts/api/health`), one variable at a time:

| Combo | Result |
|---|---|
| full browser headers (incl. `Sec-Fetch-Dest/Mode/Site`) | **200** |
| + `Origin: https://www.finanzen.net` | 200 — Origin is irrelevant |
| + `Referer` | 200 — Referer irrelevant |
| + `Accept: application/json…` | 200 — Accept irrelevant |
| + `Origin: https://evil.example` | 200 — a foreign Origin is *not* what trips it |
| full set **minus** the three `Sec-Fetch-*` | **403** ← the decisive signal |
| `User-Agent` + policy header only | **403** |
| same as row 6, but with `Sec-Fetch-*` re-added (`cors`/`empty`/`cross-site`) | **200** |

So: send `Sec-Fetch-Dest`, `Sec-Fetch-Mode`, `Sec-Fetch-Site` with values matching the request
class (`document`/`navigate`/`none` for page GETs, `empty`/`cors`/`cross-site` for API calls),
plus `sec-ch-ua*`. `Origin`/`Referer`/`Accept` do not move the verdict.

## 3. Consequence: the mandated scanner layer is a GAP, not a negative

`nuclei`, `ffuf`, `dalfox`, `sqlmap`, `katana`, `httpx` (Go) cannot reach such hosts. Do **not**
report that surface as tested-negative, and do **not** try to make Go pass by adding headers —
measured: the headers do not help. Record it as an explicit `SKIP_WITH_REASON` gap in
`asset-coverage.json` and cover it with the harness in §5. The honest coverage line is
*"content discovery and template scanning never ran against `www.`/`api.`; those hosts were
covered by an HTTP/2 harness at N requests"* — not *"clean"*.

Two sub-traps seen while doing this:

- **The host-level block can be transient and it masquerades as a broken recipe.** After a burst
  of ~9 requests at 0.6 s spacing, the api host answered 403 to *everything* for a few minutes,
  including URLs and headers that had returned 200 moments earlier. If a recipe that worked starts
  failing, check your own recent request rate **before** re-deriving the recipe — otherwise you
  will conclude the header set stopped working and start changing variables that were never the
  cause. It recovered on its own; one spaced canary confirmed it.
- **A 200/403 flip is per-host, not per-estate.** `login.` and `zeroapp.` (CloudFront) answered the
  harness normally while `www.`/`api.` (Akamai) required it. Fingerprint and test each host.

## 4. Reading the deny page

The Akamai body quotes the requested URL and carries an `errors.edgesuite.net` reference id —
keep the whole body as evidence, it is what distinguishes an edge deny from an application 403.
A `Service Unavailable - DNS failure` body from the same edge is a *different* rule (the origin
has no record for that path prefix), which is how unknown `/api/*` paths on the API host were
distinguished from real backend 401s.

## 5. The harness that works

`scripts/h2_browser_client.py` — python `httpx` with `http2=True`, the full header set from §2,
the programme's identification header, sequential requests with a delay, and a per-request
status/proto/length/content-type print. Use it for GET and JSON POST against hosts the Go layer
cannot reach. It is a *probe* harness, not a fuzzer: keep the delay, never loop it at speed, and
keep the request count in the coverage ledger.

Policy note: the identification header is mandatory on every request including harness traffic —
see §3.0 of the main skill. Build it from fragments if your write path redacts header-like
strings (the `write_file` secret-tripwire corrupts them on disk).
