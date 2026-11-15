---
name: api-host-surface-mapping
description: "Map API/SPA hosts when the apex is just marketing."
version: 1
author: curator
license: MIT
category: security
metadata:
  hermes:
    tags: [security, recon, api, saas, host-triage, cors, dns, tls, bug-bounty]
---

# API-host surface mapping (SaaS estates)

## When to Use

- Phase 0B just produced a live-host list for a SaaS/platform target and several hosts are
  SPAs or JSON APIs
- You are about to point the audit pipeline at a target and need to decide **which host**
- A `confirmed=0` pipeline result came back from a host that 403s everything
- You need to map an authenticated API surface without a wordlist or an account

Worked case: `references/appcharge-worked-case.md` — appcharge.com bounty (2026-10-18), 12
findings, and the pipeline mismatch that motivated this skill.

For targets where the apex is a static marketing site and the application lives on
`api.<t>` / `dashboard.<t>` / `pay.<t>` / `*.store.<t>`. Worked case: **appcharge.com**
bug bounty, 2026-10-18 — apex 403'd every probe while four API hosts carried the entire
surface and were never touched by a single automated scan.

## When to load

- Phase 0B just produced a live-host list for a SaaS/platform target and several hosts are
  SPAs or JSON APIs
- You are about to point the audit pipeline at a target and need to decide **which host**
- A `confirmed=0` pipeline result came back from a host that 403s everything
- You need to map an authenticated API surface without a wordlist or an account
## Step 1 — Classify hosts by role BEFORE launching 0C

The orchestrator takes ONE target URL and drives every variant/impact/business-logic probe at
it. Aiming it at a marketing apex burns the whole run.

| Host role | Signal | Pipeline target? |
|---|---|---|
| Marketing / docs / blog | static, 403 on all sensitive paths, no auth endpoints | **No** — skip 0C volume |
| API | `406`/`401`/`403` JSON bodies, `X-Powered-By`, schema-validation errors | **Yes — primary** |
| Authenticated SPA | `config.js` with `REACT_APP_*` / `VITE_*`, S3+CloudFront shell | **Yes** — bundle first, then probe |
| Per-tenant storefront | identical SPA shell, `*.store.<t>` | Yes, one representative + CORS diff |

If the estate has several API hosts, run the pipeline **once per host** (or `--scope` each)
rather than once at the apex. A `confirmed=0` against a host that 403s everything is not a
negative finding — it is evidence the probes never reached the application.

## Step 2 — The error-code oracle (route existence, no wordlist)

On Express behind an AWS ELB the **response body** tells you whether a route exists. One
request each, no fuzzing.

| Response body | Verdict |
|---|---|
| `404 {"message":"Cannot GET /x"}` / `"Cannot POST /x"` | route does **not** exist (Express catch-all) |
| `403 {"message":"Forbidden resource"}` / `401 {"message":"Publisher token is required"}` | route **exists**, gated |
| `400 {"message":"Schema Validation Error","body":"Property X has failed…"}` | route exists **and is pre-auth** — walk the schema |
| `500 {"message":"Internal Server Error","debugMessage":"…"}` | route exists and crashes on your input |
| `406` + `Fixed response content` (22 B, `Server: awselb/2.0`) | ELB catch-all — **never reached the app**; not a route |
| `409` + `error code: 1001`, `Server: cloudflare` | Cloudflare zone misconfiguration, no content |

**Method matters.** A path that 404s on GET may exist on POST. On appcharge,
`/checkout/v3/apply-promo-code` returned `404 Cannot GET` but `403 SESSION_INVALID` on POST.
Probe both methods before declaring a path absent.

**The 400 is the jackpot** — it enumerates required property names, ID formats and enum values
for free:

```
POST /store/otp/deeplink  {}
-> 400 "Property publisherId … publisherId must be a mongodb id.;
        Property device … must be one of the following values: MOBILE, DESKTOP, APPCHARGE."
```

## Step 3 — Pre-auth crash probes

Send a payload a careless merge/deserialiser will choke on, to every schema-gated endpoint:

```
POST /store/support/prelogin
{"publisherId":"<valid-objectid>","__proto__":{"polluted":true}}
-> 500 {"debugMessage":"Cannot read properties of undefined (reading 'replace')"}
```

- `__proto__` / `constructor.prototype` / `__proto__.x` crashing a merge helper is a **real,
  reportable unhandled-error finding** (Low). It is **not** proof of prototype pollution —
  pollution requires an observable effect on a subsequent request. Report the crash, not the
  pollution, unless you demonstrate the latter.
- A 500 whose `debugMessage` names an internal controller (`[IntegrationController]: TypeError:
  Cannot read properties of null (reading 'apiKey')`) is an info-leak finding on its own.
- Severity: Low each. Bundle same-root-cause crashes as one family (programs pay one bounty per
  root cause).

## Step 4 — Origin-header CORS crash

A non-empty `Origin` on token-gated endpoints can 500 **before** auth runs:

