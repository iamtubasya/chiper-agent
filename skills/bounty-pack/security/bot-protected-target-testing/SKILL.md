---
name: bot-protected-target-testing
description: "Use when a web target returns 403/429 for curl, wget, headless browsers or scanners (Akamai, Cloudflare, DataDome, PerimeterX, Imperva) — how to build a harness that actually gets through, how to extract the real API surface from minified front-end bundles, and how to stay inside VDP scope while doing it."
version: 1.0.0
metadata:
  hermes:
    tags: [security, bug-bounty, recon, waf, akamai, cloudflare, bot-management, graphql, recon]
    related_skills: [security-recon, web2-recon, exploit-cookbook, triage-validation]
---

# Testing targets behind commercial bot management

> Hard block: CF `error code: 1015` (17 B `text/plain`) = per-hostname rate-limit ban that outlives the
> session → `references/cloudflare-1015-rate-limit-ban.md`.

> App evicts you mid-flow (redirect to help/bail-out page kills `page.evaluate`)?
> Route-abort the eviction navigation to keep the JS context alive and keep testing the
> API — plus the `credentials:'include'` cookie pitfall, UI-block vs API-block
> diagnosis, and Wicket wizard walking: `references/keep-page-context-for-api-testing.md`

> ALTCHA proof-of-work solving, fingerprint-vs-IP anti-fraud diagnosis, and rotating-token
> session handling: `references/altcha-and-fingerprint-antiautomation.md`
>
> OAuth popup provider flows, invisible reCAPTCHA signup gates, and React wizard
> automation (popup handler, network-capture diagnosis, trusted-keyboard rules):
> `references/oauth-popup-and-invisible-captcha-signup.md`
>
> Captcha-gated signup (ProtonCAPTCHA jigsaw, hCaptcha drag) + Proton platform auth/API
> mechanics (per-app session UID, x-pm-appversion gating, session forks, wallet API):
> `references/proton-platform-notes.md`; reusable headed-browser manual-solve handoff:
> `templates/headed_captcha_handoff.py`
>
> Turnstile-walled flows (token never populates in headless OR headed Chromium), nuclei
> stalling on CF-challenged hosts (kill-and-go-manual rule), camoufox tab-create recovery,
> and the status-code-differential method for mapping an auth chain without credentials:
> `references/turnstile-and-scanner-stall-patterns.md`
>
> Cloudflare edge signatures — uniform-403 scanner blocks (ffuf default-UA fix), nuclei
> stalling, Turnstile automation walls, subzy takeover false positives on proxied hostnames,
> and edge-level smuggling 400s: `references/cf-bot-management-signatures.md`

Most large retail/finance/hosting estates sit behind a commercial bot manager.
Denied" from `curl` is **not** evidence the site is untestable — it is evidence you have not
yet presented a client the manager believes. This skill is the playbook for getting through,
and for getting the real attack surface out of the front end once you are.

Two failure modes produce a false "nothing to test here" report: (a) concluding the target is
unreachable because a scanner got 403, and (b) scanning only what a scanner can reach when the
interesting logic is behind a challenge-protected API.

## 1. Build a harness that passes

| Attempt | Typical result |
|---------|----------------|
| `curl` / `wget` with any UA | 403 "Access Denied" (Akamai) / JS challenge (Cloudflare) |
| `curl` with a full browser header set (Sec-Fetch-*, sec-ch-ua, Accept-Language) | still 403 — TLS/JA3 fingerprinting, not headers |
| Playwright/Puppeteer **headless** | 403 — headless is a signal in its own right |
| Playwright/Puppeteer **headless=False with `channel="chrome"`** (real installed Chrome) | **usually 200, full access** |

Working recipe (Python + Playwright):

    pw = sync_playwright().start()
    br = pw.chromium.launch(headless=False, channel="chrome",
                            args=["--disable-blink-features=AutomationControlled",
                                  "--no-sandbox", "--start-maximized"])
    ctx = br.new_context(viewport={"width": 1440, "height": 900}, user_agent=UA,
                         locale="en-AU", timezone_id="Australia/Sydney",
                         extra_http_headers={"Accept-Language": "en-AU,en;q=0.9"})

Match locale/timezone to the target's market when you know it — geo mismatch is itself a
scoring input on several products. Launching a real window is fine in an interactive session;
on a headless host pair it with a virtual display (`xvfb`) or accept manual confirmation.

## 2. Two different fetch paths — they do not behave the same

This is the non-obvious part and it costs hours if you miss it.

    ctx.request.get(url)     # Playwright's APIRequestContext
                            # -> shares cookies, but its own TLS/HTTP fingerprint
                            # -> frequently 403 even on the SAME origin the page loaded fine

    pg.evaluate("async (u) => (await fetch(u)).text()", url)
                            # fetch from INSIDE the page: real browser fingerprint
                            # -> succeeds where ctx.request fails

So: **use `ctx.request` for cheap authenticated same-origin enumeration, and drop to
`pg.evaluate` fetch the moment you hit 403.** Use `pg.evaluate` to download JS bundles too —
script `src` files fetched with `curl` or `ctx.request` frequently come back as an
"Access Denied" HTML page, which is a silent failure that looks like an empty bundle.

Same trap for `page.goto` of a sub-page: if it returns a challenge, the "page" you then parse
is the challenge, not the app. Always assert on the title/status before parsing.

## 2b. Akamai CPR on a GraphQL API: how the wall actually breaks (worked case)

Field case: `api.kmart.com.au/gateway/graphql` answered `429 {"cpr_chlge":"true"}` to
everything — including **the storefront's own XHR**, which is your proof the block is
egress/reputation, not your client. What worked, in order of reliability:

| Transport | Result |
|-----------|--------|
| `curl` / headless / `ctx.request` | 403 at the edge (TLS/JA3 + geo policy) |
| POST + `content-type: application/json` | 429 `cpr_chlge` (the rule matches this exact value) |
| POST + `content-type: application/json;charset=UTF-8` | **200** — the rule misses the parameterised value |
| GET + `content-type: application/json` | **200, and never challenged** — most reliable transport |

Two independent tricks, both worth trying on any Akamai-fronted GraphQL API:

1. **Content-type parameter bypass.** WAF/bot rules that match a header *value* often match
   it literally. `application/json;charset=UTF-8` (or `;charset=utf-8`, extra whitespace)
   reaches the same origin parser while skipping the signature.
