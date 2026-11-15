---
name: telekom-audit
description: Deutsche Telekom bug-bounty — scope, estate map, channel.
sources: authorized-engagement
---

# Deutsche Telekom — bug bounty engagement

Vendor engagement skill. Read this before touching any `telekom.*` / `t-systems.*` /
`otc-service.*` host so you don't re-derive scope, re-scan dead CI hosts, or re-report
out-of-scope third-party systems.

Companion skills: `recon-scope-triage` (ownership before testing), `hunt-spa-api`
(bundle → API map, the dominant play on this estate), `web2-recon` (subdomain pipeline).

---

## Program facts

| Item | Value |
|---|---|
| Program page | `https://www.telekom.com/bug-bounty-program` (EN) · `/de/ueber-uns/…/bug-bounty` |
| Submit channel | **email `bugbounty@telekom.de`** (no platform). PGP not stated — offer it. |
| Public rewards | P1/Critical **€5,000** · P2/High **€2,000** · P3/Medium **€1,000** |
| Private program | P1 €10,000 · P2 €4,000 · P3 €2,000 (broader targets, invite via the same mailbox) |
| Severity basis | Bugcrowd VRT **or** CVSS 4.0 |
| Hall of fame | `/en/about-us/data-privacy-and-security/hacking-and-testing/acknowledgments` |
| T-Mobile US | **separate** program on Bugcrowd — do not mix estates |

### Scope

**In:**
`*.telekom.de` · `*.telekom.net` · `*.telekom.com` · `*.t-systems.com` ·
`*.open-telekom-cloud.com` · `auth.otc.t-systems.com` · `*.otc-service.com`

**Out:**
- `*.reverse.open-telekom-cloud.com`
- `*.lila.dih.telekom.com`
- **All customer systems not owned by Deutsche Telekom AG** — this kills the whole
  `*.shared.dih.telekom.com` customer-tenant fleet (DIH "Connect & Integrate" per-customer
  subdomains named after the customer company: `basfcoatingsgmb-…`, `beijingvanjeetechnol-…`).
  Those hosts *are* `*.telekom.com` but are **customer-owned tenants** → out of scope. Also
  out: the third-party backend behind them.
- **PHP RCE CVEs CVE-2026-109618 / CVE-2026-109619** — explicitly excluded "due to current
  events". Do not test `hunt-php2shell` on this target; the class is carved out.
- Third-party SaaS the estate CNAMEs to (Heroku, Netlify, ServiceNow, Salesforce, Qualtrics,
  Frontify, Infobip, Vonage, SAP BTP `cfapps`, Azure websites) — attacking those is "attacking
  third-party systems", a RoE violation.

### Rules of Engagement (verbatim constraints)

- **"Do not access, modify, download, delete, or disclose any data."** This is the binding
  constraint on every PoC: prove reachability + response *shape*, never exfiltrate records.
  Do not enumerate tables, do not pull PII, do not `totalCount`-scrape.
- **"If you discover personal data while testing, stop the attack immediately, delete the
  transferred personal data, and contact the Bug Bounty Team."**
- Do not limit availability (no load/stress, no `--rate` above polite, no brute force).
- No social engineering. No physical access. No testing outside scope. No public disclosure
  before written approval.
- Pay once per vulnerability even if it affects multiple systems.

**Practical read:** this is a *data-conservative* program. Every finding must be provable
from headers, status codes, response shape, and one non-sensitive record — not from dumped data.

---

## Core business (what actually makes money — target this, not the login page)

DTAG is a telco. The money flows:

1. **Consumer mobile/fixed contracts** — MagentaZuhause/MagentaMobil: plan selection → KdNr
   (customer number) → MSISDN provisioning → monthly billing → tariff change → cancellation.
2. **Wholesale / carrier** — MVNOs and resellers buy SIM pools, tariff options, and API access
   per-partner (`carrierportal.wholesale.telekom.com`, M2M Customer API).
