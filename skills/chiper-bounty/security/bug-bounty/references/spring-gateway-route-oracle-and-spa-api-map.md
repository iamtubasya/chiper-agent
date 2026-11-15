# Spring "openapi" gateway + SPA bundle: mapping a bank/fintech API without guessing

Verified on moneta.cz (2026-10-26): React SPA on `ib.moneta.cz`, Spring Boot gateway at `/openapi`,
F5 ASM in front, Liferay DXP 7.4 marketing site on `www`. Same shape appears across EU banking/fintech.

## 1. Config before bundle

A CRA-style SPA usually ships `<host>/config.json` next to `index.html` (loaded synchronously in
`config-init.js`). It is the cheapest surface map you will get:

- `API_URL: "/openapi"` → the real API base (the SPA's own `main.<hash>.js` also embeds
  `.replace("/openapi","")` calls, confirming the gateway prefix).
- `FEATURE_FLAGS: {...}` → a flat roadmap of live product surface (moneta leaked ~70: QR_LOGIN,
  BULK_PAYMENT, INVESTMENTS, SME_MULTI_LENDING, SCREENSHARING_ENABLED, HASH_PASSWORDS, SENTRY,
  TRANSACTIONS_TAMPER_DETECTION_ENABLED …). Use it to pick which flows are worth attacking, not as
  a finding.
- `OLD_IB_LOGIN_PAGE`, `ASSISTED_CHAT_URL`, external hosts appear here too — check each against scope.

## 2. Bundle → API paths

Minified React bundles call the API through one helper. Regex the call sites, not all string literals:

```
hD\)\("/[^"]{2,90}"          # redux-saga style:  (0,X.hD)("/account/envelope/list")
(?:get|post|put|delete)\("/  # axios style
```

moneta: 1840 quoted `/…` strings but only **364 real gateway calls**; the rest were client routes,
i18n keys and PDF-viewer internals. Split them: client-side routes (`/accounts/secondCurrentAccount/…`,
`/application/express/…`) are navigation, not API — only the ones the request helper takes matter.

## 3. The route-existence oracle (the high-value part)

The gateway answers three distinguishable ways. That turns path discovery into a 1-request-per-path
classification instead of blind fuzzing:

| Response body | Meaning |
|---|---|
| `{"code":"openapi.process.request.exception","message":"No static resource <path>."}` | path is NOT mapped on this gateway |
| `{"code":"cbl.missing.userid.exception"}` / `POWER_AUTH_SIGNATURE_INVALID` | path EXISTS, session or step-up signature enforced |
| field validation (`NotNull "must not be null"`, enum-deserialize error) or real 200 payload | **unauthenticated endpoint** — attack here |

Notes that cost time on moneta:
- `"Request method 'GET' is not supported"` also proves the path exists — always try both verbs.
- Error codes leak the internal backend: `cbl.*` (challenge/PowerAuth layer) vs `openapi.*` (Spring
  routing) vs `cz.gemoney.api.model…` (a third-party white-label lending backend) vs `ERROR_GENERIC`.
- Jackson messages are a free schema: enum deserialize errors print the full accepted value set
  (`[PERSONAL_EXPRESS, SME_EXPRESS, PERSONAL_CONSOLIDATION]`), and `NotNull "insurance"` walks you
  field-by-field through the request object.
- A `/testing/*` namespace may be deployed to prod behind a soft guard (`"This endpoint is for testing
  purposes only."`). Do not stop at the guard: 12 path variants (trailing `/`, `/.`, `;`, `;a=b`, `//`,
  `%00`, `%20`, case change, `?x=1`, `./`, `..;/`) is a cheap, bounded bypass sweep. On moneta all 12
  were blocked — a verified control worth writing down.

## 4. ffuf against an F5 ASM-protected gateway

The WAF returns one synthetic page for everything. Signature: identical byte size on every path
(moneta: **46650 bytes**; 48397 for directory 403s). Without a filter ffuf reports dozens of "200 hits"
that are all the block page.

    ffuf -u https://host/FUZZ -w list.txt -mc all -fs 46650 -s
    ffuf -u https://host/openapi/unsecured/portal/MOD/OP -X POST -H "Content-Type: application/json" \
         -d '{}' -w ops.txt -fr "No static resource" -s

`-fs` for the block page, `-fr` for the gateway's "not mapped" body — the second one is what actually
maps an API namespace. `-mc all -mr "responseObject|status"` also works when sizes vary.
Also: `403` on `/dir` (vs `404` elsewhere) means the directory EXISTS — always probe inside it.

## 5. Never guess a request contract — capture it

Seven hand-written bodies for `exchangerate/history/list` all failed. One Playwright run with a request
listener on the page that renders the widget produced the exact payload immediately:

```python
pg.on("request", lambda r: cap.append(r.post_data) if "exchangerate" in r.url else None)
await pg.goto("https://www.moneta.cz/kurzovni-listek", wait_until="domcontentloaded")
await pg.wait_for_timeout(12000)          # widgets hydrate late; networkidle never settles
```

→ `{"exchangeRatesDate":"2026-10-26T01:00:00"}`. Wire contracts are Jackson `LocalDateTime` / enum
types: quote, `OR 1=1`, stacked `PG_SLEEP`, `${7*7}` and raw epoch are all rejected at
deserialization, so the injection surface is effectively zero. Confirm with a timing check
(flat 0.27–0.88 s here) rather than declaring "strictly typed" from the error text alone.

## 6. Crawl gating (learned the hard way)

`katana -d 3` on a bank site walked into sibling marketing domains (esg.<target> — out of scope) and had
to be killed. Gate it instead of aborting: `-d 2`, and scope output by host afterwards. **Before
discarding a killed crawl, grep its partial output** — moneta's dying katana tail still emitted
`/unsecured/portal/exchangerate/{list,history/list}`, the only new surface found after the initial
report. Killing a crawl is not the same as having no data from it.

## 7. Over-claim guards specific to this shape

- **Never conclude from a truncated tool result.** An `ssl-pinning.json` whose 8 entries were cut to 4
  looked like "every pin expired". The full parse showed 4 expired + 4 valid with intentional overlap.
  Re-fetch and parse whole before writing any sentence that starts with "all" or "none".
- Uniform-size responses = WAF, not an app map (see §4). Same for uniform `{}` + 403 pairs.
- Public-data endpoints (FX tables, branch lists, public registry) can look like business logic but carry
  no impact; a future date returning today's table is a curiosity, not a finding.
- Read the programme's Hall of Fame first and treat those classes as dedupe-saturated (moneta: rate
  limit, info disclosure, HTTP headers, clickjacking, dir listing, text injection, reflected XSS, CORS,
  host-header injection, Liferay portlet misconfig, session enumeration, chatbot upload XSS).
