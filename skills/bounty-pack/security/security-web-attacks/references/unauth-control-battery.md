# Unauthenticated control battery — proving a control HOLDS with tool evidence

Use when the operator requires "negative results must have tool evidence", or when a first finding is
submitted and the engagement continues. Each probe below was run on a hardened production estate
(blink.sv / blinkbtc.com, 2026-10-12/13) and produced a **recorded negative** — the readable signature is
listed so the next run can tell "control holds" from "my probe was wrong".

Rule of thumb: a negative is only worth writing down if you can name (a) the exact request, (b) the exact
response signature, and (c) why that signature means the control engaged.

---

## 1. Rate-limit bypass via client-IP headers (`X-Real-IP` / `X-Forwarded-For`)

The highest-value cheap test after any limiter is observed: does the limiter key on a header the client
controls? Rotate a *different* fake IP per attempt.

```python
for i in range(12):
    hdr = {"X-Real-IP": "10.%d.%d.%d" % (rnd(), rnd(), rnd()),
           "X-Forwarded-For": "192.0.2.%d" % rnd()}
    post("/auth/email/login", {"code": "%06d" % (200000+i), "emailLoginId": lid}, hdr)
```
- **Holds:** `401 invalid code` ×5 → sticky `429 too many requests` for every remaining attempt, *identical
  to the un-spoofed control run*. Conclusion: the limiter keys on the socket IP / an edge-set header.
- **Bypass:** statuses keep returning `401` forever with rotating headers → the limiter trusts
  `X-Real-IP`; then a 5–6 digit code brute force becomes a real ATO chain. Verify with a second client
  (different real IP) before claiming.
- Always run the no-spoof control first and keep both histograms in one JSON.

## 2. HTTP request smuggling (CL.TE / TE.CL) without smuggler.py

Raw socket, 6 lines, works everywhere:

```python
payload = (b"POST /graphql HTTP/1.1\r\nHost: %s\r\n"
           b"Content-Length: 4\r\nTransfer-Encoding: chunked\r\n\r\n"
           b"5c\r\n{\"query\":\"{__typename}\"}\r\n0\r\n\r\nG" % host.encode())   # TE.CL variant
# CL.TE variant: swap to "Content-Length: 6" and body b"0\r\n\r\nG"
```
- **Holds:** `400 Bad Request` + `Connection: close` for *both* variants, exactly one `HTTP/1.1` in the
  buffer → the front-end rejects conflicting length headers. Never write "no smuggling" without both
  variants and the close.
- **Desync tell:** two status lines in one read, a delayed second response, or the trailing `G` coming back
  as a request prefix on the next connection.

## 3. WebSocket GraphQL subscription authz

```python
ws = websocket.create_connection("wss://<host>/graphql", suppress_origin=True,
                                 subprotocols=["graphql-transport-ws"])
ws.send(json.dumps({"type": "connection_init", "payload": {}}))   # -> {"type":"connection_ack"}
ws.send(json.dumps({"id":"1","type":"subscribe","payload":{"query":"subscription{myUpdates{__typename}}"}}))
```
- Anonymous `connection_ack` is normal — the socket is not the auth boundary, the resolver is.
- **Holds:** `{"type":"next","payload":{"errors":[{"extensions":{"code":"NOT_AUTHENTICATED"}}]}}` then
  `complete`. Private streams stay private.
- **Introspection over WS is refused** (`Only subscription operations are supported`) — introspect the
  `Subscription` type over HTTP instead (`{__schema{subscriptionType{fields{name args{name}}}}}`), then
  probe each subscription name over WS.

## 4. Full unauth GraphQL sweep (mutations + queries)

Introspect `Mutation`, build the **minimally-invalid** argument set (`null` for every non-null input
object, `"zz"` for scalars), fire all of them unauthenticated, and classify:

| response | meaning |
|---|---|
| `Not authorized` / `Not authenticated` | gateway/resolver gate present (good) |
| `Expected value of type "X!" found null` | **argument validation runs BEFORE the auth check** — this row tells you nothing about authz; re-run with real input |
| `OK: {...}` | genuinely anonymous (only `captchaCreateChallenge` should be) |
| `HTTP fetch failed from '<internal-service>': 500` | **gateway auth gate MISSING for this resolver** — the request was forwarded to an internal subgraph. That is both an info leak (internal service name, `SUBREQUEST_HTTP_ERROR`, `"Token is anon"`) and an inconsistency finding. Blink `kycFlowStart`, 2026-10-13. |

Zero-arg mutations are the cheapest signal: they cannot be masked by argument validation, so their
`Not authorized` / subgraph-error difference is a true gate comparison. Record the JSON sweep as evidence
and only ever report the exception, never the noise.

## 5. Password-reset link poisoning via `Host` header

