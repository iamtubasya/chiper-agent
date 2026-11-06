# Cloudflare-fronted target + automated pipeline: throttle trips, coverage integrity, FP traps

Session origin: SpectroCoin bug-bounty engagement, 2026-10-12. Self-hosted, paid program, no published
scope list and no scanner prohibition → full-mode pipeline. Whole estate sits behind Cloudflare.

## 1. The pipeline's own scanners can trip Cloudflare rate-limiting on the WHOLE host

`audit-pipeline-orchestrator.py` enumerates deep endpoints (sitemap + JS bundles → 506 URLs on this target)
and fires nuclei/sqlmap/dalfox/arjun across them. On a Cloudflare-fronted host that got the **IP** rate-limited:
every subsequent request to `spectrocoin.com` returned HTTP **429** with body `error code: 1015`.

- **Per-host, not whole-estate.** While `spectrocoin.com` was 429 on every path, `auth.spectrocoin.com`,
  `profile.spectrocoin.com` and `docs.spectrocoin.com` still answered 200. Always re-test a *different*
  subdomain before concluding the engagement is blocked — the limit buckets per hostname/route.
- **Some route families are limited harder than others.** `/api/fe/currencies/active` answered 200 while
  `/api/oauth2?wsdl` (a legacy SOAP route) stayed 429 in the same minute — a per-path CF rule.
- **Cooldown is minutes.** Wait 30–75 s and re-probe; do not switch to proxies to route around it (that
  escalates a benign throttle into evasion).

## 2. Coverage integrity: a 429 recorded as "EXECUTED" is fake coverage

The gate counts an evidence FILE, not a valid response. On a throttled run:
- `sqlmap-sqli.txt` → `[CRITICAL] all tested parameters do not appear to be injectable` **and**
  `[INFO] WARNING: the web server responded with an HTTP error code (403)` + `WAF/IPS identified as 'CloudFlare'`.
  The 403s are CF WAF blocks, not injectability results — the negative is weak, say so.
- `race-checker.py-race.txt` printed `Successful requests: 4/50` then `✓ All responses OK (no obvious race
  conditions detected)`. 4/50 = 46 requests were throttled/dropped; the tool's own verdict logic ignores that.
  **A race/rate-limit result with a low success ratio is not a negative — it is no result.**
- `nuclei-cmdi.txt` contained only `waf-detect:cloudflare` + `tech-detect:cloudflare` → zero real templates hit.

Rule: read the evidence BODY before believing any "EXECUTED"/"no findings" line. If responses were 429/403,
record the vector as an explicit **GAP** (throttled), never as "clean".

## 3. False-positive trap — dalfox `[I] Reflected` is NOT `[VULN]`

dalfox emitted dozens of `[I] Reflected <param> param => PTYPE: URL Injected: /inATTR-double(1)`
lines against `https://spectrocoin.com` (params `image_url`, `keywords`, `api_key`, `unsubscribe_token`, …).
The reflection lands in the SSR `<meta property="og:url" content="https://spectrocoin.com/en/IndexPage/IndexPage?image_url=VALUE" id="og-url"/>`.

- Re-checked by hand: the value is **URL-encoded** (`"`→`%22`, `<`→`%3C`, `>`→`%3E`). Sending a raw `"` via curl
  still produced `%22` in the output (the framework re-serialises the parsed URL), so no attribute breakout and no XSS.
- Do NOT read the normal closing `"` of `content="…" id="og-url"` as an injected quote — that is the attribute's
  own delimiter, present on every request.
- Discrimination recipe: fetch once with an encoded payload (`%22%3C%3E`) and once with a raw one; if BOTH come back
  encoded, it is not a reflection bug. `dalfox` only prints `[VULN]`/`[POC]` for confirmed executions — treat bare
  `[I] Reflected` as a candidate, not a finding.

## 4. False-positive trap — ISO-3166 alpha-2 vs alpha-3 looks like a country-logic inversion

`/api/fe/signup-contracts/<code>`: `LT`, `US`, `DE` → `400 {"key":"invalid_request","errorParameters":[{"key":"countryCode","value":"Can not be null"}]}`
while `IRN`, `GBR`, `FRA`, `RUS`, `JPN`, `CHN`, `PRK`, `LVA`, `POL`, `IND`, `BRA` → `200` with real ToS contract JSON.
It first reads like "restricted countries are accepted / allowed countries rejected" (an access-control inversion).

It is not. The set that works is exactly the **3-letter (alpha-3)** codes; the set that fails is the **2-letter
(alpha-2)** codes — `XX`/`1234` also fail. The endpoint simply expects alpha-3 and looks up the correct legal entity
per jurisdiction (`Spectro Finance OÜ` for some, `Specto Finance Systems Inc.` BVI for others). Reproduce 3× before
believing an access-control pattern; a mixed accept/reject set is more often an **input-format** mismatch than a logic bug.

## 5. Notes on the OAuth/OIDC provider surface (auth.<host>, not throttled)

Worth mapping on any crypto-exchange target — credentials/consent live here:
- `.well-known/openid-configuration` + `.well-known/oauth-authorization-server` → endpoints, `grant_types`
  (here `authorization_code`, `refresh_token`, `client_credentials`), `token_endpoint_auth_methods_supported:
  client_secret_basic`, `code_challenge_methods_supported: S256`, `scopes_supported: [openid]`, and **no**
  `registration_endpoint` (no dynamic client registration). `.well-known/jwks.json` → `kid`, `RS256`.
- The public OAuth `client_id` is in the frontend config, not a secret: `gen-cfg.js` exposed
  `AUTH_DOMAIN`, `EXCHANGE_PUBLIC_API_URL`, `RECAPTCHA_SITEKEY`, and `clientId: "spectrocoin_oauth"` came
  from `GET /api/session`.
- `GET /oauth/authorize?...` 302→`/login` for **every** redirect_uri (evil host, suffix lookalike, `//host`,
  path-traversal) — validation is deferred until after authentication, so a pre-login probe cannot conclude
  "redirect_uri bypass". The one input that errored pre-login (`user@host`) failed on URL *parse*, not policy.
  Confirm with an authenticated session.
- `POST /oauth/token` returned `401 invalid_client` for both `client_credentials` and a bogus
  `authorization_code` → client authentication is enforced (no public-client token minting).
- Legacy SOAP alongside modern OIDC: `/api/oauth2?wsdl` served a real WSDL
  (`OAuth2ServiceService`, ns `…spectrofinance.lt`), and `POST /api/oauth2` returns SOAP faults
  (`Message part X was not recognized. (Does it exist in service WSDL?)`). WSDL exposure = enumerate operations
  then test SOAP-class bugs (XXE) — but reach it AFTER the CF throttle clears.

## 6. Estate coverage gap the single-host pipeline leaves

The orchestrator runs one host (`spectrocoin.com` + a handful of peripheral hosts). On this target subfinder
returned **19 subdomains**; `urls.txt` was 502×`spectrocoin.com` + 1 each of help/docs/careers/blog. The high-value
subdomains — `auth`, `profile`, `exchange`, `pro` — were **not** in the pipeline's URL set. Report this as a
residual gap, and run a separate pipeline invocation per key subdomain (auth first: it is the IdP).
