# Adafruit.com — 2026-09-04 Exhaustive Audit State

**Platform:** E-commerce IoT (hardware + cloud IoT platform)
**Stack:** Cloudflare WAF, Zen Cart (www), React SPA (io), Rails (learn), Vite frontend
**VDP:** https://www.adafruit.com/page/security-bounty-program
**Bounty:** Yes, via VDP

## Infrastructure
- **www.adafruit.com**: Cloudflare-protected, Zen Cart backend
- **io.adafruit.com**: React + Redux SPA, origin IPs 52.4.253.177 / 52.7.84.197 (AWS EC2, NOT Cloudflare)
- **accounts.adafruit.com**: Authentication portal (Auth0-style)
- **learn.adafruit.com**: Content platform (Rails backend + Stimulus/Hotwire)
- **Origin ports**: 22 (SSH), 80/443 (HTTP/S), 8080/8443 (alt HTTPS), 1883 (MQTT)
- **Sentry**: sentry.adafruit.us (org=adafruit, project IDs 9 and 10)

## Recon Summary
- 18 subdomains mapped
- 26 JS bundles analyzed (Vite production, CloudFront CDN)
- Multiple Sentry DSNs extracted from JS bundles
- WebSocket on io.adafruit.com (connects without auth, needs API key for data)
- GraphQL endpoint on io.adafruit.com (422 on POST, introspection empty)

## Tested Vectors (30+ phases, ALL NEGATIVE or INFORMATIONAL)

### Explicitly Negative (no finding)
- SQLi, SSTI, CRLF, XXE, path traversal → blocked by Cloudflare
- SSRF via webhooks → auth required ("not found - invalid URL")
- Rate limit bypass (X-Forwarded-For, CF-Connecting-IP, X-Real-IP) → session-based, tdp bypass
- Open redirect → none found
- Subdomain takeover → clean (all resolve properly)
- GraphQL introspection → empty, tdp schema leak
- CORS origin reflection (evil.com) → tdp reflected
- Password reset CSRF → token present (86 chars)
- Origin IP .env → 403 Forbidden
- Hidden parameters (debug, admin, test, callback, jsonp) → none responsive
- CRLF injection → negative
- Email header injection → negative
- Cookie manipulation → properly configured (Secure=True, HttpOnly=True)

### Informational Only (NOT reportable)
- Product API dump (7.4MB JSON) — public catalog, by-design
- Category API dump (28.8MB JSON) — public taxonomy, by-design
- Learn API dump — public content, by-design
- Category IDOR (sequential IDs 1-55) — returns public data
- CORS wildcard on io.adafruit.com — `credentials: false`, no cookie theft
- User enumeration via API — 15 usernames via response diff (empty vs populated)
- Sentry DSNs in JS bundles — DSN ≠ auth, only sends errors
- XSRF-TOKEN missing HttpOnly — by-design (Rails CSRF token access)
- MQTT port 1883 open — auth-protected, standard IoT protocol
- WebSocket connects without auth — needs API key for subscribe

## What Should Be Tested Next (untested angles)
1. **Business logic** — checkout flow, gift card redemption, coupon abuse, pricing manipulation
2. **IDOR on user data** — orders, invoices, addresses, payment methods (requires auth)
3. **Stored XSS** — product reviews, user profile fields, support tickets
4. **Race conditions** — cart operations, gift card double-spend
5. **Account takeover** — password reset flow, OAuth SAML, email verification
6. **Admin panel access** — /admin on various subdomains
7. **API key enumeration** — io.adafruit.com key patterns

## Lessons Learned
- **E-commerce public data ≠ finding.** Product catalogs, categories, pricing are scraped by competitors daily. Reporting these wastes everyone's time.
- **Cloudflare WAF is effective.** Injection vectors are properly blocked.
- **Well-defended sites require business logic focus.** Standard recon/injection vectors will all be negative. Pivot to checkout flows, payment logic, account management.
- **The "informational trap"**: Many technical findings (CORS, headers, Sentry DSNs) are real observations but NOT vulnerabilities. Self-filter ruthlessly.