2. **Move the operation to GET.** Akamai frequently applies the challenge to POST only.
   Apollo Server blocks naive GETs as CSRF ("This operation has been blocked as a potential
   Cross-Site Request Forgery") — but only for *simple* requests. Add a non-simple header
   (`content-type: application/json`, or `apollo-require-preflight: true`) and Apollo
   serves the query with no preflight problem. Bake the document into the URL:
   `?query=...&variables=<json>&operationName=...`

Also: `429 {"cpr_chlge":"true"}` is not one of the CORS-friendly responses — the browser
surfaces it as `TypeError: Failed to fetch`, which looks like a network error and wastes
time if you do not know to expect it. And challenge scripts can navigate your page
mid-run (`Execution context was destroyed`): make every harness step check
`location.href` and re-warm before retrying.

## 2c. Do not use Playwright's `connect_over_cdp` on sites with blob: shared workers

Modern Next.js sites spawn `blob:` shared workers. Playwright's driver asserts on the
attached target and the whole connection dies:

    targetInfo {"type":"shared_worker","url":"blob:https://...","canAccessOpener":false}
    -> BrowserType.connect_over_cdp: Connection closed while reading from the driver

The same failure kills long runs that launch their own browser and then navigate the app.
Fix: drive the existing real Chrome over **raw CDP over websocket** (no Playwright). A
~160-line `cdp.py` with `websocket-client` gives evaluate/navigate/cookies/click and is
immune to the worker event. Keep `Runtime.evaluate` + `awaitPromise: true` for in-page
`fetch()` work.

## 2d. Auth0/Akamai: the credential POST is the wall — and the sibling endpoint is the door

Worked case (kmart.com.au, 2026-09-29). The identity provider sits on its own host
(`auth.<target>` = Auth0 universal login) behind the same Akamai estate:

| Request | Result |
|---|---|
| GET /u/login/identifier, GET /u/signup | 200 — pages render fine |
| POST /u/login/identifier (no credentials in it) | **200** — you even reach the password step |
| POST /u/login/password (form, with credentials) | **403 "Access Denied"** (errors.edgesuite.net) |
| POST /u/signup (form, with credentials) | **403 "Access Denied"** |
| POST /co/authenticate (auth0.js, JSON) | 403 `unauthorized_client: Cross origin login not allowed` |
| POST /oauth/token (ROPС / password grant) | 400 `invalid_request: Redirection is not available` |
| **POST /dbconnections/signup (JSON)** | **200 — account created** |

Two transferable lessons:

1. **Find the sibling endpoint.** When one path of an operation is edge-blocked, look for the
   *same function on another path of the same service*. Auth0 still exposes
   `POST /dbconnections/signup` (`{client_id, email, password, connection}`) — a legacy path
   that the WAF rule did not cover. The ULP path was blocked; the functional twin was not.
   Harvest `client_id` from the app's `/authorize?...` redirect with a CDP Network capture
   (the sealed `state` hides it, the request URL does not).
2. **Only some methods/classes are covered.** Here plain GETs and credential-free POSTs
   passed; only *credential-bearing* POSTs under `/u/` were denied. Do not conclude
   "the whole host is blocked" from one 403 — enumerate method × path × payload-class.

**Diagnosing the deny:** read the `_abck` cookie for the target domain via CDP
`Network.getAllCookies`. A value containing `-1~-1~` means Bot Manager has **not** validated
that browser session — that is the state which produces 403s on high-risk POSTs. If `_abck`
is invalid, adding human-like behaviour does **not** fix it (verified: randomised
`Input.dispatchMouseEvent` paths + per-character `Input.dispatchKeyEvent` typing still got
403). Matching timezone/locale to the market did not fix it either. What actually matters is
the egress reputation — plan for a residential IP in the target's country, or have the
operator complete the login in their own browser and hand you the session (cookies /
localStorage). WARP/ datacentre exits get flagged; `warp-cli` on some builds has no
`set-custom-endpoint`, and rotating simply re-issues the same flagged address.

Also note the file-level trap from this session: a *sibling automation* on the machine can
hijack tabs in a shared debug browser (a tab being driven for target A turned out to be
navigated to target B's app mid-flow). Give each engagement its own Chrome
`--user-data-dir` **and its own debug port**, and verify the port is yours (a fresh profile
that already shows another project's tabs means the port belonged to someone else's Chrome).

## 2e. Form POST / document-navigation endpoints are invisible to XHR capture

Not every API call is an XHR. A classic order-tracking form submits as a **document navigation**,
and that breaks the two capture methods you would reach for first:

- an in-page `window.fetch` / `XMLHttpRequest` hook captures nothing, and
- a CDP `Network.requestWillBeSent` listener filtered to `type in (XHR, Fetch)` captures nothing
  either — the request arrives with `type == "Document"`,
- while `Network.getResponseBody` on the navigation returns nothing (the HTML is already gone).

Signature of this situation: the CDP log shows a `200` **response** for an endpoint URL with no
matching request entry, the in-page hook is empty, and the page re-renders with a validation or
error message. Do not conclude "no request was made".

Workaround that always works — **replicate the POST yourself and read the body**:

    POST <endpoint>                                  # form-urlencoded first
      -> 415 Unsupported Media Type = route exists, it wants JSON
    POST <endpoint>  content-type: application/json  {"orderId":"0000000000","email":"<test>"}
      -> 200 {"success":false,"data":{"error":{"code":"ERROR_ORDER_TRACKING","message":"..."}}}

Then vary exactly one field per request (unknown id / malformed email / empty body) and read the
answer as an oracle: a generic message for every unknown id means no enumeration oracle (a control
that works); field errors that name an internal form object (`orderSearchForm`) are low-grade info
disclosure; a 500 on an empty body is sloppy input handling. None of those are findings on their
own — they are calibration, and they are only visible because you replayed the call yourself.

Content-type tells you which transport a route wants: form-urlencoded → 415 means JSON, JSON →
`application/json;charset=UTF-8` is the CPR-dodging variant (section 2b), and XML → 403 usually
means the edge rule is content-type sensitive in both directions.

## 2f. DataDome: when BOTH `curl` and in-page `fetch()` are 403 — rewrite the app's own request

Verified on `www.vinted.com` (2026-10-01). DataDome blocks at a layer that section 2's advice does
not cover: the page loads fine, but **your** `fetch()` from inside it returns
`403 <!doctype html>` while the app's own XHR to the same origin returns 200.

| Transport | Result |
|---|---|
| `curl` (any UA/headers) | 403 HTML |
| Playwright `ctx.request` | 403 |
| `pg.evaluate("fetch('/api/v2/banners', {credentials:'include'})")` | **403 HTML** |
| Same fetch + copy of every header the app sends | 403 |
| `page.route('**/api/v2/banners')` → `route.continue_(url=target)` | **200 JSON** |

The discriminator is not headers you can copy — the bot manager instruments the *app's* request
path, so the only reliable transport is to let the app issue the request and rewrite its
destination in flight:

```python
async def route_handler(route):
    if "/api/v2/banners" in route.request.url and not box["status"]:
        await route.continue_(url=HOST + path)          # same headers/cookies, new path
        # POST: route.continue_(url=..., method="POST", post_data=body, headers={...})
async def resp_handler(resp):
    if resp.request.url == HOST + path and not box["status"]:
        box["status"], box["body"] = resp.status, await resp.text()
await pg.route("**/api/v2/banners", route_handler)
pg.on("response", lambda r: asyncio.create_task(resp_handler(r)))
await pg.goto(HOST, wait_until="domcontentloaded")      # app fires banners → our target answers
```

Find a request the app makes on *every* page load (a banners/telemetry call is ideal), pick a
fixed path + query as the trigger, and loop `page.goto` per path. Each query costs one page load
(~3-5 s); batching several endpoints per load works by matching request N → target N.

Two related facts worth having up front:

- **A "static" CSRF token is a real observation.** The token the bundle sets
  (`csrfTokenInterceptor` → `e.headers.set("X-CSRF-Token","<uuid>")`) was a literal baked into the
  minified chunk, identical for every visitor and every rebuild — grep the chunk, do not assume
  it is per-session.
- **Signup behind DataDome is CAPTCHA-gated, not merely fingerprinted.** The registration POST
  answers `403 {"url":"https://geo.captcha-delivery.com/captcha/?...&t=fe&..."}` from every
  transport above, including an app-originated route-rewritten POST. That challenge page exposes an
  **audio alternative** (`#captcha__audio__button`, six `.audio-captcha-inputs`, WAV at
  `https://dd.prod.captcha-delivery.com/audio/<date>/<lang>/<hash>.wav`, hash also inline as
  `captchaAudioChallenge`).
  **Working solve (verified end-to-end, 2026-10-01):**
  1. `page.goto(captcha_url)`; regex the `.wav` URL out of the HTML; download it.
  2. Transcribe with a **pre-loaded** faster-whisper model. Load the model *before* fetching the
     challenge — a cold `WhisperModel()` takes so long the challenge expires. Audio is
     `"Please type the numbers you hear."` followed by six digits; `base` is accurate, three
     models (base/small/tiny) voting makes it robust. Expect ~2 min end-to-end per attempt.
  3. Click `#captcha__audio__button`, play `.audio-captcha-play-button`, then type the digits
     one-per-field into the six `.audio-captcha-inputs` and click `.audio-captcha-submit-button`.
     Confirm the fields really hold the digits (`eval_on_selector_all(..., "e=>e.map(x=>x.value)")`)
     — `.fill()` alone does not always satisfy the widget.
  4. **The ticket comes back on `GET geo.captcha-delivery.com/captcha/check?cid=...`** as
     `{"cookie":"datadome=<value>; Max-Age=31536000; Domain=.vinted.com; Path=/; Secure..."}`.
     The browser will **not** apply that cookie (it arrives from a `captcha-delivery.com` origin
     for a `vinted.com` domain), so parse it out and graft it yourself:
     `ctx.add_cookies([{"name":"datadome","value":v,"domain":".vinted.com","path":"/","secure":True}])`.
     Then retry the registration request → **200**.
  The register call itself has to be the app's own request (route-rewritten); a hand-built POST
  still lands on the wall. This is the whole chain: rewrite → captcha → ASR → graft ticket → rewrite.

  **Expect the account to be auto-restricted anyway.** Vinted returned `200` with a real user id and
  then served `/main/banned` on the very next navigation:
  `GET api.www.vinted.com/restrictions/api/v1/user-restrictions` →
  `{"permitted_actions":[1,2],"restriction_type":2}`. A solved-CAPTCHA registration from a
  datacentre/VPN egress is exactly the pattern the target's own anti-fraud scores — plan for a
  residential IP, or have the operator sign up in their own browser and hand you the session
  (section 2d). Do **not** create a second account to route around the block; report the block and
  ask the program contact to unblock, which is what their own rules ask for.
- **Do not retry signup hot.** Repeated `POST /api/v2/users/validations` calls (the app fires one
  per keystroke) trip a real `429 {"code":106,"message":"Request rate limit exceeded"}`. Back off,
  record the block, and return later — hammering a registration endpoint is exactly the behaviour
  the program's rules prohibit.

**Also: not every API call terminates on the in-scope host.** The www.vintedgo.com tracking form
POSTs through the page then issues `GET https://carrier.vintedgo.com/public/v3/tracking_events/<n>`
— a host that appears in *no* scope list. Confirm which side of the boundary an XHR lands on
before you enumerate it; the in-scope front end calling it does not make the third host in scope.

## 2g. Real Chrome over CDP: the two flags that make it work, and the method-keyed wall

Real installed Chrome driven over raw CDP is the escalation target of §1/§2c/§3b. Two launch facts
waste a cycle each if you do not know them:

```bash
"/c/Program Files/Google/Chrome/Application/chrome.exe" \
  --remote-debugging-port=9222 --remote-allow-origins='*' \
  --user-data-dir="D:/data/hermes/chrome-cdp/profile" \
  --no-first-run --no-default-browser-check about:blank
```

- **`--remote-allow-origins=*` is mandatory for websocket clients.** Without it the CDP *HTTP*
  endpoints answer normally (`/json/version` is 200) and every WS connect dies at the handshake:
  `WebSocketBadStatusException: Handshake status 403 Forbidden … 'Rejected an incoming WebSocket
  connection from the http://127.0.0.1:9222 origin. Use the command line flag
  --remote-allow-origins=…'`. A 200 on `/json/version` does **not** mean the socket will open.
- **`/json/new` is `PUT`, not GET**, on Chrome 131: `GET /json/new?<url>` → `405 Method Not
  Allowed`. Use `urllib.request.Request(url, method='PUT')`. `/json/list` and `/json/version`
  stay GET.

**Confirm you are talking to the app, not the challenge.** After opening the tab, assert on
`document.title` / `body.innerText` before treating the page as the target. Verified discriminator
(lecturio.com, 2026-10-13): curl and in-page `fetch` from a non-browser client both got the
Cloudflare challenge, while real Chrome over CDP returned
`{"title":"Lecturio Login","body":"Login now. CONTINUE WITH GOOGLE … You are not registered yet? Sign up"}`
— the actual login page. That is the §3a-0 table's "client fingerprint" row resolving in the
favourable direction, and it is the moment to move the whole engagement into the browser.

When the stealth-browser tab-open returns `503` repeatedly **and** a full server restart does not
clear it, stop restarting it: the documented escalation is already real Chrome + CDP above
(§3b). `GET /health` reporting `browserConnected: true` is not a health signal either way (§ the
lazy-spawn note in the `camoufox` skill).

### The method-keyed POST wall (CloudFront, and the sibling host that is not behind it)

A CDN can deny an **HTTP method** estate-wide while serving GETs normally. Verified
(lecturio.com, 2026-10-13):

```
POST https://www.lecturio.com/account/register   -> 403
  "This distribution is not configured to allow the HTTP request method that was used
   for this request. The distribution supports only cachable requests."        (CloudFront body)
POST https://www.lecturio.com/<any path>          -> 403   (same body — it is the METHOD, not the path)
GET  https://www.lecturio.com/                   -> 200
POST https://app.lecturio.com/api/...            -> 404 JSON  (nginx sibling: method allowed)
```

Three transferable steps:

1. **Run a control POST on an arbitrary path of the same host.** If it also 403s with the
   distribution-configuration body, the block is method-scoped, not path- or payload-scoped — no
   amount of payload shaping will help.
2. **Do not rotate egress for a method-keyed wall.** Verified: WARP connected
   (`104.28.226.245`, `warp-cli status`) and the POST answered the **identical** 403 body. A
   method/config rule does not read your address, so an egress change is pure cost. (Contrast §3c,
   where a TLS/403 block *was* IP-scoped and rotating did fix it — the discriminator is whether a
   plain GET from the same client still succeeds.)
3. **Find the sibling host that is not behind that distribution.** Here the same product's login/signup
   lived on `app.<target>` (nginx, no CF/CloudFront), which **accepted POST** and answered a JSON
   `404` for unknown API paths. The registration path blocked on `www` was reachable on `app` — this
   is the §2d "sibling endpoint" rule at host granularity: enumerate the hosts, and test the method
   matrix per host instead of concluding the estate is closed.

## 2h. HTTP/2 / ALPN: when the whole Go scanner layer is structurally blocked

A third, independent discriminator — separate from header completeness (§2) and from the TLS
stack (§5 of `references/akamai-interstitial-and-header-differentials.md`). Measured on an
Akamai-fronted finance estate: the **same client, same full browser header set, only the
negotiated protocol changed** — HTTP/2 → `200` (811 KB body), HTTP/1.1 → `403 Access Denied`.

Two rules, do not conflate them:

1. **Header rule** — without `Sec-Fetch-Dest/Mode/Site` the request is denied regardless of
   protocol. The decisive signal is those three headers, **not** `Origin`/`Referer`/`Accept`/UA:
   a 7-combo differential showed full set minus `Sec-Fetch-*` → 403, re-added (`empty`/`cors`/
   `cross-site`) → 200, foreign `Origin: https://evil.example` → still 200.
2. **Protocol rule** — with those headers present an HTTP/1.1 client is *still* denied and an
   HTTP/2 client passes, **unless its TLS/HTTP2 fingerprint is itself denied — which is the case
   for Go's crypto/http stack.**

The expensive consequence: **`nuclei`, `ffuf`, `dalfox`, `katana` and `httpx` (Go) cannot reach
such hosts at all, and adding the headers does not help** (measured: Go httpx with `Sec-Fetch-*`
still 403). That is a structural coverage gap, not a negative result — record it
`SKIP_WITH_REASON` and cover the host with an HTTP/2 harness (`scripts/h2_browser_client.py`).
Never write "clean" for a surface no mandated scanner could reach.

- **Proxying does not rescue an HTTP/1.1 client.** mitmproxy with `--set http2=true` still
  returned 403 for an h1 client — it re-originates with the client's protocol. Change what the
  client negotiates; do not insert a proxy.
- **A transient host block masquerades as a broken recipe.** After a ~9-request burst at 0.6 s
  spacing the api host 403'd *everything* for a few minutes, including URLs and headers that had
  just returned 200. If a working recipe starts failing, check your own recent request rate
  before re-deriving it — otherwise you change variables that were never the cause.
- Matrix, header differential, deny-page reading and the coverage-gap wording:
  `references/http2-alpn-edge-discriminator.md`.

## 3. Rate discipline

Expect to be throttled after roughly 50–150 programmatic requests from one IP, even with a
good fingerprint. Symptoms: 403s that were 200s a minute ago, or `429` on endpoints the page
itself calls successfully.

- Slow down deliberately. It is also the VDP-appropriate thing to do.
- Batch: one page load often fires dozens of the requests you would otherwise make one by one.
- When throttled, **back off and say so** rather than retrying hot. A throttled engagement
  looks like an attack.
- If the API stays challenged, that is a **coverage gap** — document it with the exact response
  (`429 {"cpr_chlge":"true"}`) rather than quietly dropping the area.

### 3a-0. Distinguish EGRESS-scoped from FINGERPRINT-scoped before concluding anything
"The whole site is blocked" is the most expensive wrong conclusion in this class, and one browser load
settles it. Send the *same* request through curl and through a **real installed Chrome driven over CDP**
(not headless — see §1/§2c):

| curl | real Chrome (CDP) | conclusion | action |
|---|---|---|---|
| 429 / 403 | **200** | client fingerprint | fix the harness (§1) |
| 429 / 403 | **429 / 403** | **egress/IP-scoped** — your *address* is flagged, the target is healthy | check egress, do not re-engineer the client |

Verified 2026-10 (`cabify.com`): the apex answered `429` to curl **and** to a real Chrome 131 over CDP,
while `www.` / `api.` / 80+ other hosts on the same estate answered normally (`308`/`404`). So only the
apex host was refusing that address — the estate was wide open. The exit was a **consumer VPN
(Cloudflare WARP, `104.28.x.x`)** whose pool had already been flagged on a *previous* engagement, so the
first request was blocked before any behaviour of ours existed.

Two consequences worth internalising:

1. **A 429 on your very first request is a reputation signal, not feedback on your conduct.** Before
   blaming the scanner, check the egress: `warp-cli status` and `curl -s https://api.ipify.org`. A
   datacentre/VPN pool can arrive pre-flagged, and then *every* target in that class looks "hardened".
2. **Rotating egress is a machine-wide network change.** On a shared operator box, report the finding
   (`warp-cli disconnect` is the documented recovery) and let the operator decide — do not toggle their
   VPN mid-engagement to unblock yourself.

Also note the sibling shapes seen in the same session: the apex `429` came with a 564-byte nginx body
once and **0 bytes** the next time, and the same estate rate-limited a *different* host after only ~8
spaced requests. A per-host counter that low means the right response is fewer requests per host spread
across hosts — not a WAF-evasion project.

### 3.0 Read the published policy FIRST — a rate cap is a rule, not a throttle hint

Before the first automated request, open the program's policy/terms page and extract three
numbers. Getting this wrong can cost the whole engagement's reward, and it takes five minutes:

1. **The hard RPS cap, per host.** Some programs publish an explicit number instead of leaving
   it to judgement. Atmail's terms (§3.3, read 2026-09-30) state: *"automated tooling must not
   exceed **5 requests per second per host**"*. Under that cap, the `-rate 20` / `-t 40` values
   that are perfectly normal on a self-hosted VDP are **policy violations**, not merely rude.
   Set every tool explicitly: `ffuf -rate 5`, `gobuster --delay`, `nuclei -rl 5 -c 4`,
   `arjun --rate-limit 2`, `sqlmap --delay`. Note that `-t N` (threads) and RPS are different
   dials — a handful of threads against a slow endpoint can still exceed a low RPS cap.
2. **Whether unattended scanners are permitted at all.** Atmail's terms ban *"unattended scanners
   that fire untargeted payloads"* outright, and separately declare *"anything reported by
   passive or active automated scanners is ineligible"*. So a full-template nuclei sweep is
   **prohibited conduct whose output cannot ever be reported** — it is pure downside. Read the
   stats line, kill it, and replace it with targeted, manually-read probes.
3. **Whether there is a strike ladder.** Reaching it is an account-level consequence, not a
   scoring one. Atmail: 1 = warning, 2 = final warning + pending reports re-reviewed,
   3 = six-month ban with pending unpaid rewards forfeited, 4 = permanent ban.

Still send the identification header the policy names (`X-Bug-Bounty: <email>`) on **every**
request including scanner traffic - "a throttled engagement looks like an attack" is much worse
when the program cannot tell otherwise, and some programs dock up to 50% of a reward for
persistently unidentified traffic.

Two more policy clauses worth reading before you plan the work, because they change what is
worth testing:

- **"One root cause, one reward."** A fleet-wide exposure on 145 hosts is *one* bounty. Do not
  split it, and do not spend a whole round enumerating additional affected instances hoping for
  separate payouts - just list them inside the single report.
- **The ineligible list dominates the accepted-class table.** A CWE that appears on the accepted
  list can still be explicitly excluded elsewhere in the same document. Example: Atmail's table
  accepts CWE-307 (missing login rate limiting) but §9.1 says *"most rate-limiting issues"* are
  Informative ($0), alongside verbose errors, version disclosure, and enumeration without PII.
  Read both sections and predict the outcome **before** writing a report.

The general rule: the policy page is reconnaissance. Extract the accepted classes, the ineligible
classes, the rate cap, the prohibited-activity list and the rewrite-throttle for low-quality
reports, and write them into the engagement log so later rounds do not re-derive them.

**Estimate the blast radius BEFORE you fire a scanner.** A full-template run against a wide
subdomain list is a denial-of-service-scale event whether or not you intended one:

    2011 templates x 260 hosts = 1,279,200 planned requests   # real number from nuclei's own stats

Read the plan from the scanner's stderr stats line (`Templates | Hosts | RPS | Requests n/total`)
within the first minute. If the total is in the hundreds of thousands, kill it and switch to a
curated `priority_hosts.txt` (10-25 hosts that carry the actual product) with `-rl 3..5` and a
narrow tag set. Same rule applies when the brief says throttling is enforced across the whole
estate (common wording: "the fact that you can make 50 requests/minute does not mean we won't
block you"): keep single-digit RPS, and never report the rate limit itself as a finding - most
programs put rate-limit/bruteforce issues on non-auth endpoints explicitly out of scope.

**Supervise the process, not just the tool — a "stopped" scan can still be hitting the target.**
Long scans get started in the background, and stopping the job you launched does not always stop
the work: a scanner's own child processes can survive the kill and keep issuing requests while you
believe you have stood down. Verify before you move on to a different phase of the engagement:

    ps -W | grep -i <scanner>        # count the survivors; kill each PID, not just the job id

Three traps found the hard way while standing a scan series down (all cost time and one produced a
false "the series is dead" statement):

**Before killing a PID, read its command line — sibling engagements share the box.** Mid-audit a *second*
`nuclei` appeared next to mine writing to `D:/data/hermes/<other-target>/nuclei-www.txt`; `cat /proc/<pid>/cmdline
| tr '\0' ' '` showed a different `-u` target and output path — the operator's other job. Killing by image
name (`taskkill //IM nuclei.exe`) or by grepping the binary would have taken out an unrelated engagement, so
the "count the survivors, kill each" advice above becomes collateral damage without this check. Rule: only
touch PIDs whose command line names **your** output path or hosts file.

- **A multi-stage wrapper outlives the stage you kill.** A `run_scans.sh` that invokes the scanner
  three times in sequence is a *parent* bash process; killing the tool's binary — or killing the
  Hermes background job that launched it — leaves the wrapper alive, and it simply starts the next
  stage. Observed: stage 1 killed by hand and reported as stopped, then stages 2 and 3 ran
  unattended for another 20 minutes. Look for the wrapper (`pgrep -f run_scans.sh` /
  `tasklist | grep -i bash`) and kill the wrapper's PID, not just the child.
- **Killing by image name can hit the wrong stage.** `taskkill //IM sqlmap.exe //F` fired while a
  *later* stage had already spawned its own process → it terminated that stage instead of the one
  being chased. Kill by PID, and read the series log to see which invocation you actually ended
  (`t1 exit=1` / `t2 exit=1` / `[3/3] …` markers are the tell).
- **Liveness = log mtime, not process count.** `stat -c '%y' scan.log` twice ~30 s apart: still
  advancing means still running. Confirm the mtime has *stopped* before telling the operator a scan
  finished, then read the tool's own summary line from the tail of that file.

A **risk-2 run is not full coverage** of sqlmap's payload set, and the tool says so itself:
`skipping test 'OR boolean-based blind - WHERE or HAVING clause' because the risk (3) is higher than
the provided (2)`. If you used `--risk=2` for speed, either follow up with a `--risk=3
--technique=BU --text-only` pass or state in the report which test families were skipped — otherwise
"all tested parameters do not appear to be injectable" overclaims what was tested.

Two related traps seen in the same session, both of which cost real time:

- **Two writers, one log file.** Restarting a background job with `> scan.log` while the previous
  process is still alive gives you an interleaved file padded with NUL bytes — the old run writes
  at its own offset, so `grep` sees garbage and you misread the run as failed. Use a *fresh* log
  filename per run, and confirm the old PID is gone before starting the replacement.
- **A stale process silently doubles your request rate** against a rate-limited target. If stats
  look inconsistent with the flags you set, count the processes before blaming the target.

Also check the total the scanner intends to send *before* walking away: `1262 templates x 10 hosts`
at `-rl 6` planned **39 010** requests and ran for ~32 minutes, all while the interesting surface
had already been covered by targeted probes. A clean `Matched: 0` at low RPS is still worth having
as coverage evidence, but budget for it explicitly rather than discovering it mid-session.

## 3a. A burst block masquerades as a clean 403 result set — canary before you trust a scan

The nastiest false result in this class is not a missed finding, it is a *fabricated* one: a scan
that reports 403 for every single input, which reads like "the whole path space is protected" and
gets filed as evidence of hardening.

Signature to watch for: **one status code and one byte length repeated across essentially the whole
wordlist.** Real 403s vary. A block page does not:

    5152/5152 results:  403  118 bytes  7 lines  text/html   <- block page, not a result set

That happened on an nginx target at `ffuf -t 40`. The same paths answered normally moments later,
and `curl` was never affected. **Later re-testing showed the concurrency was incidental — the real
discriminator was ffuf's default User-Agent (see the UA matrix below). Check that first; it costs
one command and it is the more common cause.** Three checks, in order:

1. **Canary.** Request a path you already know returns 200 (a documented config/health endpoint).
   If the canary also 403s, the matrix is garbage — discard it, do not interpret it.
2. **Read the body, not the status.** `-mc all` plus an eyeball of one 403 body distinguishes
   nginx's `403 Forbidden` (118 b), an Akamai `Access Denied` page, and a real application 403.
3. **Compare the transport.** If `curl` works while the scanner does not, the discriminator is
   your client, not the target.

The usual triggers, and the fixes — **check in this order, cheapest first. A scanner's own default
User-Agent is the most common cause and it is not a rate problem at all.**

| Trigger | Fix |
|---|---|
| **The scanner's default `User-Agent`** — not concurrency | ffuf: `-H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"`. gobuster: `-a "<same>"`. See the UA matrix below |
| Concurrency (`-t 40`, nuclei default `-c 25`) | `-t 2 -rate 5` — **not `-rate 20`**: some programs publish a hard cap (Atmail: 5 req/s per host, §3.0) and exceeding it is a policy violation, not just rude. nuclei `-rl 5 -c 4` |
| A **new TLS connection per request** — a bare `requests.get()` in a loop trips the block even at ~3/s | `requests.Session()` + `HTTPAdapter(pool_connections=4, pool_maxsize=4)`, then an adaptive backoff (3 s, 7 s, 11 s) with a hard error print so you notice |
| Long wordlist x many prefixes planned at once | run it **in the background**, log to a file, and poll — do not hold a foreground call open for 6 minutes of blind requests |

### The UA matrix — run this before you blame concurrency

Verified case (atmail, 2026-09-30). A run at **`-t 2 -rate 8`** — i.e. nowhere near a burst —
still returned `403 / 118 bytes` for **every one of 5 176 wordlist entries**. The all-403 was
originally blamed on a 40-thread burst; that attribution was wrong. One matrix settled it, using
a path already known to answer 200:

```bash
U="https://<host>/<known-good-endpoint>"
for ua in "Fuzz Faster U Fool v2.1.0" "ffuf/2.1.0" "curl/8.4.0" \
          "Go-http-client/1.1" "python-requests/2.34.2" "Mozilla/5.0 (bug-bounty)"; do
  printf "  UA=%-34s -> " "$ua"
  curl -sk -m 15 -o /dev/null -w "HTTP %{http_code} %{size_download}b\n" -A "$ua" "$U"
  sleep 0.5
done
```

```
UA=Fuzz Faster U Fool v2.1.0   -> HTTP 403  118b     <- ffuf's DEFAULT
UA=ffuf/2.1.0                  -> HTTP 200 3780b
UA=curl/8.4.0                  -> HTTP 200 3780b
UA=Go-http-client/1.1          -> HTTP 200 3780b
UA=python-requests/2.34.2      -> HTTP 200 3780b
UA=Mozilla/5.0 (bug-bounty)    -> HTTP 200 3780b
```

The edge rule fingerprints the **literal string** `Fuzz Faster U Fool v2.1.0`; note that
`ffuf/2.1.0` passes, so it is not "ffuf is blocked", it is that one stock UA. Fix and re-run —
the corrected run is not merely cleaner, it is the run that **finds things**: on this target the
UA-overridden ffuf surfaced a third path to the same unauthenticated config object
(`/settings`, no `/api` prefix, on three hosts) that the custom enumerator had missed. Treat a
tooling fix as a reason to **re-run the enumeration**, not just the failing tool.

### The decisive one-command test: a CLEAN request from the scanner's own UA

Before you interpret any 403 flood as "the WAF is filtering my payloads", ask the engine's
fingerprint the question on its own. Verified on Quarterwise (Cloudflare front, 2026-09-30):
a sqlmap run reported **3,742 × 403** and its summary suggested `--tamper` / `--random-agent`
to get past the WAF — which invites the wrong conclusion that payloads are being filtered.

```bash
U="https://<host>/api/v1/categories?sourceType=uk-property"     # known-good, enum-valid value
curl -s -o /dev/null -w "%{http_code}\n" -A "sqlmap/1.9#stable (https://sqlmap.org)" "$U"   # -> 403
curl -s -o /dev/null -w "%{http_code}\n" -A "Mozilla/5.0 ... Chrome/139.0.0.0 Safari/537.36" "$U"  # -> 200
curl -s -o /dev/null -w "%{http_code}\n" -A "Mozilla/5.0 ..." "$U%2F**%2FAND%2F**%2F1%3D1"   # -> 422 (app, not edge)
```

The 403 was **the tool being fingerprinted**, not the payload being filtered: a *clean* request
with the sqlmap UA also 403s, and a *tampered* request with a browser UA reaches the app. Fix is
one flag — `--random-agent` (or `sqlmap -A "<browser UA>"`) — and the re-run logged **zero 403s**.
Same shape as the ffuf row above: the block is per-UA-string, and the tool's own defaults are the
cheapest thing to rule out first.

Two things to carry forward from this:

- **A scanner's verdict is only as good as its transport.** "sqlmap found nothing (N requests
  were 403)" is a transport artefact until you have proven the requests arrived. Once the UA is
  fixed the verdict becomes usable — and, better, you can state *why* the surface is closed.
- **Beating the WAF is not the same as finding an injection.** Fire the payloads by hand with a
  browser UA and read the application's own answer: here every parameter was shaped/enum
  validated with a named reason (`limit` whole number 1–200, `cursor` must be a transaction id,
  `from`/`to` real `YYYY-MM-DD`, `sourceType` one of three, `category` whitelisted per source
  type, a SQL-looking category rejected as `400 invalid_json`). "The app rejects it with a
  precise message" is a far stronger negative than "the WAF blocked me" or "the scanner was
  quiet" — and it is reportable as a control that works.

Two block pages, two different rules — read the byte length to tell them apart:

| Length | Trigger | Meaning |
|---|---|---|
| 118 b `403 Forbidden` (nginx) | the scanner's default UA | client-fingerprint rule |
| 520 b `403` | **sensitive-file path patterns** (`.env`, `.gitattributes`, `.bashrc`, `.htpasswd`, `awstats.conf`) | path-based rule; a UA change does not clear it |

**Vercel Security Checkpoint — `403` + ~34 KB HTML `<html lang="en" data-astro-cid-…>` / `<title>Vercel Security Checkpoint</title>` | tripped by attack-shaped payloads (XSS/SQLi probes in URL or body); it is **estate-wide and self-clearing**, not per-path.**

Two traps make this one expensive if you don't recognise it (verified across 5 Vercel hosts, 0.xyz, 2026-10):

- **One payload ends the session for the whole estate.** A single XSS probe against `app.0.xyz` put
  `app / ai / explorer / docs / dfx-claim` all behind the checkpoint within minutes — including endpoints
  that had answered `200` seconds earlier. It cleared on its own in **~15 min**. Canary before resuming: one
  benign GET with a browser UA. Healthy = the app's *own* JSON body (here `403 {"error":"Forbidden",
  "message":"Origin not allowed"}` is application logic, i.e. fine); still challenged = the 34 KB astro page.
  Back off and stay stopped for the full window — don't rotate egress, don't lower `-rl`, don't "just try
  one more".
- **It fabricates an entire result set.** A ffuf run that straddles the transition wrote `4719` results of
  which `4718` were `403 / 34.1xx bytes` — one status, one size, across the whole wordlist. Discard the file;
  it is a block page, not "these paths are protected". The same artefact shows up as `sens_*.json` where the
  *only* `200`s are the wordlist's own comment lines (`# Config files`, `# Source: …`) being fuzzed as paths —
  read the URLs, not just the status histogram.

A useful side effect: with a normal UA an unknown path returns a real `404`, so
`200 / 401 / 405 / 404` are trustworthy signals on the target and the wordlist results become
interpretable.

### When UA rotation does NOT clear it: escalate the whole header set, then the client stack

Verified 2026-10 on `app.vana.com` (Cloudflare front). The UA was a browser UA in every attempt,
and the matrix still looked like a hard wall until the transport changed:

| Transport | Result |
|---|---|
| plain `python requests.get()` (minimal headers) | **403 block page** for every path, including `/api/health` |
| `ffuf` default UA | 403, block page |
| `ffuf -H 'User-Agent: Mozilla/5.0 … Chrome/131'` | **still 403** — UA rotation alone changed nothing |
| `curl` with the *complete* browser header set | **200** on the same paths (`/api/health`, `/api/debug-auth`, `/api/app-creation/relayer-key`) |
| `katana` (headless-Chrome transport) | crawled the same host normally |

The tell was the byte size: `33957–33981` for **every** path, a spread of ~24 bytes explained
entirely by the reflected path/host. Near-identical size across a whole wordlist is a block page
even when your UA says Chrome — do not read it as "this path space is protected".

Escalation order once the canary confirms an edge block and UA alone does not clear it:

1. **Canary** a path you already know answers 200 (see above) and note the size.
2. **Add the rest of the header set on `curl`**, not just the UA — `Accept`,
   `Accept-Language`, `sec-ch-ua`, `sec-ch-ua-mobile`, `sec-ch-ua-platform`,
   `Sec-Fetch-Dest/Mode/Site`. The discriminator on this target was the full set / client stack,
   not the UA string.
3. **Change the client**, not the payload: `python requests` → `curl` → real Chrome over CDP
   (§1/§2). A client library's connection handling is itself a signal.
4. If a browser passes, route the actual testing through it (in-page `fetch()` per §2, or CDP),
   and keep the CLI client only for the paths it can reach.

Then **re-run** the enumeration that failed rather than dropping the surface: on this target the
blocked client had produced a fake "nothing here" result set, and the curl-header pass found live
unauthenticated endpoints immediately. Record the blocked tool as a coverage gap; never report the
403 as a control.

The block is transient and per-source, so recovery is a matter of seconds-to-minutes, not a
banned IP. Treat "the scanner says 403 everywhere" as a **tooling fault to disprove**, never as
a finding — and if you genuinely cannot get a clean run, report it as a coverage gap with the
canary result, not as a security control.

**Two opposite failure shapes, same root cause — know which one you are looking at.** A tool under
a burst block either *fabricates* results (ffuf: 5152/5152 × 403) or *self-aborts* (arjun prints
`Encountered an error: <host>` then `Skipped <url> due to errors`). The self-abort is easy to
misread as "the target is unreachable" or worse, to skip past silently. arjun's default parameter
wordlist is ~25k probes, so it trips the same block that a fuzzer does; re-running it with a small
explicit list fixes it:

```bash
arlist=$(mktemp)          # 30-40 names you actually suspect
printf '%s\n' webdomain domain tenant host realm server id account user email \
              app format debug full raw expand version locale > "$arlist"
arjun -u "$URL" -m GET -w "$arlist" -t 1 --rate-limit 2 -T 12 \
      --headers "X-Bug-Bounty: <you>"        # -> "No parameters were discovered."
```

Rule of thumb: when a scan tool takes a wordlist, assume the default list is too big for a
rate-limited target and pass your own. A clean `No parameters were discovered.` at `-t 1` is a
usable negative; `Skipped ... due to errors` is not a result at all and must be recorded as a
coverage gap (or fixed and re-run) rather than reported as "no parameters".

### 3a-1. The operator's rule: 429 means REHAT, not "route around it"

Operator instruction, verbatim (2026-10-12, mydays.de): ***"rehat aja jgn spam"***. A 429 / `Just a
moment…` is a signal to **stop and stay stopped for hours**, not a prompt to rotate the egress, raise
`-rl`, or spread the same request volume across hosts. Three consequences worth internalising:

1. **Verify the whole surface is actually quiet before declaring a rehat.** Stopping the tool you
   launched is not stopping the work (§3, process-supervision above): count the survivors
   (`ps -W | grep -iE 'nuclei|ffuf|katana|amass'`) and kill each, then prove it with one *single*
   liveness probe against a cheap endpoint. A leftover `amass` from four hours earlier was still
   running after the scanner was killed.
2. **Do not swap egress to dodge a per-host rate limit.** It is tempting to "just hit the same route
   from the other brand hostname" — but when both hostnames front the *same* backend estate, the
   target's counter sees one client and the attempt is simply more load. Verified: requests to
   `www.jochen-schweizer.de/...` and `b2b.jochen-schweizer.de/wp-json/...` resolve to the same
   Cloudflare-fronted origin group, so the rotation would have bought nothing.
3. **Resume later with an explicit request BUDGET, not with resolve.** When the 429 clears, do not
   pick up where you left off — write the probe as a small script with a hard cap and a
   stop-condition baked in, so the next 429 ends the run by itself:

```python
LIMIT = 12                                    # total requests, printed at the end as "used N/12"
if N[0] >= LIMIT: return None, None
...
if code.startswith("429") or "Just a moment" in body:
    print(f"[{code}] {path} -> RATE LIMITED, stopping"); N[0] = LIMIT   # self-terminate
    return code, body
time.sleep(3)                                 # 3-4 s between probes
```

Two traps inside this pattern, both hit in one sitting:

- **URL-prefix loss when you generalise a route list.** Reading routes out of a WordPress REST index
  gives you `/mcp/mcp-adapter-default-server`; the real URL is
  `https://host/wp-json/mcp/mcp-adapter-default-server`. Dropping the `/wp-json` prefix produced a
  `404` with a full HTML page and looked like *"the route does not exist"* for four endpoints — i.e.
  a fabricated negative that would have gone into the report as "not present". Always build the URL
  from the index's own `_links.self.href`, never by re-concatenating the path by hand.
- **A budget that is spent before the interesting probe.** Order the list most-valuable-first; a
  budget of 12 that opens with six route-table fetches leaves nothing for the actual handlers.

### 3a-1c. A long automated run degrading from minutes to hours = throttling in progress — stall detector + TCP preflight

Distinct from a single 429: here nothing ever says "rate limited", the run just gets slower until it is
effectively stopped. Measured 2026-10-17 (16-product orchestrator queue): payload-variant steps went
16 min → one step took 6 h → the host then stopped answering **at TCP level**
(`socket.create_connection((ip,443), timeout=8)` → timed out ×3, `httpx` silent) while *other hosts on the
same estate kept returning `200`* — i.e. a per-host drop at their edge, not a broken client. A second host
served a uniform `403 nginx` (behind Cloudflare) for **every** path including `/` and `/robots.txt` after
~3 h of probing, having been `200` earlier.

- **Preflight every target before launching a run:** `httpx -u <url> -silent -status-code -timeout 12` twice
  plus one TCP 443 connect. Either failing → record the product as `BLOCKED-throttled` with an ISO timestamp
  in a cooldown file and move to the next target (6 h cooldown worked as the standing number).
- **Stall detector while it runs:** `find <target-dir> -type f -mmin -45 | head -1` empty **and** the host no
  longer answers → kill the run (whole tree), mark `BLOCKED-throttled`, cooldown, next product. The
  orchestrator's own rework loop cannot recover from a dropped port — restarting is cheaper than grinding.
- **Attribute before you fix:** sibling hosts answering 200 → their per-host edge drop (stop knocking, do not
  rotate egress); *every* host failing → your egress (§3c).
- The block is a **working control**, never a finding: log it as operational state (host, window, the raw
  timeout/403 evidence) and list the coverage that went untested because of it.

### 3a-1b. Vercel Security Checkpoint: path-pattern first, estate-wide second, self-clears ~15 min

Three shapes in the order they appeared on one engagement (0.xyz, 2026-10-14), and the discriminator
for each:

1. **Path-pattern keyed, not estate-wide.** A `sensitive-files` wordlist returned `403` with a
   **~34 KB** body (`<html lang="en" data-astro-cid-…>`, `<title>Vercel Security Checkpoint</title>`)
   on every `.env` / `config.php` / `web.config` path, while `/` on the *same host* in the *same
   run* still answered `200` with its real byte length. So a `403` on one path is a WAF rule firing
   — a working control worth stating — and a `403` flood confined to one path family must NOT be
   read as "the estate blocked me" or as "these paths are protected" (they may not exist at all).
2. **Triggered by your own payloads, then estate-wide.** Reflective-XSS-shaped inputs on a JSON
   endpoint flipped *every* Vercel host in scope (app / ai / explorer / docs / dfx-claim) to the same
   `403 34 KB`, including a benign canary on a host that had been `200` minutes earlier. The block
   arrived from the scan, and it is per-estate: a run against host A takes host B down with it, so
   budget the whole Vercel group into one blast-radius decision.
3. **Self-clears in ~15 minutes.** Resume with exactly one canary request, never by restarting the
   scanner. Best canary is an endpoint whose *success body you know*:
   `curl -A "<browser UA>" https://host/api/known-good`.
   - body = the app's own JSON (here `403 {"error":"Forbidden","message":"Origin not allowed"}`) →
     the **application** is talking again, block cleared.
   - body = `<title>Vercel Security Checkpoint</title>` → still challenged.
   Note both states are HTTP `403`: **status code cannot distinguish them, the body can.** Prefer a
   canary whose success body is application-specific over any status-based check.

While challenged: kill the scanner **process tree** (`kill <pid>`, then `ps -W | grep -iE 'nuclei|ffuf|katana'`
to confirm survivors are gone — a wrapper outlives its child), stop the whole tool series, wait,
canary, then resume at low `-rl`. Record the window as a coverage gap with the exact response bytes.

**Two result-set artifacts seen alongside the same block — both must be discarded, not reported:**

- **`308` on a hidden path is trailing-slash normalisation, not existence.** `/.git/logs/` answering
  `308 Location: /.git/logs` looks like a live `.git` directory; it is Next.js stripping the slash.
  The sibling `/.git/HEAD` returns a genuine `404`. Always probe the no-slash sibling before believing
  any `308` — the same applies to `/.git/`, `/.env/`, `/.well-known/…/`.
- **One status + one byte length across a whole wordlist = block page.** Here: `4719` results,
  `4718` of them `403` at 34.1–34.2 KB. Per §3a that is a fabricated result set; it is neither
  "protected" nor "absent", and the run has to be re-done after the canary clears.

### 3a-2. A 500 that fires BEFORE the permission check is not a bypass

WordPress/WooCommerce hand you several shapes that read like one thing and mean another. The route
index is public by design; what matters is the status of each *handler*:

| Observation | Reading |
|---|---|
| `GET /wp-json/` returns the full route table, hundreds of routes | **normal WordPress**, not a finding, not a leak |
| handler → `401 {"code":"rest_forbidden"}` | permission check running, control works |
| handler → `403 {"code":"invalid_nonce"}` ("The request nonce is invalid") | nonce gate running, control works |
| handler → `500 {"code":"woocommerce_rest_cannot_view","message":"You must supply an array of options."}` | **argument validation ran before the permission callback** — an ordering artefact, NOT an auth bypass. Do not report it; do not escalate it to "missing authorisation" because the body mentions the permission constant |
| handler → `404 {"code":"rest_no_route"}` | route genuinely absent (or you dropped the `/wp-json` prefix — §3a-1) |
| `wp/v2/users` → `401 rest_user_cannot_view` | user enumeration closed |

The rule generalises: **when a 500 arrives where you expected a 401, read the message and ask which
code path produced it. Validation-before-permission is an ordering quirk; only proving that a
state-changing request *succeeded* without credentials makes it a finding.**

### 3a-3. Vercel Security Checkpoint — estate-wide, self-inflicted, self-clearing

Vercel's bot check presents as **403 with a ~34 KB HTML page** (`<title>Vercel Security Checkpoint</title>`,
body marked `data-astro-cid-…`). Two properties make it the nastiest false-result generator in this class:

