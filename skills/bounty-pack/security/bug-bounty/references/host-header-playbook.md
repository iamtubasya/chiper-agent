# Host Header Attacks — Bug Bounty Playbook

> Source: PortSwigger Web Security Academy — https://portswigger.net/web-security/host-header (compressed extract). Companion to web-cache-poisoning playbook.

## 1. Quick Detection

| Step | Probe | Signal |
|---|---|---|
| 1 | Arbitrary Host: `Host: evil.com` on GET / | Normal 200 or attacker-host redirect = app trusts Host |
| 2 | Confirm routing: send to **real IP** with evil Host (bypass DNS) | Same response = Host controls routing |
| 3 | Virtual hosting check: brute-force `Host: intranet.<domain>`, internal-name wordlists | Hidden vhosts reachable via Host alone |
| 4 | Ambiguous requests: **duplicate Host** (`Host: a.com` twice) | Front-end vs back-end treat differently = desync |
| 5 | **Absolute URL** in request line (`GET https://a.com/ HTTP/1.1` + `Host: b.com`) | Which wins for routing vs app logic? |
| 6 | **Indented header**: ` Host: evil.com` (leading space) | Some stacks parse it as override |
| 7 | Overrides: `X-Forwarded-Host`, `X-Host`, `X-HTTP-Host-Override`, `Forwarded: host=` | Host-derived URLs in response/email = exploitable |
| 8 | Retry with cache-buster; if Host reflected and cached, test cacheability | Cache key excludes Host = poisoning |

Use Burp Repeater; 403/404 on evil Host = validation exists → go to bypass table.

## 2. Attack Vectors

| Vector | Mechanism | Impact |
|---|---|---|
| **Password reset poisoning → ATO** | Reset link built from Host; inject attacker host → victim's token lands on attacker site → full reset | Account takeover (HIGH/CRIT) |
| **Web cache poisoning via Host** | Host reflected in response (resources, canonical links) + cache not keyed on Host | Stored XSS/defacement at scale (CRIT) |
| **Routing-based SSRF** | Proxy routes by Host → point at `169.254.169.254`, localhost, internal vhosts, admin panels | Internal SSRF (CRIT) |
| **Auth bypass** | Access checks keyed to Host (e.g. `localhost` skips auth) | Unauthorized access (HIGH) |
| **Virtual host brute-forcing** | Enumerate internal vhosts via Host against public IP | Info disclosure, gateway to above (LOW–MED) |
| **Classic server-side vulns** | Host flows into SQLi, outbound fetches, redirects, file paths | Chained (MED–CRIT) |
| **Connection state attacks** | Keep-alive reuse: request A (valid Host) binds state, request B (malicious) inherits it | Session/routing confusion (MED–HIGH) |
| **SSRF via malformed request line** | Absolute URL / odd syntax makes intermediary route to attacker-chosen host | Internal SSRF (HIGH) |

**Reset poisoning recipe:** POST /forgot-password (own email) with `Host: attacker.com` → email link points to attacker domain = chain proven. Blocked → bypasses (§3). Max severity needs poisoned link reaching a **real victim's inbox**.

**Routing SSRF recipe:** vary Host to internal targets; confirm via differential content/latency, not status codes alone.

## 3. Payload / Bypass Table

| Technique | Payload | Bypasses |
|---|---|---|
| Duplicate Host | `Host: legit.com` + `Host: evil.com` | First/second header precedence differs per layer |
| Indented header | ` Host: evil.com` (space-prefixed) | Treated as continuation, then used by app |
| Absolute URL in request line | `GET https://legit.com/ HTTP/1.1` + `Host: evil.com` | Router uses URL, app uses Host (or reverse) |
| X-Forwarded-Host | `X-Forwarded-Host: evil.com` | App prefers XFHost over Host; often default-supported |
| Other overrides | `X-Host`, `X-HTTP-Host-Override`, `Forwarded: host=evil.com`, `X-Original-Host`, `X-Rewrite-URL` | Validation only on Host |
| Padded Host | `legit.com.evil.com`, suffix/padding variants | `endsWith`/`contains` allowlists |
| Subdomain / userinfo tricks | `legit.com@evil.com`, `legit.com:80@evil.com` | Naive regex allowlists; parser differences |
| Port injection | `Host: legit.com:8080`, `Host: evil.com:80` | Host-only checks; port-based routing |
| X-Forwarded-* chain | Host allowlisted but `X-Forwarded-Host: evil.com` honored | Proxy rewrites Host, app trusts XFHost |
| Scheme abuse | `Host: https://evil.com` | Loose `https://$host/...` link building |

## 4. By-Design Filters (SKIP)

- Vhost routing that cleanly rejects unknown Host with generic error — expected.
- CDNs rejecting non-customer Hosts — by design.
- Correct framework allowlists (Django `ALLOWED_HOSTS`, Rails): 400 on evil Host = fix working. Rejection alone ≠ bug.

## 5. Severity Guide

| Scenario | Severity |
|---|---|
| Unauthenticated Host-based cache poisoning → stored XSS on shared pages | CRITICAL |
| Routing-based SSRF to internal/metadata endpoints | CRITICAL |
| Reset poisoning with proven token capture → ATO | CRITICAL/HIGH |
| Auth bypass via Host manipulation | HIGH |
| Host reflected in emails/links to attacker, no ATO proven | MEDIUM |
| Host reflected in response only, not cacheable, no downstream use | LOW/INFO |
| Internal vhost enumeration | LOW |

## 6. Reporting Checklist

- [ ] Differential proof: legit vs injected-Host request side by side (with cache-buster).
- [ ] ATO: email/link artifact with attacker-hosted reset URL + completed reset on test account.
- [ ] Cache poisoning: poisoned response served to a second user (different session/IP), exact cache-key conditions.
- [ ] SSRF: internal response evidence (metadata body, internal-only content), redacted.
- [ ] Minimal reproducible raw request + which component reads Host (app vs proxy) if known.
- [ ] Impact tied to real user harm — "Host is user-controllable" alone is not a bug.
- [ ] Fix: server-side Host allowlist, disable override headers, avoid Host for absolute URLs.

> ⚠️ Blocked/unproven exploit chain = INFORMATIONAL per master KB rule. Never claim HIGH/CRIT from theory alone.
