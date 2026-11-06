# Unauthenticated Next.js recon: route map, Server Actions, CSRF mechanics

Technique bank for auditing a Next.js site (marketing site or portal) WITHOUT credentials.
All patterns below were used live on cdn77.com (2026-10-23): the marketing site is Next.js
App Router (turbopack), the portal client.cdn77.com mixes pages router (login) + app router
(support KB). Everything here is passive/read-only recon plus a handful of validation probes.

## 1. Crawl first, then mine the chunks

```
katana -u https://www.target.com -d 3 -rl 10 -c 2 -silent -o crawl.txt
```

A deep crawl of a Next.js site yields every `/_next/static/chunks/*.js` referenced by every
page. Download them all; the shared chunks (especially `pages/_app-*` on pages router, or
`app/layout-*` on app router) carry the app's route + endpoint configuration.

## 2. Extract the full route/endpoint map from the _app chunk

```bash
# every client route (the config object uses pathname:"...")
grep -oE 'pathname:"[^"]+"' chunk-pages__app-*.js | sort -u
# every API endpoint string
grep -oE '"(/api/[a-zA-Z0-9/_{}-]+)"' chunk-pages__app-*.js | sort -u
```

Live result: one chunk yielded ~90 portal routes (`/billing/*`, `/organization/team-members`,
`/cdn/edit/:resourceId/*`, `/traffic-logs/*`, ...) and the complete API map
(`/api/public/login`, `/api/public/join`, `/api/public/logout-all`, `/api/password/reset/request`,
`/api/auth`, `/api/get-sums`, `/api/download/raw-log`, ...) — including endpoints with no UI
link. This is the single highest-yield recon step on a Next.js target.

## 3. Server Action discovery (App Router)

Server action IDs are long hex strings passed as the first arg to `createServerReference`,
with the action NAME as the last arg:

```bash
grep -ohE '"[a-f0-9]{40,64}"' chunks/*.js | sort -u     # candidate IDs
grep -oE '.{200}createServerReference\("[a-f0-9]{40,64}".{100}' chunks/*.js
# => createServerReference("600faf1a...", s.callServer, void 0, s.findSourceMapURL, "sendInquiry")
```

Filter false positives: Sentry release IDs look identical (also 40-hex) — confirm by checking
the surrounding context names an action (`"sendInquiry"`), not a release.

## 4. Testing a Server Action

```
POST https://site/<page-that-uses-it>
Next-Action: <action-id>
Content-Type: application/json
```

- `useActionState(fn, initial)` actions take `(prevState, formData)`: send a JSON array
  `[prevState, formData]`. A wrong shape returns an opaque error digest (custom 5xx codes
  like 570/572 with `{"digest":"..."}` in RSC flight format) — shape-guess until the error
  class changes.
- **Multipart may be edge-blocked**: real form posts are `multipart/form-data`, but the CDN
  edge can 403 ALL multipart POSTs from non-browser clients (nginx 403, even with a browser
  UA + Origin/Referer) while JSON POSTs reach the app. If multipart 403s but JSON gets an
  app-level response, the form is captcha/bot-gated — note it and move on rather than
  burning cycles on the wire format.
- Add `Origin:` + `Referer:` headers; some edges require them.

## 5. Decode CSRF mechanics from JS before probing

Find the token source and transport in the chunk:

```bash
grep -oE '.{300}csrf-token.{300}' login-chunk.js
```

Live pattern (double-submit): client reads `meta[name='csrf-token']` or generates
`crypto.randomUUID()`, stores it in `document.cookie` (`csrf-token=<uuid>; Secure`), and sends
it as header `csrf: <uuid>`. Probe validation depth with four requests — header-only,
cookie-only, mismatched, and matched:

- all three unmatched shapes rejected => proper double-submit, move on
- matched pair accepted => validation is cookie==header only (still OK if SameSite set)

Also map the **validation ORDER per endpoint** (cheap, high-signal): POST the login endpoint
with no CSRF (does it say "Invalid CSRF token"?) vs the data-proxy endpoint with no session
(does it say "Unauthorized"?). Login checked CSRF first; the proxy checked auth first — that
ordering tells you which gate to attack for each endpoint class.

## 6. The catch-all auth gate kills content discovery

If `/zzz-nonsense-$RANDOM` 302s to `/login` like every other path, the portal is fully
auth-gated and ffuf/raft discovery returns thousands of identical 302s. Prove the pattern
with the nonsense path, then STOP and record the surface as untested (see the
recon-scope-triage skill, catch-all-auth variant).

## 7. Grading blind SSRF found on the app (DNS-resolution oracle)

A server-side checker tool (TLS checker, DNS lookup, URL preview) that resolves
user-supplied hostnames is an SSRF primitive. Impact grading without a data channel:

1. **OOB proof (mandatory)**: submit `<unique>.<interactsh-payload>` as the host; inbound
   DNS A/AAAA queries from the vendor's cloud ranges prove server-side resolution. Repeat
   with 2-3 fresh subdomains for the 3x validation rule — each run is one validation.
2. **Internal reach**: loopback (127.0.0.1), link-local (169.254.169.254), and
   `metadata.google.internal` that return the tool's *connection-attempted* error (not the
   input-validation error) prove internal connection attempts.
3. **The oracle differential**: if the tool's error output reveals the resolved IP for
   resolvable names (e.g. `Can't connect to '185.102.216.100:443'`) but a generic failure
   for non-resolving ones, you have a limited DNS oracle — internal-only names that resolve
   would leak internal IPs. Test non-resolving public names from your subdomain list; if
   none resolve internally, say so explicitly in the report.
4. **Injection check**: host:port, shell metacharacters (`;`, `$()`, backticks), newline,
   null byte, tab — all rejected with 400 means no command injection; document it as tested.
5. **Honest grade**: TLS-handshake-only tools return no response bodies, so no data
   exfiltration is demonstrable — claim the primitive (P3-class per most taxonomies), state
   what was NOT proven in a two-column table, and let the vendor grade.

## Pitfalls

- DoH for DNS checks: `python3` + `https://dns.google/resolve?name=X&type=A` — `dig`/
  `nslookup` are unreliable/absent on this box.
- Parallel tool calls that read a file another call is downloading = race. Sequence
  download-then-parse in separate turns.
- `httpx` version on this box rejects `-c` (concurrency); use `-rate N` only.
- interactsh-client prints its payload URL only after startup ("Listing 1 payload for OOB
  Testing") — run with `-v`, capture stdout to a file, wait ~10s, then grep for the `.oast`
  domain before firing tests.
