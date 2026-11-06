## ⛔ RULE 18: Anti-Premature-Classification (MANDATORY)

**User correction (ALSCO audit 2026-09-23): "kamu blg informational tanpa mengerahkan semua krmampuan dan variasi attack satu persatu bia multi sesion"**

```
╔══════════════════════════════════════════════════════════════╗
║  NEVER claim "informational" or "low" UNTIL:                ║
║  1. ALL 30+ vectors tested with PROPER TOOLS (not curl)     ║
║  2. ALL 16 WAF bypass techniques attempted                  ║
║  3. Origin server tested DIRECTLY (bypass CDN/WAF layer)    ║
║  4. Race condition tested with 50+ concurrent requests      ║
║  5. SSRF tested with 30+ parameter names × 25+ payloads    ║
║  6. Nuclei full scan completed                               ║
║  7. ffuf directory brute-force completed                     ║
║                                                              ║
║  "WAF blocks everything" = NOT an excuse to stop.            ║
║  Try WAF bypass → origin direct → protocol tricks.           ║
║  ONLY after ALL bypass paths exhausted = classify.           ║
╚══════════════════════════════════════════════════════════════╝
```

### WAF Bypass Checklist (16 techniques — ALL mandatory before "blocked" claim)

| # | Technique | Command Pattern |
|---|-----------|----------------|
| 1 | Direct origin IP | `curl --resolve target:443:ORIGIN_IP` |
| 2 | HTTP/2 binary framing | `curl --http2 --resolve ...` |
| 3 | Chunked transfer encoding | `curl -H "Transfer-Encoding: chunked" -X POST` |
| 4 | Large body (>8KB) | Python http.client with 16KB+ payload |
| 5 | Content-Type switch (JSON) | `curl -H "Content-Type: application/json"` |
| 6 | Multipart form data | `curl -H "Content-Type: multipart/form-data; boundary=..."` |
| 7 | HTTP method override | `curl -X PUT/PATCH/DELETE/OPTIONS/TRACE` |
| 8 | Path normalization | `/./path`, `//path`, `/../path`, `/%2e/path` |
| 9 | Backslash path (IIS) | `/path\..\secret` |
| 10 | Semicolon path (Tomcat) | `/path;jsessionid=fake` |
| 11 | Null byte injection | `/path%00.jpg`, `/path%00` |
| 12 | URL encoding bypass | `%2e%65%6e%76` for `.env` |
| 13 | Double URL encoding | `%252e%65%6e%76` |
| 14 | Case variation | `/Admin`, `/ADMIN`, `/.Env` |
| 15 | Absolute URI format | `GET http://target/path HTTP/1.1` |
| 16 | Host header manipulation | `curl -H "Host: evil.com"` |

### Origin-Level WAF Detection Pattern
> **Detailed reference:** `references/origin-level-waf-patterns.md` — Secure Gateway® WAF pattern, detection method, bypass attempts log.

```
When ALL paths return same status (302/403) regardless of content:
1. Check DNS: does target resolve to CDN IPs or direct IPs?
   - nslookup target.com 8.8.8.8
   - If IP is NOT Cloudflare (104.x/172.67.x) → direct origin found
2. If direct IP found → test with --resolve (bypass CDN)
   - curl --resolve target:443:DIRECT_IP https://target/
3. If STILL blocked → WAF is at origin level (nginx/Apache module)
4. Check Server header for WAF product name
   - "Server: Secure Gateway®" = origin-level WAF
   - "Server: cloudflare" = CDN-level WAF
5. Origin-level WAF = much harder to bypass (16 techniques above)
6. CDN-level WAF = find origin IP, bypass becomes easier
```

