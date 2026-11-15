# Clickjacking Testing Playbook — Bug Bounty

> Source: PortSwigger Web Security Academy. UI redressing / frame-based attacks.

---

## Quick Detection

```bash
# Frame protection headers on sensitive pages
for ep in / /login /profile /settings /admin; do
  echo -n "$ep: "
  curl -sI "https://TARGET$ep" | grep -iE 'x-frame-options|frame-ancestors' | head -1 || echo 'NO PROTECTION'
done
```

Browser check: `document.createElement('iframe').src='https://TARGET/'` appended → loads = frameable.

---

## Core Concept

User is tricked into clicking actionable content on a HIDDEN target page overlaid via transparent iframe on a decoy page. Difference vs CSRF: requires actual user click; **CSRF tokens do NOT mitigate clickjacking** (session established on-domain inside iframe, all requests legit within hidden session).

---

## Attack Vectors

### V1 — Basic overlay
```html
<style>
#target_website { position:relative; width:128px; height:128px; opacity:0.00001; z-index:2; }
#decoy_website { position:absolute; width:300px; height:400px; z-index:1; }
</style>
<div id="decoy_website">...WIN A PRIZE button...</div>
<iframe id="target_website" src="https://vulnerable-website.com"></iframe>
```
Notes: use abs+rel positioning for cross-screen overlap; opacity near 0 (Chrome ≥76 has transparency-threshold detection, Firefox doesn't — pick value that evades).

### V2 — Prefilled form input
GET-param form prepopulation → attacker URL carries values → transparent submit overlaid:
```
https://TARGET/transfer?to=attacker&amount=10000
```

### V3 — Frame-busting bypass
- **Sandbox iframe:** `<iframe src="https://TARGET" sandbox="allow-forms">` — allow-forms/allow-scripts WITHOUT allow-top-navigation kills buster (frame can't check top window)
- Double-iframe / onBeforeUnload race: cancel navigation event, reset frame location

### V4 — Multistep clickjacking
Multiple divs/iframes for sequential actions (add-to-basket → place-order). Needs precision for stealth.

### V5 — Clickjacking + DOM XSS carrier
Combine iframe target URL with known XSS exploit → victim click executes DOM XSS. "True potency" of clickjacking.

---

## Server-Side Protections

| Header | Directive | Notes |
|---|---|---|
| X-Frame-Options | `deny` | effective |
| X-Frame-Options | `sameorigin` | effective |
| X-Frame-Options | `allow-from https://site.com` | NOT supported Chrome 76+ / Safari 12 → bypassable |
| CSP | `frame-ancestors 'none'` | recommended, ≈ deny |
| CSP | `frame-ancestors 'self'` | ≈ sameorigin |
| CSP | `frame-ancestors site.com` | whitelist |

Frame-busting scripts = client-side only, often circumventable — not real protection.

**Tool:** Burp Clickbandit — browser-based, generates interactive PoC overlay in seconds.

---

## By-Design Filters (SKIP)

- Public login page frameable (no sensitive hidden action)
- Pages with `frame-ancestors 'none'/'self'` = NOT vulnerable
- 404/error pages frameable
- Actions requiring typed input (typing can't be hidden easily)

---

## Severity Guide

| Impact | Severity |
|---|---|
| Payment / funds transfer via click | HIGH |
| Account settings / email change | MEDIUM |
| Social like/follow boost | LOW / INFO |
| Frameable but no actionable state change | INFO |
| ALLOW-FROM only protection (Chrome ignores) | MEDIUM if sensitive action exists |

---

## Reporting Checklist

- [ ] URL frameable (headers documented)
- [ ] Sensitive action identified + PoC overlay HTML
- [ ] Frame-bust bypass if applicable
- [ ] Concrete action victim performs

> ⚠️ "Page is frameable" without sensitive action = INFO.