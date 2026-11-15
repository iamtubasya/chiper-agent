# GraphQL Bug Bounty Playbook

> Source: PortSwigger Web Security Academy — GraphQL API vulnerabilities (https://portswigger.net/web-security/graphql). Compressed for field use.

## 1. Quick Detection

**Common endpoints:** `/graphql`, `/api`, `/api/graphql`, `/graphql/api`, `/graphql/graphql` — try appending `/v1` on miss. A "query not present"-style error on any URL is a GraphQL tell.

**Universal probe:** `query{__typename}` → response contains `{"data":{"__typename":"query"}}` = live endpoint.

```bash
# POST JSON (best-practice method)
curl -s https://target/graphql -H 'Content-Type: application/json' -d '{"query":"query{__typename}"}'
# GET variant
curl -s 'https://target/graphql?query=query%7B__typename%7D'
# form-encoded POST (forgable — gold for CSRF)
curl -s https://target/graphql -d 'query=query{__typename}'
```

**Method matrix:** prod best practice = JSON POST only. Always retry with GET and `x-www-form-urlencoded` POST — both widen the surface (CSRF + bypass filters that only guard POST).

**Introspection probe (compact one-liner):**
```json
{"query":"{__schema{queryType{name}}}"}
```
200 with type name → introspection on, full dump possible. Blocked → see §3.

**Suggestion enum (Apollo):** send invalid field (`{xyz}`). Errors like `Did you mean 'productInformation'?` leak valid schema tokens → feed to **Clairvoyance** to reconstruct schema without introspection.

## 2. Attack Vectors

| Vector | Technique | Notes |
|---|---|---|
| Schema dump | Full introspection via `__schema` + FullType/InputValue/TypeRef fragments | Delete `onOperation/onFragment/onField` if rejected |
| Suggestion enum | Malformed fields → "Did you mean" errors | Info disclosure; automatable |
| BOLA / IDOR | Args resolve objects directly: `product(id:3)` returns delisted/hidden items | Enumerate sequential IDs; test authz per object |
| Path traversal | File-path args: `path:"../../etc/passwd"` in resolvers touching fs | Trace arg → server file op |
| SSRF | URL args on fetch/webhook/image fields: `url:"http://169.254.169.254/latest/meta-data"` | Chain to cloud metadata |
| SQLi / NoSQLi | Raw args to resolvers: `id:"1' OR 1=1--"`; NoSQL via JSON vars `{"$ne":null}` | GraphQL ≠ safe; args hit backend |
| Mutation abuse | Enumerate mutations (reset, role, delete); invoke privileged/own-only ones cross-user | State-changing = high impact |
| CSRF | Endpoint accepts GET / form-POST, no content-type check, no CSRF token | Forge cross-site mutation as victim |
| Subscription abuse | WebSocket subs leak other tenants' live events; weak auth on connection | Check auth at upgrade + per-event |
| Alias brute force / DoS | Aliases pack N ops per request, defeating request-count rate limiters; deep nesting = DoS | See §3 |

## 3. Payload / Bypass Table

| Goal | Payload / Trick |
|---|---|
| Regex blocks `__schema{` | Insert ignored chars: `{"query":"query{__schema\n{queryType{name}}}"}` — also try space, comma |
| Blocked over POST | Resend via GET `?query=query%7B__schema%0A%7BqueryType%7Bname%7D%7D%7D` or form-encoded POST |
| Minified dump | One-line minified introspection (InQL / Burp generates) — evades length/multiline filters |
| Single-query filters | Batch ops: JSON array `[{"query":"..."},{"query":"..."}]` — check if server merges |
| Rate limiter (per-request) | Aliases: `query{a:isValid(code:"A1") b:isValid(code:"A2") c:isValid(code:"A3")}` — thousands of ops in 1 HTTP req |
| Directive-frag error | Strip `onOperation/onFragment/onField` from full introspection query |

## 4. By-Design Filters (SKIP)

Do **not** report these alone — intended hardening:

- Introspection enabled on a *public* API (by design; only report if it exposes private/sensitive fields).
- Suggestions enabled but schema contains nothing sensitive.
- JSON-POST-only endpoints (correct CSRF posture).
- Query depth / operation limits / max-bytes / cost analysis in place.

## 5. Severity Guide

| Severity | Findings |
|---|---|
| CRIT | Auth bypass / privilege escalation via mutation; SQLi; SSRF hitting cloud metadata with credentials |
| HIGH | BOLA cross-tenant data exposure; CSRF on sensitive mutation (email change, role, payment); IDOR on PII |
| MEDIUM | Alias-based brute force (OTP/discount/coupon validness); DoS via deep nesting accepted; hidden-object disclosure |
| LOW / INFO | Introspection or suggestions alone with non-sensitive schema |

## 6. Reporting Checklist

- [ ] Endpoint URL + accepted methods (POST/GET/form) + content-type behavior.
- [ ] Exact repro: raw HTTP request + `curl` one-liner a triager can paste.
- [ ] Proven impact: what data/action gained, from which auth level (show before/after).
- [ ] For CSRF: full PoC page + confirm no token/content-type validation.
- [ ] For BOLA: two accounts, show object A readable as user B.
- [ ] For rate-limit bypass: count of ops per request and measured effect.
- [ ] Screenshots of introspection/suggestion output if used as part of chain.
- [ ] Scope check: mutation/subscriptions tested only against permitted targets.

> ⚠️ Blocked/unproven exploit chain = INFORMATIONAL per master KB rule. Never claim HIGH/CRIT from theory alone.
