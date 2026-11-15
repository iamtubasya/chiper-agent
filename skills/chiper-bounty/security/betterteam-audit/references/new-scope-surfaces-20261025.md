# betterteam — the 2026-10-25 scope additions, probed

Every probe below ran at ≤5 req/s with `X-Bug-Bounty: <trial email>`. Results are the measured
outcome of ONE full session (2026-10-25). Re-run the probes before quoting them as current: the
program page can change again (it changed once already, in a way that invalidated the old
Critical path — see the scope block in SKILL.md).

## 1. GCS upload bucket — `betterteam-app-uploads`
Discovered from an authenticated `POST /.api/career-page/logo` (multipart, field name `file`):
the response is `{"url":"https://betterteam-app-uploads.storage.googleapis.com/career-page-logos/<uuid>.png","uuid":...}`.

Probes and outcome:

| probe | result |
|---|---|
| `GET https://betterteam-app-uploads.storage.googleapis.com/?list-type=2` | 403 `AccessDenied` — **full message leaks project scope**: "Anonymous caller does not have storage.objects.list access … resource '//storage.googleapis.com/projects/_/buckets/betterteam-app-uploads'" |
| `?acl ?cors ?lifecycle ?logging ?uploads ?versions` | 403 AccessDenied (all) |
| `?retention ?encryption` | 400 NotImplemented (API not implemented, not a win) |
| object we uploaded | 200, `Cache-Control: public, max-age=3600`, `x-goog-storage-class: REGIONAL` — logos are public by design |
| `.svg` upload (SVG with `<script>`) | 403 "Access blocked — Betterteam" (extension/content rejected) |

Takeaway: bucket ACL is closed; the only interesting primitive is the cross-tenant logo uuid
reference (`PUT /.api/career-page {"logo":{"uuid": "<other>"}}` → `{"message":"logo not found"}`),
so logo objects are uuid-scoped server side.

## 2. `s.betterteam.com` — the same bucket behind Cloudflare
- `/` and `/?list-type=2` → 403 `AccessDenied` XML (GCS error surfaced through CF).
- Any missing key → 404 `NoSuchKey` — a clean object-existence oracle, but only for keys you already
  know (all app-given).
- Traversal: `/dashboard/`, `/..%2f..%2fetc/passwd`, `..%252f..%252f..` → 403/404, no escape.
- `/dashboard/assets/*.js` is the real dashboard bundle root (`https://s.betterteam.com/dashboard/assets/`).

## 3. `i.betterteam.com` + `*.i.betterteam.com` (measurement hosts + their DNS)
- `GET /i/dash-home.png?c=<hash>` → 200, 73 bytes, `Server: Varnish`, `Via: 1.1 varnish`,
  `X-Served-By: cache-sin-*`, `Cache-Control: no-store, private`. It is a 1×1 beacon.
- `?c=`, `?url=` values ignored (no SSRF, no template eval); traversal (`/i/../..`, `%2e%2e`,
  double-encoded) → 404.
- `/`, `/metrics`, `/health`, `/status`, `/debug/pprof`, `/i/` → 404 on both the Fastly front
  (`i.betterteam.com`) and the origin-shaped names (`g.d.i`, `<hash>.n.d.i`).
- **Delegated DNS found by walking NS/SOA**: `n.d.i.betterteam.com` is authoritative-served by
  `ns1.d.i.betterteam.com` → A `136.79.187.74`. Probe it with dnspython, not dig:
  - `version.bind CH TXT` → REFUSED (no version leak)
  - recursion `google.com A` → REFUSED (closed resolver)
  - `AXFR n.d.i.betterteam.com` → refused ("No answer or RRset not for zone origin")
  - dynamic `UPDATE` → NOTIMP; `ANY` → NOTIMP; wildcard `*` → answers with its own A only
  - Verdict: hardened. Cost: 6 packets. Cheap enough to always do when a custom NS is in scope.

