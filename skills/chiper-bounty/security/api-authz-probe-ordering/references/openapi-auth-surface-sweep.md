# OpenAPI Auth-Surface Sweep: spec → declaration → live probe → chain

§7 covers reading a spec's `security` field to separate by-design anonymous routes from broken-AC.
This reference is the **operational sweep** that turns a published spec into a finding: find the
spec, categorise every operation by its auth declaration, probe the declared-public set **live**,
read the error strings as a layer oracle, and chain identifier-leak endpoints into per-identifier
detail endpoints.

Worked case: RunOnFlux (2026-10-27). `docs.runonflux.io/fluxapi/` served a Redoc shell whose HTML
linked `/fluxapi.json`, `/fluxapi.yaml`, `/fluxapi.md`. 576 KB JSON, **339 paths**, `info.version`
8.20.0 (live `/flux/version` reported 8.22.0 — docs lag deployment, note the drift). Result: 180
no-auth-declared operations → **169 returned HTTP 200 with data unauthenticated**, 6 × 404 (route
not mounted), 4 × 403 (private-network / protocol gate), 1 × 401 (the lone correctly-enforced one).
The High finding came from a **sibling API host**, not the flagship.

---

## 1. Find the spec — grep the docs HTML, don't guess paths

The docs landing page is usually a JS shell ("This reference needs JavaScript"). Grep it for the
spec links; Redoc/ReDoc/Docusaurus/Stoplight all advertise them:

```bash
curl -sS -A "$UA" "https://docs.<target>/" -o docs.html
grep -oE '(href|src)="[^"]*(yaml|json|md|spec)[^"]*"' docs.html | sort -u
# -> href="/fluxapi.json"  href="/fluxapi.md"  href="/fluxapi.yaml"
```

Redoc-based docs also commonly expose `/llms.txt` and `/llms-full.txt` (AI-tools pointers) — those
are often *plain-text* endpoint inventories, even cheaper than the JSON.

Fallbacks when no link: `/openapi.json` `/openapi.yaml` `/swagger.json` `/api-docs`
`/v3/api-docs` `/spec.json` `/<product>/openapi.json`.

**Prefer `.json`** — no YAML parser dependency.

**Sibling API hosts run different stacks with different route sets.** `api.<t>.io` and
`api.<t>.com` may mirror each other, but `api.console.<t>`, `api.titan.<t>`, `api.paposse.<t>` are
separate deployments. Probe each — the RunOnFlux IDOR was on `api.titan.runonflux.io`, whose route
set (`/nodes`, `/stats`, `/config`, `/stakes/{zelid}`, `/pendingpayments`) appeared in **no** spec
and was recovered from the frontend bundle instead.

## 2. Categorise by declaration — three buckets, not two

```python
import json
d = json.load(open('fluxapi.json', encoding='utf-8'))
print(d.get('openapi'), d.get('info',{}).get('title'), d.get('info',{}).get('version'))
for k, v in d.get('components',{}).get('securitySchemes',{}).items():
    print('SCHEME', k, json.dumps(v)[:300])
print('GLOBAL security:', d.get('security'))     # None = per-operation only
```

Per-operation `security` overrides the global block, so read the **operation**, never the root:

| Declaration | Meaning |
|---|---|
| `security: []` (empty list) | vendor explicitly declares **no auth required** |
| `security: [{'FluxID': []}]` | auth required, named scheme |
| key absent, global is `None` | **undeclared** → must be probed, cannot be assumed either way |

