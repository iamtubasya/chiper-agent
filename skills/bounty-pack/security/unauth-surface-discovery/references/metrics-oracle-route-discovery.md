# Metrics-as-oracle route discovery

Companion to `unauth-surface-discovery` step 1f. Worked on **binobi.com / api.binobi.com**
(2026-10-28): a crypto-casino whose payment-callback layer was the highest-value target and the
only thing standing between the engagement and a balance-manipulation finding.

## Why this technique exists

Scanners and wordlists score on **status code and body**. An authenticated callback route answers
`401 {"message":"Invalid Moneygrator authentication"}` — indistinguishable, to ffuf, from a route
that does not exist. Results on this engagement:

| approach | volume | result |
|---|---|---|
| `ffuf` POST, 1 935 candidate paths (providers x callback/notify/webhook) | 1 935 | **0 hits** |
| `ffuf` GET with `-fr "Cannot GET"` | 1 935 | **0 hits** |
| `nuclei` 5 726 templates, 3 hosts | 43 652 req | only `/metrics` |
| **metrics-delta oracle** | ~60 probes | **`/moneygrator/callback` found** |

The route name was not in any product vocabulary in the bundle. It *was* in the metric labels.

## The oracle

```python
import urllib.request, re
M = "https://api.binobi.com/metrics"

def grab():
    with urllib.request.urlopen(urllib.request.Request(M, headers={"User-Agent": "Mozilla/5.0"}),
                                timeout=20) as f:
        t = f.read().decode()
    d = {}
    for line in t.splitlines():
        if line.startswith("#"):
            continue
        m = re.match(r'^(binobi_[a-z_]+(?:\{[^}]*\})?)\s+([0-9.e+-]+)$', line)
        if m:
            d[m.group(1)] = float(m.group(2))
    return d
```

Algorithm:

1. `grab()` → baseline.
2. **Calibrate**: 3 more `grab()` at ~6 s spacing with no traffic. Every candidate key must be
   delta-0. If not, the exporter is mirroring live traffic and your signal is buried — stop and use
   a different oracle.
3. For each candidate path: `probe(path)` → `sleep(0.4)` → `grab()` → diff every key.
4. Any non-zero delta = the probe reached a real handler. Log the path and the counter that moved.

Cost per probe is 2 GETs of a ~24 KB registry plus a sub-second sleep; ~60 candidates is a couple of
minutes and is *gentler* than any fuzzer.

## Reading the registry as a route map (do this BEFORE probing)

`# HELP` lines describe intent; the label values describe the deployed surface.

```
binobi_rate_limit_decisions_total{provider="<p>",rule="callback-burst",outcome="allowed"}
binobi_rate_limit_decisions_total{provider="<p>",rule="callback-minute",...}
binobi_moneygrator_callback_events_total{outcome="received|authenticated|invalid_signature|
                                                 configuration_error|status_error|duplicate|
                                                 deposit_credited|deposit_failed|review"}
```

Extracted on sight:

- **Provider enum** (15): `100hp, amatic, antrpay, avepay, bestpay, dns-pay, expay, fxmb,
  moneygrator, paysage, repay, settle, slotegrator-betting, slotegrator-casino, twilio`.
  This alone is the sibling-callback candidate list.
- **`rule="callback-burst"`** proves callback endpoints exist per provider even before you find one.
- **`outcome=`** is the callback state machine — and `invalid_signature: 843` vs `received: 901`
  told us the endpoint was publicly reachable and rejecting forgeries, i.e. actively fuzzed by
  someone else.
- `binobi_auth_refresh_events_total{outcome="replay"}` and `binobi_auth_origin_errors_total`
  pre-announced the session-layer findings before any request was sent.

Sibling sweep after the first hit (`provider x {callback, notify, webhook, cb}`):

```
400 /avepay/callback      {"message":"Missing signature header"}
410 /bestpay/callback     {"message":"Payment provider is disabled"}
400 /fxmb/callback        [12-field DTO dump]
200 /games/callback       {"error_code":"INTERNAL_ERROR","error_description":"Invalid sign"}
200 /games/callback/amatic {"error_code":"INTERNAL_ERROR","error_description":"Invalid sign"}
401 /moneygrator/callback {"message":"Invalid Moneygrator authentication"}
```

## Per-controller auth-ordering classification

Same platform, three different qualities of guard. **The inconsistency is the reportable finding.**