- **A per-path wall and an estate-wide wall share one look.** A sensitive-file wordlist (`.env`,
  `config.php`, `web.config`) trips it *per path* while `/` still answers 200 — so the run looks
  like "every sensitive path is protected (403)". Then a single URL carrying an XSS payload
  (`<img src=x onerror=…>`) trips it **estate-wide**: app / api / ai / explorer / docs all 403 on
  everything, including the app's own benign endpoints. One status + ~34 KB on every path = block
  page; discard the run exactly as in §3a, and do not report "path protected".
- **It clears itself in ~10-20 minutes and the recovery test is ONE request.** Stop every scanner
  first (kill per PID — §3), wait, then send a single benign GET with a browser UA
  (`/api/announcements`, `/robots.txt`). Two answers: the app's own JSON/error body = recovered;
  the 34 KB Astro page = still challenged, wait again. No egress rotation, no hot retries, and
  never "verify" with a second payload — that is what earned the block.

Related Vercel/Next path-oracle artefact: `GET /<anything>/` answering
`308 Location: <same path minus the trailing slash>` is **Next.js trailing-slash normalisation,
not a file**. `/.git/logs/` produced exactly that during a fuzz run and 404'd on the follow-up.
Always follow the redirect before counting a hit, and note that a 200 on `/` next to 403s on
suspicious paths means the estate was NOT globally challenged at that moment — which is why the
per-path 403s from that window are equally untrustworthy.

