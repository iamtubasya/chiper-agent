# HTTP Request Smuggling Playbook

> Source: PortSwigger Web Security Academy (request-smuggling). Classic vectors = HTTP/1.1 CL/TE ambiguity; H2 needs downgrade.

## 1. Quick Detection

**Root cause:** FE and BE disagree where one request ends (CL vs TE, or obfuscated TE).

### Timing (1 send, look for delay)
| Probe | Request | Why delay |
|---|---|---|
| CL.TE | `POST / HTTP/1.1` + `Content-Length: 4` + `Transfer-Encoding: chunked` + body `1\r\nZ\r\nQ\r\n0\r\n\r\n` | BE reads TE → partial chunk `Q` hangs |
| TE.CL | same headers, body `0\r\n\r\nX` | BE reads CL → trailing `X` hangs |

### Differential confirm (low FP)
| Desync | Request |
|---|---|
| CL.TE | `POST /`, `Content-Length: 35`, `TE: chunked`, body `0\r\n\r\nGET /404 HTTP/1.1\r\nX:` → merges into next victim request → 404 |
| TE.CL | `POST /`, `Content-Length: 4`, `TE: chunked`, body `8\r\nX\r\n0\r\n\r\n` (trailing `\r\n\r\n` required) → poisons next request |
| TE.TE | Find TE obfuscation one server parses, other ignores → re-run CL.TE/TE.CL confirm |

**Timing vs differential:** timing = fast triage, noisy (jitter). Differential = reliable confirm; re-send normal requests after to check desync fallout.

## 2. Attack Vectors
| Vector | Mechanism | Impact |
|---|---|---|
| CL.TE | FE reads CL, BE reads TE → body remnant = start of next request | base for all below |
| TE.CL | FE reads TE, BE reads CL → smuggled prefix after CL cutoff | same |
| TE.TE | Both parse TE; obfuscate so one ignores it → reduces to CL.TE/TE.CL | same |
| Capture victim requests | Smuggle `POST /comment` w/ oversized CL; victim's next request appended to captured body → view (stored page/log); also reveals FE-rewritten headers (auth/IP) | steal cookies/tokens → session hijack |
| Reflected XSS | Smuggle request w/ XSS in params; victim's next request carries it as prefix → XSS reflects at victim | account takeover |
| On-site redirect → open redirect | Smuggle redirector request (`GET /redirect?to=/home`) w/ victim URL appended; FE sends victim off-site | phish via trusted domain |
| Cache poisoning | Smuggle malicious header/value; BE response to victim's request cached under shared key | persistent XSS for all users |
| Cache deception | Smuggle so victim's sensitive response caches under attacker-known static-looking path | victim data leak |
| Bypass FE controls/WAF | Smuggle `GET /admin` in body; FE ACL never sees path; BE executes | internal endpoints |
| CL.0 | BE ignores request body on some endpoints (0-length body assumed); any POST w/ CL desyncs next request | frontend-agnostic |
| 0.CL | Backend assumes no body on 0-length CL; smuggle via normal-looking request | CL.0 variant |
| Client-side desync | CL.0 triggered from victim's browser (fetch); victim poisons own connection | single-server sites, no Burp |
| H2 downgrade (H2.CL/H2.TE) | FE downgrades H2→HTTP/1; inject full HTTP/1 request via header CRLF; CL/TE ambiguity reborn | classic smuggling on H2 sites |
| H2-exclusive | CRLF in header names/values; ambiguous `:path`/`:host`; full request line in header | desync w/o CL/TE headers |
| Response queue poisoning | Desync → mismatched responses; steal other users' responses on shared conn | session hijack, data leak |
| Request tunnelling | Hide 2nd request inside one; HEAD (non-blind) or blind size/timing oracle leaks response + internal headers | intranet probe, header leak |
| Pause-based desync | Half-send, pause mid-body; timeout → remainder treated as new request (server- or client-side) | works where probes fail |

## 3. Payloads / Bypasses
| Purpose | Template |
|---|---|
| CL.TE detect | `POST / HTTP/1.1\r\nHost: t\r\nContent-Length: 4\r\nTransfer-Encoding: chunked\r\n\r\n1\r\nZ\r\nQ\r\n0\r\n\r\n` |
| TE.CL detect | same, body `0\r\n\r\nX` |
| Prefix smuggle | `Content-Length: N` = bytes of `\r\n\r\nGET /admin HTTP/1.1\r\nHost: t\r\n\r\n` |
| TE: 0 value | `Transfer-Encoding: 0` / `Transfer-Encoding: x` |
| TE: space before colon | `Transfer-Encoding : chunked` |
| TE: tab in value | `Transfer-Encoding:\tchunked` |
| TE: leading space | ` Transfer-Encoding: chunked` |
| TE: duplicate | `Transfer-Encoding: chunked\r\nTransfer-Encoding: x` |
| TE: newline fold | `X: X[\n]Transfer-Encoding: chunked` |
| TE: split header | `Transfer-Encoding\r\n: chunked` |
| TE: bad value | `Transfer-Encoding: xchunked` |
| TE: mixed case | `tRansfer-Encoding: chunked` |

Notes: Burp Repeater → uncheck Update Content-Length; end chunked bodies with `0\r\n\r\n`; retry (desync may hit other conns); H2 toggle in Inspector.

## 4. By-Design Filters (SKIP)
- HTTP/2 end-to-end, no downgrade = inherently immune.
- Backend closes connection per request (no reuse) — nothing in flight to desync.
- Active probing corrupts shared connections: confirm scope first, avoid high-volume prod probes.

## 5. Severity Guide
| Finding | Severity |
|---|---|
| Victim request capture (cookies/session tokens) | Critical |
| Cache poisoning affecting other users | High–Critical |
| H2.CL / H2.TE downgrade desync | Critical |
| FE security control / ACL bypass | High–Critical |
| XSS delivered to victims via smuggling | High |
| Open redirect via redirector hijack | Medium–High |
| Client-side desync (browser PoC) | Medium–High |
| Timing-only, no differential proof | Informational |

## 6. Reporting Checklist
- [ ] Desync type named (CL.TE/TE.CL/TE.TE/CL.0/H2.x) + FE & BE parsing behavior identified.
- [ ] Differential proof (not timing): captured request, poisoned response, or 404-on-next-request.
- [ ] Byte-exact raw request/response transcripts.
- [ ] End-to-end impact shown (cookie stolen, cache poisoned, admin reached) — not just desync.
- [ ] Collateral damage noted + connections reset.
- [ ] Minimal reliable repro; note hit rate/retries.
- [ ] Fix advice: H2 end-to-end, no downgrade, reject ambiguous requests, never assume no body, close conn on parse errors.

> ⚠️ Blocked/unproven exploit chain = INFORMATIONAL per master KB rule. Never claim HIGH/CRIT from theory alone.
