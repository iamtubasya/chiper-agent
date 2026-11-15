# Worked case — appcharge.com (2026-10-18)

Email-submission bug bounty (`bountyprogram@appcharge.com`), CVSS-aligned payouts
$100–$2,000. Rules of engagement: own test accounts only, ≤15 rps, UA
`appcharge-bugbounty-<email>`, PoC mandatory, no brute-force/DoS.

## Estate shape

| Host | Role |
|---|---|
| `appcharge.com` / `www.appcharge.com` | Vercel + Astro marketing site. 403 on every sensitive path. |
| `api.appcharge.com` | Publisher API (`x-publisher-token`), dashboard API (session), checkout v3 (bearer) |
| `api-store.appcharge.com` | Player-facing store API (login/orders/offers/campaign/otp) |
| `pay.appcharge.com`, `checkout-v2.appcharge.com` | Checkout v3 SPAs |
| `dashboard.appcharge.com` (+ `-sandbox`/`-staging`/`-dev`) | React SPA on S3+CloudFront |
| `~40 × *.store.appcharge.com` | Per-customer storefronts, identical SPA shell |
| `subscriptions-portal.appcharge.com` | ChargeBee hosted portal (third-party) |
| `go.appcharge.com` | nginx :80 → https, but :443 has no certificate |
| `help.appcharge.com` / `publishers.appcharge.com` | Zendesk help centers |

## Findings produced by this method (12, all reproduced 3×)

| # | Finding | Class |
|---|---|---|
| L1 | `POST /checkout/v3/cancel` → `201 {"isOrderCancelled":true}` for **any** bearer token; 10 sibling endpoints correctly return `SESSION_ENDED` | needs impact proof |
| L2 | `/store/otp/deeplink` unauth 500 on any valid-schema body | pre-auth crash |
| L3 | `__proto__` → TypeError on 4 endpoints (merge helper walks the key) | pre-auth crash |
| L4 | `/store/auth/login/external` leaks `[IntegrationController]` + null-deref on any JWT | info leak |
| L5 | Dashboard MFA endpoints public, schema-gated; no user-enum signal | info |
| L6 | Any `Origin` → 500 on 6 publisher-token endpoints (pre-auth crash) | pre-auth crash |
| L7 | api-store CORS: 21-host allowlist enumerated; blocked origin → 500 leaking reason | info + crash |
| L8 | 5 hosts publish RFC1918 A records (3 internal /16 ranges) | info disclosure |
| L9 | 8 subdomains → Cloudflare error 1001 | misconfig |
| L10 | `go.appcharge.com` :443 presents no certificate | misconfig |
| L11 | ChargeBee portal leaks allowed domains + payment methods + field schema | third-party info |
| L12 | `/checkout/v1/boot` authenticated by public `x-checkout-token` only | needs a real token |

## The pipeline mismatch (the reason this skill exists)

The orchestrator was aimed at `https://appcharge.com` and ran its full 0C set — variants,
400 DOM-XSS probes, 72 impact checks, 15 business-logic vectors — against
`www.appcharge.com/blog?page=2`. Result: `confirmed=0`. Every one of the 12 findings above came
from manual probing of the four API/SPA hosts that the pipeline never touched.

Read the tool-evidence files before trusting a `confirmed=0`: if the target URL in
`tool-evidence/*.txt` is the marketing apex, the negative covers the apex only.

## What the API auth boundaries actually looked like

- **Publisher API** (`x-publisher-token`): `401 Publisher token is required` → `403 Invalid
  publisher token`. No bypass with empty / `null` / `undefined` / `[]` / `{}` / JWT-shaped
  values. One transient `502` on a JWT-shaped token did not reproduce across 5 retries — treat
  single 5xx as noise, not signal.
- **Checkout v3** (`Authorization: Bearer <sessionId>`, sessionId from URL path): bogus token →
  `SESSION_ENDED` on 10 endpoints; `/checkout/v3/cancel` returns success for any value (L1).
- **Player store API**: session-gated 403 on orders/offers/campaign/template. `/store/offers`
  and friends hold without a session; no IDOR demonstrated.
- **Dashboard API**: `connect.sid` session with a version check — an arbitrary/forged cookie
  yields `invalid session version`, not a bypass.

## Tokens that would unlock the remaining two leads

Both L1 and L12 are blocked on credential acquisition, not on technique:

1. **A real checkout token** — the documented distribution model is deeplinks shared on social
   media / QR codes, so valid tokens exist in the wild. With one, test whether
   `/checkout/v1/boot` returns publisher/offer data to any holder, and whether
   `/checkout/v3/cancel` terminates another player's live session.
2. **A sandbox publisher account** — self-serve signup is reCAPTCHA-gated
   (`6LfIpjUrAAAAAD3Uch_7J_KmikI3ADGwondkwNTw` on prod). With a token, the ~110 dashboard
   routes and the documented publisher API become testable for IDOR / mass-assignment /
   price manipulation.

## Program-rules notes

- The policy forbids brute-force and DoS, so MFA code-rate and lockout behaviour were probed
  only to 5 gentle attempts and then dropped.
- The policy requires a working PoC — every finding above has a paste-ready curl repro.
- ChargeBee (L11) is a third-party component; check the program's third-party clause before
  submitting.
