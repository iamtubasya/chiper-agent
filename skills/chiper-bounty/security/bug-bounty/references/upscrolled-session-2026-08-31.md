# UpScrolled VDP15 Recon Session (2026-08-31)

## Target
- Platform: UpScrolled (upscrolled.com) — social media platform
- Program: VDP15 on Bugcrowd
- Bugcrowd URL: https://bugcrowd.com/engagements/vdp15-upscrolled

## Infrastructure Map
| Component | Technology | Notes |
|-----------|-----------|-------|
| Main site | Next.js 5 + Turbopack | upscrolled.com — React Server Components |
| API backend | AWS Lambda + API Gateway | api.upscrolled.com — behind CloudFront |
| Media CDN | CloudFront + S3 | media.video.upscrolled.com |
| Chat | Matrix/Tuwunel | chat.upscrolled.com — federation disabled |
| Newsroom | DNA CMS | newsroom.upscrolled.com — Cloudflare |
| Support | Intercom | support.upscrolled.com |
| Auth | Cloudflare Turnstile | Session via x-upscrolled-session-token header |
| Analytics | Amplitude | sync.upscrolled.com |
| Video | Mux | Embedded player |
| Identity | Veriff | Identity verification |
| Payments | Stripe + RevenueCat | Subscription handling |
| Company ID | 39 | Leaked in newsroom HTML |

## Key Subdomains
- `api.upscrolled.com` — Backend API (CloudFront → Lambda)
- `newsroom.upscrolled.com` — DNA CMS with exposed internal APIs
- `chat.upscrolled.com` — Matrix homeserver (Tuwunel)
- `media.video.upscrolled.com` — S3 bucket for topic images
- `support.upscrolled.com` — Intercom integration
- `sync.upscrolled.com` — Amplitude analytics

## Recon Technique: Turbopack Chunk Analysis
UpScrolled uses Next.js 5 with Turbopack bundler. Chunks have hash-based names:
- `12k208sar5979.js` (main app bundle)
- `12jhfwim_pc-9.js` (second main bundle)
- `12g9a12t3k.js` (analytics bundle)
- `12igqn70u3.js` (Stripe/RevenueCat bundle)
- `12jgx8t95h.js` (video/media bundle)

**How to find:** Look for `<script src="/_next/static/chunks/...">` in main page HTML.

**Grep patterns:** `/api/`, `/user/`, `fetch(`, `x-upscrolled-session-token`, `DeviceSession`, `turnstile`, `PostHog`, `Amplitude`, `/api/upstream/`

## Auth Flow
1. User visits upscrolled.com → Cloudflare Turnstile challenge
2. POST to `/register` with Turnstile token → `DeviceSession` (UUID)
3. Session token in localStorage → sent as `x-upscrolled-session-token` header
4. Server validates via Lambda

## Validated Findings
1. **CORS Misconfiguration (Medium P2)** — `ACAO=* + ACM=*` on ALL api.upscrolled.com endpoints. CVSS 5.3.
2. **Permissions-Policy Misconfiguration** — `camera=*, microphone=*` on main site
3. **Missing Security Headers on API** — no CSP, HSTS, XFO, XCTO, RP
4. **Information Disclosure via Errors** — Lambda proxy error messages leak structure
5. **Newsroom robots.txt Leak** — admin paths exposed
6. **Matrix Federation Key Exposed** — chat subdomain leaks signing key
7. **Internal API Leaks in Newsroom JS** — PostHog key, Company ID 39, DNA CMS endpoints

## API Endpoints Discovered (30+)
See full list in session. Key: /util/topics/v1 (unauth), /user/profile/get, /activity/get, /user/scroll-packs/get, /user/register, /health (bypasses CloudFront WAF).