`security: []` is **not** the same as `{}`-inside-a-list (§7's Zenya case): `[]` is an explicit
"no auth" statement, while `[{}, {basic}]` means "anonymous is one allowed option alongside
others". Both need live probing, but `[]` is the stronger prior.

Also bucket by top-level path segment to see which product area carries the most public surface,
and prioritise the money-moving one (`flux` 89, `apps` 87, `daemon` 85, `syncthing` 22, `id`/`zelid`
12, `benchmark` 11, `explorer` 10, `backup` 5, `arcane`/`payment` 2 on RunOnFlux).

## 3. Probe live — a declaration is a claim, the server is the truth

**NO-AUTH-DECLARED ≠ UNAUTHENTICATED.** Fill required query params with a placeholder so you get
the auth verdict rather than a 400:

```python
import json, urllib.request, ssl, concurrent.futures
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE

def probe(t):
    m, u = t
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, method=m,
                                      headers={'User-Agent':'BC_USERNAME'}), timeout=15, context=ctx)
        return f"{r.status} {m:6} {u} :: {r.read(200).decode('utf-8','ignore')}"
    except urllib.error.HTTPError as e:
        return f"{e.code} {m:6} {u} :: {e.read(200).decode('utf-8','ignore')}"
    except Exception as e:
        return f"ERR {m:6} {u} :: {str(e)[:80]}"

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    for res in ex.map(probe, targets): print(res)
```

Rules:

- A `200` carrying an **error envelope** (`{"status":"error","data":{...}}`) still proves the route
  is reachable unauthenticated. That is the signal — record it.
- Concurrency 8, timeout 15 s. ~180 routes finished in under a minute. **Do not raise it**: a
  separate ffuf run against a sibling host on the same estate drew Cloudflare `error code: 1015`
  rate-limits and burned that host for the rest of the session.
- Record status **and** the first ~200 bytes of body so triage needs no re-request.
- **A 404 is a negative, log it.** `/apps/operations/{jobId}` and
  `/apps/fileoperationimage/{imageid}` are documented but not mounted on the live host.
- **`410 Gone` / `Deprecated` envelopes** (`/apps/appmonitorstream/{appname}` → code 410) mean the
  route answers but is retired. Not a finding.
- **Deprecated aliases double the count.** `/zelid/*` mirrors `/id/*`;
  `/daemon/getzelnodecount` mirrors `/daemon/getfluxnodecount`. Dedupe by *behaviour*, not path,
  or you report one bug twice.

## 4. Read the description before you claim — the by-design defence is in the prose

The spec's own text usually states the design decision explicitly. RunOnFlux's
`POST /payment/verifypayment` is `security: []` **and** its description says:

> "Nothing is verified and nothing is recorded: the transaction id is relayed as a claim, not
> checked against any chain … **Public**"

That is documented design, not broken-AC — even though the endpoint lets any party POST an
arbitrary txid into any payment session (reproduced 3/3). Same discipline as the relay.link lesson
in memory: read the route's own documentation before calling unauth access a vulnerability.

Conversely, documented rate limits (`429` at >5/s, 10 pending ids on
`GET /payment/paymentrequest`) tell you the abuse model the vendor already considered — quote them
in the report as context, and do not exceed them.

## 5. The error-string oracle — which layer did you reach?

Distinct messages reveal the validation stack and whether signature verification actually runs.
Map them before concluding anything:

| Response | What it proves |
|---|---|
| `"No Flux ID is specified"` | body parsed, field missing |
| `"none"` (from `/id/checkprivilege`) | privilege lookup ran, returned none |
| `"Access denied"` (401) | auth middleware enforced |
| `"Not a valid ZelID"` | identifier format validated |
| `"Missing Data"` vs `"Invalid Data"` | **different layers** — missing field vs failed signature check |
| `"Unauthorized. Access denied."` (401) | auth enforced on this method |
| `"Request must be from an address on the same private network as the host."` (403) | network-segment gate, not an auth bypass |
| `"HTTPS required for ArcaneOS authentication endpoints"` (403) | protocol gate — and note it fires *even over HTTPS*, so read the body before assuming a bypass |

The `Missing Data` / `Invalid Data` split is the useful one: it proves the handler distinguishes
"you didn't send the field" from "your signature didn't verify", i.e. signature checking is real.

## 6. The finding shape: GET open, POST gated, same identifier

The reusable IDOR pattern on spec-mapped APIs:

1. An **identifier-leak endpoint** returns other users' identifiers
   (`GET /pendingpayments` returned 5 user ZelIDs with Flux addresses, stake UUIDs and amounts).
2. **Per-identifier detail endpoints** take that identifier in the path and return financial data
   (`GET /stakes/{zelid}`, `/payments/{zelid}`, `/tos/{zelid}`, `/earnings/{zelid}`).
3. **Neither requires auth**, while the POST siblings on the same API do
   (`POST /register`, `POST /redeem` → 401).

That inconsistency — same API, same identifier, POST gated and GET wide open — is the reportable
bug, and it is stronger than "endpoint is unauth" because the vendor demonstrably *has* the auth
middleware and applied it to half the surface.

**Prove the GET ignores auth three ways** before claiming it: no header at all, a garbage header
(`zelidauth: garbage`), and a valid-format header belonging to a *different* user. All three
returning identical data closes the "maybe it scopes by header" question.

Grep the spec for path templates (`{param}`) and cross-reference them against the required-auth
bucket — any `GET /x/{id}` whose sibling `POST /x` is in the required bucket is a candidate.

## 7. Chain it and validate

```
/pendingpayments (unauth)  -> leaks ZelIDs
      |
      +-> /stakes/{zelid}     collateral, reward, paid, expiry, tx hash, signature hash
      +-> /payments/{zelid}   payment history + on-chain txids
      +-> /earnings/{zelid}   total earned, cashed out, currently accrued
      +-> /tos/{zelid}        account status
```

Validate **3×** with byte counts, not just status codes — identical `(status, size)` across three
runs is what makes the reproduction paste-ready for a triager. Save the full evidence JSON to the
engagement dir so the report can cite exact figures.

## 8. Report framing

- State the inconsistency explicitly (POST gated / GET open) — it pre-empts "that endpoint is
  public by design".
- Quote the spec's own `security: []` declaration for the GET routes and the 401 for the POST
  routes, side by side.
- Give the chain, not just the endpoint: leak → enumerate → full financial profile.
- Note the spec version vs the live version drift; it tells the vendor which deployment you tested.
