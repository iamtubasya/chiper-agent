# PoC Technique Atlas — Index

Method-level techniques extracted from the local PoC corpus (2,223 GitHub PoC repos,
2,024 after malware/scam filtering + dedup). Read ONE class file at the phase you need.
This is a **method shelf**, not a payload dump — no exploit bodies, no malware.

| Class | What it covers | Techniques | File |
|---|---|---:|---|
| Other / Unclassified | Techniques not matched to a primary class — skim for patterns. | 904 | `references/other.md` |
| RCE & Command Injection | Run code/commands via injection, unsafe eval, template, or gadget chain. | 412 | `references/rce.md` |
| IDOR / BOLA / Access Control | Missing/weak object & function-level authorization. | 89 | `references/idor-bola.md` |
| SQL Injection | Extract/modify DB data via query injection; incl. blind, UNION, second-order. | 85 | `references/sqli.md` |
| Crypto Flaws | Weak algos, padding oracles, key recovery, IV/nonce misuse. | 76 | `references/crypto.md` |
| Auth Bypass / AuthN flaws | Bypass login, MFA, JWT, OAuth, SAML, session trust. | 74 | `references/auth-bypass.md` |
| Cross-Site Scripting | Execute JS in victim context: reflected, stored, DOM, mXSS, CSP bypass. | 67 | `references/xss.md` |
| Information Disclosure | Leak source/keys/config via debug, VCS, backups, verbose errors. | 48 | `references/info-disclosure.md` |
| LFI / Path Traversal | Read/include local files, escape upload dirs, wrapper abuse. | 51 | `references/lfi.md` |
| Memory Corruption | Stack/heap overflow, UAF — binary targets / native parsers. | 36 | `references/buffer-overflow.md` |
| Misc Web | CORS, clickjacking, websocket, cache, parser/WAF quirks. | 28 | `references/misc-web.md` |
| File Upload | Extension/MIME/content bypass, polyglot, archive, path escape. | 25 | `references/file-upload.md` |
| Insecure Deserialization | Gadget chains (Java/PHP/Python/Node/.NET) to RCE. | 23 | `references/deserialization.md` |
| SSRF | Make the server issue requests; hit metadata, loopback, internal services, DNS-gap bypasses. | 20 | `references/ssrf.md` |
| DoS (report-only) | ReDoS, billion laughs, algorithmic complexity — DO NOT run against live. | 15 | `references/dos.md` |
| Cloud / Metadata | IMDS, bucket, IAM, container escape, SSRF-to-cloud. | 15 | `references/cloud.md` |
| SSTI / CSTI | Template injection to RCE or client-side code exec. | 7 | `references/ssti.md` |
| Race Conditions / TOCTOU | Concurrent abuse of check-then-act: limit/coupon/stock/double-spend. | 6 | `references/race-condition.md` |
| NoSQL Injection | Mongo/operator injection, blind, auth bypass. | 6 | `references/nosql.md` |
| CSRF | State-changing request without/weak token, SameSite bypass. | 6 | `references/csrf.md` |
| XXE Injection | XML external entity: file read, SSRF, OOB exfil, blind XXE. | 5 | `references/xxe.md` |
| Supply Chain | Dependency confusion, malicious package, build pipeline. | 4 | `references/supply-chain.md` |
| CRLF / Request Smuggling | Header injection, response splitting, HTTP desync. | 4 | `references/crlf-injection.md` |
| LLM / AI Attacks | Prompt injection, jailbreak, agent/tool abuse, RAG & training-data issues. | 3 | `references/llm-ai.md` |
| GraphQL | Introspection, batching, alias/IDOR, injection, DoS. | 3 | `references/graphql.md` |
| Prototype Pollution | Client/server JS proto pollution to XSS or RCE. | 2 | `references/prototype-pollution.md` |
| Open Redirect | Unvalidated redirect (chain fodder for OAuth/SSRF). | 2 | `references/open-redirect.md` |
| LDAP / XPath Injection | Filter/query injection in auth and search. | 2 | `references/ldap.md` |

**Total techniques: 1953** across 28 classes.

