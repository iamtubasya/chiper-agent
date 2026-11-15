# DOM-Based Vulnerabilities Playbook — Bug Bounty

> Source: PortSwigger Web Security Academy. DOM taint-flow source→sink analysis.

---

## Core Concept

DOM vuln = JavaScript takes **attacker-controllable value (source)** → passes to **dangerous function (sink)** → unsafe handling in client's session context. 100% client-side: server response can be clean.

---

## Sources (attacker input)

`document.URL`, `document.documentURI`, `document.URLUnencoded`, `document.baseURI`, `location` (hash/search), `document.cookie`, `document.referrer`, `window.name`, `history.pushState`/`replaceState`, `localStorage`, `sessionStorage`, `IndexedDB`, `Database`.

Additional source kinds: **reflected data**, **stored data**, **web messages**.

---

## Source → Sink Matrix

| Vulnerability | Example sink |
|---|---|
| DOM XSS | `document.write()` |
| Open redirection | `window.location` |
| Cookie manipulation | `document.cookie` |
| JavaScript injection | `eval()` |
| Document-domain manipulation | `document.domain` |
| WebSocket-URL poisoning | `WebSocket()` |
| Link manipulation | `element.src` |
| Web message manipulation | `postMessage()` |
| Ajax request-header manipulation | `setRequestHeader()` |
| Local file-path manipulation | `FileReader.readAsText()` |
| Client-side SQL injection | `ExecuteSql()` |
| HTML5-storage manipulation | `sessionStorage.setItem()` |
| Client-side XPath injection | `document.evaluate()` |
| Client-side JSON injection | `JSON.parse()` |
| DOM-data manipulation | `element.setAttribute()` |
| Denial of service | `RegExp()` |

---

## Example: DOM Open Redirect

```javascript
goto = location.hash.slice(1)
if (goto.startsWith('https:')) { location = goto; }
```
Exploit URL: `https://innocent-website.com/example#https://www.evil-user.net` → auto-redirect → phishing vector.

---

## Detection Methods

1. **URL-based DOM XSS:** unique marker in param → devtools search DOM for marker → test each location for exploitability
2. **Non-URL sources / non-HTML sinks** (`document.cookie`, `setTimeout`): no substitute for JS code review (Burp scanner does static+dynamic JS analysis)
3. **Static grep on JS bundles** for source/sink pairs

---

## DOM Clobbering

Inject HTML to manipulate DOM → change JS behavior. Most common: **anchor element overwrites global variable** used unsafely (e.g., generating dynamic script URL).

```html
<a id="config"><a id="config" name="url" href="https://evil.com">
```
If app reads `config.url` for script src → attacker-controlled URL injection.

---

## Prevention Reference (remediation section)

- Best: avoid data from untrusted source dynamically altering value transmitted to any sink
- If unavoidable: whitelist validation on client-side, or sanitize/encode — JS escaping + HTML encoding + URL encoding **in appropriate sequence** per insertion context

---

## By-Design Filters (SKIP)

- `location.hash` displayed as text, never reaches a sink
- URL param used in properly-encoded client-side rendering
- `eval()` on trusted constant (not user-controllable)
- DOM clobbering affecting layout only, no security behavior

---

## Severity Guide

| Impact | Severity |
|---|---|
| DOM XSS → session/auth token theft | HIGH |
| Open redirect → OAuth code interception | HIGH (chain) |
| Open redirect → phishing | LOW–MEDIUM |
| JS injection via `eval()` from user input | HIGH |
| Cookie manipulation → session fixation | MEDIUM–HIGH |
| alert-only on public page, no data | INFO |

---

## Reporting Checklist

- [ ] Source identified
- [ ] Sink identified
- [ ] Taint flow documented source→sink
- [ ] PoC URL / triggering steps
- [ ] Impact tied to real data/action

> ⚠️ Taint flow that never reaches a sink = not a finding. Blocked chain = INFO (master KB rule).