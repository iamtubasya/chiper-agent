# Layer Checklists (10 Layers) — Deep Audit Doctrine

**SURFACE AUDIT = MEMATIKAN.** Jangan pernah berhenti di permukaan.

## LAYER 1: SURFACE

**JANGAN BERHENTI DI SINI.** Surface findings (CORS, headers, info leak) bukan bounty material. Lanjut ke Layer 2+.

```
Subdomain enum → live hosts → ports → directories → JS endpoints
WAF fingerprint → technology stack → CSP analysis
→ Surface findings: misconfig, info leak, headers
→ LANJUT! Ini baru 5% dari audit. Jangan claim "done".
```

## LAYER 2: INFRASTRUCTURE DEEP
```
□ DNS history (dnsdumpster, securitytrails) — old subdomains still alive?
□ CloudFront/S3/Azure/GCP — bucket policies, ACLs, public access?
□ Staging/QA/dev subdomains — weaker security controls?
□ Non-Cloudflare origins — direct IP access?
□ Internal services exposed (MongoDB, Redis, Elasticsearch, Kafka)?
□ Certificate transparency (CT logs) — wildcard certs reveal internal naming?
□ Reverse DNS — what IPs resolve to what?
□ ASN/IP range — neighboring infrastructure?
□ Email security (SPF/DKIM/DMARC) — phishing vector?
□ MX records — mail server version/patch level?
□ TLS config — old ciphers, protocols?
□ HTTP methods — PUT/DELETE/PATCH on sensitive endpoints?
□ Web server version disclosure (Server header, error pages)?
□ Backup files (.bak, .old, .swp, .git, .env, .DS_Store)?
□ Source code disclosure (source maps, .map files)?
```

## LAYER 3: AUTHENTICATION DEEP
```
□ Auth flow FULL trace (from signup → verify → login → session → logout)
□ OAuth flow — redirect_uri validation, state parameter, PKCE
□ Password policy — complexity, history, breach check
□ Session management — fixation, rotation, invalidation
□ JWT — algorithm confusion (none, HS256 vs RS256), expiry, refresh
□ Multi-factor — bypass via API vs portal, recovery codes
□ Account lockout — does GraphQL bypass portal lockout?
□ Password reset — token reuse, host header poisoning, timing
□ Email verification — bypass via race, replay
□ Privilege escalation — role manipulation via API
□ Impersonation — can admin impersonate user? Abuse?
□ API key management — rotation, scope, key in URL vs header
□ Device fingerprinting — can be spoofed?
□ Geo-restriction bypass — VPN/proxy detection?
```

## LAYER 4: AUTHORIZATION DEEP
```
□ Horizontal IDOR — ALL object types (not just one)
□ Vertical IDOR — user → admin on EVERY endpoint
□ Function-level access — admin-only mutations with user token
□ GraphQL field-level auth — which fields accessible per role?
□ Batch/alias injection — bypass auth by batching?
□ Mass assignment — add role/admin/plan fields to profile update
□ Parameter pollution — duplicate params, JSON array injection
□ HTTP method confusion — GET endpoint accessible via POST?
□ API versioning — v1 weaker auth than v2?
□ Tenant isolation — org_id manipulation, cross-tenant data access?
□ Resource-based access — shared resources, team access?
□ File-based access — other users' files via path manipulation?
```

## LAYER 5: BUSINESS LOGIC DEEP
```
□ Pricing logic — negative quantities, zero-price, rounding errors?
□ Coupon/discount — stacking, race condition, self-referral?
□ Payment flow — amount manipulation, currency confusion?
□ State machine — cancel→refund, expired→active?
□ Race conditions — double-spend, TOCTOU, coupon reuse?
□ Quota/limit — bypass via API vs UI, multiple accounts?
□ Import/export — CSV injection, data exfil via import?
□ Webhook/callback — SSRF, payload manipulation?
□ Notification — email/SMS bombing, template injection?
□ Workflow bypass — skip steps in multi-step flows?
□ Form validation — client-side only, server trusts?
□ File upload — path traversal, polyglot, zip slip?
□ Request size — oversized payload DoS?
□ Timeout behavior — expired session still processes?
```

## LAYER 6: THIRD-PARTY INTEGRATION DEEP
```
□ Sentry DSN — can it be abused to inject error reports?
□ Segment write key — can inject data that reaches CRM/analytics?
□ Auth0/OIDC — well-known config, client enumeration, dynamic registration?
□ Cloudinary — unsigned presets, CORS, upload abuse?
□ Stripe — test mode, webhook signature bypass?
□ Algolia — secured key scope, index listing?
□ Intercom/Zendesk — cross-tenant data?
□ Analytics (Amplitude/Mixpanel/PostHog) — data poisoning?
□ Feature flags (LaunchDarkly/Pendo) — can be toggled?
□ Chat/CS widgets — XSS via support ticket?
□ Status page — does it leak internal infra?
□ CDN bypass — direct origin IP, different behavior?
```