> Sizes, timeline and the discard rule: `references/vercel-security-checkpoint.md`.

## 3b. Challenge-protected *forms*: Turnstile / CAPTCHA-gated signup

A bot manager doesn't only block fetches - it gates the interactive flow you need to become an
authenticated user. Detect before fighting: on the signup/login page look for a hidden
`input[name=cf-turnstile-response]` and a `challenges.cloudflare.com/turnstile/v0/api.js` script,
then check the submit button. One evaluate answers it:

    JSON.stringify({turnstile: typeof window.turnstile,
                    token_len: ((document.querySelector('input[name=cf-turnstile-response]')||{}).value||'').length,
                    disabled: [...document.querySelectorAll('button')].filter(b=>b.disabled).map(b=>b.innerText.trim())})

- Turnstile solved (real Chrome, managed mode) => `window.turnstile === "object"`, a ~700-char token
  appears by itself, the button enables. No clicking, no solver needed.
- Widget never initialises (no challenge iframe, `typeof window.turnstile === "undefined"`, button
  stuck disabled) => that browser profile will never pass. Do not burn time on it: launch a **real
  Chrome** with `--remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=<dedicated
  profile>` and drive the flow over CDP. Full driver plus React-form techniques live in the
  `browser-cdp-auth-audit` skill (`scripts/cdp.py`).