| shape | meaning | verdict |
|---|---|---|
| single uniform `401` for every input | guard runs first | correct, log as held control |
| `400` + full DTO / enum list, no signature at all | body validated *before* auth | **disclosure finding** — hands attacker the internal contract |
| `Missing signature header` vs `Invalid signature` | header name leaked; comparison not key-lookup | **disclosure finding** — authentication oracle |
| `200 {"error_code":...}` | aggregator-style, auth inside a 200 envelope | scanners misread as success; verify by delta/oracle |

Severity framing that survives triage: *"authentication held; this is disclosure of the internal
contract and the auth scheme"* — Low-Medium. Do **not** dress it as a bypass.

## Forgery negative checklist (run it, then publish it as a negative)

Every one of these was tried against `/moneygrator/callback`, `/avepay/callback`,
`/fxmb/callback` and `/games/callback`, and every one was rejected. Publishing the list is what
makes "the signature check is sound" credible instead of hand-waving.

- **Header discovery**: 27 candidate header names (`signature, sign, x-signature, x-sign,
  x-<provider>-signature, x-api-key, api-key, authorization, token, secret, hash, hmac, checksum,
  x-merchant-key, ...`) and 8 query-param equivalents. Watch the *error text* change, not the code.
- **HMAC/secret guessing**: `md5/sha1/sha256(secret + body)`, `(body + secret)`,
  `hmac-sha256(body, secret)` for secrets `""`, `provider`, target brand, `secret`, `test`, `key`.
- **Magic values**: `0e0000...`, `true`, `1`, `admin`, `" "`, empty string.
- **Type juggling**: `sign` as `[]`, `{}`, `0`, `true`, `null`, `["a","b"]`, `{"toString":...}`.
- **Prototype pollution**: `{"__proto__":{"sign":"x"}}`, `{"constructor":{"prototype":{"sign":"x"}}}`.
- **Shape abuse**: non-hex, `"A"*64`, `"a"*5000`, truncated bodies, `{}garbage`, `null`, `[]`, `"x"`,
  invalid UTF-8, missing body, `PUT`/`GET`/`HEAD` on the route, trailing slash, case-flip,
  `//`, `/./`, `;.json`, `%00`.
- **Bearer/JWT**: replay a *valid user access token* at the callback (guards sometimes accept either).
- **Settlement spoofing without the callback**: fetch the provider's return URL
  (`/redirect/success/<provider>?tr_id=<ours>`) for an unpaid order. Did not credit — settlement is
  server-to-server only. Document that, because it proves the return URL is not trusted.

## Adjacent win: Next.js `_buildManifest.js` is a route dump

`/_next/static/<buildId>/_buildManifest.js` (buildId from any page's `_next/static/<buildId>/`) is
served to everyone and contains both the **rewrites** (which reveal the API proxy!) and the complete
`sortedPages` list:

```
__rewrites: { afterFiles: [ { source: "/:locale(...)/_binobi/api/:path*",
                              destination: "/api/mirror/:path*" } ] }
sortedPages: ["/account/[username]","/account/sessions","/finance-hold", ...]
```

Regex `"/[^"]*"` over it yields every page including ones nothing links to. Then fetch the
per-page chunks listed in the manifest and grep the API paths out of them — on this target that
produced the 196-route internal inventory (deposit/withdraw/bonus/wheel/referral/KYC/admin-ish)
that the landing page never mentions. Two `curl`s, zero requests to the API.

## Driving an authenticated SPA headless (for the paths the API alone can't reach)

The front end refreshes into an `__Host-` httponly cookie and keeps the access token in memory, so
copying cookies from a script does not log you in. What worked (Playwright, `playwright-core` +
system Chrome):

```js
// intercept the whole API namespace: forge the refresh, stamp auth on everything else
await ctx.route('**/_binobi/api/**', async route => {
  const req = route.request();
  if (req.url().includes('/auth/refresh'))
    return route.fulfill({status:200, contentType:'application/json',
      body: JSON.stringify({result:{...USER, token:TOKEN, expiresAt:USER.expiresAt}})});
  return route.continue({headers:{...req.headers(),
    authorization:'Bearer '+TOKEN, 'x-binobi-csrf':'1'}});
});
```

Pitfalls that each cost a retry:

- **`addInitScript` + `window.fetch` monkey-patch is unreliable** on Next.js (bundled fetch, and a
  single typo like `window.fecth` fails silently with no console error). `ctx.route` operates below
  the page and always works — prefer it.
- Log in over the API first, then feed that token into `route.fulfill` for `/auth/refresh`; the SPA
  treats refresh as the source of truth and will overwrite anything in localStorage.
- The CSRF header (`X-Binobi-CSRF: 1`) is required on every mutating call and is checked on the
  *origin* + a static header, not a token — copy it as-is.
