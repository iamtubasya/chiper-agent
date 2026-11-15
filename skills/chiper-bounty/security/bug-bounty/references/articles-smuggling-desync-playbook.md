# HTTP Smuggling & Desync — Research Articles Compendium

Source: PortSwigger Research 2015-2026, group=smuggling-desync (13 articles). Consolidated hunting/proof/reporting reference.

## Article Map

| Year | Article | Core contribution |
|---|---|---|
| 2015 | Request Smuggling Research | Hub; revived forgotten 2004 technique for modern bounty work |
| 2019 | Desync Reborn | CL.TE/TE.CL classes, timeout detection, socket-poisoning exploit playbook |
| 2019 | What Happened Next | New TE triggers (\r, \x00chunked); self-only-smuggling troubleshooting |
| 2019 | Breaking the Chains | Tool update: auto-PoC confirm, ATS gap, `identity,chunked` |
| 2022 | Browser-Powered Desync | CSD, CL.0/H2.0, pause-based desync, connection-state attacks, worm |
| 2022 | H3 Connection Contamination | Coalescing + first-request routing = cross-site desync threat |
| 2022 | Header Injection → RQP | Upgrade header injection to desync via response queue poisoning |
| 2022 | Research Into Profit | CL.0 hunting strategy; CL obfuscation permutations (`+7`, `0, 7`, `7.0`) |
| 2025 | Pipelining vs Smuggling | False-positive triage; connection-locked smuggling proof paths |
| 2024 | TRACE Desync | TRACE loopback intel; HEAD+TRACE response-smuggling gadget |
| 2026 | CRLF-Powered Desync | nginx $uri splitting → RQP; worms; IP-locked; HTTPOnly theft |
| 2021 | HTTP/2 Sequel | H2.CL/H2.TE downgrade desyncs; request tunnelling; HEAD technique; Jira RQP |
| 2025 | HTTP/1 Must Die | V-H/H-V discrepancy scans; 0.CL deadlock + /con gadget; Expect desyncs |

## Key Techniques

- **CL.TE / TE.CL / TE.TE**: obfuscate TE (`TE : chunked`, `\x00chunked`, `cow, chunked`, `identity, chunked`) or CL (`CL: 0, 7`, `+7`, `7.0`, tab) so front-end/back-end disagree on body length.
- **CL.0 / H2.0**: backend ignores CL on unexpected POSTs (static files, redirects, /%2e%2e, IIS /con). Browser-issuable → client-side desync (CSD) poisons victim connection pool.
- **H2.CL / H2.TE**: downgrade smuggling — inject \n, colon, space via H2 header names, values, pseudo-headers, or request line; forged CL or smuggled TE survives downgrade.
- **0.CL**: CL hidden on continuation line → upstream deadlock; break with early-response gadget (nginx, IIS /con, redirects); convert to CL.0 via double-desync.
- **Expect**: `Expect: 100-continue` triggers 0.CL/CL.0 desyncs (T-Mobile, GitLab, Netlify, Akamai), memory disclosure, second header block defeating header removal.
- **CSD gadgets**: stacked HEAD (headers become body), host-header redirect, client-side cache poisoning (top-level nav beats partitioning); worm = XSS + self-replicating fetch().
- **CRLF-worm / RQP**: nginx `proxy_pass $uri` decodes %0d%0a → request splitting → response queue poisoning; also via upstream headers (X-Original-Url) and cookie insertion points.
- **TRACE & misc**: TRACE loopback reveals internal headers + H2→H1 downgrade proof; HEAD+TRACE assembles HTML body → cache-poisoned XSS. First-request routing/validation → Host attacks, intranet access, H2/H3 coalescing contamination. Pause-based: mid-request pause past server timeout, MITM-deliverable.
- **Detection → proof**: timeout probes (hang backend, zero user impact), V-H/H-V masked-header differential scans, 417/Expect probes, Mystery-400 (/con) sweep. Confirm = socket poisoning visibly alters a near-identical victim request. Then prove impact: cache poison, header capture, front-end bypass, RQP.

## Payload / Bypass Table

| Technique | Trigger | Proof-of-exploit |
|---|---|---|
| CL.TE | `TE : chunked` + short CL; hang probe | Victim request gets prefix prepended → 404/302 |
| TE.CL | `0\r\n\r\n<full request>` in body | Smuggled request executes; extra response seen |
| CL.0 | POST to CL-ignoring endpoint | `GET /404` in body runs as new request |
| H2.TE | \n in H2 header value → TE on downgrade | Redirected JS includes; OAuth code via Referer |
| H2.CL | Forged CL header on H2 request | Prefix redirect / cache poison |
| 0.CL | Hidden CL + early-response gadget | Double-desync converts to CL.0 prefix |
| CSD | fetch() POST, body ignored | Same connection-ID second request shows injected response |
| RQP | Double-CRLF request splitting | Harvest other users' authenticated responses |
| TRACE gadget | Smuggled HEAD then TRACE | Reflected headers = HTML body → cache-poisoned XSS |
| Tunnelling | Desync on no-reuse frontend | HEAD over-read leaks smuggled response/headers |

## By-Design / SKIP Filters

- Skip: responses differing only because you reused your own client connection (pipelining/keep-alive) without frontend desync evidence.
- Skip: WAF-blocked obfuscated TE/CL with no working variant; single-IP-only effects with no exploitation path.
- Skip: TRACE enabled but not reflected into an exploitable context; "by design" banner/header disclosures with no security impact.
- Skip: theoretical parser quirks (e.g. \n\n handling) with no desync chain; Expect oddities that are only DoS.
- Skip: pure denial of service; self-DoS; h2c upgrade on non-standard configs without frontend evidence.

## Severity Guide

- Timing-only detection, no differential/visible-response proof = INFO.
- Pipelining/keep-alive artifact (only works with connection reuse, no nested HTTP/1-in-H2 response) = INFO.
- Blocked or unproven chain = INFORMATIONAL; never claim higher without executed PoC impact.
- Desync confirmed, self-impact only (Mystery 400, unexpected 404) = LOW.
- Cache poisoning, internal-header leak, front-end bypass, request capture = HIGH.
- Cross-user account takeover, credential/token theft, RQP serving other users' data, persistent site takeover = CRITICAL.

## Reporting Checklist

- Reproduce desync with differential proof (two distinct responses to identical requests), reuse disabled.
- Confirm backend socket poisoning: victim request response visibly altered; note connection ID.
- Map trigger conditions: method, path, headers, cache presence, backend routing, IP affinity.
- Demonstrate an impact gadget: cache poison, header capture, redirect, RQP, tunnelling leak.
- Attach raw request/response pairs (hex for binary H2) and tool versions (Request Smuggler, Turbo Intruder).
- Minimize collateral: timeout-based detection, cachebusters on victim requests, off-peak regions.
- Recommend fix: HTTP/2 end-to-end, reject ambiguous requests, normalize at frontend, drop invalid header fields.

> Master KB: agent-kb-bounty-exploit-master.md authority > SKILL.md. Unproven/blocked chain = INFORMATIONAL.