- The token expires - read it immediately before the submit click, and re-read after any reload.

### 3b-trigger. FIRST: the cheap test-key check (do this before building any harness)

Cloudflare publishes **always-pass testing keys**. If a developer left the test *secret*
(`1x0000000000000000000000000000000AA`) in production, `siteverify` returns success for **any** token —
the bot check is decorative and you never need a browser at all.

One request settles it: **send the server a garbage `captcha_token`.**

```
POST <gate>  {"captcha_token":"INVALID_TOKEN_FOR_TESTING", ...valid rest of schema...}
  -> 403 captcha_failed   = production secret is real; a minted token is the only way in (proceed below)
  -> 200 ok               = test secret in use = free bypass = FINDING
```

Verified on Euredas (2026-10-06): a bogus token returned `403 captcha_failed`, which *proved* the
server-side verification was genuine and told us not to waste effort looking for a shortcut. That is a
one-request answer to a question that otherwise costs an hour of harness work.

### 3b-noheadless. When you have no visible display: Camoufox, and use the SITE's own widget

Headless Chrome does **not** pass a managed Turnstile widget — the challenge simply times out
(`--virtual-time-budget` returns `TIMEOUT`, no token). If you cannot open a real visible window, use the
**Camoufox** stealth Firefox server instead of burning time on headless Chrome flags.

Start it (it is not a daemon — if `/tabs` fails with *Cannot connect to Camofox*, start it):

```bash
cd ~/camofox-browser && npm start        # run with background=true; poll GET /health until 200
# API: POST /tabs {userId,sessionKey,url} -> tabId ; GET /tabs/{id}/snapshot ; POST /tabs/{id}/evaluate
```

**Do not try to render Turnstile yourself.** Injecting `api.js` and calling `turnstile.render(el,
{sitekey})` from inside `/evaluate` **fails** — verified error: `page.evaluate: turnstile is not
defined`, even though the script was appended and awaited (CSP / isolated-world / load-timing). You do
not need it.

**Instead, trigger the page's OWN widget and read the token it writes.** The site already has a
correctly-configured widget; your job is only to make it appear:

```js
// 1. click the site's own CTA to open the gated form (find the hook in the bundle)
document.querySelector('[data-open-waitlist]').click()          // -> "clicked"
// 2. poll the input the widget fills in — this is the token, ready to use
(() => { const i = document.querySelector('input[name="cf-turnstile-response"]');
         return i && i.value ? i.value : 'pending'; })()
// -> 1.mdiSukmEWQPDBqnXGbuqjvqZEpEOVLQTuht-vnY6wYlEKFUh76xPTe-JAJZSgU_ExKrG
```

Keep the tab on the target's **own origin** — the token is hostname-bound. Then replay the submission
from `curl` with the real token and you control every field (schema, injection payloads, oracle probes)
instead of fighting a React form. Note the token is **single-use and ~300 s** — mint, then immediately
use it.

Two selector traps seen while doing this: a comma-joined selector with a nested quote
(`iframe[src*=challenges.cloudflare]`) throws `is not a valid selector` and kills the whole evaluate —
query one thing per call. And the widget may take several seconds to appear, so poll rather than
sleep-then-read once.

The target's own per-email signup lock ("sign-up using this email will be available again in one
hour") is anti-abuse, not a vuln: park the flow, schedule a resume, and keep the cookie jar alive.
If the flow offers "use authenticator app" instead of SMS, take it - you then hold the TOTP secret
and stop depending on the account owner's phone.

