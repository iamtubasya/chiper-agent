# Essential Skills Playbook — Burp Tooling, HTTP Fundamentals & Obfuscation

> Source: PortSwigger Web Security Academy — "Essential skills" (https://portswigger.net/web-security/essential-skills). Raw extract was a hub page; encoding topics + Scanner workflows are from source, tooling/HTTP fundamentals supplemented with standard operator knowledge. Apply to all other playbooks.

## 1. Quick Detection / Tooling Reference

**Burp core tools**

| Tool | Operator use |
|---|---|
| Proxy | Intercept + history triage; scope-locked. Reissue requests, inspect TLS/HTTP2 quirks. |
| Repeater | Manual probing; send to Repeater from history, vary one param at a time, diff responses. |
| Intruder | Fuzz/brute-force; Sniper (1 payload set) → Cluster bomb (multi-param combos). Throttle to avoid bans. |
| Encoder/Decoder | Smart decode any part of a request; encode payloads per context (URL, HTML, Base64, hex, octal, unicode). |
| Match & Replace (Proxy) | Silent tamper in-flight: swap `Content-Type`, add method-override headers, strip SPA noise. |
| Scanner (manual-assist) | Per source: scan a specific request; define custom insertion points; handle non-standard data structures (custom serialization, nested params). Automates injection-technique brute force so you focus on exploitation/chaining. |
| Crawl phases | Enumerate → discover content (links, JS, sitemaps) → parameter extraction. Re-crawl after auth-state changes. |

**HTTP basics**

- Request: `METHOD path HTTP/1.1` + headers + blank line + body. Query = `?k=v&k2=v`; body per `Content-Type` (`form-urlencoded`, `multipart`, `JSON`).
- Methods: GET/POST baseline; HEAD/OPTIONS recon; PUT/DELETE/PATCH when API allows; override headers (§2).
- Headers that matter: `Host`, `Cookie`, `Authorization`, `Content-Type`, `Referer`, `X-Forwarded-For`, `X-HTTP-Method-Override`.
- Cookies: `k=v; Path; Domain; Secure; HttpOnly; SameSite`. Session replay via Cookie jar; test scope/attribute handling.

## 2. Key Techniques

- **Method override:** `X-HTTP-Method-Override: PUT/DELETE` (also `X-Method-Override`, `_method` param) to slip past methods-restricted WAF rules or reach hidden endpoints.
- **Parameter tampering:** mass-assignment (`role=admin` added to POST), hidden-field edits, HTTP→param switch (`?_method=PUT`), duplicate params (`?id=1&id=2` — parser discrepancy).
- **Encoding workflow (source core):** 1) Smart-decode the observed value → identify context (URL, HTML, XML, JSON, SQL). 2) Re-encode attack payloads in the same context. 3) Exploit **decoding discrepancies** between connected systems (frontend filter vs backend parser) — the filter sees encoded garbage, backend decodes to the payload.
- **Filter bypass by obfuscation** (per source encodings): double URL encoding; case manipulation (`SeLeCt`); comment insertion (`SEL/**/ECT`); alternative encodings (HTML entities, XML, unicode/hex/octal escapes, `CHAR()`); stacked/multiple encodings when layers decode sequentially.

## 3. Payload / Obfuscation Table

| Technique | Example | Mechanism |
|---|---|---|
| URL encoding | `<` → `%3C` | Context-safe transport |
| Double URL encode | `'` → `%2527` | First decode passes filter, second yields quote |
| HTML entity | `'` → `&#39;` / `&apos;` | Decoded post-filter in HTML context |
| XML encoding | `<` → `&#x3C;` | XML parser normalization |
| Unicode escape | `\u0027` | JS/JSON-level decode |
| Hex/octal escape | `\x27` / `\047` | String-literal decode layers |
| SQL CHAR() | `CHAR(83)CHAR(69)...` = `SELECT` | Bypasses keyword regex |
| Case manipulation | `SeLeCt` | Naive case-sensitive keyword match |
| Comment insertion | `UNI/**/ON SELECT` | Splits keywords for regex, valid for SQL |
| Multiple encodings | URL+HTML stacked | Multi-layer decode chains |

## 4. By-Design Filters — SKIP

Standard framework encodings, CSP headers, CSRF tokens, SameSite cookies observed in normal responses are by-design behavior — do not report. Only filter bypasses that enable an *actual* injection matter.

## 5. Severity Guide

Methodology/tooling page — not a vulnerability class. Severity comes from what the decoded payload achieves on the real target (RCE ≫ XSS ≫ noise). An obfuscation trick with no downstream exploit = no finding.

## 6. Reporting Checklist

1. Show the working payload **and** the encoded form that traversed the filter.
2. Name the discrepancy: which component decodes what, in which order.
3. Evidence: request/response pairs proving backend execution (not just echo).
4. Demonstrate impact (the underlying vuln class dictates severity).
5. Note scope/authorization compliance and reproducer steps.

> ⚠️ Blocked/unproven exploit chain = INFORMATIONAL per master KB rule. Never claim HIGH/CRIT from theory alone.