3. **B2B / T-Systems** — managed services, cloud (T Cloud Public = Open Telekom Cloud), SAP.
4. **MagentaBusiness APIs (CPaaS)** — SMS/RCS/WhatsApp **Messages API**, **Verify API** (2FA),
   **Voice API**, **5G Slicing**. Pay-per-message / per-verification. A billing-bypass or an
   OTP-bypass here is the highest-value logic bug class on the estate.
5. **Retail shop** — `shop.telekom.de` accessory shop: cart → coupon → DCB (direct carrier
   billing) voucher → Computop/Dimoco payment → Brodos fulfillment.

**Business-logic surfaces worth attacking (in priority order):**

- **Verify API / OTP** — rate limit on `verify` send, OTP attempt counter, silent-auth bypass,
  reuse of a verified token across MSISDNs. Bypassing 2FA on a telco = ATO at scale.
- **DCB voucher flow** (`/api/shop/dcb_vouchers/` + `/confirm` with `double_optin_token`) —
  is the DOI token bound to the MSISDN? Can a voucher be confirmed without the SMS round-trip?
- **Coupon stacking / provider whitelist** — the storefront cart carries
  `coupon.providersWhitelist` / `productNumbersBlacklist` / `providersBlacklist` **client-side**;
  if the server trusts them, a coupon scoped to accessories applies to handsets.
- **Partner/SIM lifecycle API** — `simallocation`, `simtransfer`, `limitoverride`,
  `optionbooking`, `tariffchange`, `termination` keyed by `{partnerId}`. Integer partnerId →
  BOLA across wholesale partners = fraud + DoS on real subscribers.
- **5G Slice Booking** — `product-order`, `role-booking-configs`, `customer-booking-configs`.
  A role/booking-config that a customer can mutate = free slice capacity.

---

## Estate shape (what you will actually find)

The estate is enormous and mostly **not** customer-facing. 93k subdomains, ~5.1k resolving,
~2.3k answering HTTP. Composition matters for scan budgeting:

- `*.tap.telekom.de` — **~49,000 hosts, almost all ephemeral CI preview deployments**
  (`<uuid>.trap.prod.tap.telekom.de`, `development-<ts>.trap-go-gin-example.…`). Dead or
  unauthenticated-by-design build previews. **Filter `trap|tap\.|caas-t[0-9]+` out of the httpx
  list** or you burn the entire scan on throwaway previews. Keep them only if a specific one
  shows up in a JS bundle or a CSP `connect-src`.
- `*.caas-t41 / caas-t3413 / caas-t14 / caas-p41` — internal container platforms (~4.5k hosts).
- `*.shared.dih.telekom.com` / `*.commx.bo.dih.telekom.com` — **customer tenants, OUT of scope.**
- `*.obs.*.otc.t-systems.com` — Object Storage Service buckets. Public-read listing is
  **by design** for the `-public` ones; check `?acl` for `AllUsers` write before reporting.
- `*.p5x.telekom.net` / `*.gc.telekom.net` — production GCP ingress (`login`, `account`).
- `wow-dev/wow-test`, `idm-dev`, `gsus`, `ng.telekom.net`, `ids.telekom.net`, `tmagic-*`,
  `dcpo`, `pix`, `ipls` — internal dev/QA namespaces. `403` is the norm; `200` here is worth a look.

Full host-class map, endpoint inventory, and verified negatives:
`references/telekom-estate-map.md`.

---

## What works on this estate (play order)

1. **`hunt-spa-api` on every `admin.*` / `app.*` / `*-tool.*` / `dashboard.*` host.** The estate
   is full of bespoke Vue/Angular/React admin panels that ship their whole API to the browser.
   This is where the only real defects were found. See
   `hunt-spa-api/references/framework-runtime-config-extraction.md`.
2. **`/v3/api-docs` sweep.** Spring Boot services expose full OpenAPI unauthenticated. One
   request = 46–72 documented ops with schemas. Highest signal-per-request on the target.
3. **`/api/config` on self-hosted SaaS** (Bitwarden, Open WebUI, Dependency-Track, Matomo,
   Argo CD, Portainer) — version + feature flags in one request, no auth.