### 3b-geetest. Geetest v3 (`slide3`): the notch is threshold-ERODED — align CENTRES, not edges

Geetest is a third captcha family (common on Chinese-built wallets/fintechs and any Galoy-derived
stack). It is not a check-the-box widget: you drag a puzzle piece into a notch, and the widget posts
a server-validated `w` blob that encodes the piece's final x **and your whole mouse track**. Two
independent things must be right, and one of them is a silent trap.

**Step 0 — one request tells you whether you need to solve it at all.** Geetest's SDK ships a
"bypass / downtime mode": when `GET https://bypass.geetest.com/v1/bypass_status.php?gt=<gt>` does
**not** return `{"status":"success"}`, server-side validation falls through to the SDK's
`failValidate()`, which passes for **any non-empty** challenge/validate/seccode:

    gt = <from the site's own captcha-init call, e.g. POST /graphql {captchaCreateChallenge{result{id challengeCode}}}>
    curl -s "https://bypass.geetest.com/v1/bypass_status.php?gt=$gt"
      -> {"status":"success"}      = NORMAL mode, you must really solve it (proceed below)
      -> anything else / timeout   = decorative captcha; send junk and move on
    # corroborate on-site: the init response usually carries `failbackMode` (Galoy: success === 0)
    #   failbackMode:true  == decorative.   failbackMode:false + bypass "success" == real wall.

**The solve.** For `type=slide3` the widget draws three canvases; you need three:

| canvas | content |
|---|---|
| `.geetest_canvas_bg`     | background **with** the notch |
| `.geetest_canvas_fullbg` | background **without** the notch |
| `.geetest_canvas_slice`  | the puzzle piece, at its current x |

1. `notch = bbox(|bg − fullbg| > thr)`; `piece = bbox(alpha(slice) > 10)`.
2. **`thr` must be high.** At `thr=20..60` the mask bleeds into the piece's shadow and the "notch"
   measures ~170 px wide; at `thr=100..150` it collapses to the real ~45 px hole. Use
   `col > 0.40·col.max()` over the piece's row band, then the leftmost column above it.
3. **Align the piece's CENTRE to the notch's CENTRE.** This is the trap: the notch is a
   *threshold-eroded* silhouette (~45 px) of a ~52–59 px piece, so left-edge-to-left-edge lands you
   ~4–5 px too far right — enough to fail. Centring is immune to symmetric erosion.
4. Slider travel maps to piece travel **1:1** (calibrate once: move 40 px, re-read the slice bbox).
   Convert canvas→CSS with `cssWidth/canvasWidth` (≈0.993 on a 260 px canvas rendered at 258.14).
5. Drag with a **dense** track — 50–90 `mouse.move` steps over ~1 s, smoothstep
   accelerate/cruise/decelerate, ±1 px y jitter. A 5-step drag is rejected even when the final
   position is pixel-perfect.
6. **Close the loop while the button is still down**: re-read `alpha(slice)` every few steps and stop
   when the piece's centre equals the notch's centre. That removes all scale error.

Read the verdict by wrapping `initGeetest` (it is assigned dynamically, so use an
`Object.defineProperty` setter) and buffering `onSuccess`/`onFail`/`onError` into `window.__gt`.
`['FAIL']` after a pixel-perfect drag means the *trajectory* was rejected, not the position — that is
the signal to stop tuning the maths.

**When it still refuses: hand the drag to the operator.** It is a 1-second human action and strictly
cheaper than a third hour of trajectory tuning. Drive the flow to the widget, print
`CAPTCHA READY — drag the slider`, poll for the URL to leave the captcha route, then take the OTP from
the operator. Run it as a `background=true` job and poll — never close the browser context between
turns, and never let the wait loop time out before the operator has seen the window (launch
maximised; a hidden window is the #1 reason a handoff "fails").

**Check the delivery CHANNEL before assuming SMS.** Galoy/Blink gates signup by country: `+62`
(Indonesia) offers `TELEGRAM` and `WHATSAPP` only. Read `select[name=channel]`'s options after
picking the country. Typing a bare national number without the `+CC` prefix silently parses as the
wrong country (an `08…` number became `+82` South Korea) and returns *"Invalid phone number type.
Please use a mobile number."*

Full recipe, calibration maths and a runnable solver:
`references/geetest-v3-slider-solving.md` and `scripts/geetest_v3_slide_solve.py`.

## 3c. The block can escalate to the TLS layer — read the symptom, then rotate egress

A per-IP burst block does not always appear as 403. On a Hostinger-fronted WooCommerce target
(cardoma.shop, 2026-10-02) the block surfaced as **TLS handshake failure** with the HTTP status going
to `000`:

```
$ curl -sv https://TARGET/     # schannel: SEC_E_INTERNAL_ERROR -> a LOCAL Windows error, ignore it
$ echo | openssl s_client -connect TARGET:443 -servername TARGET
  ... tlsv1 alert internal error ... SSL alert number 80 ... Cipher is (NONE)   # SERVER-side alert
```

Attribute the alert correctly: `SEC_E_INTERNAL_ERROR` from curl's schannel is local noise, but
`openssl s_client` reporting **`SSL alert number 80` (internal_error)** is the peer refusing — trust
the second. And `www.<host>` answering `301`/`200` while the apex fails is the tell that the block is
**IP-scoped per edge**, not a dead site or a broken cert.

Confirm the shape before changing anything:
- the same request from a **different egress** returns 200 → it is your IP, not the target;
- the 403 body is an anti-bot interstitial (`Checking your browser before accessing. Just a moment…`,
  `Server: hcdn` / cf-mitigated), not an nginx/Akamai deny page;
- a single spaced-out request still 403s for several minutes → time-gated block, not a UA rule.

**Recovery: rotate the egress, do not abandon the engagement.** On this host the machine egressed via
Cloudflare WARP and WARP was the flagged address; disconnecting it restored the ISP IP and access
immediately:

```bash
warp-cli status                 # Connected, IP 104.28.x.y  (the flagged pool)
warp-cli disconnect; sleep 5
curl -s https://api.ipify.org   # the real ISP address
curl -sD - -o /dev/null -H "User-Agent: Mozilla/5.0 … Chrome/124.0 Safari/537.36" https://TARGET/robots.txt   # 200
```

Then **resume at low volume** (sections 3 / 3.0): the block was earned by `ffuf -t 25 -rate 80` plus a
nuclei sweep, and re-earning it costs the rest of the session. Practical order on a CDN-fronted target:
hand-probe the interesting routes first (curl/python, one at a time), keep `nuclei`/`ffuf` for last at
`-rl 3..5`, and remember a scanner killed by the block emits **no partial results** — an aborted scan is
a coverage gap, not a clean negative.

An anti-bot block is a **working control worth stating** in the report; the fact that a scanning burst
defeated *your* access is not a finding about the target.

**Third block shape — a 302 to the vendor's own anti-fraud help article.** Some estates do not reject,
they *redirect*: `302 -> https://support.<target>/hc/en-gb/articles/.../Preventing-fraud`, returning
the same Location for **every application host at once** (signup, login, own tenants, api, sandbox,
dev) while the marketing apex keeps answering 200. Onset was ~8 minutes of `nuclei -rl 20` against a
single host; it **self-cleared in ~15 minutes** and the operator's accounts and API tokens kept
working (only that egress was affected), so it is a temporary anti-abuse trip rather than the
"permanent IP block" the policy warns about. Measure it, do not assume either way — and do **not**
stack proxies to get back in while the redirect stands.

Running a scanner at all on a program that forbids it? Validate the toolchain on a **local** target
first (four tools here returned rc=0 while producing nothing because MSYS rewrote their
wordlist/template paths — the classic fabricated-coverage run), ship the volley as one env-gated,
scope-guarded, rate-limited script, and kill the **whole process tree** when the block appears: an
orphaned wrapper here kept scanning the next host after the launcher was killed. Full recipe, the
blast-radius check, and the honest cost/benefit of the run that produced zero findings:
`references/anti-fraud-redirect-and-gated-volley.md`.

## 3d. ISP-level interception: DNS hijack is layer 1, TCP interception is layer 2

Distinct from every block above: this is not the target defending itself, it is the **operator's
network** (mobile ISP / tethering) rewriting your traffic. Two layers, and only diagnosing the
first wastes an hour:

| layer | symptom | fix that actually works |
|---|---|---|
| 1. DNS hijack | resolver returns a foreign IP (`block.<isp>.co.id`, `static-<ip>.<isp>.net.id`) | DoH + `--host-resolver-rules` / `curl --resolve` — **sufficient** |
| 2. TCP interception | resolver is right, but the route to the real IP is hijacked, so TLS answers **as the target regardless of SNI** | DNS bypass is **NOT** enough — use a browser that validates the cert |

**Symptom that sends you down the wrong path:** plain `curl` → `http=000` in milliseconds, and
`curl --doh-url https://cloudflare-dns.com/dns-query` → **also** `000`. That is *not* "DoH is
broken" and *not* "the target is down" — DoH fixes the *name*, not the *route*. Confirm with
`curl --resolve host:443:<real-ip>`: if **that** works while plain curl fails, you have layer 2.

**Detection trick for layer 2 (the tell):** connect to the REAL IP but send a *foreign* SNI
(`example.com`). A correct server presents its own cert or resets; a transparent interceptor
presents the cert for **the SNI you asked for** — the certificate follows the SNI, not the IP:

```
html.duckduckgo.com  INTERCEPTED  ip=20.43.161.105
   own-SNI cert    : *.duckduckgo.com
   foreign-SNI cert: *.duckduckgo.com   ← follows SNI, not IP  => interceptor
```

Observed: MyRepublic ID (`158.140.186.3`, PTR `block.myrepublic.co.id`) = **layer 1 only**;
Telkomsel via Android hotspot (DNS `192.168.43.1` → `202.3.218.137`,
`static-202-3-218-137.telkomsel.net.id`) = **layer 1 + layer 2**, strictly harder.

**Practical consequences:**

- On a layer-2 network, `curl` (plain or `--doh-url`) is *designed to fail*. Do not use it to
  diagnose, and do not report its `000` as a target-side finding.
- The browser path works because it pins the resolved IP **and** validates the cert chain:
  Camoufox with Firefox-native DoH (`network.trr.mode=3`,
  `network.trr.uri=https://cloudflare-dns.com/dns-query`,
  `network.trr.bootstrapAddress=1.1.1.1`) succeeded where curl failed — 16–18 SERP results.
- **Never report a negative from such a network without naming the layer.** Empty tool output on
  an intercepted path is a silent failure, not "no findings".
- Script the check so it is one command, not an investigation. A self-contained diagnoser that
  prints both layers, a verdict, and an exit code (`0` clean / `1` DNS-only / `2` +interception)
  turns this into a preflight: run it first, and label the whole session with the result.

### 3d-1. ISP DNS sinkhole on a layer-1 network: patch `hosts`, and audit the evidence for silent failures

Layer-1 hijack has a **persistent** fix that the per-request workarounds above do not give you, and
skipping it costs an entire automated phase. Worked case (`toshi.bet`, 2026-10-18, MyRepublic ID):

```
nslookup toshi.bet
-> Server: gpon.net (fe80::1)
-> Name:    block.myrepublic.co.id
-> Address: 158.140.186.3
-> Aliases: toshi.bet
```

The resolver sinkholes the gambling domain to an ISP block page. `curl --resolve` and
`--host-resolver-rules` fix **the one client you type them on** — every scanner that reads system
DNS (nuclei, dalfox, sslscan, smuggler, subjack, ffuf, sqlmap, katana) still resolves to the
sinkhole and **fails silently**: rc=0, output full of `context deadline exceeded` /
`Client.Timeout exceeded` / `Could not open a connection to host`, which reads exactly like a
clean negative. It is not. It is **NO RESULT** and the phase must be re-run after the fix.

**The fix — patch `hosts` once, elevated, so every tool benefits:**

```powershell
# C:\...\Temp\patch_hosts.ps1  — run via Start-Process -Verb RunAs (needs admin)
$hosts = "$env:SystemRoot\System32\drivers\etc\hosts"
Copy-Item $hosts "$env:TEMP\hosts.backup.$(Get-Date -Format yyyyMMdd_HHmmss)" -Force
if (-not (Select-String -Path $hosts -Pattern "# TEMP: <target> audit" -Quiet)) {
  Add-Content -Path $hosts -Value @"
# TEMP: <target> audit - ISP DNS sinkhole bypass
104.26.1.49 <target>
104.26.1.49 www.<target>
172.64.147.209 docs.<target>
"@ -Encoding ASCII
}
```

Three traps, all hit in one session:

1. **`nslookup` keeps lying after the patch.** It still prints the sinkhole address (resolver
   cache). Verify with a **TCP connect / curl**, not a name lookup: `curl -s -o /dev/null -w
   "%{http_code} %{time_total}s" https://<target>/` returning `403` in 0.2 s is the proof; a
   timeout is not.
2. **Do not trust a scanner's "negative" on a sinkholed network.** Audit the evidence files
   before believing any phase result — grep for `context deadline exceeded|no such host|
   connection timed out|i/o timeout|dial tcp|not running|Unable to connect to host`. Any hit
   means that tool produced **no result**, and the run is void for that vector.
3. **A sinkhole fabricates findings as well as negatives.** dalfox reported "reflected" hits on
   ten parameters (`lang`, `page`, `username`, `callback`, …) — every one of them inside the
   **Cloudflare challenge page's own JS** (`cUPMDTk:"/?lang=<marker>&__cf_chl_tk=..."`,
   `cOgUHash`, `history.replaceState`). The marker was real, the sink was the challenge
   interstitial, not the app. Marker Discipline plus one `grep -c "<marker>"` on the response
   settles it: if the marker only appears next to `__cf_chl_tk`, it is the wall, not a finding.

