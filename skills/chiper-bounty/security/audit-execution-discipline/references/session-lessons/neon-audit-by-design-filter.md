# By-Design Filter & Pre-Auth Exhaustion (Neon audit 2026-09-23)

## Problem
During Neon (neon.tech) HackerOne audit, agent kept presenting "by-design" behavior as findings.
User: "sy udh blg temuan informational itu, tidak ush kamu tampilkan, by design"

## By-Design Gate
Before presenting ANY finding, ask:
1. Is this INTENTIONAL by the operator?
2. Would a security team say "yes, that's how it works"?
3. Does it require additional exploitation to become real?
4. Is there a public spec that requires this?
If 2+ YES → DO NOT present. Skip entirely.

## Common By-Design Findings to SKIP
- OIDC .well-known/openid-configuration (spec requires public)
- SAML SSO URL accessible (federation requires it)
- Source map on login theme (public asset, not app source)
- API OpenAPI spec public (docs are public)
- .git returns 403 (server correctly blocks)
- Health endpoint returns OK (supposed to work)
- Version in error response (standard, unless CVE exists)
- CORS not reflected (GOOD security)
- OAuth callback accessible (required for OAuth)
- Admin panel behind Cloudflare Access (correctly protected)
- GraphQL introspection blocked (GOOD security)

## Pre-Auth Exhaustion
Before asking for credentials, exhaust ALL no-auth vectors:
1. GraphQL introspection
2. Source map extraction (.js.map files)
3. JS bundle analysis (secrets, config, env vars)
4. OAuth/OIDC endpoint enumeration
5. SAML endpoint probing
6. Health/metrics/debug endpoints
7. Staging/dev/preview environments
8. Alternative auth flows (device code, CIBA)
9. API versioning (v1, v2, deprecated)
10. WebSocket endpoints
11. gRPC endpoints
12. Subdomain enumeration (all TLDs)
13. Port scan non-standard ports
14. Nuclei scan all templates
15. Sensitive files (.env, .git, robots.txt)
16. CORS on all hosts
17. Host header injection
18. CRLF injection
19. Path traversal
20. HTTP method tampering

## Presentation Rules
- Only show bounty-worthy findings (Medium+ with proven impact)
- Don't pad lists with low/info
- Be honest if nothing exploitable found
- Don't repeat findings user dismissed
- Ask before deep-diving