```
curl -o /dev/null -w '%{http_code}\n' -H 'Accept: application/json' https://api.<t>/v1/price-points
# 401
curl -o /dev/null -w '%{http_code}\n' -H 'Origin: https://x.example' -H 'Accept: application/json' \
     https://api.<t>/v1/price-points
# 500
```

**Run the four controls before attributing it to "any cross-origin request":** `Referer`,
`Sec-Fetch-Site`, `X-Requested-With`, and an empty `Origin:` all left the 401 intact on
appcharge. The trigger was specifically a non-empty `Origin`.

On a second host the same class was louder — non-allowlisted origin → **500 with
`debugMessage: "<origin> is blocked by CORS policy"`** (errors instead of 403, and discloses the
reason). The allowlist is enumerable: probe `Origin: https://<host>` per known storefront and
treat `200` vs `500` as allowlisted/blocked. That enumerated 21 hosts in one pass.

## Step 5 — RFC1918-in-public-DNS sweep

`socket.gethostbyname_ex()` over the full subdomain list; flag `10.0.0.0/8`, `192.168.0.0/16`,
`172.16.0.0/12`. Passive, cheap, and it found real internal topology (5 hosts, 3 distinct
internal /16 ranges on appcharge).

**Trap — exclude CDN ranges.** `172.64.0.0/13` is Cloudflare, not RFC1918. `checkout.appcharge.com
-> 172.64.152.100` looked like a leak and is not. Check the octet before writing the finding.

Impact framing: internal-topology disclosure that converts a future blind SSRF into a targeted
hit. Not exploitable alone — say so.

## Step 6 — TLS-cert presence sweep

One handshake per live host catches two misconfigurations:

```python
import ssl, socket
ctx = ssl.create_default_context()
s = ctx.wrap_socket(socket.create_connection((h, 443), timeout=8), server_hostname=h)
print(h, s.version(), s.getpeercert().get("notAfter"))
```

- **No certificate at all** — `go.appcharge.com`: nginx on :80 issued `301 → https://…` (itself)
  while :443 returned `tlsv1 alert internal error` / `no peer certificate available` on every
  handshake (TLS 1.2 + 1.3, all SNI variants incl. empty, all 3 backend IPs, several ciphers);
  no-SNI connections were reset. Reproduced 3× with openssl and Python. Report as
  availability/misconfiguration, not confidentiality.
- **Cloudflare error 1001** — `409 Conflict`, body `error code: 1001`, `Server: cloudflare`.
  Zone misconfiguration; no content served.
- Capture expiry per host while you have the handshake open.

## Step 7 — Where the surface hides on a SaaS estate

The apex told us nothing. Everything came from:

1. **`/config.js` on every SPA host** — API base URL, OAuth issuer + client IDs, analytics
   tokens, reCAPTCHA site keys, internal hostnames, license metadata.
   Site keys / client IDs / public keys are **public by design — not findings**; internal
   hostnames and license blobs are recon intel.
2. **SSR payloads on storefront hosts** — embedded access tokens, tenant IDs, feature-flag dumps.
3. **The app bundle** — route constants for every authenticated feature. Extract with windowed
   `str.find`, never context-grep on minified JS (the regex backtracks and hangs).
4. **Public API docs** — `docs.<t>/llms.txt` lists every documented endpoint; probing those with
   the §2 oracle maps the authenticated surface with zero scanning.

## Step 8 — Third-party hosted surfaces

`subscriptions-portal.appcharge.com` served a **ChargeBee** hosted portal whose unauthenticated
`retrieve_init_info` disclosed allowed domains, payment methods and the field schema.

- **Check the program's third-party clause before reporting** anything on a vendor-hosted
  component — many programs exclude third-party services outright.
- The vendor's CDN hostname is a *separate* asset from the target domain; treat it as out of
  scope unless the brief names it.

## Documented negatives — do not repeat

- **403-bypass on session-gated routes**: path suffixes (`/`, `.`, `%20`, `..;/`, `#`, `%00`),
  case variants (`/STORE/OFFERS` → 406 = ELB route miss, **not** a bypass), `X-Forwarded-For`,
  `X-Original-URL`, `X-Rewrite-URL`, `X-Forwarded-Host`. All still 403.
- **JWT signature bypass on deeplink auth**: alg=none and wrong-signature HS256 both return a
  generic `Login Failed` — no differential, no bypass.
- **Timing oracle on token validation**: short vs 24-char tokens gave 1.304 s vs 1.284 s
  (n=6 interleaved, within 1σ). No signal.
- **User enumeration on MFA initiate**: existing vs nonexistent emails gave byte-identical
  bodies and means within 1σ (n=6 interleaved). No signal.
- **`x-dynamo-payload` header injection** on checkout-session creation: no effect.

## Companion skills

- `security-recon` — Phase 0B pipeline, bundle extraction, scope mapping (user-owned)
- `bb-methodology` — 5-phase workflow + discipline rules (user-owned)
- `hunt-spa-api` — turning an extracted bundle into an API test plan
- `unauth-config-disclosure` — when `/config.js` leaks tenant config or keys
- `bot-protected-target-testing` — when a WAF/CDN blocks the probes above