**Re-run obligation:** after patching hosts, re-run every tool that failed — the corrected runs
are the coverage evidence. On this target the retry produced real results (sslscan connected and
reported TLS 1.0/1.1 enabled; smuggler completed all TECL/CLTE variants; subjack returned a real
verdict; nuclei ran 11,143 templates) where the first pass had produced nothing at all. Record
both runs in the coverage ledger: the failed one as `BLOCKED-dns-sinkhole`, the retry as the
actual result.

Detail, the evidence-audit script shape, and the challenge-reflection fingerprint:
`references/isp-dns-sinkhole-silent-scanner-failure.md`.

## 4. Extract the real API surface from the front end

This is how you get past the challenge-protected API: the front end tells you the schema.

**Next.js** — `__NEXT_DATA__` carries `runtimeConfig` (build-time public env), `buildId` and
`assetPrefix`. `runtimeConfig` names the internal API hosts outright:

    # api.kmart.com.au/gateway/graphql, /search/v1, /shopping-agent/v1/get-token,
    # a Constructor.io key, a Google Maps key, a Yotpo app key
    # => leads directly to the GraphQL endpoint and the unauthenticated token endpoint

**GraphQL documents** are in the minified bundle as tagged template literals. Operation names
survive minification, so regex them out:

    ops = re.findall(r'(?:query|mutation)\s+([A-Za-z_]\w{2,40})\s*(?:\([^)]*\))?\s*\{', js)
    # -> GetOrderForGuest, GetOrderForGuestByHash, createMyBag, updateMyBag, linkAccountsV2 …

The operation **names are the bug list**: anything like `GetXForGuest`, `getXByHash`,
`createX`, `linkX`, `updateX` is an unauthenticated-reachable or under-authenticated surface
until proven otherwise. Then read the full query text (they follow the name immediately) and
the fragment's field list — the field list tells you the blast radius (`shippingAddress {
firstName, lastName, address1, postalCode }` ⇒ PII, not a status string).

**Trace the call site**, not just the query definition, or you will misread the design. Example:
the query defined `getOrderByHash($hash: String!)`, but the call site was
`v = readQueryParam("hash"); query({hash: v})` — i.e. the URL parameter is passed straight
through, so the "secret" is whatever appears in the confirmation-email link. Same bundle also
showed the hash's origin (`crypto.randomUUID()` or a GA4 client id) which decided whether it
was guessable. **Deciding guessability needs a real artefact** — state that as a gap rather
than guessing.

**Other bundle wins:** unauthenticated token/broker endpoints, feature flags that gate
client-side only, fingerprint parameters used for real decisions, and the countries/envs the
build targets (a second country's API in the bundle is usually another jurisdiction — check
scope before touching it).

### ⛔ Tune the secret regex BEFORE you trust the hit count

A loose secret pattern is a false-positive factory, and a list that is 100 % noise is worse
than no list — it gets the whole category ignored. Verified 2026-10-12 on a GitBook docs
front-end: `(api[_-]?key|secret|token)["']?\s*[:=]\s*["']([A-Za-z0-9_\-]{24,})["']`
returned **90/90 false positives**, because minified JS is full of `token:`/`key:` object
literals whose values are identifiers, not credentials. Four fixes, apply all:

1. **Demand a real value shape.** `private_key` → `(?:0x)?[0-9a-fA-F]{64}` exactly;
   `infura_key`/`walletconnect` → `[0-9a-f]{32}`; `mnemonic` →
   `[a-z]{3,8}(?: [a-z]{3,8}){5,}` (space-separated words), not `[a-z ]{20,120}`.
2. **Add an entropy floor** for generic keys — require Shannon entropy ≥ 3.5 before accepting
   an `apiKey: "..."` match. Identifiers sit ~2.5–3.2; real keys are above.
3. **Scope the word list down** — `apikey|api_key|secret_key|access_token|auth_token`,
   never a bare `secret|token`.
4. **Skip bundled documentation atlases.** GitBook / Docusaurus / `_next/static/` /
   `/static/chunks/` / `[pagePath]` are ~99 % noise and also produce one match per locale
   variant of the same file. Filter them out of the crawl before scanning.

**Dedupe the input as well.** One `katana -jsl` run returned **1,769 candidate URLs that
collapsed to 1 real bundle** on that target — scanning the same chunk 40× inflates the count and
nothing else. After all five fixes the honest result was **0 hits**, which is a usable negative; the
90 was not. Report the tuned lane's output, never the naive run's.

**Sibling deployments hand you the production route map.** When the production host is the one
fighting you, crawl its *preview/branch* twins instead — they are usually the same app on a
different hostname with a different (often absent) edge policy, and their chunks embed the
production route names verbatim. Verified 2026-10: a CT-log + subfinder sweep of a Vercel-hosted
estate returned 232 `*.vercel.<target>` hosts (per-branch deploys plus production aliases of the
same Next.js apps); `katana -d 2 -jc` over ten of them produced 17,740 URLs that included the
production app's **complete route-chunk list** — `/api/admin/*`, `/api/debug-auth`, `/api/proxy`,
`/api/relay`, `/api/app-creation/relayer-key`, `/api/artifacts/[operationId]/[...artifactPath]`,
`/api/trusted-server` — i.e. exactly the surface the production host had been blocking. Two of the
resulting findings came straight off that list.

Method: enumerate the CDN's hostname pattern (CT logs, then passive DNS), fingerprint the whole
set with `httpx -sc -title -tech-detect` to group siblings, then crawl the group and diff the route
list. Treat the branch deploys as **route discovery, not targets** — they are staging copies, and
the reportable surface is the production host; confirm each harvested route there with the client
that actually passes.

**Then walk the auth state machine the bundle just handed you.** Path extraction gets you the
endpoint list; the *API client class* in the same chunk gets you the exact request bodies, the
field names per stage, and the response contract (`continuationToken`, `methods[]`, `action.type`).
That is what turns "there is a login here" into a scriptable sequence: first-step call → token →
credential call → second-factor call → refresh/revoke. It also surfaces the endpoints the UI only
reaches on rare paths (OTP, reissue, revoke) which no crawl will ever trigger. Recipe, the
worked case, and the field-name-trap table: `references/auth-flow-reconstruction.md`.

## 4b. Probing app routes without touching state, and not fooling yourself

Once the bundle gives you route literals (`/admin/entities/${id}`, `/api/${env}/entity_application/${id}`,
`/api/admin/funds/${id}/gas-costs/invoice`), most vendor policies forbid state changes — so you cannot fire a POST
to "see if the route exists". Three techniques keep you both productive and compliant:

**1. `OPTIONS` is a route-existence oracle with no side effects.**

```bash
curl -s -o /dev/null -w "%{http_code} allow=%header{allow}\n" -X OPTIONS "https://<host><path>"
# 405 with `allow: GET, HEAD`  -> the route EXISTS and serves those methods
# 200 with an empty `allow`    -> NOT evidence; SvelteKit and friends answer 200 to any unhandled OPTIONS
```

That single line turned a literal harvested from a bundle into a confirmed live route, and a subsequent **GET**
(never a state-changing verb) then told us it reached a handler without a credential. Report that shape as a
LEAD with the exact request/response and an explicit "no data, no side effect, no method sent" — a 500 instead of
401/403 is a hypothesis about auth ordering, not a finding.

**2. Catch-all SPAs manufacture whole false-positive sets — discriminate by size, then by diff.**
N unrelated paths returning 200 with near-identical sizes is one HTML shell, not N endpoints. Confirm with a
deliberately-random path:

```bash
for p in /.well-known/security.txt /.well-known/openid-configuration /zzz-not-a-real-path-98765; do
  curl -s -o /dev/null -w "%{http_code} %{size_download}\n" "https://<host>$p"; done
# 200 31498 / 200 31506 / 200 31495  +  identical <title>  => catch-all shell, NOT files
```

Seven `.well-known/*` "hits" collapsed to zero real files this way. Same trap applies to `/api`, `/app`, `/portal`,
`/onboarding`, `/signup`, `/forgot-password` on a SPA apex — if the byte length matches the shell, the route does
not exist. A real route returns a *different* page (`/signin` came back at 11,516 b against a 31,4xx b shell).

**3. Redirect target tells you WHICH layer enforces auth — and whether the apex is really an app.**
A marketing-looking apex is often the authenticated product. Compare redirects:

```
/admin                 -> 302 https://<tenant>.cloudflareaccess.com/cdn-cgi/access/login/...   (EDGE auth)
/dashboard             -> 303 https://<host>/signin?v=2&redirect_url=%2Fdashboard              (APP auth)
```

So `/admin` is edge-gated while `/dashboard` is served by the app itself and enforces auth in-app — meaning
`/signin`, `/dashboard` and the app API are reachable without the edge layer, and the `?v=2&redirect_url=`
parameter is a redirect surface worth testing.

**4. The CSP on a pre-auth page is a free inventory of the estate.** Fetch the signin page and read
`img-src` / `connect-src` / `frame-src`: on one target that single header enumerated `assets.dev`, `assets.staging`
and `assets.devddx` (a non-production host that appeared in no documentation) plus a live third-party RPC endpoint
which then answered `getHealth` 200. Cheap, passive, and it corroborated a host found independently by subfinder.

**5. Dedupe bundle URLs by host before mining.** `katana -d 2 -jc` yields thousands of lines that are the same
chunk under different casing/cache-busters (`[pagepath]` vs `[pagePath]`, `?dpl=...`). Strip the query, normalise
the bracket casing, then count per host — that is what reveals which hosts carry real app chunks versus docs or
marketing assets (1677 unique of 53k raw lines in one run).

## 4c. GitBook dangling CNAME — the takeover signal is a 307, not an error page

Found while working a Cloudflare-challenged target (`toshi.bet`, 2026-10-18). Every other
provider in the takeover family announces itself with an error string; GitBook does the opposite,
which is why it gets missed.

```
dig +short CNAME docs.<target>          -> a885c8b4e0-hosting.gitbook.io
curl -sI https://docs.<target>/         -> 307 Location: https://app.gitbook.com/o/<org>/sites/<site>/
curl -s  https://a885c8b4e0-hosting.gitbook.io/
   -> 200 "This domain is a CNAME target for DNS configuration only.
            No direct access is required. Please use your configured custom domain instead"
```

Three readings, in order:

1. **The CNAME target answering 200 proves the GitBook tenancy still exists** — the site was not
   deleted outright, so this is not the classic dangling-CNAME shape yet.
2. **A `307` into `app.gitbook.com/o/.../sites/...` instead of published content is the signal.**
   A healthy custom domain serves the docs; a redirect into the GitBook *app dashboard* means the
   site is **unpublished or deleted** while the custom-domain mapping is still attached.
3. **The redirect lands on the app, not on a 404** — so a status-code check reads as "healthy" and
   the candidate is silently dropped. Follow the redirect and read *where it went*.

Verification before reporting (Gate 0 applies): confirm the GitBook space is genuinely unclaimed
by attempting to claim it with a test account, and demonstrate control with a minimal marker page.
Until then this is a **candidate**, not a finding — and note that a takeover on a `docs.` subdomain
is Low/Informational on its own; run the five escalation chains in `hunt-subdomain` (OAuth
`redirect_uri`, parent-domain cookie scope, CSP `script-src`, CORS regex, email DNS) before
assigning severity.

Cross-reference: `hunt-subdomain` owns the takeover methodology and the chain table; this
subsection only records the GitBook-specific fingerprint, which is absent from the standard
`can-i-take-over-xyz` signature list.

## 5. Scope hygiene is part of the technique

**A backend host the in-scope front end calls is still out of scope if it is unlisted — and a *weaker*
WAF posture makes it more tempting, not more authorised.** Vinted's brief said "any/all subdomains not
listed above" are out of scope. During recon the app itself was seen calling two unlisted hosts whose
edge posture was completely different from the primary:

| Host | Transport that works |
|---|---|
| `www.vinted.com` (listed) | DataDome challenges everything except the app's own in-browser requests |
| `api.www.vinted.com`, `api.vinted.com` (unlisted) | **plain `curl` returns JSON — no bot management at all** |

It is an obvious pull to pivot an entire API test onto the host with no WAF. Don't: the authorisation
follows the *list*, not the reachability. The correct move is to write it into the coverage ledger as
"discovered via the in-scope front end; not tested — unlisted subdomain", tell the operator it exists
and let them decide, and keep testing the listed surface. Same rule for a tracking/lookup flow that
hands off mid-request: `www.vintedgo.com/<tracking>` POSTs through the page and then issues
`GET https://carrier.vintedgo.com/public/v3/tracking_events/<n>` — confirm which side of the boundary
an XHR lands on before you enumerate it.

A subdomain enum on a big estate reliably returns dev/uat/sit/nonprod/sandbox hosts. Read the
program's scope wording: "this is the production environment" means non-prod is **out**.
Enumerate passively (DNS, CT), classify, and do not send a single active request at them.
Same for another country's endpoints embedded in a build, and for mobile apps when the brief
excludes them. State the exclusions in your report — it is evidence of discipline, not a gap.

Do not use a third party as an oracle either: a credential minted by the target but belonging
to another vendor's ecosystem (e.g. a Google-format OAuth token) is out of that program's
scope. Document the finding, exercise it only against the target's own surfaces.

## 6. Header verification gotcha

`response.headers` in Playwright is filtered; security-header absence claims get overturned by
`response.all_headers()`. Always confirm a missing `Content-Security-Policy` /
`X-Frame-Options` with `all_headers()` before writing a word about it — and check whether an
API sibling host *does* send them, because "storefront has none, API has a full set" is a far
more actionable line than either fact alone.

## 7. Support files
- `references/cloudflare-challenge-and-local-dns-failure.md` — the Cloudflare managed-challenge
  playbook when the *machine's* routing is also broken: DoH for the IP set → `curl --resolve` to
  find a routable IP (a bare-IP curl dies on SNI mismatch) → read `Cf-Mitigated: challenge` to
  confirm the wall → SeleniumBase `Driver(uc=True)` with `--host-resolver-rules` → title-poll the
  challenge → fetch bundles **in-page** (curl gets the challenge HTML for every `/_next/static`
  chunk, which looks like a successful download) → go GENTLE on API subdomains (429 JSON = throttled).
  Includes the Windows/MSYS traps (`/tmp` missing, no path translation for native tools).
- `references/isp-dns-sinkhole-silent-scanner-failure.md` — when the ISP (not the target) sinkholes
  the domain to `block.<isp>.*`: the elevated `hosts` patch that fixes every scanner at once, why
  `nslookup` keeps lying afterwards (verify with a TCP connect), the evidence-grep that exposes a
  whole phase of rc=0 timeout output as **NO RESULT** rather than a negative, and the challenge-page
  reflection artefact that makes dalfox report ten fake XSS hits out of the interstitial's own JS.
  Read this before trusting any "clean" result from a network that blocks the target's category.
- `references/express-api-auth-and-cors-verification.md` — once the module graph has handed you a
  multi-host Express API estate: why `ACAO: *` **without** `ACAC: true` is not exploitable (and the
  three CORS shapes that separate real bugs from hygiene), why a `200` with an empty body next to
  `401` siblings is an observation rather than an auth bypass, the four-request JWT verifier probe
  (`alg:none` / `null` / garbage) and the two distinct error strings as an oracle, using Express's
  `Cannot GET /path` 404 echo to calibrate service-prefix namespaces, and the Imgix/CDN default
  page as a soft-404 to discard.
- `references/webpack-module-graph-api-map.md` — when a plain endpoint grep returns 9 paths and you
  need 23: chase `baseURL` → the numeric webpack module IDs (`r(38577)` → `r(85850)` → `r(77033)`)
  → the service→host switch → the request-descriptor config array. Yields hosts, methods, the auth
  model, the `{1}` IDOR placeholders, `RE_FETCH` consistency graphs, client-side rate-limit config,
  GraphQL siblings, and third-party hosts that are a scope question rather than a target.
- `references/anti-fraud-redirect-and-gated-volley.md` — the 302-to-help-centre block shape (host
  table, onset ~8 min, self-cleared ~15 min, accounts unaffected), the blast-radius +
  authenticated-still-works checks, the MSYS path trap that makes nuclei/ffuf/gobuster/sqlmap return
  rc=0 while scanning nothing, and the env-gated/scope-guarded/process-tree-supervised volley script
  pattern with the honest "zero findings" outcome.
- `references/datadome-harness.md` — the runnable DataDome harness: the transport matrix
  (curl / `ctx.request` / `pg.evaluate` fetch / route-rewrite), the ~30-line `query()` that
  rewrites an app-originated request, the trigger-selection traps, and the full audio-CAPTCHA
  solve (selectors, WAV URL, ASR step, ticket graft onto the target domain, and the account
  restriction that follows). Read this before writing a client for any DataDome-fronted target.
- `references/akamai-challenge-playbook.md` — symptom → cause → fix table, the harness
  patterns, and the coverage-gap language.
- `references/akamai-interstitial-and-header-differentials.md` — four walls that all look like
  "Access Denied" and their separate keys: the `bm-verify` interstitial POW solve (parse
  `var i`/`var j`, POST `/_sec/verify?provider=interstitial`, retry loop), the header-completeness
  differential (Sec-Fetch-*/sec-ch-ua; assets need Referer + `Sec-Fetch-Dest: script`), the
  warm-the-jar cookie chain (home → deep path), the per-host UA-class split (desktop403/mobile200
  on the same host), the Schannel-vs-WSL TLS-stack split, why a uniform-403 scanner run means
  rediscover from client code, and the WSL `/tmp` persistence rule (`/mnt/c` + `grep -a`).