4. **Keycloak realm enumeration.** `.well-known/openid-configuration` per realm is public.
   Then fingerprint the client: `Missing parameter: code_challenge_method` on the authorize
   endpoint = **public PKCE client**; `unauthorized_client: Client not allowed for direct access
   grants` on `/token` = no password grant. Both mean "no self-registration path" → stop, do not
   brute force (RoE).
5. **Object storage listing check** — `?list-type=2&max-keys=3` then `?acl`.

## What does NOT work (verified, don't re-burn hours)

- **Registration is closed almost everywhere.** Telekom Login, `account.idm.telekom.com`,
  Bitwarden (`disableUserRegistration: true`), Open WebUI (`enable_signup: false`), every
  Keycloak realm, iMSA/qc-tool/wats (all `AUTH_PROVIDER: icu` / Entra). No test account = no
  authenticated lane. Do not ask the operator for OTPs; find an unauthenticated surface instead.
- **JWT forgery against Keycloak-fronted APIs is wasted time.** `alg:none`, `HS256:secret`,
  `HS256:empty` against 3 endpoints × 3 payloads → all `401`. The resource server validates
  against JWKS. Check for a JWKS endpoint first; if present, skip alg-confusion entirely.
- **`/api/*` on an SPA origin usually returns the 200 shell** (catch-all). Always compare body
  against a random-path baseline before believing a 200.
- **`admin.<corp>` Angular `feature-guard` 404s** mean the route exists and is switched off —
  not that it's absent. See the `hunt-spa-api` §2e note.
- **`/actuator/*`, `/.env`, `/.git/config` return 200 + SPA shell on ~60 hosts.** Pure noise.
  Verified by body diff. Don't report these.

## Recon at scale — pitfalls specific to this estate

- `dnsx -retry 0` → `[FTL] retries must be at least 1`. Minimum is `1`. A run that dies
  instantly on that flag looks like "no hosts resolved".
- `dnsx -a -resp` produced an **empty output file** on 93k input in one run; plain `-a` (no
  `-resp`) worked. Prefer `dnsx -l hosts -silent -a -threads 300 -timeout 3 -retry 1` and do
  `-cname -resp` in a *separate* pass.
- `httpx` on 93k hosts does not finish in a foreground window — run it
  `background=true, notify_on_complete=true` and poll the jsonl line count.
- On this Windows host `curl` (schannel) fails `SEC_E_UNSUPPORTED_FUNCTION` on some TLS
  endpoints (e.g. `t-shop.telekom.de`, `cockpit.dev.dcpo.telekom.net`). Fall back to Python
  `requests` with `verify=False` — same wire result, no schannel. Do not conclude the host is down.
- `nuclei` runs on this list take a long time to emit anything (`-jsonl` file stays at 0 lines
  while it works). Don't kill it early; check `ps` and the `.err` file for liveness.

## Reporting notes for this program

- Channel is **email**, so the report must be self-contained: summary → impact → exact repro
  (`curl` and a Python alternative) → CVSS 4.0 vector → remediation. Attach PoC PDF.
- **Scope eligibility is the first thing they check.** State which in-scope pattern the host
  matches, and explicitly confirm it is *not* a customer tenant and *not* a third-party SaaS.
- Two-claim discipline: separate *"authentication is absent from the handler chain"* (proven by
  non-401 responses) from *"data is reachable now"* (needs a 2xx). Never merge them.
- One finding per email (operator preference), signed RESEARCHER_NAME, no reward discussion.

## Related

- `hunt-spa-api` — the primary play here; carries the framework-config extraction reference.
- `recon-scope-triage` — settle customer-tenant vs DTAG-owned before testing `*.dih.*`.
- `hunt-business-logic` — Verify API / DCB voucher / coupon-stacking lanes.
- `hunt-brute-force` — OTP send/verify rate-limit lane (polite, low volume only).
- `evidence-hygiene` — no PII in screenshots; this program's RoE is strict on data.