## LAYER 7: CLIENT-SIDE DEEP
```
□ Source maps — internal endpoints, secrets, private keys?
□ __NEXT_DATA__ — staff emails, internal URLs, config?
□ env-config.js — wrong values, staging URLs, debug flags?
□ localStorage/sessionStorage — sensitive data stored?
□ Service worker — cache poisoning?
□ WebSocket — message injection, auth bypass?
□ PostMessage — XSS via message handler?
□ DOM clobbering — stored XSS via HTML?
□ Prototype pollution — client-side gadget chains?
□ CSP evaluation — what's actually blocked vs allowed?
□ Mixed content — HTTP resources on HTTPS page?
□ Subresource integrity — missing SRI on third-party scripts?
```

## LAYER 8: CRYPTO/WEB3 DEEP (if applicable)

**Jika target punya smart contract → WAJIB check semua ini:**

```
□ Reentrancy — external calls before state updates?
□ Flashloan — price manipulation in single tx?
□ Access control — unprotected critical functions?
□ Oracle — single source? Manipulable TWAP?
□ Integer overflow — pre-0.8.0 or unchecked?
□ Delegatecall — user-controlled target?
□ Bridge — message validation, nonce reuse?
□ Governance — flashloan voting, proposal manipulation?
□ Fee-on-transfer — balance calculation off-by-one?
□ Vault/share math — inflation attack, donation attack?
□ Proxy — storage collision, uninitialized implementation?
□ MEV — sandwich, frontrunning, backrunning?
□ Signature — malleability, replay, missing nonce?
□ Time dependency — block.timestamp manipulation?
□ Cross-contract reentrancy — multi-hop exploitation?

□ UNVERIFIED CONTRACT? → MUST decompile (cast disassemble/pyevmasm/Dedaub)
□ DECOMPILED CODE ANALYSIS:
  □ Map all function selectors (4byte.directory)
  □ Find unprotected critical functions
  □ Identify hardcoded addresses
  □ Check storage layout for admin/owner slots
  □ Look for known vulnerable patterns in bytecode
```

## LAYER 9: ADVANCED TECHNIQUES
```
□ HTTP request smuggling (CL.TE, TE.CL)?
□ Web cache deception (internal path behind cache)?
□ Host header injection (password reset, cache poisoning)?
□ SSI injection (server-side includes)?
□ Log injection (log4j-style, log poisoning)?
□ XML external entity (XXE)?
□ Server-side template injection (SSTI)?
□ Insecure deserialization?
□ Integer overflow in price/quantity calculation?
□ TOCTOU in file operations?
□ Path traversal (beyond basic ../)?
□ Null byte injection?
□ Unicode normalization attacks?
□ HTTP parameter pollution (HPP)?
□ Subdomain takeover (Dangling DNS)?
□ Open redirect chains (→ XSS → cookie theft)?
```

## LAYER 10: EXOTIC / RARE VECTORS
```
□ HTTP/2 smuggling?
□ gRPC reflection (internal methods exposed)?
□ Protobuf deserialization bugs?
□ GraphQL batching DoS?
□ WebSocket message size abuse?
□ Server-Sent Events (SSE) injection?
□ PDF generation SSRF (HTML-to-PDF)?
□ Markdown XSS (stored via rich text editor)?
□ Regex DoS (ReDoS)?
□ Unicode confusable characters in URLs?
□ Internationalized domain name (IDN) homograph?
□ MIME sniffing (content-type mismatch)?
□ Cookie tossing (subdomain sets cookies for parent)?
□ DNS rebinding?
□ Race in concurrent session operations?
□ API key in Referer/Origin header leak?
□ CORS preflight abuse (OPTIONS returns 200)?
```

## Deep-Dive Decision Tree

```
After Surface (Layer 1) findings:
  ↓
Layer 2-10: systematically test each layer
  ↓
Each layer output:
  ├─ FINDING → document, verify PoC, check chain potential
  ├─ BY-DESIGN → compare across layers, check for inconsistency
  ├─ BLOCKED → document blocker, try alternative in same layer
  └─ CLEAN → move to next layer
  ↓
After ALL layers exhausted:
  ↓
REPORT GATE checklist (219 boxes)
  ↓
ALL checked → ONE comprehensive report
ANY unchecked → GO BACK to unchecked layer
```

## Deep-Dive Anti-Patterns (NEVER DO THESE):

| Anti-Pattern | Why it's wrong | What to do instead |
|-------------|---------------|-------------------|
| "WAF blocks everything" | WAF blocks specific vectors, not ALL | Pivot to business logic, auth, CORS, client-side |
| "Can't test auth" | Always auth flow to test pre-auth, OAuth, reset | Degraded path per §1.0 |
| "By-design" | Only if you checked ALL endpoints + compared | Cross-endpoint comparison first |
| "Informational" | Only after chaining attempt | Chain with other findings |
| "Nothing found" | You tested 5 vectors, 25 remain | Test all 33 vectors |
| "Report partial" | Stopped at first finding | Continue ALL layers first |
| "Tool failed" | One tool fails, pivot to manual | curl, Python, browser automation |
| "CORS misconfig" | 95% bounty programs exclude social engineering | Mark as P3 note, pivot to IDOR/auth/biz-logic |
| "CSRF found" | CSRF needs victim login + click = social attack | Check if endpoint has IDOR instead (direct access) |
| "Found XSS" | Stored XSS needs victim visit page = interaction | Check if XSS can exfil data directly (bypass auth) |
| "Clickjacking" | Almost never paid in bounty | Skip, focus on server-side vulns |