- `references/frontend-api-surface-extraction.md` — bundle mining recipes: Next.js runtimeConfig,
  GraphQL operation extraction, call-site tracing, soft-404 detection, and a worked example.
- `references/auth-flow-reconstruction.md` — turn a pre-auth JS bundle into a scriptable login
  state machine: capture the first step, pull the route chunks, find the API client class, and
  the **field-name-trap table** (wrong key = a generic 500; missing `token` = an empty 400;
  a body-sent-but-`POST body can not be empty` = wrong content type). Includes the policy
  boundaries for OTP/reset endpoints.
- `scripts/spa_bundle_endpoint_miner.py` — runnable version of the extraction: fetch an entry
  page, follow its chunk manifest, regex endpoint-shaped literals and credential-shaped strings,
  and print a deduped candidate list (plus the client chunks worth grepping for field names).
  Every hit is a candidate — confirm each with one real request.
- `scripts/datadome_audio_captcha_solve.py` — runnable solver for the §2f signup wall: pulls the
  challenge WAV, transcribes the six digits with faster-whisper (three models voting), drives the
  audio widget, then tells you exactly how to graft the `datadome` ticket onto the target domain
  (the browser refuses it because it arrives from a `captcha-delivery.com` origin). Use it when you
  must create your own test account on a DataDome-gated program.
- `references/geetest-v3-slider-solving.md` — the §3b-geetest detail: the `bypass_status` /
  `failbackMode` decorative-captcha check, the bg-vs-fullbg notch extraction with the correct
  threshold band, the centre-not-edge alignment rule, the 1:1 slider calibration, the
  `initGeetest` verdict hook, and the operator-handoff pattern for when the trajectory is refused.
- `scripts/geetest_v3_slide_solve.py` — runnable solver + handoff driver: given an init callback
  that yields `(gt, challenge)`, it opens the real widget, computes the notch, drags in a closed
  loop, reports `window.__gt` verdict, and can fall back to waiting for a human to drag.
- `references/http2-alpn-edge-discriminator.md` — the third wall: the edge keys on the negotiated
  protocol, so HTTP/1.1 gets 403 where HTTP/2 gets 200 with identical headers, and the whole Go
  scanner layer (nuclei/ffuf/dalfox/katana/httpx) is blocked regardless of flags. Includes the
  A–F header differential proving `Sec-Fetch-*` is the decisive header (not Origin/Referer/Accept),
  the mitmproxy "proxying does not help" negative, the transient-block-that-looks-like-a-broken-
  recipe trap, and the honest coverage-gap wording for hosts no mandated scanner could reach.
- `references/cors-verification-readable-is-not-a-finding.md` — the verification discipline for
  CORS work on edge-blocked hosts: the raw client and the browser disagree in **both** directions.
  Covers the mirror-image of a multi-item-ACAO block — a reflect-any-origin + `ACAC: true` host
  where a real-Chrome credentialed read **succeeds** and is still not a finding because the host
  serves only a static SPA shell, mounts no API, and sets no session cookie; the third header
  shape (a *fixed* non-reflecting `ACAO`, which is neither reflection nor wildcard); the
  two-origin sweep that separates the shapes; and why a `sandbox` iframe cannot be used as a
  null-origin emitter from a served page.
- `scripts/cors_origin_sweep.py` — runnable two-origin sweep: classifies every reachable host as
  REFLECTS-EVIL / MULTI-ITEM / WILDCARD / FIXED-ALLOWLIST / none and prints the leads that need
  browser verification. A lead is not a finding until the body is sensitive and the host can set
  a session.
- `scripts/h2_browser_client.py` — the harness for those hosts: python httpx with `http2=True`,
  the full browser header set (document-class or API-class Sec-Fetch values via `--api`), the
  programme's identification header, GET and JSON POST, delayed sequential requests. A probe
  harness, not a fuzzer — keep the delay and keep the request count in the coverage ledger.

## Absorbed playbooks (complete sub-packages under `references/`)
- `references/waf-stateful-bypass/PLAYBOOK.md` — when every path is blocked: classify WHICH layer is
  blocking (WAF vs rate-limit vs bot manager) before attempting any bypass, then the low-and-slow
  stateful origin crawl, its support files, and the 2026 dork sweep.
