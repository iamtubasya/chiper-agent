# Spring-Boot gateway route oracle + SPA bundle API extraction

Class-level technique for targets shaped like: **one host = a Spring Boot JSON gateway behind an F5/CDN,
plus a React/Angular SPA that owns all the real routes.** Verified end-to-end on a bank
(`ib.<target>.cz` + `main.<hash>.js`), but the shape is generic — it applies to any
`/openapi`-style gateway that returns a wrapped JSON envelope instead of 404s.

The payoff: you can turn a minified bundle into a *complete, classified* map of the server's
unauthenticated API surface — which endpoints don't exist, which are open, which are auth-enforced,
which are merely guarded — without guessing and without brute force.

---

## 1. Find the gateway base from runtime config, not from the bundle

Modern SPAs load a JSON config **synchronously before boot**. The loader is a give-away
(`xmlhttp.open("GET","./config.json",!1)` → `!1` = sync). Just fetch it:

```bash
curl -s https://<host>/config.json | python -m json.tool
# { "API_URL": "/openapi", "APP_MODE": "production", "OLD_IB_LOGIN_PAGE": "...", "FEATURE_FLAGS": {...} }
```

This one file frequently leaks more than the bundle: feature flags for unreleased features, legacy app
paths, third-party endpoints (chat/analytics/AV vendors), pricing constants, and the API base. Read it
before you read 9 MB of webpack output.

## 2. Extract the *API calls*, not the route table

A minified bundle yields ~1,800 quoted paths; only ~360 were actual API calls in the worked case.
Probing all of them is noise. Find the project's request-builder call shape and extract by that:

```python
import re
s = open("main.<hash>.js", encoding="utf8", errors="ignore").read()
eps = sorted(set(re.findall(r'hD\)\(\s*["\']([^"\']{2,90})["\']', s)))   # hD = their api() helper
```
Generic fallbacks, in order of reliability:
- `(0,X.hD)("/path")` / `hD)("/path")` — custom redux/saga request builder (best signal)
- `url:"/path"` / `axios.get("/path")` / `` `/api/${x}` `` template literals
- `.unsecured()` / `.secured(false)` / `.useBaseURL(...)` markers next to the call

**The `.unsecured()` flag is client presentation, not a control.** It tells the client which wrapper to
use; the server decides auth. Never infer "this is unauthenticated" from the bundle — prove it with a
request, and probe **both GET and POST** on every path (a POST-only mapping answers
`Request method 'GET' is not supported`, which is itself proof the route exists).

For the marketing host of the same org, `/o/<vendor-plugin>/<entry>.js` chunk names plus a headless
Playwright network capture (`page.on("request")`) recovers the same thing when the bundle isn't named
statically. That capture revealed which widget endpoints exist:
`/unsecured/codetable/{lang}/{id}`, `/unsecured/log/create`,
`/unsecured/portal/lead/alacarte/create`, `/unsecured/portal/alacarte/sms/send`.

## 3. Turn the error envelope into a route-existence oracle

Spring Boot with static-resource fallback **does not 404**. It answers 400 with a wrapped envelope:

```json
{"status":"ERROR","responseObject":{"code":"openapi.process.request.exception",
 "message":"No static resource account/envelope/list.","localizedMessage":"..."}}
```

That string is a **definitive "this route is not deployed"** signal — the single most useful thing you
can get from an opaquely-hardened gateway. Classify every extracted path into these buckets:

| Response body | Meaning |
|---|---|
| `No static resource <path>.` | **NOT MAPPED** — route absent, stop |
| `Request method 'GET' is not supported` | MAPPED, other verb — flip the verb |
| `{"code":"NotNull","message":"<field>"}` / `must not be null` | MAPPED + **OPEN unauthenticated**, DTO validation reached |
| `cbl.missing.userid.exception` / `POWER_AUTH_SIGNATURE_INVALID` | MAPPED + **auth enforced** |
| `This endpoint is for testing purposes only.` | MAPPED + **guarded** (test code in prod) |
| `{"supportID":"...","response_type":"General"}` or HTML | **WAF/ASM block** — never reached the app |

Progress the schema by feeding `{}` and reading the `NotNull` field name — that is a free DTO walk
(`loanType` → enum error listing the real values → next field). It also leaks the internal package
namespace (`cz.gemoney.api.model.loan.calculator.LoanType`), which is vendor/stack intel.

## 4. Enumerate at safe volume with ffuf

```bash
ffuf -u https://<host>/openapi/unsecured/portal/FUZZ -X POST \
  -H "Content-Type: application/json" -H "User-Agent: <browser UA>" -d '{}' \
  -w words.txt -rate 10 -t 2 -fr "No static resource" -s -o out.json
```

Pitfalls that cost rounds:
- **`-fr` (filter regex) is the right tool**, `-mc 200` is not — everything is 200 on this shape.
- Filtering only by the app-level "not found" string leaves **WAF block pages** as hits
  (uniform 46–50 KB bodies on every path). Add `-fs <blocksize>` or read bodies, never trust length alone.
- A prefix guess that 404s HTML on the non-gateway vhost (`www`) vs 400-JSON on the gateway (`ib`)
  tells you which host owns the API. Don't enumerate the wrong one.
- Verify the output file actually contains results (`hits N`) before reading "clean".

## 5. What to conclude when it all holds

Write it as a **verified control**, not a finding — and say which namespace you could not reach:
`/testing/*` guarded, session/PowerAuth enforced on `/session/ib/*` and `/secured/*`, open surface limited
to public-registry proxy + calculator + QR bootstrap + captcha-gated lead/sms endpoints. That is a
legitimate, submittable-quality negative; the payable surface is whatever the 300+ auth-required
endpoints do, which needs one real account.
