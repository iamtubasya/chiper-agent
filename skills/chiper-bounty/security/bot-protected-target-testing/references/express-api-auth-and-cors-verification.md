# Verifying auth and CORS claims on a multi-host Express API estate

Worked case: `toshi.bet` (2026-10-18). The webpack module graph
(`references/webpack-module-graph-api-map.md`) yielded 23 endpoints across 8 hosts, all Express
(`X-Powered-By: Express`, `Cannot GET /path` 404 bodies). Testing them produced a run of
**verified negatives** — the shape of which is worth having, because two of them look like
findings at a glance and would have been reported as such.

## 1. The `ACAO: *` trap — readable is not exploitable

Every `user.toshi.bet` response carried:

```
Access-Control-Allow-Origin: *
```

with **no** `Access-Control-Allow-Credentials: true`, and it did not change when an
`Origin: https://evil.example.com` header was sent (still `*`, not reflected).

| Shape | Exploitable? |
|---|---|
| `ACAO: *` **without** `ACAC: true` | **No.** A browser refuses to attach credentials to a wildcard-origin response, so no cross-origin read of authenticated data is possible. |
| `ACAO: <reflected evil origin>` + `ACAC: true` | Yes — that is the real bug. |
| Fixed non-reflecting `ACAO: <app origin>` | Neither reflection nor wildcard. Not a finding. |

So: **always read both headers together, and always send a foreign `Origin` to see whether the
value tracks it.** A wildcard alone is a hygiene note at most. (Fuller treatment:
`references/cors-verification-readable-is-not-a-finding.md`.)

## 2. `200` with an empty body is not an auth bypass

Six routes answered `200` with a zero-length body while their siblings answered `401`:

```
GET /user/notifications        -> 200  (Content-Length: 0, application/json)
GET /user/banners              -> 200  (empty)
GET /user/referrals            -> 200  (empty)
GET /user/check-geo-restrict   -> 200  (empty)
GET /user/telegram             -> 200  (empty)
GET /user/verify-email         -> 200  (empty)
GET /user/meToshi              -> 401 {"error":"No token provided"}
GET /wallet/locked-balances    -> 401 {"error":"No token provided"}
```

The inconsistency is real but the impact is not: the empty 200s are routes that resolve their
handler and return nothing for an anonymous caller, while the data-bearing routes enforce the
token. **Record it as an observation, not a finding** — no data is reachable without a token, and
"returns 200 with no body" is not an access-control failure.

The one genuinely public route, `GET /wallet/challenges` → `200 []`, is public **by design**
(a global challenge list) and stayed `[]` with `?limit=100` and `?page=1`. Verified negative.

## 3. JWT forgery checks that are worth the four requests

Before spending time on token attacks, spend four requests proving the verifier is real:

```
Authorization: Bearer null        -> 401 {"error":"Invalid or expired token"}
Authorization: Bearer undefined   -> 401 {"error":"Invalid or expired token"}
Authorization: Bearer <alg:none JWT with {"name":"admin"}>  -> 401 {"error":"Invalid or expired token"}
Authorization: Bearer <200 x 'A'> -> 401 {"error":"Invalid or expired token"}
(no header)                       -> 401 {"error":"No token provided"}
```

Consistent rejection of `alg:none` and of garbage is a **control that works** — state it as such.
Note the two distinct error strings (`No token provided` vs `Invalid or expired token`): they tell
you the middleware distinguishes *missing* from *malformed*, which is a useful oracle when you
later hold a real token and want to know whether it is being parsed at all.

## 4. Route-prefix calibration — the 404 tells you the namespace

`GET /user/meToshi` → `404 Cannot GET /meToshi` while `GET /meToshi` → `404 Cannot GET /meToshi`
looks contradictory until you notice the service prefix. Express echoes the path it did not
match, so the 404 body is a **free calibration oracle**: probe the bare path, read the echo, and
prepend the `SERVICE` segment from the module graph. Here the real routes were
`/user/meToshi`, `/user/level/xpdata`, `/user/live-wins/{1}` — the `SERVICE` value is a literal
path prefix, not just an enum key. Getting this wrong manufactures a full set of false "route
does not exist" negatives.

## 5. Imgix / CDN default pages are soft-404s, not exposures

Two hosts answered `200` with the **Imgix default landing page**
(`<title>Imgix - Image Processing On-Demand, Served By CDN</title>` plus the inline SVG logo):

```
https://static-stage.toshi.bet/  -> 200  Imgix default page
https://statics.toshi.bet/       -> 200  Imgix default page
```

That is the CDN's own catch-all for an unconfigured source, not a misconfigured bucket and not a
leak. Same family as the SPA catch-all in §4b of the SKILL.md: **one status + one byte length +
a vendor-default title = the vendor's page, not the target's content.** Discard, do not report.

## 6. Hosts that are down are a coverage gap, not a negative

| Host | Response | Reading |
|---|---|---|
| `games.toshi.bet/*` | `503` nginx | origin down / not routable from this egress |
| `dojododge.toshi.bet/*` | `503` nginx | same |
| `chat.toshi.bet/` | `530` (CF Error 1016 Origin DNS) | origin DNS error |
| `track.toshi.bet/` | `522` (connection timed out) | origin unreachable |

Every game-play and provably-fair endpoint lives behind those hosts, so **all business-logic
testing of the house games was untestable from this network**. That is a `BLOCKED` ledger entry
with the exact status code — never "tested, nothing found".