## 4. `srp.betterteam.com` / `srp-api.betterteam.com` (Segment proxies)
Config is public in the dashboard SSR shell (`window.PUBLIC_ENV`):
`SEGMENT_API_PROXY_HOST=srp-api.betterteam.com`, `SEGMENT_CDN_PROXY_HOST=srp.betterteam.com`,
`SEGMENT_CLIENT_KEY=<public write key>`, `POSTHOG_PROXY_HOST=phrp.betterteam.com`.

| probe | result |
|---|---|
| `POST /v1/track` / `/v1/batch` without key | 400 `{"message":"An invalid write key was provided"}` |
| same **with** the public client key | 200 `{"success": true}` — by design |
| absolute-URI request line (`POST http://oob/... HTTP/1.1`) | Cloudflare **403** |
| `X-Forwarded-Host` / `X-Host` / `X-Original-URL` → OOB host | 200, request still served locally, **0 interactsh callbacks** |
| `GET /v1/projects/<public key>/settings` (on `srp.`) | 200, public Segment settings, `Age`/`ETag` cached |
| CORS preflight | `ACAO: *`, `ACA-Headers: Content-Type, Authorization` — no credentials |
| 13-path fuzz (`v1/track`, `analytics.js`, `health`, …) | track/batch 400, rest 404 |

Takeaway: the only thing that would pay here is the proxy forwarding somewhere it should not, or
passing cookies/Authorization to Segment. Neither reproduced. Do **not** report the public write key —
it is in the public HTML on purpose.

## 5. Subdomain takeover sweep (the "rated by impact" exception)
- `subfinder -d betterteam.com -all` → **628** subdomains (almost all customer career sites);
  `crt.sh` adds the other domains: `sandbox`/`preview`/`marte`/`luis`/`allan` on `betterteam.net`,
  `mail.betterteam.xyz`, `www.betterteam.au`.
- `dnsx -cname -resp` over everything → only **7** CNAMEs platform-wide:
  `help → betterteamapp.zendesk.com`, `login → cname.workos-dns.com`,
  `www → dualstack.n.sni.global.fastly.net`, `i → j.sni.global.fastly.net`,
  `pay → custom.chargedesk.com`, `subscribe → hosted-checkout.stripecdn.com`,
  `phrp → <id>.cf-prod-us-proxy.proxyhog.com` (PostHog).
- Wildcard check first, else every miss looks like a takeover:
  `https://wrongwildcardtest-<rand>.betterteam.com` resolves to Cloudflare anycast ⇒ the apex has a
  wildcard ⇒ **dangling-record hunting must be CNAME-based, not NXDOMAIN-based.**
- Every CNAME target resolved and is registered (RDAP: `proxyhog.com` exp 2027-01-16,
  `chargedesk.com` exp 2027-05-11). `nuclei -tags takeover,exposure,misconfig` over the sub list and
  the other-domains list: **0 hits**.
- Two hosts print URLs in HTML that merely *look* retired: `phrp` (404 at `/`, alive as PostHog proxy)
  and `srp` (404 at `/`, alive on `/v1/*`). Always probe a sub-resource before calling a 404 a takeover.

## 6. Cheap recon that paid off here
- `TXT betterteam.com` leaks the whole vendor stack in one query: ahrefs, anthropic,
  openai, slack, stripe, globalsign, apple, google ×2, yahoo, yandex, have-i-been-pwned, SPF
  (mandrill/zendesk/intercom/google) — use it to pick which vendor surfaces to expect.
- `app.betterteam.com/feed-static/sitemap.<uuid>.xml` → 200, **30,844** live job URLs on customer
  career sites. Grep it for *your own* trial company to prove (or disprove) a feed leak. Our rows were
  absent → unpublished jobs do not leak into the feed (checked `bugbountytestco`, `bb-logic-probe`,
  `dup-req-test`, `race-test` → 0 occurrences).