Test with **your own** test account + a mailbox you control — never a real user's address.

```
POST /api/v4/users/password/reset/send  {"email":"<your test mailbox>"}   # baseline
POST ... same body, header  Host: evil-attacker.example                   # poisoned
```
Fetch the mail and inspect the link host:
- **Holds:** links still point at the configured canonical host (`https://chat.blink.sv/reset_password_complete?token=…`)
  → the app uses a configured SiteURL, not the request host.
- **Vulnerable:** link host = your spoofed value → attacker-controlled reset links (account takeover class).

## 6. Next.js surface probes

```bash
GET /_next/image?url=http://169.254.169.254/computeMetadata/v1beta1/&w=64&q=75
GET /_next/image?url=https://example.com/&w=64&q=75          # control
GET /api/auth/providers        # NextAuth: exposes providers + signin/callback URLs (normal)
GET /api/auth/csrf             # normal
GET /api/auth/signin?callbackUrl=https://evil.example/       # reflection / open redirect
GET /api/auth/signin?callbackUrl=javascript:alert(1)         # 500 = validated
```
- Optimizer locked → `400 "url" parameter is not allowed"` (do not report as SSRF).
- Optimizer open → the *second* (external) URL returning bytes is the SSRF; then try the metadata URL.
- `callbackUrl` handling: assert the raw value is **not** in the response body and that `javascript:` is
  rejected; a reflected absolute URL would be the finding.

Also check `<chunk>.js.map` for the app's source maps (a 200 JSON with `sources` = full TS source
disclosure) — a fast, cheap check that most sweeps skip.

## 7. App-level SSRF proxies (the `lnurl-proxy` shape)

Server-side "CORS proxy" routes (`POST /api/lnurl-proxy {lnurl, paymentRequest}`) fetch an
**attacker-supplied** URL and may relay the body. Run a fixed matrix rather than one payload:

| callback | hardened build | vulnerable build |
|---|---|---|
| same host as the supplied `lnurl` blob | works (`{"status":"ERROR","reason":"Withdraw request failed"}`) | works |
| `http://169.254.169.254/...`, `http://127.0.0.1:PORT/...`, `http://10.0.0.1/` | `400 Invalid lnurl` / `Invalid callback URL` in <1.2 s | fetch attempted / metadata returned |
| foreign public host (`https://example.com/`) | `Invalid callback URL` | works |
| userinfo trick `https://<allowed-host>@169.254.169.254/` | rejected (URL parsed, effective host compared) | bypasses substring checks |

Host a JSON blob for the first hop with a free paste service (`POST https://paste.rs` → URL; jsonblob is
Cloudflare-403). Encode it as `lnurl1...` with a small bech32 encoder. **Deployed builds are often hardened
relative to the public OSS snapshot** — the Galoy snapshot has no callback validation, production rejects
every off-host callback. Verify live before writing anything; the snapshot is a hypothesis generator.

## 8. Buckets / CNAMEs — name collisions are not findings

- Generic names (`blink-web`, `blink-assets`, `blink-files`, `blink-staging`) belong to *someone*. Before
  claiming a publicly listable bucket: prove ownership (asset URLs referencing the target's domains, or the
  target's own JS/CSS referencing the bucket host). Here: 4 listable buckets, **zero** attributable —
  contents were unrelated (UUID media, business logos, a PHP app with `/var/www/html/blink/...` paths).
- Read the **listing only**; never download objects from a bucket that is not the target's, and say so in
  the coverage note.
- Dangling CNAME map: `nslookup -type=CNAME <host>` over the enumerated hosts, then check the target is
  live/claimed (`<org>.github.io`, `<id>.hosting.gitbook.io`, S3 website endpoints). A CNAME pointing at a
  *live* page is not a takeover.

## 9. Mobile static review from source (no APK needed)

When the app source is public, the manifest answers most of the mobile checklist in minutes:
`android/app/src/main/AndroidManifest.xml` → `android:exported`, intent-filter actions
(`VIEW` + `NFC_DEF_DISCOVERED` for a wallet is by design), `android:allowBackup`,
`res/xml/network_security_config.xml` (`cleartextTrafficPermitted` in release vs debug),
`ios/…/Info.plist` → `CFBundleURLSchemes`, `NSAllowsArbitraryLoads`, `NSAllowsLocalNetworking`.

## Evidence discipline

One JSON per probe family under `evidence/`, named for the control (`rate_limit_bypass_xrealip.json`,
`http_smuggling_probe.json`, `ws_subscription_unauth.json`, `graphql_unauth_mutation_sweep.json`, …), each
carrying raw request + response pairs. The final report's COVERAGE section cites these filenames — the
operator reads the file list as the proof that the negative was measured, not assumed.
