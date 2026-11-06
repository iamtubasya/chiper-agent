---
name: unauth-surface-discovery
description: "Find bugs on the unauthenticated perimeter of a hardened web target when the authenticated area is unreachable (no test account, KYC-gated signup, VDP with no creds). Covers page-config extraction, error-oracle API mapping, namespace enumeration on error text, escaping-map measurement, mass-assignment verification, availability parameter sweeps, internal-hostname leakage, generated-SDK auth-flag grep (secure:!0) with dual-prefix sweeping and the 401-vs-403 auth-model map, source-map recovery, SSO/SAML domain oracles, live-telemetry health verification, dangling-CNAME anti-reuse checks, vendor-docs-before-escalating, unauth OAuth dynamic client registration + client-metadata impersonation, vendor demo-keyset provenance triage, the read/write PAM asymmetry that makes a messaging-keyset write reportable, session-middleware presence-check auth bypass, public-config-file key triage, reCAPTCHA-Enterprise signup order mapping, the chain-escalation battery, and engagement discipline."
metadata:
  hermes:
    tags: [security, bug-bounty, unauth, api-discovery, recon, fintech, discipline]
version: 1.2.0
---

# Unauthenticated Surface Discovery

> For hardened targets where you cannot reach the authenticated area. The payable findings live on the
> unauthenticated perimeter, and template spraying is not how you find them.

## The unauth vector battery (ordered) — run this FIRST, before any auth

The single most-asked question is *"vektor apa yang wajib diperiksa di unauth surface?"*.
The answer is a tiered checklist, not more guessing. `references/unauth-vector-battery.md`
is the ordered pass — cheapest→most expensive, every item producing an artifact:

```
Tier 0  fingerprint (headers, favicon, TLS SAN, OPTIONS/TRACE)  -> picks the templates
Tier 1  .well-known + security.txt + openid-configuration + jwks
Tier 2  source/config/backup: .git .env .svn .DS_Store package.json *.bak *.js.map
Tier 3  framework-specific: actuator / ignition / __debug__ / rails routes / jenkins / swagger
Tier 4  discovery oracles: Vite config, NotNull oracle, error-text enum, dispatcher sweep,
        /metrics delta, secure:!0 grep, source maps
Tier 5  access-control on unauth: collection-no-cookie, method-override, presence-check,
        forgot-password enum, SSO oracle, OAuth DCR, keyset read/write asymmetry
Tier 6  injection on reflected surface (only after escaping map) + host-header + SSRF
Tier 7  infra/DNS: subdomains, dangling CNAME, S3/GCS lock, RFC1918
```

Open the battery file the moment the estate is enumerated, and do NOT gate into
authenticated testing until the reachable tiers are walked. The tiers below (1a–1s)
are the *technique details* behind the battery; the battery is the ordered checklist.

## When to use
- The programme provides no test account and signup is KYC/BankID-gated (common for banks, fintech, telcos)
- A VDP gives you a host list but no credentials
- You have exhausted the obvious unauth endpoints and need a *routine*, not more guesses
- Signup is waitlist-, invite-, or domain-gated (technical-preview platforms that self-serve only
  `.edu/.mil/.gov` and wave everyone else in) - see step 11
- You are about to run a large scanner sweep against a regulated target (read the discipline section first)

## The discovery routine (6 steps)

### 1. Mine the pages for the API contract (free white-box)
Product / calculator / onboarding pages that host React widgets carry an inline `configuration` block.
Fetch the HTML and read it - it typically contains:
- `searchEndpoint`, `endpointUrl`, `historyEndpoint`, `qrEndpoint`, `apiUrl`, `cblOpenApiUrl`, `serverUrl`
- `customRequestBody` - sometimes a full backend query body with a `##placeholder##` in it
- the exact request shape the widget will send

This costs one GET per page and zero API requests. Do it before touching the API.
- Public content/file feeds count as pages too: a checkpoint or document endpoint that serves stored
  HTML (`/api/checkpoints/public/<id>/content`) can contain JS-driven forms posting to
  undocumented endpoints (a red-team-program apply form and a capacity-offer form were both found
  this way, neither in the OpenAPI contract). Fetch every public file, grep for `fetch(`,
  `action=`, and `/api/` strings, then probe the discovered endpoints for validation quality
  (empty POST -> field oracle, CRLF in email fields, type confusion, SSRF via URL fields with an
  interactsh collaborator).

### 1b. Vite / Vue SPAs — `window.VITE_*` is the config block, and it names the API base

Vue/Vite/Svelte builds inject every `VITE_`-prefixed env var into the HTML shell as
`window.VITE_<NAME>`. On a Vite target this is the single highest-value grep, because one
2.5 KB shell usually carries the API base, the captcha sitekey, the payment vendor id and
the custom-domain DNS targets together:

```bash
curl -s https://TARGET/cloud -o shell.html        # the SPA route, NOT the apex
grep -oE 'window\.VITE_[A-Z0-9_]+' shell.html | sort -u
```

Measured on a live file-sharing SaaS (2026-10-26): the shell was 2,567 bytes and carried
`VITE_API_URL='/api/'`, `VITE_CLOUDFLARE_TURNSTILE_KEY`, `VITE_PADDLE_VENDOR_ID`,
`VITE_CUSTOM_DOMAINS_CNAME='cname.<prod>.cloud.'` and `VITE_CUSTOM_DOMAINS_A='75.2.85.205'`.
Two are directly actionable: the API base (every route below is relative to it) and the
custom-domain A record — which is exactly what a custom-domain-claim test needs to know.

**Fetch the SPA route, not the apex.** That target's apex served a 174,869-byte marketing
page with no config at all; the block only existed on `/cloud`. Probe the app route names
you found in the bundle (`/app`, `/console`, `/dashboard`, `/cloud`, `/portal`) before
concluding a target has no client config.

**Extract the state machine, not just the routes.** The minified bundle holds the enum
literals for every access-control state the product has. Grep the `case` labels:

