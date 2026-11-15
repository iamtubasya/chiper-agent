# Premature-Negative & Coverage Math — why "platform matang" keeps being wrong

Operator complaint that created this note (2026-10-10), verbatim:

> *"kenapa dari setiap target yg sy kasih selalu kamu bilang platform matang dan terkunci rapi,
> tapi kemudian dari bounty hunter lain mampu menemukan celah dr low sampai high dan critical,
> apa yg salah? … apakah guard kamu yg membuat semua tidak berguna?"*

The answer was **not** guards, and **not** missing tools (nuclei +13k templates, sqlmap, dalfox,
ffuf, katana, gau, jsluice, arjun, qsreplace, ghauri, graphql-cop, interactsh, mitmproxy/proxy:8080
were all present). It was **methodology depth**. This file records the four failure modes and the fix.

## The four failure modes (all observed in the same session: city-data → ably → safeguard)

1. **Drift to polite manual `curl`** — a handful of hand-sent requests + reasoning, *not* the real
   tool battery (no `nuclei -all-templates`, no `sqlmap` per param, no `dalfox`, no `ffuf` dirbust,
   no `katana` crawl, no `arjun` param-mine, no proxy replay). ~5% of the arsenal used, then declared done.
2. **Auth-perimeter only** — tested the login/401/403/redirect edges and never touched the product's
   core (scan pipeline, SCM/webhook integrations, multi-tenant data, marketplace, MCP internals).
   Hardened targets are hard at the perimeter *by design*; the bugs are inside the product.
3. **"Not found by me" treated as "does not exist"** — the phrase "platform matang / terkunci rapi"
   is an **over-claim**. The honest sentence is *"diuji: X,Y,Z (tipis); BELUM diuji: A,B,C"*.
4. **Gate used as a brake, not a final filter** — `finding_gate`/`triage_gate` correctly drop
   info-only items, but the deeper bug was **not chaining** the real-but-low signals (internal
   issuer leak + CORS `*`) into something bigger, then stopping at "0 findings".

## Coverage math — a check that can go RED

A bare "clean" verdict is not evidence. Model each *well-executed* vector as an independent chance
`p` of surfacing a real bug; if the target is genuinely buggy, the probability that **all** N vectors
miss it is:

```
P(all negative | target buggy) = (1 - p)^N
```

With a conservative `p = 0.10` per well-executed vector:

| vectors tested (well-executed) | P(all negative) | verdict on a "clean" claim |
|---|---|---|
| 0 | 1.00 | UNSUPPORTED (nothing tested) |
| 5 | 0.59 | not evidence |
| 20 | 0.12 | borderline |
| 30 | 0.04 | credible, **if** every vector has real tool evidence on disk |

Rule of thumb: **< 20 well-executed vectors ⇒ forbidden to conclude "matang/clean".**
Run it: `python scripts/test_negative_result_audit.py <vectors_tested> [p]` (exit 1 = thin coverage).
This is the quantitative form of RULE 0c ("prove the check can fail") applied to the *conclusion*.

## The fix (enforced, not advised)

- **`deep-audit-mode.py guard <dir>`** must be GREEN before any "clean/0 findings" statement — it
  calls the real 13-check `verify-tool-usage.py`. Manual/`curl-only` is a **hard prohibition**;
  the only escape hatch is an on-disk `POLICY-FORBIDS-SCANNERS.md` quoting a program that bans scanners.
- **`deep-audit-mode.py report-guard <dir> <report>`** blocks over-claim language
  ("matang / terkunci rapi / no vulnerabilities / tidak ada temuan") that lacks a **COVERAGE** section
  (`diuji: … ; BELUM diuji: …`).
- **`deep_audit_watchdog.py`** (cron) alerts when an armed job has not passed the gate.

## Scope discipline: the product core is in scope

When a program's in-scope list names "the platform / API surface / scan pipeline / marketplace / MCP
server / CLI / IDE extension", those ARE the target. "The perimeter is clean" says nothing about them.
A free-tier account that gates data tools by plan is a **pricing wall, not a security wall** — keep
looking for the ungated product surfaces (search, integrations, webhooks, public API, SSO callback).

Proven surface-mining technique used here (reusable): pull the front-end bundles — Next.js
`/_next/static/chunks/*.js`, Vite `assets/*.js` **plus `*.js.map` `sourcesContent`** — and grep for
`/api/…`, `/auth/api/v1/…`, and **localStorage key names** (e.g. `sg:user_permissions`, `sg:user_roles`)
because those names reveal the authz model a future test must try to subvert.
