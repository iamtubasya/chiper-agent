# Bounded exposure sweep + hit triage

Use when the program rate-limits (or forbids heavy automation) but you still want the
document/config-exposure class that historically produces the paying P4s. Replaces a
full-template nuclei run that would queue millions of requests.

## Budget math first

`templates × hosts = requests`. A full local template mirror (2,500) × 260 hosts = ~1.5M requests;
at the mandated `-rl 4` that is days, and it is exactly the kind of volume a brief means when it says
"rate limits are enforced environment-wide". Instead: **14 paths × hosts**, ~4 req/s.

Observed: 260 hosts × 14 paths (+1 root probe each) ≈ 3,600 requests ≈ 8.5 min, 99 raw 200s.

## Ready-to-run shape

`scripts/`-style pattern (adapt paths; run it foreground or backgrounded with notify):

```python
PATHS = ["/README.md", "/README", "/readme.md", "/CHANGELOG.md", "/.env", "/.dev.vars",
         "/config.json", "/wrangler.toml", "/package.json", "/swagger.json", "/openapi.json",
         "/.git/config", "/.well-known/security.txt", "/api-docs"]
HDR = {"User-Agent": UA, "X-Bugcrowd": Bugcrowd-BC_USERNAME, "Accept": "*/*"}   # program-identifying header
# ThreadPoolExecutor(max_workers=4) + time.sleep(0.25) per path  -> ~4 req/s
```

Per host: fetch `/` first and keep `{status, len, sha256(body[:200k])}` as the root signature.
Per path: keep only `status == 200` and not-same-as-root (hash match **or** byte length within ±8 of a
large root body).

## Triage — this is where the value is

Raw hits → filter → then read bodies. Filter order:

1. **Leaf markers** (drop): `Cloudflare Access`, `Sign in ・ Cloudflare`, `cf-access`, `Access denied`.
2. **SPA shell markers** (drop): `__next`, `data-next-head`, `id="root"`, `id="app"`, `@vite/client`,
   `window.__NUXT__`, `ng-version`.
3. **De-dupe** by `(host, sha256(first 200 bytes))` — one host serving an identical interstitial for
   every path collapses to one row.
4. **Read the survivors' bodies** and classify honestly:

| Survivor looks like | Verdict |
|---|---|
| `README.md` describing *the target's* internal service (endpoints, KV schema, deploy steps) | **report** — internal doc disclosure (P4 class) |
| stock upstream README (WordPress/Pantheon, Cloudflare `remote-mcp-server`, other boilerplate) | not a finding |
| `config.json` with site keys / analytics IDs / OAuth client_id / feature flags | not a finding (public by design) |
| `.env`, `.dev.vars`, `*.pem`, real tokens | verify by reading the body — this IS a finding if the value is live |
| `swagger.json`/`openapi.json` with real API surface | lead: enumerate the documented endpoints, don't report the doc |

## Pitfalls

- `same length as root` alone mis-fires on gated hosts (root 302, path 200 interstitial) — always keep
  the marker filters too.
- A `200` on a path that returns HTML when you expected JSON is the SPA catch-all; check `content-type`.
- Send the program's researcher header on every request; note the tools and rate in the log so the
  sweep is defensible if asked.
- Record which hosts were *not* reachable (timeouts, 403s) — "0 findings" over an unreachable set is a
  false clean, not a clean.