```bash
grep -oE 'case`[a-z_]+`:return`[^`]+`' bundles/*.js | sort -u
```

On that target this yielded `everyone` (Anyone with the link) · `password` (Password
protected) · `team` (Team members only) · `private` (Only me), plus a second enum for
comments (`everyone`/`team`/`disabled`) and an `expire_after` day-counter. **That list is
your authenticated test plan**: each state is a differential (owner sets state X, then read
as another user and as an anonymous viewer). Without it you test "can I read it"; with it
you test all four gates.

### 1c. A wildcard subdomain that echoes the apex is a catch-all, not an app host

`api.<prod>.cloud` returned HTTP 200 with a body **byte-identical (same sha256) to the apex
marketing page**, while `app.`, `cloud.`, `upload.`, `cdn.`, `static.` and `assets.` on the
same wildcard all failed to connect. Reading: the wildcard resolves and the origin serves
the apex for any unknown host — there is no per-subdomain app there.

**Rule:** before treating a discovered `*api*` host as a backend, sha256 its body against
the apex. Identical = catch-all; log it and move on, do not spend probes on its paths. A
nonsense host under the same wildcard that fails to connect at all is the useful control —
it proves the wildcard is not universal.

### 2. Recover parameter names with the NotNull error oracle
POST an empty body `{}` and read the validation error:
```json
{"status":"ERROR","responseObject":{"code":"NotNull","message":"fixation"}}
```
Add that field with a plausible value, repeat. Stop when the response shape changes (usually a generic
backend error, which means every required field is present). Never guess parameter names - the oracle
gives them to you for free.

### 3. Enumerate namespaces by module x operation, filtering on ERROR TEXT
```bash
ffuf -u "https://TARGET/openapi/unsecured/portal/MODULE/FUZZ" -X POST \
     -H "Content-Type: application/json" -H "User-Agent: <browser UA>" -d '{}' \
     -w ops.txt -rate 10 -t 2 -fr "No static resource" -s -o out.json
```
**Filter on the error text, never on status code or size.** A WAF block page and a real 404 share both,
and a uniform-size response across every path is a WAF artifact, not a result. If every probe returns the
identical byte count, you are measuring the WAF, not the application.

### 3b. A single dispatcher endpoint — enumerate COMMAND NAMES from its error text

Some backends expose one path (`/api/v1/`) and route by the *first path segment*
being a command name. Every unknown name returns a structured error naming the
handler, which is a free oracle:

```
GET /genians/api/v1/user     -> 400 {"error":"unknown command user"}
GET /genians/api/v1/member   -> 200 {"result":"failed"}          <-- live command
```

**Tell:** every path returns a *same-shaped* error whose text interpolates your
input, and the response size tracks the input length. That is a dispatcher, not a
404 handler. Record the exact wording — it is your filter string.

**Then sweep, and sweep properly.** Generate `nouns × prefixes` rather than
guessing: the product's own vocabulary (from page/JS extraction: license, site,
trial, subscription, sensor, node, policy, quota, billing…) crossed with
`get/list/create/add/set/update/delete/check/find/search/register/…` plus
`camelCase` (`getPlans`) and suffix forms (`licenseList`, `license_info`). ~5 000
candidates at 8 threads finishes in a few minutes and is the cheapest coverage
you will get on an otherwise opaque surface.

**Calibrate the result before believing it.** On Genians (2026-10-27) 5 651
candidates against `/genians/api/v1/` produced **2** live commands (`samlauth`,
`member`). Two out of 5 651 is a *normal* ratio for a dispatcher — it does not
mean the sweep failed. What it does mean is: **the dispatcher now holds no more
surface for you**, so stop sweeping that namespace and move to the front-end's
own AJAX layer instead (see below) rather than iterating the wordlist.

**Do the same on the CMS's AJAX layer.** WordPress `admin-ajax.php` is a second
dispatcher with the same property, except an unregistered action returns the bare
string `0` instead of JSON, and live actions return real payloads. Sweeping 155
`<plugin>_`-prefixed verbs there found 7 live handlers that the HTML never
mentioned. Note that a `-1` / `0` / `false` body is the *not-registered* signal
and must be filtered out, exactly like `fr "No static resource"` in step 3.

**Read the CSRF behaviour of the dispatcher while you are there.** On Genians the
token came from its own `*_create_csrf_token` action and was **single-use** — the
same token replayed returned the authz error. That is a *held control*: record it
as a negative with evidence, and derive the harness consequence — mint a fresh
token immediately before each mutating call, in the same session, or every
"bypass" you measure is really just a stale token.

### 4. Measure the escaping map before trying payloads
For any reflected parameter, send one character at a time and record what comes back:
```
<  -> &lt;      >  -> &gt;      "  -> &#034;     '  -> &#039;     &  -> &amp;
\  / = ; ( { ] [ tab % # @ ^ | ~   -> RAW
newline, CR -> blocked by WAF
```
If every breakout character is entity-encoded, there is no injection point - say so and move on. HTML
entities are NOT decoded inside `<script>`, so `"` -> `&#034;` is safe in a JS string context even though
it looks wrong. This measurement also stops you filing a reflection that is actually safe.

### 5. Verify before claiming mass assignment
If an extra field changes the output, grep the live pages for that parameter name. If the site's own
widget sends it, it is a documented feature (a product comparator sending `productId`, for example).
Claiming mass assignment on a legitimate parameter burns credibility with the triager.

### 6. Establish whether an unbounded parameter is systemic or isolated
When you find a numeric parameter with no upper bound that drives server-side work, run the same probe
against every sibling endpoint. "Isolated to the mortgage calculator, the personal-loan and savings
calculators reject the same value in 0.4 s" is a credible report. "One endpoint is slow" is not.

### 7. For availability findings: sweep EVERY numeric parameter, and hunt for a SUCCESSFUL slow value
Two separate moves, both of which materially changed a real report:

**(a) Parameter-isolation matrix.** When one parameter drives unbounded server-side work, sweep every other
numeric parameter individually before writing the finding. On the worked example this turned a one-parameter
report into a two-parameter one (`maturity` AND `fixation`), and produced the root-cause sentence that
convinced: *the validation layer exists and rejects `realtyAmount`/`loanAmount` in 0.3 s, but misses these
two fields*. A single weird parameter reads as an anomaly; a matrix reads as a missing guard.

**(b) Find a value that returns HTTP 200 + `"status":"OK"` with a VALID result after a long time.**
This is the single most useful trick for availability findings. Nearly every programme excludes *"errors
thrown by a web service when using an invalid request"*. A value that produces a *successful* computation
after 7-28 s is not an error response - it is an unbounded computation that happens to succeed, and the
strongest ineligibility argument against the report disappears. Search the parameter's range for that
point; it usually exists just below the value where the backend starts erroring.

### 8. Leak proxy topology with a URI-resolution error
Send a double quote in a path parameter of a proxied route. Gateways that build an upstream URL frequently
echo it on failure:
```
GET /openapi/unsecured/codetable/cs/X%22
-> {"code":"openapi.process.request.exception",
    "message":"Failed to resolve URI from 'https://cbl-prod.awslb.mbid.cz/cbl/codetable/cs/X\"'"}
```
That discloses the internal host and path unauthenticated. Then run the same trigger across **every**
endpoint before concluding - on the worked example exactly one of eleven endpoints leaked, and the second
hunt confirmed there was no second internal host. Also check response headers; they are usually clean.

### 9. Prove a SQLi negative with Jackson strict-typing, not just sqlmap
Send a type-confusion probe to every parameter (string where a number belongs, object, array, bool). If all
are rejected at deserialization with `java.lang.Integer` / `String` / `BigDecimal` / `Boolean`, no untyped
string ever reaches a query builder. State that explicitly in the report - it is a stronger and more honest
negative than "sqlmap found nothing", and it survives a triager asking *how do you know*.

### 10. Estates behind an authentik proxy outpost
When every host 302s to `/outpost.goauthentik.io/start`, the outpost's public-path allowlist IS the
unauthenticated attack surface. Map it by probing a curated path list (anything not allowlisted
302s to sign-in), then test path-normalization bypasses of it (`../`, `%2e%2e`, `//`, `..;/`,
null byte) - the auth check must still hold at the API layer behind the proxy; a bypass that
reaches a 401 is correct behaviour, not a finding. To exercise sign-in itself, drive the flow
executor API directly (full recipe in the reference below): the POST must be form-encoded and the
identification stage's real field is `uidField`. Also map each OAuth client's redirect_uri
validation (exact-match is the secure pattern) and any MCP dynamic-client-registration
redirect_uri whitelist (loopback-only is secure). A 422-before-401 on parameterised routes is
FastAPI validation ordering, not an auth bypass - confirm with complete parameters.

### 11. When signup itself is the blocker (waitlist / invite / .edu-only platforms)
Do not burn the session re-probing signup. Join the waitlist with a disposable inbox (mail.tm API:
GET /domains, POST /accounts, POST /token, GET /messages), set a cron monitor that checks the
inbox every 20m for the "spot opened" mail, and build the authenticated attack plan meanwhile:
extract the full endpoint inventory from the SPA's inline JS (string literals and template
literals starting with `/`, including org-scoped paths like `/api/orgs/{uuid}/...`) and rank the
IDOR/business-logic targets by bounty tier so execution starts the instant a credential exists.
State the blocker explicitly to the operator with the options (their own token / an eligible
address / wait) rather than silently idling.

### 12. Pivot to the target's PUBLIC GitHub repos when live exploitation is CAPTCHA-blocked
When every signup channel (web form, OAuth, WHMCS, WorkOS) validates Turnstile/reCAPTCHA server-side and
headless browsers are detected, stop burning time on account creation. Instead:
1. Check the target's schema.org JSON-LD, footer, or `sameAs` fields for a GitHub org URL
   (`github.com/<org>`). Many companies link it from their about/legal pages.
2. List the org's public repos: `curl -s "https://api.github.com/users/<org>/repos?per_page=100"`
3. Match repo names to the live subdomains you fingerprinted (e.g. repo `sesdashboard` → host
   `ses.<target>.com`). Fetch the file tree: `curl -s "https://api.github.com/repos/<org>/<repo>/git/trees/<branch>?recursive=1"`
4. **Verify the deployed version matches the repo** by comparing build asset hashes. The live page's
   `<link href="/build/112.069aa3e8.css">` should match `public/build/112.069aa3e8.css` in the repo.
   If they match, the source IS the deployed code — findings are not theoretical.
5. Read the security-critical files first: `config/packages/security.yaml` (or equivalent),
   authenticator classes, controllers with `PUBLIC_ACCESS` routes, and any file with a `TODO` comment
   near an auth check. Grep for `TODO Permissions`, `TODO Auth`, `// no check`, `find($request->get(`.
6. Confirm the vulnerable routes exist on the live site: a 405 on GET for a POST-only route proves the
   route is public (router rejects method before auth); a 302 to /login proves the route exists behind auth.
7. Report with source code + live endpoint behavior as combined PoC. The vendor can verify in minutes
   with their own credentials/tokens even when you cannot trigger the full chain.

This pivot found a PUBLIC_ACCESS SSRF and two IDORs on a real engagement (DuoCircle, 2026-10-26) where
every authenticated endpoint was unreachable. Full worked example: `references/github-source-pivot.md`.

### 1d. SPA bundles state their own auth model — grep the auth MARKER, not the paths

The highest-yield move on an SPA whose API base you already know: the request layer usually
carries an explicit per-call auth flag, and that flag *is* the unauthenticated surface.

Measured on MONETA internet banking (2026-10-28). Every call is built as
`hD("/path").httpMethod("POST").unsecured()` — `.unsecured()` is the client-side marker for
"no auth required". One regex over the 9.57 MB app bundle returned the complete unauth surface:

```python
re.findall(r'hD\)\(?\s*["\'`](/[^"\'`]{2,90})["\'`]\s*\)([^;]{0,260}?)unsecured\(\)', js, re.S)
# 28 call sites -> 18 unique paths, no guessing
```

Generic marker vocabulary to grep for, per framework:

| marker | framework |
|---|---|
| `.unsecured()`, `secured:!1`, `secure:false` | in-house fetch wrappers |
| `skipAuth`, `noAuth`, `requireAuth:false`, `withCredentials:false` | axios/fetch wrappers |
| `@Public()`, `isPublic`, `PERMIT_ALL` | NestJS / Spring annotations leaking into bundles |
| `public: true` next to a route object | React Router / Vue Router route tables |
| `unauthenticated:!0` | Firebase-style SDK wrappers |

Two hard-won details:
- **The entry chunk is a shell.** Enumerate `static/js/main.<hash>.js` (or the equivalent app
  chunk referenced from the login HTML) — not the vendor `launch-*.min.js`, which is analytics.
  Confirm by size: the app chunk was 9.57 MB vs 176 KB for the vendor file.
- **The client's own marker is a claim, not proof.** Each marked path still has to be probed;
  of MONETA's 18, several were gated server-side anyway (PowerAuth signature, upstream 401).
  Use the marker to get the *complete candidate list*, then verify every entry.

### 1e. Route-existence differential beats any wordlist

On a gateway that returns structured errors, three response shapes separate cleanly:

```
/openapi/some/path                 -> 400 "No static resource x/y"   route DOES NOT exist
/openapi/session/ib/password/...   -> 401 POWER_AUTH_SIGNATURE_INVALID  exists, auth required
/openapi/testing/skip-login        -> 400 "No static resource ..."    absent in this deployment
```

The `No static resource <path>` message **echoes the path you asked for** — that is a 404 in
disguise, not an error about your input. Filter on that exact string. A sibling probe
(`routeXXX` vs `route`) is the cheapest confirmation that a route is real.

### 1f. A leaked `/metrics` registry is a ROUTE-DISCOVERY ORACLE, not just an info-disclosure finding

An exposed Prometheus endpoint is usually filed as Medium information disclosure and then dropped.
Treat it as an instrument instead: **snapshot -> send one probe -> re-snapshot**, and a delta in any
per-route or per-provider counter proves the probe reached a real handler. The metric labels also
*spell out* route vocabulary that no wordlist contains.

This is the move that cracked binobi (2026-10-28). `ffuf` over 1 935 POST paths against
`api.binobi.com` returned **zero** hits; the callback the whole engagement was aimed at was found in
under a minute once the counters were read:

```python
# oracle.py — delta on the counter, not on the response body
K = 'binobi_moneygrator_callback_events_total{outcome="received"}'
before = grab()[K]; st, body = probe("/moneygrator/callback")      # 401, looks dead
after  = grab()[K]                                                  # +1.0  -> ROUTE EXISTS
```

Hard-won calibration rules, all of which cost time when skipped:

- **Prove the counters are quiet first.** Take 3 snapshots ~6 s apart with no traffic; if they move,
  you are watching other people's production traffic and every delta is noise. On binobi they read
  exactly 0 delta for 18 s — only then is a +1 meaningful.
- **Sleep ~0.4 s after the probe** before re-snapshotting; the exporter is scraped, not live.
- **A 401/403 is a hit, not a miss.** Scanners score on status code and body, so they discard the
  authenticated route as "not found". The oracle scores on *counter movement*. That is the whole
  reason this route survived 1 935 fuzzed paths.
- **Mirrors usually expose the same registry.** `api.<mirror-domain>/metrics` returned 200 with the
  same content when the primary was edge-cached — enumerate the mirror apex list before concluding
  a host is closed.

**Read the label sets as a route map before probing anything.** `provider="<name>"` enumerates every
payment/aggregator integration (binobi: `100hp, amatic, antrpay, avepay, bestpay, dns-pay, expay,
fxmb, moneygrator, paysage, repay, settle, slotegrator-casino, slotegrator-betting, twilio`);
`rule="callback-burst"` confirms callback endpoints exist for those providers; `outcome="received /
authenticated / invalid_signature / duplicate / credited"` hands you the callback's state machine.
Cross `provider x {callback, notify, webhook}` and the sibling list is free — that is how
`/avepay/callback`, `/fxmb/callback` and `/games/callback` were found after `/moneygrator/callback`
landed.

**Then classify per-controller, because they are not written by the same person.** Same platform,
three behaviours: `/moneygrator/callback` returned one uniform 401 (correct); `/fxmb/callback`
validated the body *before* the signature and dumped its full 12-field DTO + enums to anonymous
callers; `/avepay/callback` distinguished `Missing signature header` from `Invalid signature`, leaking
the exact header name (`signature`) and that the check is a comparison rather than a key lookup.
That inconsistency **is** the finding (Low-Medium disclosure / auth-ordering) — report it honestly as
disclosure, never as a bypass. Full recipe and the complete forgery negative checklist:
`references/metrics-oracle-route-discovery.md`.

### 1g. Generated SDK clients carry a per-call auth flag — grep the flag, then sweep BOTH prefixes

When the SPA bundle contains a *generated* API client (shape `this.request({path:"/api/x", method:"GET", secure:!0, ...})`), every route in the product is enumerated by one regex and each is explicitly marked:

```python
blocks = re.findall(r'\{path:\s*[`"]([^`"]+)[`"]\s*,\s*method:\s*"([A-Z]+)"([^{}]{0,300})', js, re.S)
unmarked = [(m, p) for p, m, rest in blocks if "secure:!0" not in rest]
```

PubNub admin dashboard (2026-10-31): **293 (method,path) pairs — 255 marked `secure:!0`, 38 not.** The 38 are the client's own claim of "no auth required": the same signal as `.unsecured()` in step 1d, different vocabulary. Marker-table additions:

| marker | framework |
|---|---|
| `secure:!0` / `secure: !0` | generated TS/JS SDK clients (openapi-generator style) |
| `unsecured()` | in-house fetch wrappers |

Two hard-won details:
- **Sweep BOTH prefixes.** A generated client's `path` is relative to a base set in another module (`baseUrl:"/api"` in one, `""` in another). On PubNub the same route existed at both `/api/keys` and `/keys` against *different backends* — 586 probes across two prefixes found routes a single-prefix sweep missed.
- **The 401-vs-403 split is a free auth-model map.** `401 {"code":401,"error":"Unauthorized"}` = the auth middleware never ran; `403 {"message":"Forbidden resource"}` = it ran and refused. Grouping the sweep by response shape told me which routes sat behind which guard before sending one authenticated request.

### 1h. Deployed source maps are a free white-box read

A CRA/Vite deployment that ships `*.js.map` hands you the whole original source tree with `sourcesContent`:

```
GET https://TARGET/static/js/main.<hash>.chunk.js.map
-> {"version":3,"sources":[...],"sourcesContent":[...]}
```

PubNub moderation dashboard (2026-10-31): two maps totalling **2.5 MB of readable application source** (53 app component files + 744 node_modules files). Worth one probe on every SPA host *before* minified-bundle archaeology — `asset-manifest.json` lists the chunk names and the `.map` sits beside each `.js`. Grep the recovered source for keys, endpoints and the `secure` flag from 1g; it reads far easier than the minified bundle. File the exposure itself as Low information disclosure and use it as the reconnaissance input for everything else.

### 1i. An SSO/SAML domain-lookup endpoint is a CUSTOMER-LIST ORACLE

Login pages that ask "type your corporate domain, we'll redirect you to your IdP" expose an unauthenticated discriminator:

```
GET /api/saml?domain=dazn.com     -> 200 {"redirect_url":"https://login.microsoftonline.com/<tenant-id>/saml2?SAMLRequest=..."}
GET /api/saml?domain=example.com  -> 400 {"error_data":["SSO is not enabled for this domain"]}
```

**The 200/400 split is the oracle.** Submit a corporate-domain wordlist and you enumerate which organisations are enterprise customers — and for each, the identity provider, the Entra **tenant ID** (normally only obtainable post-auth, and the primary input to tenant-scoped identity attacks), the Okta federation app path, and the internal ACS/issuer contract (decode the base64+deflate `SAMLRequest` to read it).

**Calibrate before claiming.** Prove the split is enrollment state, not injection: suffix/prefix tricks (`evil.dazn.com`, `dazn.com.evil.example.com`, `dazn.co`, `sub.dazn.com`, NUL/CRLF variants) must all return 400; uppercase normalisation matching is correct behaviour, not a bug. Then chase the obvious escalation — unsigned assertion, self-signed signature, XXE — and record it as a **negative** if the ACS validates properly (PubNub's did: `No Signature found` / `Signature validation failed`). Filing the disclosure honestly as Medium rather than dressing it as ATO is what gets it paid.

**A second shape of the same oracle is the Origin-gated `checksaml` variant (LoginRadius,
2026-11):** `GET /auth/checksaml?sitename=saml_{slug}` returns
`{"ErrorCode":500,"Message":"Not allowed by CORS"}` in a **200 BODY** when the `Origin` header is
absent or wrong — but returns `{"isFound":true|false}` the moment you set two client-controlled
headers: `Origin: https://<the-app-own-origin>` plus an `X-<App>-Ajax: true` flag. "Not allowed by
CORS" returned *in the body* is NOT a browser-enforced CORS policy (that would send no header and
the browser would block the read); it is a **server-side allowlist keyed on the trivially spoofable
Origin header**. When you see that string, re-issue with the app's own `Origin` plus any
`X-*-Ajax`-style flag and re-check for a response divergence — this is the cheapest access-control
probe on SPA admin backends (and the flag name itself surfaces from the bundle's request layer,
same grep as §1g/§1d). The discriminator (`isFound:true` for `saml_postmedia` / `saml_ultabeauty`
/ `saml_northumbrianwater` vs `false` for random slugs) is the same customer-list oracle §1i
describes; the gate is a header, not a query param. Escalation dead-ends worth naming: the sibling
`/auth/config` (which also answers via the same Origin gate) returns the console's OWN config and
ignores tenant params (`?domain=`, `?sitename=`, `?appname=`), so it does NOT leak other tenants.

### 1j. Prove a health endpoint is LIVE instrumentation before filing it

An unauthenticated `/api/health` returning JSON is only a finding if it is real telemetry. Three cheap checks:

1. **Sample 3x, ~2 s apart.** If `Connections in pool` moves (6, 8, 9, 10 observed), the endpoint executes code reading live pool state — not a cached string.
2. **SPA-catch-all negative control.** On an SPA host every unknown path returns 200 + the HTML shell. Confirm this path returns `application/json` and that `GET /api/zzz-nope-<random>` returns a genuine 404 — otherwise you are reporting the SPA's generic 200.
3. **Credential-insensitivity.** `Authorization: Bearer <garbage>`, an empty session cookie and a junk session header must all return the identical body; that proves no auth evaluation happens on the path.

Then sweep sibling hosts: on PubNub the same endpoint was live on `admin.`, `dashboard.` and `demo-admin.`, which is what made it a product-wide exposure rather than one host's misconfiguration.

### 1l. An OIDC discovery document hands you the whole provider surface — then test registration FIRST

`/.well-known/openid-configuration` is one GET and it names every endpoint you need, including ones
no scanner probes. PubNub's (2026-10-31) advertised `registration_endpoint`, a
`pushed_authorization_request_endpoint`, `token_endpoint_auth_methods_supported` **including `none`**,
and `end_session_endpoint`:

```json
{"issuer":"https://admin.pubnub.com/oauth",
 "authorization_endpoint":"https://admin.pubnub.com/oauth/auth",
 "token_endpoint":"https://admin.pubnub.com/oauth/token",
 "registration_endpoint":"https://admin.pubnub.com/oauth/reg",
 "pushed_authorization_request_endpoint":"https://admin.pubnub.com/oauth/request",
 "end_session_endpoint":"https://admin.pubnub.com/oauth/session/end",
 "scopes_supported":["openid","email","profile","offline_access"],
 "token_endpoint_auth_methods_supported":["client_secret_basic","client_secret_jwt","client_secret_post","private_key_jwt","none"]}
```

**Test the registration endpoint unauthenticated before anything else.** RFC 7591 DCR is frequently left
open on internal/enterprise IdPs because it is only needed by IDE/CLI integrations:

```bash
curl -s -X POST https://TARGET/oauth/reg -H "Content-Type: application/json" \
  -d '{"client_name":"zzprobe","redirect_uris":["http://localhost:9999/cb"],
       "token_endpoint_auth_method":"none",
       "grant_types":["authorization_code","refresh_token"],
       "scope":"openid profile email offline_access"}'
# 201 -> client_id + registration_access_token + registration_client_uri
```

**The minted client must then be proven functional, not just issued.** Two cheap proofs that it is a
real client on the production IdP:

1. Feed the `client_id` into the authorization endpoint — HTTP 200 serving the genuine login SPA means
   the client is accepted.
2. Feed the same `client_id` to the PAR endpoint — a `201` with a `request_uri` confirms it end-to-end.

**Rate-limit probe is part of the finding.** Six registrations 0.4 s apart from one unauthenticated IP
all succeeded with no `X-RateLimit-*` header. That is a separate, independently reportable weakness.

**Then test whether client identity metadata is verified — this is where the real severity lives.**
Registration endpoints that accept anonymous callers usually skip verification of `client_name`,
`client_uri`, `logo_uri`, `policy_uri`, `tos_uri` and `contacts` entirely:

```json
{"client_name":"PubNub Admin Dashboard",
 "client_uri":"https://admin.pubnub.com",
 "logo_uri":"https://admin.pubnub.com/logo.png",
 "policy_uri":"https://www.pubnub.com/policies/",
 "tos_uri":"https://www.pubnub.com/terms/",
 "contacts":["security@pubnub.com"]}
```

All six accepted verbatim, HTTP 201. **Prove persistence, not just echo** — read the client back with
the issued `registration_access_token` via `registration_client_uri`; if the branding comes back, it is
stored server-side and is what a victim would see on a consent screen. Validate 3x.

That combination — unlimited anonymous client creation + arbitrary brand impersonation persisted on a
production IdP — is the precondition for a consent-phishing campaign indistinguishable from a genuine
OAuth grant. It is the strongest thing an unauth OAuth audit can produce without a token.

### 1m. The chain-escalation battery — how to argue a Medium upward without overclaiming

When you hold a Medium and the operator asks *"can this reach High or Critical?"*, run this battery
rather than reasoning about it. Every row is a concrete probe, and every row that fails is a documented
negative that makes the report stronger.

| # | probe | what a pass would mean |
|---|---|---|
| 1 | `redirect_uri` allowlist bypass at **registration** (22 vectors: `localhost.evil.com`, `evil.com@localhost`, `localhost@evil.com`, `[::1]`, `[::ffff:127.0.0.1]`, `0.0.0.0`, `127.127.127.127`, `127.0.0.1.nip.io`, `localtest.me`, uppercase, trailing dot, `%68`-encoding, port 80, fragment, query `next=`, backslash, `../` traversal, double slash, whitespace, tab, newline) | code lands on an attacker host → **ATO, Critical** |
| 2 | Does the **authorization endpoint** honour each registered URI in a live flow? | registration acceptance ≠ flow acceptance; only this proves theft |
| 3 | `post_logout_redirect_uris` — a **separate field**, routinely validated more loosely than `redirect_uris` | open redirect after logout |
| 4 | `end_session_endpoint` with a forged `id_token_hint` (`alg:none`, tampered, absent) + the `post_logout_redirect_uri` | logout CSRF / open redirect |
| 5 | Logout-CSRF: does `/session/end` auto-submit a form with no token? (PubNub's returned a 200 HTML page with `<form ... action="/oauth/session/end/confirm">` and an `xsrf` field) | forced logout |
| 6 | Token-endpoint `redirect_uri` mismatch — does the error differ from an invalid code? | an oracle for code brute-force |
| 7 | `client_id` substitution at the token endpoint (client B's id with client A's code) | cross-client code theft |
| 8 | Scope escalation at registration (`openid admin`, `openid account_id`) | privilege grant |
| 9 | Silent auth / pre-selection: `prompt=none`, `max_age=0`, `login_hint`, `acr_values`, `id_token_hint` | account enumeration |
| 10 | Brand/metadata impersonation (see 1l) | convincing phishing primitive |
| 11 | **Cross-finding chain**: does finding A supply the target list for finding B? | narrative upgrade, not a CVSS upgrade |

**Two rules that keep this honest:**

- **A registration-time acceptance is not a flow-time acceptance.** On PubNub, 12 of 22 `redirect_uri`
  vectors were accepted at `/oauth/reg`, but every one of them resolved to `localhost` in a real
  browser (userinfo tricks, path traversal and percent-encoding are parser quirks, not redirects). Only
  row 2 settles it. Do not report row 1 alone.
- **Say which rows failed, in the report.** "I attempted 11 escalation paths; these controls held" is
  what earns a Medium its payment and pre-empts the triager's first question. It also stops the next
  session re-running the same dead ends.

**On severity inflation.** If the chain does not complete, keep the CVSS at what you proved and add one
sentence inviting reassessment: *"If your triage considers unauthenticated brand impersonation on a
production IdP to raise the impact, I would welcome that reassessment."* That is how a Medium gets
upgraded by the vendor without you claiming a severity you cannot demonstrate — and claiming one you
cannot is what gets the report closed.


### 1n. A vendor's demo keyset is not a data-exposure finding — fingerprint provenance FIRST

Real-time/messaging SaaS vendors (PubNub, Ably, Pusher, GetStream, Stream, Firebase) ship
**sample keysets inside their own demo apps and docs**. The subscribe key MUST be public — that
is how the client SDK works — and a demo app has no PAM configured, so stored data reads back
anonymously *by design*. The vendor's scope almost always excludes demo/sandbox assets.

**Miss terukur (PubNub, 2026-10-31).** `moderation-dashboard.pubnub.com` shipped
`sub-c-a15882e8-…` in its JS bundle. `GET /v3/history/sub-key/<ks>/channel/default` returned 60
messages with sender UUIDs, no auth. Reported as "real user chat history", **CVSS 7.5 High,
sent**. The operator caught it with one question — *"Ini bukannya data public?"* Every available
signal had said demo keyset:

| sinyal | demo keyset | keyset nyata |
|---|---|---|
| format UUID / identifier | bentuk **default** SDK vendor (PubNub Chat: `user_<32hex>`) | skema milik pelanggan |
| envelope pesan / record | byte-for-byte envelope demo yang didokumentasikan SDK | field spesifik pelanggan |
| entropi isi | keyboard mash, emoji tunggal, `"x"`, `"test"` — playground publik | nama, kalimat, pertanyaan, repetisi antar-sesi |
| penamaan host + channel | `<fitur>-demo.<vendor>.com`, channel `default` dengan `type:"default"` | host menghadap pelanggan, nama channel bermakna |

**Rules**

1. **Fingerprint provenance before scoring any read.** A key from `<fitur>-demo.<vendor>.com`,
   `<vendor>.com/docs`, or a `main.*.chunk.js` bundle on a feature-showcase host is a sample key
   until proven otherwise.
2. **Read the vendor's OOS list for "demo", "sample", "sandbox", "test".** If present, a
   demo-keyset finding is out of scope regardless of severity.
3. **The reportable case is the keyset that is NOT a demo** — harvested from a real customer
   surface, whose identifiers and envelope do not match the SDK defaults, on a host the scope
   does not exclude. State the provenance of every keyset and say which you could not attribute.
4. **A public subscribe key never implies a public storage read on a real keyset** — but on a demo
   keyset it usually does, because the demo has no PAM. Absence of PAM is only interesting once
   provenance is established.
5. **Same discipline applies to any unauth read, not just keysets:** demo/auto-login instances,
   sample tenants, and feature-showcase hosts are all "the product working as designed" until you
   prove otherwise (see the `demo-admin.pubnub.com` pitfall above).

**What would have made the PubNub case reportable:** a keyset from a *customer* surface, data
whose UUID scheme and envelope do not match the SDK defaults, and a host the vendor's scope does
not exclude. All three were checkable in under a minute before the report went out.

**Rule 6 — the reportable case is the WRITE, not the read, and the asymmetry is the proof.** On the
same PubNub run the *write* primitive was reportable where the read was not, and the discriminator
was a configuration asymmetry rather than provenance:

| keyset | history read | publish | reading |
|---|---|---|---|
| `sub-c-a15882e8…` (moderation demo) | 200 readable | 200 Sent | demo keyset, no PAM anywhere → read is by design |
| `sub-c-95fe09e0…` | **403 blocked** | **200 Sent** | **PAM enforced for read, absent for write** |

The second row is the finding. When a keyset demonstrably *has* Access Manager configured — its
storage read refuses anonymous callers with 403 — but its publish path accepts them, the vendor has
made an authorisation decision and then failed to apply it to one operation. That is a bug, not a
demo default, and it survives the "public subscribe key" argument because the same key is already
gated for reads.

So: **before dismissing an unauth keyset read as by-design, test the write.** If read is gated and
write is not, you have a real integrity finding on the same asset you were about to drop.

### 1o. A session middleware that checks header PRESENCE is an auth bypass, not a hardening gap

The cheapest authentication bypass on an SPA-backed admin API is a middleware that treats *"a
value is present\"* as *\"a session is valid\"*. It is invisible to every scanner because the
unauthenticated response is a clean 401 and only a one-character header separates the two states.

**The probe.** For any endpoint that returns `401 Unauthorized`, re-send it with a single
non-empty character in every session-bearing header and cookie name you can find in the bundle:

```python
T = {"x-session-token": "a"}          # one character
st0, b0, _ = req(BASE + path)                      # 401
st1, b1, _ = req(BASE + path, hdr=T)               # 200 + data  <-- bypass
```

**Sweep the header AND cookie names — they are different code paths.** On PubNub (2026-10-31) a
34-name sweep found exactly two working channels:

| channel | result |
|---|---|
| `x-session-token: a` | **200 — bypass** |
| `Cookie: __Host-PN-2-pnAdminToken=a` | **200 — bypass** |
| `Authorization: Bearer a` / `Basic a` | 401 |
| `x-auth-token`, `x-pn-token`, `pnAdminToken`, `session`, `jwt`, `connect.sid`, … | 401 |

The cookie name and header name both came out of the SPA bundle's request layer (same grep that
produces the `secure:!0` map in §1g). **Read the bundle for the session channel before guessing.**

**Establish the boundary of the check with a value matrix.** The point is to prove it is a
presence test, not a weak validation:

| value | result |
|---|---|
| `""` (empty) | 401 — blocked |
| `" "` (space) | 401 — blocked |
| `"a"`, `"0"`, `"."`, `"p0ZZZGARBAGE"`, 300 chars, `{"a":1}`, `[1,2,3]` | **200 — bypass** |

Empty and whitespace are rejected; everything non-empty passes. That is `if (token)` where
`if (verify(token))` was intended, and the report writes itself.

**Then sweep every ID-bearing route for the differential, and be honest about what it buys.**
On PubNub the bypass changed the response on 8 of 96 routes — 3 returned data, 5 reached the
handler and were stopped by *its own* input validation (`400 accountId: is missing`). Two
consequences for the report:

1. **The 5 that reach a handler are the argument for defence-in-depth.** They prove the
   middleware is the only gate on those routes; any handler added later without its own authz
   check is exposed the same way. Report them as the blast radius, not as data leaks.
2. **Run the horizontal-IDOR negative control before claiming anything.** For each endpoint the
   bypass opens, vary the object/account ID and hash the responses:

```python
seen = {aid: (st, len(b), md5(b)) for aid in ["627651", "1", "2", "100", "999999", "0"]}
uniq = len({v[2] for v in seen.values()})
# uniq == 1  -> not account-scoped -> NO horizontal IDOR, say so
```

Identical bodies across every ID means the endpoint is not scoped to the caller, so there is no
IDOR to claim. Saying that explicitly is what stops the triager asking.

**Watch for the inverted oracle.** One endpoint answered `200` with *no* token and `500` with any
token — the opposite polarity. That is a broken code path, not an auth signal, and it is not a
finding on its own (see the Pitfalls entry on generic 500s). Record it as a negative.

### 1p. A publish key in a client bundle is an unauth WRITE primitive — test it, and get the body right

Real-time/messaging SaaS vendors ship the **publish** key in the front-end bundle next to the
subscribe key, because the browser needs it to send messages. That is a design decision, and it
means every such target has an unauthenticated write primitive sitting in public JavaScript. The
question is only whether the keyset behind it is gated.

**Harvest both keys from the bundle** — the publish key is the one that matters and it is the one
people forget to grep for:

```python
for a in assets:                       # /static/js/main.<hash>.chunk.js etc.
    js = get(host + a).decode("utf-8", "ignore")
    for m in re.finditer(r'(sub-c-[a-z0-9\-]{8,60}|pub-c-[a-z0-9\-]{8,60})', js):
        keys.setdefault(m.group(1), []).append(a)
# also: (?:publishKey|subscribeKey|publish_key|subscribe_key)["']?\s*[:=]\s*["']([a-z0-9\-]{8,60})["']
```

**Get the request shape right or you will record a false negative.** PubNub's publish endpoint
rejects a form-encoded `message=` field with `[0,"Invalid JSON",...]` and accepts a **raw JSON
body** with `[1,"Sent",...]`:

```python
# WRONG - reads as a 400 and looks like an auth failure
req(f"{P}/publish/{PUB}/{SUB}/0/default/0", "POST", {"message": json.dumps(payload)}, ctype="form")

# RIGHT
req(f"{P}/publish/{PUB}/{SUB}/0/default/0", "POST", {"text": "...", "type": "default"}, ctype="json")
# -> 200 [1,"Sent","17934167117245298"]
```

Two minutes of body-shape debugging is the difference between "publish is blocked" and a High.

**Then measure the four things that make it a finding:**

| dimension | how to measure | what it buys |
|---|---|---|
| channel scope | publish to `default`, `general`, `admin`, and a channel name you invent | arbitrary channel names accepted = no channel allowlist |
| keyset scope | repeat with every harvested keyset | more than one keyset = not a single misconfiguration |
| rate | 10 publishes, ~1 s apart | no rate limit is a separate reportable weakness |
| payload fidelity | publish `<img src=x onerror=alert(1)>`, a link, an extra JSON field, and a fake `SYSTEM:` notice; read each back | stored verbatim = content injection / stored-XSS precondition |

**Prove the write landed by reading it back** — that is the 3x validation, and it is what makes the
PoC self-contained for the triager. Then check the asymmetry against §1n rule 6: if the same
keyset's *history read* returns 403 while publish returns 200, the finding is an authorisation
omission and not a demo default.

**Controls that legitimately hold, so record them as negatives:** a 32 KB message returns `413`
from the balancer; history-delete returns `403` unless Storage Delete is enabled; publishing with
another user's UUID in the path succeeds but stores an empty `uuid`, so you cannot make a message
appear to come from a specific existing user. Each of those is a sentence that pre-empts a
triager question.

**Verify the write by matching the timetoken, not by grepping your marker.** The publish response
returns a timetoken — `[1,"Sent","17934179212294816"]`. Read the message back from history and
require `history.timetoken == publish.timetoken`. A text search alone can match an unrelated
message that happens to contain your marker; the timetoken match proves it is *the* message. On
PubNub the read-back also returned `uuid: ""` and `createdAt: null` while `text` and `type` were
stored verbatim — record that honestly rather than presenting the verification as cleaner than it
is. A triager who re-runs your PoC and sees the empty fields trusts the rest of the report more,
not less.

### 1q. A bundle that migrates build tooling is a NEW route map — re-harvest, don't reuse the old one

An SPA that switches bundler (CRA/webpack `/static/js/*` → Vite `/assets/*`, or a new content
hash on every chunk) has **re-emitted its entire route inventory**. The route list you harvested
last month is stale, and the new one is frequently *larger*.

On PubNub (2026-10-31) the admin dashboard moved from CRA to Vite and the fresh bundle carried
**148 distinct routes** against the 146 previously mapped — including whole families never
tested: `/api/usage/{summary,metrics,last24h,last24hStatsMAU,last24hStatsTXN,export,all}`,
`/api/faas`, `/api/illuminate/v1/oem`, `/api/subscription/audit/search`,
`/api/subscription/payment/webhook/*`, `/api/subscription/payment-method/webhook/*`,
`/api/subscription/batch`, `/api/subscription/price-allocation`,
`/api/subscription/pricing-exception`, `/api/billing-exceptions/{churn,churn-check,except-churn}`.

**Detect the migration in one request.** Grep the shell for the asset prefix rather than assuming
the old one — a regex keyed to `/static/js/` returns zero assets against a Vite host and silently
yields an empty route set:

```python
assets = sorted(set(re.findall(r'(?:src|href)="(/[^"]+\.js[^"]*)"', html)))
# CRA  -> /static/js/main.<hash>.chunk.js
# Vite -> /assets/index-<hash>.js, /assets/<name>-<hash>.js
```

Then re-run the §1g `secure:!0` / `.unsecured()` marker grep and the full no-token-vs-bypass
sweep over the new list. On PubNub all 45 previously-untested routes were closed (401/403/404),
which is a *publishable negative* — it converts "we never looked" into "we looked and here is the
matrix".

**Webhook routes deserve their own pass even when they look closed.** A webhook must accept
third-party callbacks, so it often has no session auth — but it should have a signature check.
Probe it in two stages:

1. **Find the valid event type first.** POST an unknown type and read the error:
   `400 {"message":"Invalid event type: probe"}` proves the request reached the handler and that
   the type is validated. Enumerate plausible types (`invoice.payment_succeeded`,
   `setup_intent.succeeded`, `charge.succeeded`, …).
2. **Then test the signature with a VALID type.** The polarity flips:
   `400 Invalid event type` → `401 {"message":"Webhook signature verification failed"}`. That
   second response is the control working. Sweep 18 bypass shapes against it — no header, empty
   header, `Stripe-Signature: t=1,v1=`, `X-Signature`, `X-Hub-Signature-256`, signature in body,
   signature in query, `Content-Type: text/plain`, form-encoded — and record that all 18 returned
   401. A webhook whose signature check holds is a strong negative and it is cheap to prove.

**A 500 on a route is not a finding, and it is not an IDOR either.** One auto-moderation metrics
route returned 500 for every dashboard ID and every parameter shape (array, object, nested JSON,
`__proto__`, 5000-char value, NUL, unicode, SQLi-ish, path traversal). No stack trace, no version,
no host — just a broken handler. File it through the product channel, not the bounty channel, and
do not spend the session trying to make it leak.

### 1r. A public config file is a KEY-TRIAGE exercise — separate client-side keys from server-side credentials

Every SPA host serves at least one unauthenticated configuration file, and it is routinely skipped because it "looks like static content". Probe the standard names on every host before concluding the perimeter is clean:

```
/config.json   /app-config.json   /env.json   /settings.json   /assets/config.json
/runtime-config.json   /appsettings.json   /configuration.json
```

Then **triage every credential by whether the front-end is supposed to hold it**, because that single distinction decides reportability:

| credential class | ships in client bundle by design? | unauth config-file exposure verdict |
|---|---|---|
| Segment / Amplitude / GA **write** key | **Yes** — documented as public, every browser gets it | Weak on its own; reportable when a *server-side* credential sits beside it |
| Sentry DSN | Yes | Informational at most |
| reCAPTCHA **site** key | Yes | Informational |
| Paddle/Stripe **publishable** id | Yes | Informational |
| **Any API key that is not prefixed `publishable`/`site`/`write`** — e.g. Inkeep, OpenAI, SendGrid, Twilio, internal service tokens | **No** — server-side only | **Reportable.** This is the finding. |
| Secret key (`sk_…`, `secret_key`, `seckey`) | No | Critical if present |

**Worked example (PubNub, 2026-10-31).** `GET https://admin.pubnub.com/config.json` with no auth returned:

```json
{"sentryEnvironment":"prd",
 "demo":{"627651":{"label":"Transport & Logistics"}, "632313":{"label":"Sports Media Entertainment"}},
 "inkeep":{"integrationId":"cm2lp5c3l00kvrt8yaczi5m3z","organizationId":"org_AoQMtSJNmMqt8U4m",
           "apiKey":"9d228670aadc10e93eb3f88314a894952a70fc26bec34f49"},
 "segment":{"writeKey":"RSzooYXYta360AkLvST610aA6zlGPwER"}}
```

**Verify liveness before scoring anything** — a key in a file is a lead, not a finding:

```python
# Segment: negative control first, then the real key
req("https://api.segment.io/v1/track", {"userId":"x","event":"y"})
# -> 400 {"success":false,"message":"An invalid write key was provided"}   <- proves the key is what works
AUTH = "Basic " + base64.b64encode((SEG_WRITE_KEY + ":").encode()).decode()
req("https://api.segment.io/v1/track", {"userId":"probe","event":"probe"}, hdr={"Authorization": AUTH})
# -> 200 {"success": true}                                                   <- live
```

The **negative control is mandatory**: without it you cannot distinguish "this key works" from "this endpoint accepts anything". Then sweep the full ingest surface (`/v1/track`, `/identify`, `/page`, `/screen`, `/group`, `/alias`, `/batch`) — all seven accepting the key is the blast-radius sentence.

For a non-Segment key (Inkeep here), one authenticated request that fails *past* auth is enough: `400 {"error":{"message":"Invalid model"}}` proves the key authenticated, because an invalid key returns 401/403 before the model layer is reached.

**Three things this file gave beyond the keys**, all worth a line in the report:
1. **The environment name** (`sentryEnvironment: "prd"`) confirms production.
2. **A demo-account map** — `627651` and `632313` labelled "Transport & Logistics" / "Sports Media Entertainment". This is the provenance evidence §1n demands, delivered for free: any account ID in that map is a demo account and its data is not a finding.
3. **Third-party integration IDs** — useful for scoping what else the vendor's stack touches.

**Score it on the server-side credential, not the client-side one.** Segment documents write keys as public, so leading with the Segment key invites a by-design close. Lead with the Inkeep key (a server-side credential that must never reach a browser), cite the Segment key as the *demonstrated impact* of the same exposure, and add one sentence inviting reassessment on the Segment portion if the triager considers client-side write keys by-design. That framing is what turns a config-file dump into a paid High.

### 1s. When signup is reCAPTCHA-Enterprise-gated, map the validation ORDER before conceding

reCAPTCHA Enterprise v3 is score-based and invisible — there is no puzzle to solve, only a reputation score the server checks. A headless or datacenter-IP browser scores low and the server answers `{"error":"Score too low","error_code":"BAD_CAPTCHA_RESPONSE"}`. That is a hard block, and it is not worth fighting for more than one session.

**What IS worth doing in that one session** is mapping the endpoint, because the map is reusable the moment any bypass appears:

1. **Find the signup endpoint from the bundle's request helper, not by guessing paths.** The base URL is frequently a variable: `QP={baseUrl:`${fm}/api`,credentials:"same-origin"}` with `fm=""` means the endpoint is `POST /api/users`, not `/users`. Grep for the fetch wrapper and resolve the template literal.
2. **Read the exact body shape** from the submit handler — `{email, first, last, password, contextData:{pageTitle,pagePath,pageUrl,pageReferrer,pageSearch,userAgent,signupSource}, "g-recaptcha-response":<token>, enterprise:true}` — plus the honeypot field (`contact-email`) that the client strips before sending.
3. **Map the server-side validation order** by removing one field at a time and reading which error comes back:

```
bad email + bad pw      -> "Email is not valid."
good email + bad pw     -> "Your password must be between 8 and 72 characters…"   <- captcha NOT checked
good email + no pw      -> "Please fill out your password."                        <- captcha NOT checked
good email + good pw    -> "Invalid response from Google reCAPTCHA"                <- captcha checked HERE
missing captcha field   -> "Please retry your registration and provide a captcha response."
```

**The order is email → password → captcha.** A weak password skips the captcha entirely — but that is an *error-message oracle*, not an account-creation bypass, and must be reported as such (or not at all). With a valid password the captcha holds.

4. **Confirm the block is real before spending the session on it.** Mint a genuine token in a real browser (`grecaptcha.enterprise.execute(sitekey, {action: undefined})` — the app passes no action string) and submit it from a headed Chrome with a warmed-up profile. If the answer is still `Score too low`, the IP/reputation gate is doing its job; record it as the blocker, name the specific gate, and move to the next surface. Do NOT write the attempts up as a workflow — they are dead ends with a clean termination point.

   Measured on PubNub (2026-10-31): a genuine 2 425-char token minted in a real browser still returned `{"code":400,"error":"Score too low","error_code":"BAD_CAPTCHA_RESPONSE"}`. The **same token submitted from Python** (no browser fingerprint) also returned `Score too low`, and a headed Chrome with `channel="chrome"`, a persistent profile, warm-up on google.com and pubnub.com, per-character typing and mouse movement before submit returned the same. Five engines, one answer. That is a reputation gate on the egress IP, not a token problem — stop there.

   One more trap worth naming: submitting the form from inside the browser is not the same as submitting the token. Intercepting `window.fetch` showed the app's own request carrying the token and still scoring too low, so the fingerprint — not the transport — is what is being judged.

5. **Read the captcha component's own code before assuming an action string.** The React component calls `executeRecaptcha(e.action)` where `e.action` is `undefined` because the register form renders it as `<_6e onVerify={g=>p("g-recaptcha-response",g)} />` with no `action` prop. So there is no per-action score to target; the score is global to the site key. Grep the component definition, not just the call site.

**The pivot that paid instead:** while mapping signup I swept the bundle for never-tested routes and found `/config.json` (§1r) plus three routes the session-token bypass newly opened. The blocker session produced a High finding on a *different* surface. That is the pattern — a blocked signup is a reason to widen the unauth sweep, not to grind the captcha.

### 1t. Microsoft 365 / Teams-app SaaS vendors — the `/api/settings` config dump + CSP subdomain leak

A whole class of bug-bounty target ships as one .NET/Kestrel admin center plus N React-SPA "app" subdomains (Calendar/Contact/KeePass/Gantt/… "Pro") that run inside Microsoft Teams via SSO. You cannot self-provision an account (signup is Microsoft-365-work-account SSO), so the entire payable surface is unauth. Four moves crack it without a token:

1. **`GET /api/settings` on EVERY app host returns the full client config in one request.** Witivio (2026-11) returned, per app: `clientId` (Azure AD app id), `tenantId` (the vendor's AAD tenant), `graphScopes` (per-app privilege — `Files.ReadWrite.All Sites.ReadWrite.All` for the KeePass/password-vault app), `adminCenterBaseUrl`, `adminCenterAppId`, `appInsightConnectionString` (InstrumentationKey + ApplicationId), `appSourceOfferId`, `trackingBaseUrl` (an internal `*.azurewebsites.net` host). The `graphScopes` field is your privilege map — an app whose scope is read/write-all is where a BOLA is Critical.

2. **The `Content-Security-Policy: frame-ancestors` header (Teams apps list every allowed embedding host) enumerates the ENTIRE app-suite subdomain set AND its backing Azure Web App names** — `calendar/ai-calendar/contact/remind/maps/parking/bookingroom/keepass/gantt/home.<target>` plus `tp-<app>-prd-preprod.azurewebsites.net`. crt.sh/subfinder miss these because they sit behind one shared App Service IP on a wildcard cert. One `curl -D -` on the admin login page is worth more than an hour of passive enum.

3. **The entitlement/licence endpoint is the auth-split oracle.** The SPA fetches `POST <adminCenterBaseUrl>/teams-app/data` with a form body `tenantId=&userId=&appId=` and **no Authorization header** — it returns the full subscription/entitlement JSON (`isUserPremium/isUserAdmin/isUserPlatinum`, `isTenantLicenceAvailable`, `subscriptionId`, `admins[]`, `tenantSuperAdmins[]`, `subscriptionOwner`). It is unauth BY DESIGN (the iframe checks the paywall pre-login), BUT it trusts client-supplied tenant/user identity with no check — a BOLA. **Prove it's a defect, not "public by design", by contrasting the siblings:** `POST /teams-app/users/licences` and `POST /teams-app/access-request` on the same host return `authentication_required`/401 unauth. The one endpoint that stays open while its siblings enforce auth is the finding. Severity is honest Medium unless you demonstrate a real customer tenant (the tenant-level `admins`/`subscriptionOwner` fields are AAD object IDs, discoverable from the victim domain via OIDC realm discovery).

4. **`GET /api/v1/graphtoken?scopesStr=<scopes>` (Bearer-gated) is a client-controlled Graph-token scope — a privilege-escalation lead** when the app's registered `graphScopes` is narrower than what the backend will mint. Flag it for authenticated follow-up.

**Bundle extraction tool — `jsluice urls` beats hand-rolled grep on a 4 MB minified React bundle.** `jsluice urls main.<hash>.js` emits one JSON object per string literal with `{url, queryParams, bodyParams, method, type}` where `type` is e.g. `sq.get` / `fq.instance.post` / `fetch`, giving you the full endpoint table *and* the method classifier in one shot (it surfaced `/graphtoken?scopesStr=`, `/teams-app/data`, `/feedback`, `/contacts/tenantId/` etc. that a path regex missed). Pair with `jsluice secrets`. Note there is no `--version` flag on this build — use the `urls` / `secrets` subcommands.

Full worked example (Witivio / Teams Pro / AI Desk Pro): `references/m365-teams-app-saas.md`.

### 1u. Environment-suffix subdomain triage — exposed test/staging/acceptance environments

For government / municipality / multi-tenant estates where the authenticated area is SSO- or
eID-gated (DigiD, eHerkenning, eIDAS, BankID) and you cannot self-provision an account, the
exposed non-production environment is a reliable Medium finding with a cheap recipe:

1. **Enumerate** subdomains (crt.sh `%25.<domain>` JSON, subfinder) and **probe** them all with
   `httpx -status-code -title -tech-detect`.
2. **Grep** for environment-suffixed hostnames: `-test`, `-staging`, `-acc`/`-acceptatie`,
   `-dev`, `-tst`, `test-`, `staging-`, `dev-`.
3. **Compare protection — the finding is the inconsistency.** Some non-prod hosts answer 403 or
   sit behind Google IAP while equivalent ones return 200. Measured (Gemeente Apeldoorn 2026-11):
   `uitvaartagenda-dev` = 403 (protected) but `uitvaartagenda-test` / `uitvaartagenda-staging` =
   200; `meldingen-acc` = 403 Google IAP but `test-e-loket` = 200. That contrast proves the org
   knows these should be gated and applied it unevenly.
4. **Prove it is a distinct LIVE env, not an alias/catch-all.** Compare tenant config/branding AND
   data between the test and prod hosts. Multi-tenant SaaS: `GET /api/assets/tenantSettings` returns
   test branding on the test host (e.g. `formsPortal.title="Djuma Formulieren"` vs production
   `"Gemeente Apeldoorn Formulieren"`); a public filters/dataset endpoint returns a small test
   dataset (14 records) vs prod (7578 + a "WOO verzoek" category). A host whose body is
   byte-identical to the apex is a wildcard catch-all, not an app (see 1c).
5. **Guard the by-design traps.** A static-file host with IIS directory listing serving public
   zoning/planning docs (`<dir>` pages) is public-by-law, not a finding. A demo/sandbox tenant is
   "product working as designed" (see 1n rule 5). Check the CVD policy for whether "test
   environment" is excluded — Apeldoorn's list excluded only "expired/inactive domains", so live
   test/staging envs carrying test data were in scope.
6. **Severity = Medium** (CVSS ~5.3 AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N). Frame the impact as:
   shared prod code reachable through a weaker-patched, less-monitored twin → a safe sandbox to
   discover and weaponise defects against the production citizen portals. Do NOT over-claim
   RCE/IDOR — that is a separate finding you have not demonstrated, and claiming it gets the
   report closed.

## Engagement discipline (banks / fintech / regulated targets)

- **"Nothing payable" is a claim you must EARN, and the operator will audit it.** On MONETA
  (2026-10-28) I reported "no findings" while my own writeup listed 13 of 18 enumerated paths as
  untested, 392 service×method combinations unprobed, and a `/documents/` surface I had named and
  then dropped. The user's response was blunt: *"kamu, dgn berbagai update, sebanyak itu skill n
  tools, cepat sekali menyerah nya"* — you have all these skills and tools, and you give up so fast.

  **The rule:** before writing any closing negative, re-read your own artifact and count what you
  wrote as "not yet tested". If that list is non-empty and the items are reachable without breaking
  scope or policy, the finding is not "absent" — *you* are not finished. Finish them, then write
  the negative.

  **A negative is only publishable with three things:**
  1. an explicit **tested** list (counts, not adjectives),
  2. an explicit **NOT tested** list where each item names the *specific gate* that blocks it
     (PowerAuth signature, KYC signup, no test account, out of scope) — never "didn't get to it",
  3. tool artefacts on disk for the classes you claim are clean.

  Partial coverage reported as complete is the single fastest way to be told you gave up early —
  and the operator is right to say so.
- **Read the vendor's out-of-scope list VERBATIM before the first probe, and carry it into the report.**
  Some CVD policies pre-declare the exact classes you would otherwise file. Zenya/Infoland
  (2026-10-30) states that an API route returning 200 without credentials when it serves the
  login/SAML flow, the support-access login, public report forms, card-file data or published portal
  content is *not* a vulnerability; that a different response for "no credentials" vs "invalid
  credentials" is *not* a vulnerability; and that public OpenAPI/Swagger, feature flags and version
  information are *not* a vulnerability. Their model is "an API request without credentials is
  handled as a built-in anonymous account that has no permissions; routes anonymous users are not
  meant to use refuse this account with 403". Fetch the policy page and extract that list first — it
  converts a session of false "broken-AC" reports into a session of real ones, and quoting the clause
  in the submission stops the triager rejecting on a technicality. Full recipe and the multi-tenant /
  spec-version / sanitizer techniques that pair with it: `api-authz-probe-ordering` §7.
- **Calibrate an enumeration oracle before trusting a zero.** 392 service×method probes returned
  zero hits on MONETA's JSONWS gateway, which looks like a dead end. It was only trustworthy after
  proving the oracle could still fire on a known case: `user/get-current-user -> 403` (service
  exists, auth required) vs `user/get-countries -> 404` (method not registered). **A sweep whose
  positive control never fires has measured nothing.** Always include one input whose answer you
  already know, and state it alongside the zero.
- **Volume is craft, not thoroughness.** A 7,000-template nuclei sweep against a bank issued 26,648
  requests in one run; a run labelled "curated" had actually loaded two whole CVE-year directories
  (4,221 connections). Both produced zero findings. Pick ~10 templates matched to the fingerprinted
  stack, cap the request count explicitly, and state in the ledger what was NOT run.
- **Never abort a crawler mid-run.** A katana run killed here had already emitted, in its tail, the only
  new endpoint family found after the initial report. Gate crawlers to in-scope hosts and cap depth
  instead of killing them.
- **Never mark a tool "N/A" without running it.** dalfox / arjun / graphql-cop were written off as N/A
  and later produced real results (arjun -> "no parameters discovered"; graphql -> proven absent across
  8 paths; ffuf on the marketing host -> a live search endpoint). "N/A" must be a conclusion you reached,
  not a shortcut you took.
- **Record where a lead dies.** Class, line, sink. A dead lead with a documented termination point is
  worth more than a live-looking one, and it stops the next run re-chasing it.
- **If the LEGITIMATE baseline also fails, you have no finding — you have an unusable oracle.** Before
  claiming a business-logic bypass (client-supplied `nodes`/`validityperiod`/`edition` trusted by the
  server), you must first send the *unmodified* values and get a success. On Genians (2026-10-27) the
  trial-provisioning action answered `"invalid access"` for both the manipulated request
  (`nodes=99999`, `validityperiod=3650`) **and** the honest one (`nodes=300`, no validity period) — which
  means the account was not eligible to provision at all, and "server ignores client input" cannot be
  distinguished from "server rejected me upstream". Two identical rejections prove nothing. Escalate the
  blocker (a role/plan that can actually create the object) instead of reporting; a triager who asks
  *"does it work with valid values?"* closes the report permanently.
- **Separate "the surface is gated" from "the surface is broken".** A single uniform denial message
  (`"invalid access"` / `"Wrong access"`) reused across unrelated handlers tells you a shared guard ran —
  not that each handler is vulnerable. Map which messages are *shared* and which are *per-handler* before
  reading meaning into any of them.
- **Chain leads at least 3x before declaring them dead, and never judge a lead in isolation.** The
  operator asks for this explicitly and repeatedly. In the worked example, five chains were walked to
  their sinks; one (a deep-link reaching a JS bridge) needed three independent confirmations across the
  full dex before it was genuinely dead. Scoring leads one at a time is the failure mode being corrected.
- **One finding = one submission = one draft.** Stage a separate Gmail draft per finding. When a finding is
  upgraded, delete the superseded draft and create the replacement so only one version of each exists -
  two drafts describing the same bug invites a duplicate/confused triage.
- **Carry the programme's ineligible clauses into the report.** If their policy excludes "errors thrown
  when using an invalid request" and "missing rate limit", say so in the submission. A triager surprised
  by a clause rejects the report; one warned in advance usually engages.
- **Correct your own ledger in public.** Two entries in the worked example were wrong (a sweep described
  as "killed at 1%" that had run to 77%, and a "curated" run that was not). Fixing them inside the
  artifact is what keeps the coverage claim auditable.

## Eligibility gate — run this BEFORE announcing any severity

Finding a bug and being *paid* for it are different questions, and this skill's scope is the
unauthenticated perimeter of regulated targets, where the second question bites hardest.

**A host being `*.target.com` proves namespace, not ownership, and not eligibility.** Two gates:

1. **Does the target operate it?** DNS + TLS certificate + IP.
2. **Does the policy admit it?** Many policies exclude third-party-operated subdomains by name.

```bash
openssl s_client -connect host.target.com:443 -servername host.target.com </dev/null \
  | openssl x509 -noout -subject    # CN naming ANOTHER domain == the target does not run that box
```

**Worked failure (Flux, 2026-10-27).** Two findings scored technical **High** and I told the
operator they were *"siap lapor"*:

| host | evidence |
|---|---|
| `awx.runonflux.com` | `subject=CN=topy.az`, IP `37.27.42.60`, rDNS `...clients.your-server.de`, body byte-identical to `topy.az` |
| `account.runonflux.com` | Shopify edge `23.227.38.74`, `shopify-y` meta, Shopify sign-in shell |

Their policy, verbatim: *"Subdomains operated by third parties (e.g: info.runonflux.com)"* and
*"Domains hosted by third parties (e.g.: Github, Gitlab, etc)"*. Both excluded, with examples the
same shape as my findings. Correct answer was "out of scope" — after I had already called them
ready. **Check eligibility before you announce a tier.**

Rules that follow:
- **TLS `CN` naming a different domain is dispositive** — the cert is issued to whoever controls the
  server, regardless of whose subdomain points at it.
- **Dangling-DNS / brand-impersonation on a subdomain = DNS-hygiene note, not a bounty finding** on
  any policy excluding third-party-operated hosts. At most a one-line good-faith note.
- **Never probe the third party's server.** The finding would be in the target's DNS, not their box.

### 1k. A dangling CNAME is NOT a takeover — check the provider's anti-reuse posture first

A CNAME sweep that finds `<host>.target.com -> <name>.<provider>dns.com` with **no A record** looks like a
guaranteed takeover. It usually is not, and the provider's own documentation is the disqualifier.

**The discriminator that settles it.** Query the provider's authoritative NS directly and compare the
three states:

```bash
dig @dns1.p05.nsone.net <name>.herokudns.com A +noall +comments   # status + AUTHORITY section
```

| state | meaning |
|---|---|
| `status: NXDOMAIN` | the name is unregistered — claimable |
| `status: NOERROR` + SOA in AUTHORITY (NODATA) | the record exists but has no address — provider-side state, usually NOT claimable |
| `status: NOERROR` + A record | live app, not dangling |

**Worked example (PubNub, 2026-10-31).** Two subdomains CNAME'd to `*.herokudns.com` with no A record,
and both returned Heroku's `404 "No such app"` page — textbook takeover signals. But `dig` against
`dns1.p05.nsone.net` returned **NOERROR with an SOA in AUTHORITY for all three**, including a random
never-registered control name. Identical answers for "deleted app" and "never existed" means the
response carries no claimability information. Heroku's own help page then confirmed it: *"On June 14,
2023, Heroku will start appending 12-character random identifiers to subdomains to prevent domains from
being taken over after renaming or deleting apps."*

**Rules:**
- **`No such app` is not proof of claimability.** A random name you just invented returns the same page.
  Run that control — it is the difference between a finding and a wasted report.
- **Check the provider's anti-reuse policy before building a PoC.** One `help.<provider>.com` fetch
  settles it; a takeover PoC against a hardened provider burns the session.
- **Certificate-transparency history is the supporting evidence, not the proof.** PubNub's two hosts had
  Let's Encrypt certs from Feb 2019 that stopped in Oct 2019 — the app was genuinely deleted seven years
  ago. That confirms the *dangling* half of the claim; it says nothing about whether the name is claimable
  now. Report the two halves separately or not at all.
- **A wildcard zone poisons the whole sweep.** `*.pubnub.com` resolves every nonsense name to
  `pubsub.pubnub.com`, so "no A record" on a specific host is only meaningful for hosts with an
  *explicit* CNAME. Test with a random name first and discard the wildcard's catch-all from the results.

## Severity honesty for availability findings
Regulated programmes usually define their reward interest as confidentiality/integrity of user data. An
unauthenticated resource-exhaustion finding is availability, so expect one of three outcomes and say so
up front: Low (paid), Hall-of-Fame-only (if it reads as "missing rate limit"), or ineligible (if it reads
as "error on invalid request"). Do not present it as High.

## Pitfalls
- **String-pool hits are not call sites.** A method name appearing in a dex string table
  (`getExternalStorageDirectory`) proves nothing. Verify with per-method analysis before treating it as
  a code path.
- **Check the vendor's own docs BEFORE escalating an unauthenticated write.** An unauth CRUD primitive
  on a keyset/tenant is only a finding if the product's documented security model says it should be
  gated. PubNub's App Context write (2026-10-31) looked like a Critical — full unauthenticated
  create/read/update/delete, verified 3x with fresh IDs and read-back — until the docs said:
  *"Access Manager is an optional add-on… Without it, any client that holds your subscribe and publish
  keys has unrestricted access to every resource on that keyset"* and *"App Context currently doesn't
  support authorization using Access Manager."* That makes the behaviour **by design**, not a bug. Two
  minutes of doc-reading would have saved the whole detour. Grep the vendor docs for the feature name
  plus "Access Manager" / "authorization" / "requires" before writing any report on an unauth write.
- **A "public" key embedded in a client bundle is not a leaked secret.** Publish/subscribe keys are
  meant to ship in front-end code; the question is only whether the *secret* key does. Check the field
  name explicitly (`secret_key`, `seckey`) and confirm it is absent or null in every response before
  claiming anything.
- **A client-side analytics write key is by design — but a config FILE is not the same as a client bundle, and the company it keeps decides the verdict.** Segment/Amplitude write keys are documented as public and ship in every browser, so a Segment key alone is not a finding. What makes the same exposure reportable is *what sits beside it*: on PubNub (2026-10-31) `/config.json` served the Segment write key **and** an Inkeep API key — a server-side credential with no `publishable`/`site`/`write` prefix, which must never reach a browser. Verify liveness with a mandatory negative control (no-auth request must fail `400 invalid write key`), sweep all seven Segment ingest endpoints to establish blast radius, then **lead the report with the server-side credential and cite the client-side key as demonstrated impact**. Add one sentence inviting reassessment on the client-side portion. Full triage table and the verification recipe: §1r.
- **A demo/auto-login instance is not an auth bypass.** `demo-admin.pubnub.com/api/me` returned a full
  user object with no credentials — but it was a read-only demo viewer hard-scoped to two demo account
  IDs, and sweeping 20 `owner_id` values confirmed only those two returned data. If the vendor's policy
  excludes "Demo Applications" and "Test Environments", the whole host is out of scope regardless of how
  exposed it looks.
- **A 422-before-401 on a parameterised route is validation ordering, not an auth bypass.** Confirm with
  complete parameters before reading anything into it (same rule as step 10).
- **A negative recorded in a reference file can go stale — re-verify before you rely on it.**
  `references/pubnub-2026-10-engagement.md` §7 records `/oauth/reg` as *"dynamic registration rejects
  non-allowlisted redirect_uris"*, which reads as "DCR is safe". The 2026-10-31 chain run found the
  opposite: the endpoint accepts **completely unauthenticated** registrations, issues
  `registration_access_token` to anonymous callers, has no rate limit, and performs **no verification of
  client identity metadata** (full PubNub branding accepted and persisted). The old note was true only
  about the `redirect_uris` sub-check. When a reference says "X is negative", check *which sub-property*
  was actually tested before treating the whole surface as closed.
- **Repeated `drafts().update()` on the same Gmail draft can silently destroy it.** During the PubNub
  run, F1 and F2 drafts vanished (404 on read) after several update cycles, while F3 survived. The
  reliable pattern is: build the full MIME message once (`multipart/mixed` → `multipart/alternative`
  text+html → `application/pdf`) and `drafts().create()` it; if a draft must be revised, **create a new
  one and delete the superseded draft** rather than updating in place. Always re-read every draft from
  `drafts().list()` before telling the operator a submission is staged.
- **jadx "finished with errors, count: N" on a large obfuscated APK is per-method failure, not missing
  classes.** All security-relevant classes were still produced. Targeted
  `jadx --single-class <fqn> --single-class-output X.java` is far cheaper and succeeded every time.
- **Windows Python cannot read files that curl.exe wrote to MSYS `/tmp`.** Write artifacts into the
  engagement directory with an absolute path instead.
- **A generic `{"error":"Internal server error"}` with no stack, version or host is not an information
  disclosure.** It is a broken feature; report it through the product channel, not the bounty channel.
- **Watch the polarity of a 200-vs-500 differential before calling it an auth signal.** An endpoint
  that answers `200` with *no* token and `500` with *any* token is a broken code path, not an
  authentication oracle — the polarity is inverted from a bypass and there is no data in either
  state. On PubNub `/api/roles/list` behaved exactly this way while `/api/roles/list` on the same
  host was simultaneously an open, unauthenticated enumeration. Test each endpoint's polarity
  individually; a 500 is never evidence of anything except that the handler ran.
- **A publish endpoint that answers `400 Invalid JSON` is a body-shape problem, not an auth
  failure.** Before recording "write is blocked", switch from form-encoded `message=<json>` to a
  raw JSON body. On PubNub that one change turned a 400 into `200 [1,"Sent",...]` and was the
  difference between a negative and a High.
- **Do not demonstrate worker-pool starvation with concurrent load against a production regulated
  target.** Reason the impact, measure the per-request cost, and say in the report that the starvation
  consequence was not demonstrated.
- **A slow response that plateaus is a server-side cap, not unbounded work.** When the timing stops
  scaling (20 000 -> 66 s, 20 000 000 -> 62 s), there is a timeout upstream. Report the plateau honestly;
  claiming "unbounded" when the server caps at ~70 s is the kind of detail a triager checks.
- **Variable timing on a repeat probe usually means caching, not a weak finding.** Re-run 3x and report
  the spread. On the worked example one parameter measured 23.79 / 14.27 / 7.39 s across three runs; the
  other was stable at 63-74 s. Lead the report with the stable one and disclose the spread on the other.

## Support files
- `references/metrics-oracle-route-discovery.md` — the delta-oracle recipe in full (calibration,
  reading `provider=`/`rule=`/`outcome=` labels as a route map, sibling-callback sweep, the
  per-controller auth-ordering classification that turns an inconsistency into a Low-Medium finding),
  the 4-provider forgery negative checklist, Next.js `_buildManifest.js` as a route dump, and the
  Playwright `ctx.route` recipe for driving an authenticated SPA. Read this the moment any host
  returns 200 on `/metrics`.
- `references/s3-bucket-lock-verification.md` — the 13-op bucket probe matrix, the
  object-level differential (known public object vs guessed vs prefix listing), the
  anonymous-write marker test with mandatory cleanup, the GCS equivalent, and the
  403-AccessDenied vs 404-NoSuchBucket distinction. Use whenever an in-scope page or API
  response names a storage bucket.
- `references/moneta-2026-10-engagement.md` - full worked example: complete endpoint inventory, TWO
  confirmed findings with their 3x measurements (unauthenticated resource exhaustion on two unbounded
  calculator parameters; internal hostname disclosure via a URI-resolution error), the deepdive round
  that upgraded the first one, and every hypothesis that died with the reason it died.
- `references/authentik-outpost-flow-testing.md` - driving an authentik-proxied estate unauthenticated:
  outpost allowlist mapping + path-bypass matrix, the flow-executor API recipe (form-encoded POST,
  `uidField`), the shadow-DOM browser fallback that actually works, OAuth redirect_uri + MCP DCR
  whitelist mapping, the waitlist/disposable-inbox playbook, and SPA-JS endpoint extraction when
  jsluice is unavailable.
- `references/github-source-pivot.md` - when live exploitation is CAPTCHA/Turnstile-blocked: find the
  target's public GitHub org, match repos to live subdomains, verify deployed==repo via build hash
  matching, grep for auth gaps (TODO Permissions, PUBLIC_ACCESS, direct find-by-ID), confirm routes
  live via 405/302/404 signatures, and report with source+endpoint as combined PoC. DuoCircle
  worked example: PUBLIC_ACCESS SSRF + 2 IDORs found entirely from source code review.
- `references/github-source-code-review.md` - the reusable technique companion to the pivot worked
  example: file-review priority table (security.yaml → authenticators → PUBLIC_ACCESS controllers →
  entities → repositories → forms → fixtures), Symfony ParamConverter field-mapping behaviour,
  nginx path-normalisation firewall-bypass pitfall, `/index.php/` front-controller prefix behaviour,
  factory-defaults-are-not-prod-creds pitfall, and the account-creation blocker matrix (Turnstile
  server-side validation, WHMCS registration-disabled, CLI-only user creation). Read this BEFORE
  the pivot file on a new target.
- `references/pubnub-2026-10-engagement.md` - worked example: 101-host estate sweep, SPA bundle
  reverse-engineering into 293 (method,path) pairs, the `secure:!0` auth-flag grep and the
  401-vs-403 auth-model map, deployed source-map recovery, the SSO domain oracle and its 3x
  validation, the live-telemetry health endpoint, the full negative matrix (SAML signature, XXE,
  Heroku takeover, App Context by-design write, OAuth state, payment webhook signature, MCP auth),
  and the reCAPTCHA-Enterprise signup blocker that left 255 authenticated routes untested.
- `references/oauth-dcr-impersonation.md` - the RFC 7591 dynamic-client-registration playbook:
  discovery-document-to-endpoint mapping, proving a minted client is functional (authorization
  endpoint + PAR), the rate-limit probe, client-metadata impersonation with a persistence read-back,
  the full 11-row chain-escalation battery with which rows held and which failed on PubNub, and the
  severity-honesty wording that gets a Medium paid without overclaiming. Read this the moment any
  host returns 200 on `/.well-known/openid-configuration` or on `POST /oauth/reg`.
- `references/oauth-control-verification.md` - the negative-control side of the DCR playbook: the
  redirect_uri ACCEPTANCE matrix (external HTTPS / localhost HTTP / wildcard `*.target` / arbitrary
  subdomain accepted, userinfo+empty rejected, and the honest Low/Med framing), the PKCE-enforcement
  test ("Missing required parameter: code_verifier" = held), the client_credentials grant-stripping
  test with token-endpoint confirmation, introspect/revoke auth checks, CORS allowlist check, DCR
  rate-limit (429), and the safe uniform-API-auth sweep (empty-body POST + non-existent-id DELETE to
  prove global auth middleware without side-effects). Read this when you need to prove which OAuth
  controls hold rather than just find the one that doesn't.
- `references/session-middleware-bypass-and-keyset-write.md` - the presence-check auth bypass
  (header/cookie channel matrix, value matrix proving `if (token)` vs `if (verify(token))`, the
  96-route differential sweep, the mandatory horizontal-IDOR negative control, the inverted-oracle
  trap), the unauth keyset WRITE primitive (key harvesting from the bundle, the raw-JSON-body
  shape trap that produces a false negative, channel/rate/payload-fidelity measurement, the
  read/write PAM asymmetry that makes it reportable where the read is not), unauth role-catalogue
  enumeration, and the full IDOR negative matrix. Read this when any endpoint returns 401 and you
  hold the SPA bundle, or when a messaging SaaS ships a publish key in front-end JavaScript.
- `references/public-config-key-triage-and-captcha-order.md` - the `/config.json` key-triage
  playbook (standard config-file name list, the client-side-vs-server-side credential table,
  the mandatory negative control, the seven-endpoint Segment blast-radius sweep, the
  Inkeep "fails past auth" liveness proof, the demo-account map as free provenance evidence, and
  the report framing that leads with the server-side credential), plus the reCAPTCHA-Enterprise
  signup validation-order map (bundle-resolved endpoint, exact body shape, honeypot field, the
  email→password→captcha ordering table, and why a weak password is an error oracle rather than
  a bypass). Read this the moment a host serves an unauthenticated config file, or when signup
  answers `Score too low`.
- `references/pubnub-2026-10-engagement.md` - the full worked example, now covering **all 8 submitted
  findings** with their message IDs (2 High, 5 Medium, 1 over-claimed), the second-round deep-dive
  (chain battery negatives, the complete IDOR negative matrix, the DataSync bypass-opened surface and
  why its 503-vs-404 split is NOT an existence oracle, the keyset write with timetoken verification,
  the role enumeration with its inverted-polarity trap, the `/config.json` disclosure, the CRA→Vite
  bundle migration, and the 18-shape webhook-signature negative), plus **§11 on the over-claim and
  §10 on the `send-draft` wrong-account trap**. Read this before any PubNub re-hunt, and read §11
  before scoring any unauthenticated read on a messaging SaaS.

- `references/m365-teams-app-saas.md` — Microsoft 365 / Teams-app SaaS vendor playbook: `/api/settings` one-request config dump (clientId/tenantId/graphScopes/adminCenterAppId), CSP `frame-ancestors` as the app-suite subdomain + backing-azurewebsites inventory, the `/teams-app/data` auth-split BOLA oracle (contrast with gated siblings), the `graphtoken?scopesStr=` scope-escalation lead, and `jsluice urls` for React-bundle endpoint extraction. Read when the target is a Teams/M365 SaaS with an AdminCenter + per-app SPA subdomains and SSO-gated signup.

## Absorbed playbooks (complete sub-packages under `references/`)
- `references/api-host-surface-mapping/PLAYBOOK.md` — host classification by role before 0C, the
  error-code route-existence oracle (no wordlist), pre-auth crash probes, Origin-header CORS crash,
  and the RFC1918-in-public-DNS sweep. Load it when the apex is marketing and the estate is
  api-*/app-* hosts.
- `references/js-spa-data-extraction/PLAYBOOK.md` — what to do when a 200 returns an empty shell:
  drive the SPA, read `window.*` config, `__NEXT_DATA__`/RSC payloads, and extract the API contract
  from bundles instead of guessing endpoints.

- `references/unauth-config-disclosure/PLAYBOOK.md` — when the perimeter leaks: asking the login page
  for its own endpoint list before any wordlist, Prometheus/exporter endpoints as architecture
  disclosure, mass-enumerate-then-triage, running a return visit as a DIFF, key triage, and ruling
  out cross-tenant access before claiming it (`references/`, `scripts/` included).
